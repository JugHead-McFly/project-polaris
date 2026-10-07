using System;
using System.ComponentModel;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Xml;
using Microsoft.Win32.SafeHandles;

namespace PolarisStandalone
{
    public sealed class CleanupRequest
    {
        public string SourceRoot, NasRoot, StateRoot, RelativePath, ExpectedSha256, AcceptedReceiptSha256, AcceptedReceiptPath;
        public string CopyDestination; // Archive planning only; never used by source deletion.
        public long ExpectedLength;
        public string ReceiptSourceRoot;
        public DeviceBinding Binding;
    }
    public sealed class CleanupAssessment
    {
        public bool Ready;
        public string Message, ApprovalPhrase;
    }
    public sealed class CleanupResult
    {
        public string Status, Message, IntentPath, ReceiptPath;
    }
    public static class CleanupCore
    {
#if CLEANUP_OFFLINE_FIXTURE
        public static Action<string> Boundary;
#endif
        private sealed class Context
        {
            public CleanupRequest Request;
            public string Source, Nas, State, SourceFile, NasFile, Route, Intent, Approval, ReceiptSource, ReceiptSourceFile;
        }
        private sealed class Verified
        {
            public string Hash, Identity;
            public long NasTicks;
        }

        // Policy caller must explicitly enable cleanup before requesting approval.
        // This derives an exact request binding, without another content hash pass.
        public static string ApprovalFor(CleanupRequest request) { return Validate(request).Approval; }

        public static CleanupResult InspectCompleted(CleanupRequest request)
        {
            try
            {
                Context c = Validate(request, true);
                using (FileStream stateLock = Lock(c))
                {
                    AcceptedReceipt(c);
                    string completed = Path.Combine(c.State, "cleanup-deleted-" + c.Route + ".xml");
                    Chain(completed);
                    bool intent = PathExists(c.Intent), receipt = PathExists(completed);
                    if (Directory.GetFileSystemEntries(c.State, "cleanup-uncertain-" + c.Route + "-*.xml").Length != 0) throw new IOException("Recorded cleanup uncertainty requires review; no automatic completion inference.");
                    if (!intent && !receipt) return new CleanupResult { Status = "NotCleared" };
                    if (!intent || !receipt) throw new IOException("Unresolved cleanup reservation blocks this route.");
                    ValidateCompletedRecord(c.Intent, c, "INTENT"); ValidateCompletedRecord(completed, c, "DELETED");
                    if (PathExists(c.SourceFile)) throw new IOException("Consumed cleanup route has a source file; no retry permitted.");
                    if (c.Request.Binding != null) c.Request.Binding.ValidateCurrent();
                    return new CleanupResult { Status = "AlreadyCleared", IntentPath = c.Intent, ReceiptPath = completed, Message = "Exact consumed cleanup records valid and current source absent." };
                }
            }
            catch (Exception ex) { return new CleanupResult { Status = "Held", Message = ex.GetType().Name + ": " + ex.Message }; }
        }

        private static void ValidateCompletedRecord(string path, Context c, string operation)
        {
            Chain(path);
            var doc = new XmlDocument { XmlResolver = null };
            using (var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read))
            using (var reader = XmlReader.Create(stream, new XmlReaderSettings { DtdProcessing = DtdProcessing.Prohibit, XmlResolver = null, MaxCharactersInDocument = 65536 })) doc.Load(reader);
            XmlElement e = doc.DocumentElement;
            if (e == null || e.Name != "PolarisCleanupReceipt" || e.GetAttribute("version") != "1" || e.Attributes.Count != 1 || e.ChildNodes.Count != 14) throw new InvalidDataException("Consumed cleanup record shape invalid.");
            var names = new System.Collections.Generic.HashSet<string>(StringComparer.Ordinal);
            foreach (XmlNode n in e.ChildNodes) if (n.NodeType != XmlNodeType.Element || n.Attributes.Count != 0 || n.ChildNodes.Count > 1 || (n.ChildNodes.Count == 1 && n.FirstChild.NodeType != XmlNodeType.Text) || !names.Add(n.Name)) throw new InvalidDataException("Ambiguous consumed cleanup record.");
            DateTime stamp;
            if (Value(e,"Operation") != operation || Value(e,"Route") != c.Route || !Same(Value(e,"Source"),c.ReceiptSourceFile) || !Same(Value(e,"Nas"),c.NasFile) || Value(e,"Relative") != c.Request.RelativePath ||
                Value(e,"Length") != c.Request.ExpectedLength.ToString(System.Globalization.CultureInfo.InvariantCulture) || Value(e,"Sha256") != c.Request.ExpectedSha256 ||
                !Same(Value(e,"AcceptedReceiptPath"),c.Request.AcceptedReceiptPath) || Value(e,"AcceptedReceiptSha256") != c.Request.AcceptedReceiptSha256 || Value(e,"Approval") != c.Approval || Value(e,"NasHandlesClosed") != "true" ||
                !DateTime.TryParse(Value(e,"Utc"), System.Globalization.CultureInfo.InvariantCulture, System.Globalization.DateTimeStyles.RoundtripKind, out stamp)) throw new InvalidDataException("Consumed cleanup record does not bind this exact accepted route.");
            string identity = Value(e,"NativeSourceIdentity"); Value(e,"Message");
            if (operation == "INTENT") { if (identity.Length != 25 || identity[8] != ':') throw new InvalidDataException("Consumed intent identity invalid."); foreach(char ch in identity.Replace(":", "")) if (!(ch >= '0' && ch <= '9') && !(ch >= 'a' && ch <= 'f')) throw new InvalidDataException("Consumed intent identity invalid."); if (c.Request.Binding != null && identity.Substring(0,8) != c.Request.Binding.VolumeSerial.ToString("x8")) throw new InvalidDataException("Consumed intent belongs to a different enrolled volume serial."); }
            else if (identity != "") throw new InvalidDataException("Consumed terminal identity invalid.");
        }

        public static CleanupAssessment AssessOne(CleanupRequest request, CancellationToken cancellation)
        {
            try
            {
                Context c = Validate(request);
                using (FileStream stateLock = Lock(c))
                {
                    Unconsumed(c); AcceptedReceipt(c); cancellation.ThrowIfCancellationRequested();
                    using (SafeFileHandle handle = OpenSource(c.SourceFile, false))
                    using (var source = new FileStream(handle, FileAccess.Read, 1024 * 1024, false))
                        Verify(c, handle, source, cancellation);
                }
                return new CleanupAssessment { Ready = true, Message = "Fresh source/NAS hashes match accepted copy; assessment deleted nothing.", ApprovalPhrase = c.Approval };
            }
            catch (Exception ex) { return new CleanupAssessment { Ready = false, Message = ex.GetType().Name + ": " + ex.Message }; }
        }

        public static CleanupResult DeleteOne(CleanupRequest request, string exactApprovalPhrase, CancellationToken cancellation)
        {
            Context c = null; bool reserved = false, dispositionSet = false;
            try
            {
                c = Validate(request);
                if (!String.Equals(exactApprovalPhrase, c.Approval, StringComparison.Ordinal)) throw new InvalidOperationException("Exact one-file source-deletion approval required.");
                using (FileStream stateLock = Lock(c))
                {
                    Unconsumed(c); AcceptedReceipt(c); cancellation.ThrowIfCancellationRequested();
                    using (SafeFileHandle handle = OpenSource(c.SourceFile, true))
                    using (var source = new FileStream(handle, FileAccess.Read, 1024 * 1024, false))
                    {
                        Verified proof = Verify(c, handle, source, cancellation);
                        // Permanent reservation is published only after fresh proof,
                        // while the exact source handle is still exclusively held.
                        NewRecord(c.Intent, c, "INTENT", proof, "Reserved for exactly one approved source-handle disposition; no automatic retry.");
                        reserved = true; Hook("IntentWritten"); cancellation.ThrowIfCancellationRequested();
                        // Verify has closed every NAS data handle. The source
                        // remains exclusive; no NAS delete/write access is requested.
                        Hook("NasClosed");
                        Chain(c.SourceFile); Chain(c.NasFile); NoActive(c); ExactSourceHandle(handle, c.SourceFile);
                        NasMetadata(c, proof);
                        AcceptedReceipt(c); cancellation.ThrowIfCancellationRequested();
                        Hook("BeforeDisposition"); cancellation.ThrowIfCancellationRequested();
                        NoActive(c); ExactSourceHandle(handle, c.SourceFile); AssertBinding(c, handle); NasMetadata(c, proof);
                        var disposition = new Disposition { DeleteFile = true };
                        if (!SetFileInformationByHandle(handle, 4, ref disposition, (uint)Marshal.SizeOf(typeof(Disposition))))
                            throw Native("Source disposition failed; no path-based fallback");
                        dispositionSet = true;
                        Hook("DispositionSet");
                    }
                    // Disposition deletes on close of the held source handle.
                    // A replacement at that path is never deleted by this code.
                    Hook("SourceClosed");
                    if (PathExists(c.SourceFile)) throw new IOException("Source path still exists after handle close; outcome uncertain.");
                    string receipt = Path.Combine(c.State, "cleanup-deleted-" + c.Route + ".xml");
                    NewRecord(receipt, c, "DELETED", null, "Exact verified source handle disposed and closed; source path absent. No directories or NAS objects deleted.");
                    return new CleanupResult { Status = "Deleted", Message = "One exact source file deleted; NAS untouched.", IntentPath = c.Intent, ReceiptPath = receipt };
                }
            }
            catch (Exception ex)
            {
                string resultPath = null;
                if (reserved && c != null)
                {
                    resultPath = Path.Combine(c.State, "cleanup-uncertain-" + c.Route + "-" + Guid.NewGuid().ToString("N") + ".xml");
                    try { NewRecord(resultPath, c, "UNCERTAIN", null, (dispositionSet ? "Disposition requested; " : "No successful disposition observed; ") + ex.GetType().Name + ": " + ex.Message); }
                    catch (Exception journalError) { return new CleanupResult { Status = "Uncertain", Message = "Permanent intent retained; uncertain receipt write failed: " + journalError.Message + "; original: " + ex.Message, IntentPath = c.Intent }; }
                }
                return new CleanupResult { Status = reserved ? "Uncertain" : (ex is OperationCanceledException ? "Cancelled" : "Held"), Message = ex.GetType().Name + ": " + ex.Message, IntentPath = c == null ? null : c.Intent, ReceiptPath = resultPath };
            }
        }

        private static Context Validate(CleanupRequest request)
        { return Validate(request, false); }

        private static Context Validate(CleanupRequest request, bool completedHistory)
        {
            if (request == null) throw new ArgumentNullException("request");
            // Snapshot caller-owned fields before approval/proof; callbacks cannot
            // redirect an operation by mutating the original request object.
            var r = new CleanupRequest { SourceRoot = Full(request.SourceRoot), NasRoot = Full(request.NasRoot), StateRoot = Full(request.StateRoot), RelativePath = request.RelativePath,
                ExpectedLength = request.ExpectedLength, ExpectedSha256 = request.ExpectedSha256, AcceptedReceiptSha256 = request.AcceptedReceiptSha256, AcceptedReceiptPath = Full(request.AcceptedReceiptPath), Binding = request.Binding,
                ReceiptSourceRoot = request.ReceiptSourceRoot == null ? Full(request.SourceRoot) : Full(request.ReceiptSourceRoot) };
            if (r.Binding != null)
            {
                r.Binding.ValidateCurrent();
                if (!Same(r.SourceRoot, Full(r.Binding.CurrentRoot)) || !Same(r.ReceiptSourceRoot, Full(r.Binding.ReceiptRoot)) || !Same(r.NasRoot, Full(r.Binding.NasRoot)) || !Same(r.StateRoot, Full(r.Binding.StateRoot))) throw new ArgumentException("Cleanup request differs from immutable device binding.");
            }
            else if (!Same(r.ReceiptSourceRoot, r.SourceRoot)) throw new ArgumentException("Receipt root remapping requires a device binding.");
            Relative(r.RelativePath); HexPin(r.ExpectedSha256); HexPin(r.AcceptedReceiptSha256);
            if (r.ExpectedLength <= 0) throw new ArgumentException("Zero/negative-length files are never cleanup candidates.");
            Separate(r.SourceRoot, r.NasRoot); Separate(r.SourceRoot, r.StateRoot); Separate(r.NasRoot, r.StateRoot);
            if (r.SourceRoot.StartsWith(@"\\", StringComparison.Ordinal) || r.StateRoot.StartsWith(@"\\", StringComparison.Ordinal)) throw new ArgumentException("Source/state UNC paths are prohibited.");
            if (new DriveInfo(Path.GetPathRoot(r.StateRoot)).DriveType != DriveType.Fixed) throw new ArgumentException("State must be fixed local, not mapped/removable.");
#if CLEANUP_OFFLINE_FIXTURE
            string fixture = FixtureParent(r.SourceRoot);
            if (!Same(fixture, FixtureParent(r.NasRoot)) || !Same(fixture, FixtureParent(r.StateRoot))) throw new ArgumentException("Fixture roots must share one unique TEMP subtree.");
            foreach (string p in new string[] { r.SourceRoot, r.NasRoot, r.StateRoot }) if (new DriveInfo(Path.GetPathRoot(p)).DriveType != DriveType.Fixed) throw new ArgumentException("Fixture roots must be fixed local.");
#else
            if ((r.Binding == null && !Same(r.SourceRoot, @"I:\")) || !Same(r.ReceiptSourceRoot, @"I:\") || !Same(r.NasRoot, @"\\Synology_NAS\Astrophotography\Polaris_Inbox") || !Same(r.StateRoot, @"G:\Polaris_Workspace\StandaloneHistory")) throw new ArgumentException("Production cleanup requires exact approved device binding, logical DWARF root, NAS inbox, and local state journal.");
            DriveInfo drive = new DriveInfo(Path.GetPathRoot(r.SourceRoot));
            if (!drive.IsReady || drive.DriveType != DriveType.Removable || !Same(r.SourceRoot, drive.RootDirectory.FullName)) throw new IOException("DWARF removable whole-root admission failed.");
#endif
            foreach (string p in new string[] { r.SourceRoot, r.NasRoot, r.StateRoot }) { Chain(p); if (!Directory.Exists(p)) throw new DirectoryNotFoundException("Required root unavailable: " + p); }
            string[] parts = r.RelativePath.Split(new char[] { '\\', '/' });
            if (parts.Length < 2 || !(Same(parts[0], "Astronomy") || Same(parts[0], "Burst") || Same(parts[0], "Normal_Photos") || Same(parts[0], "Videos"))) throw new ArgumentException("Only files below the four admitted source categories may be deleted.");
            if (Temporary(parts[parts.Length - 1])) throw new ArgumentException("Temporary files cannot be cleanup candidates.");
            var c = new Context { Request = r, Source = r.SourceRoot, Nas = r.NasRoot, State = r.StateRoot, SourceFile = Under(r.SourceRoot, r.RelativePath), NasFile = Under(r.NasRoot, r.RelativePath), ReceiptSource = r.ReceiptSourceRoot, ReceiptSourceFile = Under(r.ReceiptSourceRoot,r.RelativePath) };
            c.Route = HashText(c.ReceiptSource.ToUpperInvariant() + "\n" + c.Nas.ToUpperInvariant() + "\n" + r.RelativePath.Replace('/', '\\').ToUpperInvariant());
            c.Intent = Path.Combine(c.State, "cleanup-intent-" + c.Route + ".xml");
            string approvalBinding = HashText(c.ReceiptSource + "\n" + c.Nas + "\n" + c.State + "\n" + r.RelativePath + "\n" + r.ExpectedLength + "\n" + r.ExpectedSha256 + "\n" + r.AcceptedReceiptPath + "\n" + r.AcceptedReceiptSha256);
            c.Approval = "DELETE ONE DWARF SOURCE FILE " + approvalBinding;
            if (!r.AcceptedReceiptPath.StartsWith(c.State.TrimEnd('\\') + "\\", StringComparison.OrdinalIgnoreCase) || !Path.GetFileName(r.AcceptedReceiptPath).StartsWith("receipt-", StringComparison.Ordinal) || !r.AcceptedReceiptPath.EndsWith(".xml", StringComparison.OrdinalIgnoreCase)) throw new ArgumentException("Accepted copied receipt must be inside the existing local state journal.");
            Chain(c.SourceFile); Chain(c.NasFile); Chain(r.AcceptedReceiptPath); NoActive(c, completedHistory);
            return c;
        }

        private static FileStream Lock(Context c)
        { string p = Path.Combine(c.State, "import.lock"); Chain(p); return new FileStream(p, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None); }
        private static void Unconsumed(Context c)
        {
            Chain(c.Intent);
            if (PathExists(c.Intent) || PathExists(Path.Combine(c.State, "cleanup-deleted-" + c.Route + ".xml"))) throw new IOException("Cleanup route already reserved/consumed; no automatic retry or reset.");
        }
        private static void AcceptedReceipt(Context c)
        {
            string path = c.Request.AcceptedReceiptPath; Chain(path);
            using (var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read))
            {
                if (HashStream(stream, CancellationToken.None) != c.Request.AcceptedReceiptSha256) throw new IOException("Accepted copy receipt bytes changed.");
                stream.Position = 0;
                var settings = new XmlReaderSettings { DtdProcessing = DtdProcessing.Prohibit, XmlResolver = null, MaxCharactersInDocument = 65536 };
                var doc = new XmlDocument { XmlResolver = null };
                using (XmlReader reader = XmlReader.Create(stream, settings)) doc.Load(reader);
                XmlElement e = doc.DocumentElement;
                if (e == null || e.Name != "PolarisCopyReceipt" || e.GetAttribute("version") != "1" || e.ChildNodes.Count != 11) throw new InvalidDataException("Accepted receipt shape invalid.");
                var names = new System.Collections.Generic.HashSet<string>(StringComparer.Ordinal);
                foreach (XmlNode child in e.ChildNodes) if (child.NodeType != XmlNodeType.Element || !names.Add(child.Name)) throw new InvalidDataException("Duplicate or ambiguous receipt fields.");
                if (Value(e, "Operation") != "confirmed" || !Same(Value(e, "Source"), c.ReceiptSourceFile) || !Same(Value(e, "Destination"), c.NasFile) ||
                    Value(e, "Relative") != c.Request.RelativePath || Value(e, "Hash") != c.Request.ExpectedSha256 || Int64.Parse(Value(e, "Length"), System.Globalization.CultureInfo.InvariantCulture) != c.Request.ExpectedLength)
                    throw new InvalidDataException("Accepted confirmed copy receipt does not bind this exact route/hash/length.");
            }
        }
        private static string Value(XmlElement e, string field) { XmlNode n = e.SelectSingleNode(field); if (n == null) throw new InvalidDataException("Missing receipt field."); return n.InnerText; }

        private static void NasMetadata(Context c, Verified proof)
        {
            Chain(c.NasFile);
            var info = new FileInfo(c.NasFile);
            if (!info.Exists || info.Length != c.Request.ExpectedLength || info.LastWriteTimeUtc.Ticks != proof.NasTicks)
                throw new IOException("NAS metadata changed after its fresh verified read closed.");
        }

        private static Verified Verify(Context c, SafeFileHandle handle, FileStream source, CancellationToken cancellation)
        {
            NoActive(c); AssertBinding(c, handle); string identity = ExactSourceHandle(handle, c.SourceFile);
            if (source.Length != c.Request.ExpectedLength) throw new IOException("Source length differs from accepted copy.");
            source.Position = 0; string sourceHash = HashStream(source, cancellation);
            if (sourceHash != c.Request.ExpectedSha256) throw new IOException("Fresh source SHA256 differs from accepted copy.");
            Chain(c.NasFile); long nasTicks;
            using (var nas = new FileStream(c.NasFile, FileMode.Open, FileAccess.Read, FileShare.Read, 1024 * 1024, FileOptions.SequentialScan))
            {
                if (nas.Length != c.Request.ExpectedLength || HashStream(nas, cancellation) != sourceHash) throw new IOException("Fresh NAS length/SHA256 equality failed.");
                Chain(c.NasFile); nasTicks = File.GetLastWriteTimeUtc(c.NasFile).Ticks;
            }
            // At return, every NAS data handle owned by the core is closed.
            NoActive(c); ExactSourceHandle(handle, c.SourceFile);
            return new Verified { Hash = sourceHash, Identity = identity, NasTicks = nasTicks };
        }

        private static SafeFileHandle OpenSource(string path, bool delete)
        {
            SafeFileHandle handle = CreateFile(path, 0x80000000U | (delete ? 0x00010000U : 0U), 0, IntPtr.Zero, 3, 0x00200000U | 0x08000000U, IntPtr.Zero);
            if (handle.IsInvalid) { int error = Marshal.GetLastWin32Error(); handle.Dispose(); throw new Win32Exception(error, "Exclusive source handle open failed."); }
            return handle;
        }
        private static void AssertBinding(Context c, SafeFileHandle handle)
        { if (c.Request.Binding != null) { c.Request.Binding.ValidateCurrent(); c.Request.Binding.AssertHandle(handle); } }
        private static string ExactSourceHandle(SafeFileHandle handle, string expected)
        {
            if (GetFileType(handle) != 1) throw new IOException("Source handle is not a disk file.");
            NativeInfo info;
            if (!GetFileInformationByHandle(handle, out info)) throw Native("Source handle identity unsupported");
            if ((info.Attributes & (0x10U | 0x400U)) != 0) throw new IOException("Directory/reparse source handle denied.");
            var path = new StringBuilder(32768);
            uint length = GetFinalPathNameByHandle(handle, path, (uint)path.Capacity, 0);
            if (length == 0 || length >= path.Capacity) throw Native("Final source-handle path unavailable");
            string final = path.ToString();
            if (final.StartsWith(@"\\?\UNC\", StringComparison.OrdinalIgnoreCase)) throw new IOException("Source native final path is remote.");
            if (!final.StartsWith(@"\\?\", StringComparison.Ordinal)) throw new IOException("Unsupported native final-path format.");
            final = final.Substring(4);
            if (!Same(final, expected)) throw new IOException("Opened source handle differs from the exact approved source path.");
            return info.VolumeSerial.ToString("x8") + ":" + info.IndexHigh.ToString("x8") + info.IndexLow.ToString("x8");
        }
        private static Win32Exception Native(string message) { return new Win32Exception(Marshal.GetLastWin32Error(), message); }

        private static void NewRecord(string path, Context c, string operation, Verified proof, string message)
        {
            Chain(path);
            using (var stream = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.None))
            {
                using (XmlWriter w = XmlWriter.Create(stream, new XmlWriterSettings { Encoding = new UTF8Encoding(false), CloseOutput = false }))
                {
                    w.WriteStartElement("PolarisCleanupReceipt"); w.WriteAttributeString("version", "1");
                    Field(w, "Operation", operation); Field(w, "Route", c.Route); Field(w, "Source", c.ReceiptSourceFile); Field(w, "Nas", c.NasFile); Field(w, "Relative", c.Request.RelativePath);
                    Field(w, "Length", c.Request.ExpectedLength.ToString(System.Globalization.CultureInfo.InvariantCulture)); Field(w, "Sha256", c.Request.ExpectedSha256);
                    Field(w, "AcceptedReceiptPath", c.Request.AcceptedReceiptPath); Field(w, "AcceptedReceiptSha256", c.Request.AcceptedReceiptSha256); Field(w, "Approval", c.Approval);
                    Field(w, "NativeSourceIdentity", proof == null ? "" : proof.Identity); Field(w, "NasHandlesClosed", "true"); Field(w, "Message", message); Field(w, "Utc", DateTime.UtcNow.ToString("o"));
                    w.WriteEndElement(); w.Flush();
                }
                stream.Flush(true);
            }
        }
        private static void Field(XmlWriter w, string name, string value) { w.WriteElementString(name, value ?? ""); }
        private static void Hook(string name)
        {
#if CLEANUP_OFFLINE_FIXTURE
            Action<string> callback = Boundary; if (callback != null) callback(name);
#endif
        }
        private static string HashStream(Stream stream, CancellationToken cancellation)
        {
            using (var sha = SHA256.Create())
            {
                byte[] buffer = new byte[1024 * 1024]; int n;
                while ((n = stream.Read(buffer, 0, buffer.Length)) != 0) { cancellation.ThrowIfCancellationRequested(); sha.TransformBlock(buffer, 0, n, buffer, 0); }
                sha.TransformFinalBlock(new byte[0], 0, 0); return BitConverter.ToString(sha.Hash).Replace("-", "").ToLowerInvariant();
            }
        }
        private static string HashText(string value) { using (var s = new MemoryStream(Encoding.UTF8.GetBytes(value))) return HashStream(s, CancellationToken.None); }
        private static void HexPin(string value) { if (value == null || value.Length != 64) throw new ArgumentException("Expected SHA256 required."); foreach (char ch in value) if (!(ch >= '0' && ch <= '9') && !(ch >= 'a' && ch <= 'f')) throw new ArgumentException("Lowercase SHA256 required."); }
        private static string Full(string path)
        {
            if (String.IsNullOrWhiteSpace(path) || !Path.IsPathRooted(path) || path.StartsWith(@"\\?\") || path.StartsWith(@"\\.\")) throw new ArgumentException("Ordinary absolute paths required.");
            string root = Path.GetPathRoot(path); if (root.Length < 3) throw new ArgumentException("Drive-relative paths denied.");
            string tail = path.Substring(root.Length).Trim('\\', '/'); if (tail.Length > 0) Relative(tail);
            string full = Path.GetFullPath(path); root = Path.GetPathRoot(full);
            if (root.StartsWith(@"\\")) Relative(root.Substring(2).TrimEnd('\\', '/'));
            return full.Length == root.Length ? full : full.TrimEnd('\\', '/');
        }
        private static void Relative(string path)
        {
            if (String.IsNullOrEmpty(path) || Path.IsPathRooted(path)) throw new ArgumentException("Ordinary relative file path required.");
            foreach (string part in path.Split(new char[] { '\\', '/' }))
            {
                if (part.Length == 0 || part == "." || part == ".." || part.EndsWith(".") || part.EndsWith(" ") || part.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0) throw new ArgumentException("Illegal/ambiguous path component.");
                string stem = part.Split('.')[0].ToUpperInvariant(); if (stem == "CON" || stem == "PRN" || stem == "AUX" || stem == "NUL" || (stem.Length == 4 && (stem.StartsWith("COM") || stem.StartsWith("LPT")) && stem[3] >= '1' && stem[3] <= '9')) throw new ArgumentException("Device filename denied.");
            }
        }
        private static bool Same(string a, string b) { return String.Equals(a, b, StringComparison.OrdinalIgnoreCase); }
        private static void Separate(string a, string b) { if (Same(a, b) || a.StartsWith(b.TrimEnd('\\') + "\\", StringComparison.OrdinalIgnoreCase) || b.StartsWith(a.TrimEnd('\\') + "\\", StringComparison.OrdinalIgnoreCase)) throw new ArgumentException("Source/NAS/state roots must be separate."); }
        private static string Under(string root, string rel) { Relative(rel); string p = Path.GetFullPath(Path.Combine(root, rel)); if (!p.StartsWith(root.TrimEnd('\\') + "\\", StringComparison.OrdinalIgnoreCase)) throw new ArgumentException("Route escaped root."); return p; }
        private static bool PathExists(string path) { try { File.GetAttributes(path); return true; } catch (FileNotFoundException) { return false; } catch (DirectoryNotFoundException) { return false; } }
        private static void Chain(string path)
        {
            string p = Path.GetFullPath(path);
            while (!String.IsNullOrEmpty(p))
            {
                try { if ((File.GetAttributes(p) & FileAttributes.ReparsePoint) != 0) throw new IOException("Reparse ancestor denied: " + p); }
                catch (FileNotFoundException) { } catch (DirectoryNotFoundException) { }
                p = Path.GetDirectoryName(p.TrimEnd('\\'));
            }
        }
        private static void NoActive(Context c, bool completedHistory = false)
        {
            string p = Path.GetDirectoryName(c.SourceFile);
            while (p != null)
            {
                Chain(p);
                try
                {
                    foreach (string item in Directory.GetFileSystemEntries(p))
                        if (Same(Path.GetFileName(item), ".active")) throw new IOException("Active source marker blocks cleanup.");
                }
                catch (DirectoryNotFoundException)
                {
                    // Only completed-history inspection may traverse absent child
                    // directories. Still inspect every surviving ancestor and require
                    // the bound source root. Receipt validation and source-absence
                    // proof remain mandatory before reporting AlreadyCleared.
                    if (!completedHistory || Same(p.TrimEnd('\\'), c.Source.TrimEnd('\\'))) throw;
                }
                if (Same(p.TrimEnd('\\'), c.Source.TrimEnd('\\'))) return;
                if (!p.StartsWith(c.Source.TrimEnd('\\') + "\\", StringComparison.OrdinalIgnoreCase)) throw new IOException("Active-marker route escaped source.");
                p = Path.GetDirectoryName(p);
            }
            throw new IOException("Source ancestor admission incomplete.");
        }
        private static bool Temporary(string name) { string e = Path.GetExtension(name); return name.StartsWith("Temporary_", StringComparison.OrdinalIgnoreCase) || Same(e, ".tmp") || Same(e, ".part") || Same(e, ".partial") || Same(e, ".crdownload"); }
#if CLEANUP_OFFLINE_FIXTURE
        private static string FixtureParent(string root)
        {
            string temp = Path.GetFullPath(Path.GetTempPath()).TrimEnd('\\') + "\\";
            if (!root.StartsWith(temp, StringComparison.OrdinalIgnoreCase)) throw new ArgumentException("Fixture root must be strictly inside TEMP.");
            string tail = root.Substring(temp.Length); int separator = tail.IndexOf('\\'); if (separator < 0) throw new ArgumentException("Fixture roots need separate descendants.");
            string name = tail.Substring(0, separator); const string prefix = "PolarisCleanupFixture-";
            Guid id; if (!name.StartsWith(prefix, StringComparison.Ordinal) || name.Length != prefix.Length + 32 || !Guid.TryParseExact(name.Substring(prefix.Length), "N", out id)) throw new ArgumentException("Unique cleanup TEMP fixture prefix required.");
            return temp + name;
        }
#endif
        [StructLayout(LayoutKind.Sequential)] private struct Disposition { [MarshalAs(UnmanagedType.U1)] public bool DeleteFile; }
        [StructLayout(LayoutKind.Sequential)] private struct NativeTime { public uint Low, High; }
        [StructLayout(LayoutKind.Sequential)] private struct NativeInfo { public uint Attributes; public NativeTime Creation, Access, Write; public uint VolumeSerial, SizeHigh, SizeLow, Links, IndexHigh, IndexLow; }
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true, EntryPoint = "CreateFileW")] private static extern SafeFileHandle CreateFile(string name, uint access, uint share, IntPtr security, uint creation, uint flags, IntPtr template);
        [DllImport("kernel32.dll", SetLastError = true)] [return: MarshalAs(UnmanagedType.Bool)] private static extern bool SetFileInformationByHandle(SafeFileHandle handle, int infoClass, ref Disposition info, uint size);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern uint GetFileType(SafeFileHandle handle);
        [DllImport("kernel32.dll", SetLastError = true)] [return: MarshalAs(UnmanagedType.Bool)] private static extern bool GetFileInformationByHandle(SafeFileHandle handle, out NativeInfo info);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true, EntryPoint = "GetFinalPathNameByHandleW")] private static extern uint GetFinalPathNameByHandle(SafeFileHandle handle, StringBuilder path, uint size, uint flags);
    }
}
