using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Xml;

namespace PolarisStandalone
{
    public sealed class Progress
    {
        public string Message { get; set; }
        public int FilesDone { get; set; }
        public int Total { get; set; }
        public int TotalFiles { get { return Total; } }
    }
    public sealed class Summary
    {
        public int Copied { get; set; }
        public int Reused { get; set; }
        public int Held { get; set; }
        // Held includes these routine source-preserving deferrals. Only
        // Held - Deferred is non-routine/blocking; receipts still say hold.
        public int Deferred { get; set; }
        public int Total { get; set; }
        public bool Cancelled { get; set; }
    }

    // Copy-only personal inbox engine. No process execution, source writes,
    // destination overwrite/delete/rename, cleanup, or background activation.
    public static class Importer
    {
        private sealed class RoutineDeferredException : IOException
        {
            public RoutineDeferredException(string message) : base(message) { }
        }
        private sealed class Receipt
        {
            public string Operation, Id, Key, Source, Destination, Relative, Hash, Message;
            public long Length, SourceTicks, DestinationTicks;
        }
        private sealed class Slot
        {
            public readonly Dictionary<string, Receipt> Intents = new Dictionary<string, Receipt>(StringComparer.Ordinal);
            public readonly HashSet<string> ConfirmedIds = new HashSet<string>(StringComparer.Ordinal);
            public Receipt Confirmed;
            public bool Incomplete { get { return Intents.Count != ConfirmedIds.Count; } }
        }
        private sealed class Item { public string Relative, Problem; }

        public static Summary Run(string source, string destination, string state, CancellationToken cancellation, Action<Progress> progress)
        { return RunInternal(source, destination, state, null, cancellation, progress, null); }

        public static Summary RunBound(DeviceBinding binding, CancellationToken cancellation, Action<Progress> progress)
        {
            if (binding == null) throw new ArgumentNullException("binding");
            binding.ValidateCurrent();
            return RunInternal(binding.CurrentRoot, binding.NasRoot, binding.StateRoot, null, cancellation, progress, binding);
        }

        public static Summary RunOne(string source, string destination, string state, string relative, CancellationToken cancellation, Action<Progress> progress)
        {
            LegalRelative(relative);
            return RunInternal(source, destination, state, relative, cancellation, progress, null);
        }

        private static Summary RunInternal(string source, string destination, string state, string selected, CancellationToken cancellation, Action<Progress> progress, DeviceBinding binding)
        {
            source = Full(source); destination = Full(destination); state = Full(state);
            // Logical receipt identity is string-only: never probe the old drive letter.
            string receiptRoot = binding == null ? source : Full(binding.ReceiptRoot);
            Separate(source, destination); Separate(source, state); Separate(destination, state);
            if (state.StartsWith(@"\\", StringComparison.Ordinal) || new DriveInfo(Path.GetPathRoot(state)).DriveType != DriveType.Fixed)
                throw new ArgumentException("State receipts must be on a fixed local drive.");
            Chain(source); Chain(destination); Chain(state);
            if (!Directory.Exists(source)) throw new DirectoryNotFoundException("Source root is unavailable.");
            if (File.Exists(destination) || File.Exists(state)) throw new ArgumentException("Destination and state must be directories.");
            var result = new Summary();
            if (cancellation.IsCancellationRequested) { result.Cancelled = true; return result; }
            Directory.CreateDirectory(state); Chain(state);
            string lockPath = Path.Combine(state, "import.lock"); Chain(lockPath);
            using (var journalLock = new FileStream(lockPath, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None))
            {
                Dictionary<string, Slot> slots = ReadJournal(state);
                var items = new List<Item>();
                if (selected == null) Inventory(source, "", items, cancellation);
                else items.Add(new Item { Relative = selected });
                result.Total = items.Count;
                if (cancellation.IsCancellationRequested) { result.Cancelled = true; return result; }
                for (int index = 0; index < items.Count; index++)
                {
                    if (cancellation.IsCancellationRequested) { result.Cancelled = true; break; }
                    Item item = items[index];
                    string src = null, receiptSource = null, dst = null, key = null;
                    Receipt intent = null;
                    string calibrationHash = null;
                    try
                    {
                        if (binding != null) binding.ValidateCurrent();
                        if (item.Problem != null) throw new IOException(item.Problem);
                        LegalRelative(item.Relative);
                        src = Under(source, item.Relative); dst = Under(destination, item.Relative);
                        receiptSource = Under(receiptRoot, item.Relative);
                        key = TextHash(receiptRoot.ToUpperInvariant() + "\n" + destination.ToUpperInvariant() + "\n" + item.Relative.ToUpperInvariant());
                        Chain(src); Chain(dst); NoActiveAncestor(source, src);
                        if (CalibrationVersions.IsCalibration(item.Relative))
                        {
                            Slot original; slots.TryGetValue(key, out original);
                            if (original != null && original.Incomplete) throw new IOException("Unconfirmed original calibration intent.");
                            if (Directory.Exists(dst)) throw new IOException("Original calibration destination is a directory.");
                            if (File.Exists(dst))
                            {
                                Receipt old = original == null ? null : original.Confirmed;
                                if (old == null || !SamePath(old.Source, receiptSource) || !SamePath(old.Destination, dst)) throw new IOException("Unreceipted original calibration destination.");
                                using (var oldInput = new FileStream(dst, FileMode.Open, FileAccess.Read, FileShare.Read))
                                    if (oldInput.Length != old.Length || StreamHash(oldInput, cancellation) != old.Hash) throw new IOException("Original calibration backup changed; retained for review.");
                            }
                            else if (original != null) throw new IOException("Original calibration backup missing.");
                            using (var hashInput = new FileStream(src, FileMode.Open, FileAccess.Read, FileShare.None))
                            {
                                if (binding != null) { binding.ValidateCurrent(); binding.AssertHandle(hashInput.SafeFileHandle); }
                                calibrationHash = StreamHash(hashInput, cancellation);
                            }
                            if (original == null || original.Confirmed == null || original.Confirmed.Hash != calibrationHash)
                            {
                                dst = CalibrationVersions.Destination(destination, item.Relative, calibrationHash);
                                key = CalibrationVersions.Key(receiptRoot, destination, item.Relative, calibrationHash);
                            }
                            Chain(dst);
                        }
                        Slot slot; slots.TryGetValue(key, out slot);
                        if (slot != null && slot.Incomplete) throw new IOException("Unconfirmed prior intent: retained destination must not be retried or overwritten.");
                        if (Directory.Exists(dst)) throw new IOException("Destination file path is already a directory.");
                        if (File.Exists(dst))
                        {
                            Receipt confirmed = slot == null ? null : slot.Confirmed;
                            if (confirmed == null || !SamePath(confirmed.Source, receiptSource) || !SamePath(confirmed.Destination, dst))
                                throw new IOException("Existing destination has no exact confirmed receipt; no overwrite allowed.");
                            // Metadata reuse is deliberately not fresh content verification.
                            using (var boundInput = binding == null ? null : new FileStream(src, FileMode.Open, FileAccess.Read, FileShare.None))
                            {
                            if (binding != null) { binding.ValidateCurrent(); binding.AssertHandle(boundInput.SafeFileHandle); }
                            var si = new FileInfo(src); var di = new FileInfo(dst);
                            if (!si.Exists || !di.Exists || si.Length != confirmed.Length || di.Length != confirmed.Length ||
                                (calibrationHash == null && si.LastWriteTimeUtc.Ticks != confirmed.SourceTicks) || di.LastWriteTimeUtc.Ticks != confirmed.DestinationTicks)
                                throw new IOException("Previously confirmed metadata changed; existing destination held.");
                            if (calibrationHash != null)
                            {
                                if (confirmed.Hash != calibrationHash) throw new IOException("Calibration version receipt hash mismatch.");
                                using (var v = new FileStream(dst, FileMode.Open, FileAccess.Read, FileShare.Read))
                                    if (StreamHash(v, cancellation) != calibrationHash) throw new IOException("Calibration version content changed.");
                            }
                            WriteReceipt(state, new Receipt { Operation = "reuse", Id = Guid.NewGuid().ToString("N"), Key = key,
                                Source = receiptSource, Destination = dst, Relative = item.Relative, Length = confirmed.Length,
                                SourceTicks = confirmed.SourceTicks, DestinationTicks = confirmed.DestinationTicks,
                                Hash = confirmed.Hash, Message = "ReusedMetadata: prior confirmation only; no fresh content hashes." }, binding);
                            }
                            result.Reused++;
                            Notify(progress, "ReusedMetadata (not freshly verified): " + item.Relative, index + 1, result.Total);
                            continue;
                        }
                        if (slot != null) throw new IOException("Previously recorded destination is missing; no automatic repair or retry.");
                        using (var input = new FileStream(src, FileMode.Open, FileAccess.Read, FileShare.None, 1024 * 1024, FileOptions.SequentialScan))
                        {
                            if (binding != null) { binding.ValidateCurrent(); binding.AssertHandle(input.SafeFileHandle); }
                            Chain(src); Chain(dst); NoActiveAncestor(source, src);
                            long length = input.Length, ticks = File.GetLastWriteTimeUtc(src).Ticks;
                            // Recheck before classifying routine work. An existing
                            // destination, unsafe source, or unresolved receipt is
                            // never converted into a nonblocking deferral.
                            if (File.Exists(dst) || Directory.Exists(dst)) throw new IOException("Destination appeared before source admission; no overwrite allowed.");
                            if (TemporaryName(Path.GetFileName(src)))
                                throw new RoutineDeferredException("Recognized temporary source filename retained; not copied or verified.");
                            if (length == 0 && RootSpotlightFile(item.Relative))
                                throw new RoutineDeferredException("Ordinary zero-length root .Spotlight-V100 housekeeping retained; not copied or verified.");
                            if (length == 0 && NativeThumbnail(item.Relative))
                                throw new RoutineDeferredException("Empty preview thumbnail retained on DWARF; no image data to copy. Raw exposures are handled separately.");
                            if (length == 0) throw new IOException("Zero-length source held as incomplete.");
                            intent = new Receipt { Operation = "intent", Id = Guid.NewGuid().ToString("N"), Key = key,
                                Source = receiptSource, Destination = dst, Relative = item.Relative, Length = length, SourceTicks = ticks,
                                Message = "Reserved before create; interruption permanently holds this route." };
                            WriteReceipt(state, intent, binding);
                            Notify(progress, "Reserved: " + item.Relative, index, result.Total);
                            cancellation.ThrowIfCancellationRequested();
                            if (binding != null) { binding.ValidateCurrent(); binding.AssertHandle(input.SafeFileHandle); }
                            NoActiveAncestor(source, src);
                            string parent = Path.GetDirectoryName(dst); Chain(parent); Directory.CreateDirectory(parent); Chain(parent);
                            string copiedHash;
                            using (var sha = SHA256.Create())
                            using (var output = new FileStream(dst, FileMode.CreateNew, FileAccess.Write, FileShare.None, 1024 * 1024, FileOptions.SequentialScan))
                            {
                                byte[] buffer = new byte[1024 * 1024]; long copied = 0; int count;
                                while ((count = input.Read(buffer, 0, buffer.Length)) != 0)
                                {
                                    cancellation.ThrowIfCancellationRequested();
                                    output.Write(buffer, 0, count); sha.TransformBlock(buffer, 0, count, buffer, 0); copied += count;
                                    Notify(progress, "Copying: " + item.Relative, index, result.Total);
                                }
                                sha.TransformFinalBlock(new byte[0], 0, 0); copiedHash = Hex(sha.Hash);
                                if (calibrationHash != null && copiedHash != calibrationHash) throw new IOException("Calibration changed after version selection; reserved destination held.");
                                if (copied != length || input.Length != length || File.GetLastWriteTimeUtc(src).Ticks != ticks)
                                    throw new IOException("Source changed while copying.");
                                output.Flush(true);
                            }
                            cancellation.ThrowIfCancellationRequested(); Chain(dst);
                            string destinationHash;
                            using (var verify = new FileStream(dst, FileMode.Open, FileAccess.Read, FileShare.Read, 1024 * 1024, FileOptions.SequentialScan))
                            {
                                if (verify.Length != length) throw new IOException("Destination length mismatch.");
                                destinationHash = StreamHash(verify, cancellation);
                                if (!String.Equals(copiedHash, destinationHash, StringComparison.Ordinal)) throw new IOException("Destination hash mismatch.");
                                if (input.Length != length || File.GetLastWriteTimeUtc(src).Ticks != ticks) throw new IOException("Source changed before confirmation.");
                                Chain(src); Chain(dst); NoActiveAncestor(source, src);
                                if (binding != null) { binding.ValidateCurrent(); binding.AssertHandle(input.SafeFileHandle); }
                                var confirmed = new Receipt { Operation = "confirmed", Id = intent.Id, Key = key, Source = receiptSource,
                                    Destination = dst, Relative = item.Relative, Length = length, SourceTicks = ticks,
                                    DestinationTicks = File.GetLastWriteTimeUtc(dst).Ticks, Hash = copiedHash,
                                    Message = "Fresh copy stream hash equals reopened destination hash; source read held exclusive." };
                                WriteReceipt(state, confirmed, binding);
                            }
                            result.Copied++;
                            Notify(progress, "Copied and freshly verified: " + item.Relative, index + 1, result.Total);
                        }
                    }
                    catch (OperationCanceledException)
                    {
                        result.Cancelled = true;
                        if (intent != null) { Hold(state, item.Relative, receiptSource, dst, key, "Cancelled after reservation; partial destination retained.", binding); result.Held++; }
                        Notify(progress, "Cancelled; any reserved/partial file remains held.", index, result.Total);
                        break;
                    }
                    catch (RoutineDeferredException ex)
                    {
                        Hold(state, item.Relative, receiptSource, dst, key, "RoutineDeferred: " + ex.Message, binding);
                        result.Held++;
                        result.Deferred++;
                        Notify(progress, "DEFERRED (still held): " + item.Relative + " — " + ex.Message, index + 1, result.Total);
                    }
                    catch (Exception ex)
                    {
                        // Journal failure is not silently accepted. If even this durable
                        // HOLD fails, stop the run; an earlier intent remains unretryable.
                        Hold(state, item.Relative, receiptSource, dst, key, ex.GetType().Name + ": " + ex.Message, binding);
                        result.Held++;
                        Notify(progress, "HOLD: " + item.Relative + " — " + ex.Message, index + 1, result.Total);
                    }
                }
            }
            return result;
        }

        private static void Inventory(string root, string relative, List<Item> items, CancellationToken cancellation)
        {
            if (cancellation.IsCancellationRequested) return;
            try
            {
                string directory = relative.Length == 0 ? root : Under(root, relative);
                Chain(directory);
                string[] files = Directory.GetFiles(directory); string[] directories = Directory.GetDirectories(directory);
                foreach (string file in files)
                    if (String.Equals(Path.GetFileName(file), ".active", StringComparison.OrdinalIgnoreCase))
                    { items.Add(new Item { Relative = relative, Problem = "Active marker blocks this entire source subtree." }); return; }
                foreach (string child in directories)
                    if (String.Equals(Path.GetFileName(child), ".active", StringComparison.OrdinalIgnoreCase))
                    { items.Add(new Item { Relative = relative, Problem = "Active directory marker blocks this entire source subtree." }); return; }
                Array.Sort(files, StringComparer.OrdinalIgnoreCase); Array.Sort(directories, StringComparer.OrdinalIgnoreCase);
                foreach (string file in files)
                {
                    string child = relative.Length == 0 ? Path.GetFileName(file) : Path.Combine(relative, Path.GetFileName(file));
                    try { LegalRelative(child); Chain(file); items.Add(new Item { Relative = child }); }
                    catch (Exception ex) { items.Add(new Item { Relative = child, Problem = ex.Message }); }
                }
                foreach (string child in directories)
                {
                    string rel = relative.Length == 0 ? Path.GetFileName(child) : Path.Combine(relative, Path.GetFileName(child));
                    LegalRelative(rel); Inventory(root, rel, items, cancellation);
                }
            }
            catch (Exception ex) { items.Add(new Item { Relative = relative, Problem = "Enumeration unavailable: " + ex.Message }); }
        }

        private static Dictionary<string, Slot> ReadJournal(string state)
        {
            var slots = new Dictionary<string, Slot>(StringComparer.Ordinal);
            var confirmations = new List<Receipt>();
            foreach (string file in Directory.GetFiles(state, "receipt-*.xml"))
            {
                Chain(file); Receipt r = ReadReceipt(file);
                if (r.Operation == "hold" || r.Operation == "reuse") continue;
                if (r.Operation != "intent" && r.Operation != "confirmed") throw new InvalidDataException("Unknown receipt operation.");
                if (String.IsNullOrEmpty(r.Key) || r.Key.Length != 64 || r.Id.Length != 32 || r.Length <= 0) throw new InvalidDataException("Invalid journal identity.");
                LegalRelative(r.Relative);
                Slot slot; if (!slots.TryGetValue(r.Key, out slot)) { slot = new Slot(); slots.Add(r.Key, slot); }
                if (r.Operation == "intent") { if (slot.Intents.ContainsKey(r.Id)) throw new InvalidDataException("Duplicate intent."); slot.Intents.Add(r.Id, r); }
                else confirmations.Add(r);
            }
            foreach (Receipt r in confirmations)
            {
                Slot slot = slots[r.Key]; Receipt intent;
                if (!slot.Intents.TryGetValue(r.Id, out intent) || !SamePath(intent.Source, r.Source) || !SamePath(intent.Destination, r.Destination) ||
                    intent.Relative != r.Relative || intent.Length != r.Length || intent.SourceTicks != r.SourceTicks ||
                    String.IsNullOrEmpty(r.Hash) || r.Hash.Length != 64 || r.DestinationTicks <= 0 || !slot.ConfirmedIds.Add(r.Id) || slot.Confirmed != null)
                    throw new InvalidDataException("Unmatched or ambiguous confirmation; state held.");
                slot.Confirmed = r;
            }
            return slots;
        }

        private static void Hold(string state, string relative, string source, string destination, string key, string message, DeviceBinding binding)
        { WriteReceipt(state, new Receipt { Operation = "hold", Id = Guid.NewGuid().ToString("N"), Relative = relative, Source = source, Destination = destination, Key = key, Message = message }, binding); }

        private static void WriteReceipt(string state, Receipt r, DeviceBinding binding)
        {
            if (binding != null) r.Message += " Source is logical receipt namespace " + binding.ReceiptRoot + "; observed physical root " + binding.CurrentRoot + ".";
            Chain(state);
            string path = Path.Combine(state, "receipt-" + Guid.NewGuid().ToString("N") + ".xml");
            using (var stream = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.None))
            {
                var settings = new XmlWriterSettings { Encoding = new UTF8Encoding(false), Indent = false, CloseOutput = false, CheckCharacters = true };
                using (XmlWriter writer = XmlWriter.Create(stream, settings))
                {
                    writer.WriteStartElement("PolarisCopyReceipt"); writer.WriteAttributeString("version", "1");
                    Element(writer, "Operation", r.Operation); Element(writer, "Id", r.Id); Element(writer, "Key", r.Key);
                    Element(writer, "Source", r.Source); Element(writer, "Destination", r.Destination); Element(writer, "Relative", r.Relative);
                    Element(writer, "Length", r.Length.ToString(System.Globalization.CultureInfo.InvariantCulture));
                    Element(writer, "SourceTicks", r.SourceTicks.ToString(System.Globalization.CultureInfo.InvariantCulture));
                    Element(writer, "DestinationTicks", r.DestinationTicks.ToString(System.Globalization.CultureInfo.InvariantCulture));
                    Element(writer, "Hash", r.Hash); Element(writer, "Message", r.Message);
                    writer.WriteEndElement(); writer.Flush();
                }
                stream.Flush(true);
            }
        }
        private static void Element(XmlWriter writer, string name, string value) { writer.WriteElementString(name, value ?? ""); }
        private static Receipt ReadReceipt(string path)
        {
            var settings = new XmlReaderSettings { DtdProcessing = DtdProcessing.Prohibit, XmlResolver = null, MaxCharactersInDocument = 65536 };
            var doc = new XmlDocument { XmlResolver = null };
            using (var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read))
            using (XmlReader reader = XmlReader.Create(stream, settings)) doc.Load(reader);
            XmlElement e = doc.DocumentElement;
            if (e == null || e.Name != "PolarisCopyReceipt" || e.GetAttribute("version") != "1" || e.ChildNodes.Count != 11)
                throw new InvalidDataException("Malformed receipt; journal held.");
            var names = new HashSet<string>(StringComparer.Ordinal);
            foreach (XmlNode child in e.ChildNodes) if (!names.Add(child.Name) || child.NodeType != XmlNodeType.Element) throw new InvalidDataException("Ambiguous receipt.");
            return new Receipt { Operation = Value(e, "Operation"), Id = Value(e, "Id"), Key = Value(e, "Key"), Source = Value(e, "Source"),
                Destination = Value(e, "Destination"), Relative = Value(e, "Relative"), Length = Number(e, "Length"), SourceTicks = Number(e, "SourceTicks"),
                DestinationTicks = Number(e, "DestinationTicks"), Hash = Value(e, "Hash"), Message = Value(e, "Message") };
        }
        private static string Value(XmlElement e, string name) { XmlNode n = e.SelectSingleNode(name); if (n == null) throw new InvalidDataException("Missing receipt field."); return n.InnerText; }
        private static long Number(XmlElement e, string name) { return Int64.Parse(Value(e, name), System.Globalization.CultureInfo.InvariantCulture); }

        private static string Full(string path)
        {
            if (String.IsNullOrWhiteSpace(path) || !Path.IsPathRooted(path) || path.StartsWith(@"\\?\", StringComparison.Ordinal) || path.StartsWith(@"\\.\", StringComparison.Ordinal))
                throw new ArgumentException("Use an explicit ordinary absolute root.");
            string root = Path.GetPathRoot(path);
            if (root.Length < 3 || (root.Length == 2 && root[1] == ':')) throw new ArgumentException("Drive-relative paths are not allowed.");
            string rawTail = path.Substring(root.Length).Trim('\\', '/');
            if (rawTail.Length > 0) LegalRelative(rawTail);
            string full = Path.GetFullPath(path); root = Path.GetPathRoot(full);
            string fullTail = full.Substring(root.Length).Trim('\\', '/');
            if (fullTail.Length > 0) LegalRelative(fullTail);
            if (root.StartsWith(@"\\", StringComparison.Ordinal)) LegalRelative(root.Substring(2).TrimEnd('\\', '/'));
            return full.Length == root.Length ? root : full.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        }
        private static bool SamePath(string a, string b) { return String.Equals(a, b, StringComparison.OrdinalIgnoreCase); }
        private static void Separate(string a, string b)
        {
            if (SamePath(a, b) || a.StartsWith(b.TrimEnd('\\') + "\\", StringComparison.OrdinalIgnoreCase) || b.StartsWith(a.TrimEnd('\\') + "\\", StringComparison.OrdinalIgnoreCase))
                throw new ArgumentException("Source, destination, and state roots must not overlap.");
        }
        private static string Under(string root, string relative)
        {
            LegalRelative(relative); string full = Path.GetFullPath(Path.Combine(root, relative));
            if (!full.StartsWith(root.TrimEnd('\\') + "\\", StringComparison.OrdinalIgnoreCase)) throw new ArgumentException("Relative path escapes root.");
            return full;
        }
        private static void LegalRelative(string relative)
        {
            if (String.IsNullOrEmpty(relative) || Path.IsPathRooted(relative)) throw new ArgumentException("Invalid relative path.");
            foreach (string part in relative.Split(new char[] { '\\', '/' }))
            {
                if (part.Length == 0 || part == "." || part == ".." || part.EndsWith(".", StringComparison.Ordinal) || part.EndsWith(" ", StringComparison.Ordinal) || part.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0)
                    throw new ArgumentException("Illegal path component.");
                string stem = part.Split('.')[0].ToUpperInvariant();
                if (stem == "CON" || stem == "PRN" || stem == "AUX" || stem == "NUL" || (stem.Length == 4 && (stem.StartsWith("COM") || stem.StartsWith("LPT")) && stem[3] >= '1' && stem[3] <= '9'))
                    throw new ArgumentException("Reserved device name.");
            }
        }
        private static void Chain(string path)
        {
            string current = Path.GetFullPath(path);
            while (!String.IsNullOrEmpty(current))
            {
                try { if ((File.GetAttributes(current) & FileAttributes.ReparsePoint) != 0) throw new IOException("Reparse path rejected: " + current); }
                catch (FileNotFoundException) { }
                catch (DirectoryNotFoundException) { }
                string parent = Path.GetDirectoryName(current.TrimEnd('\\'));
                if (String.Equals(parent, current, StringComparison.OrdinalIgnoreCase)) break;
                current = parent;
            }
        }
        private static void NoActiveAncestor(string root, string file)
        {
            string directory = Path.GetDirectoryName(file);
            while (directory != null)
            {
                Chain(directory);
                foreach (string candidate in Directory.GetFileSystemEntries(directory))
                    if (String.Equals(Path.GetFileName(candidate), ".active", StringComparison.OrdinalIgnoreCase))
                        throw new IOException("Active source ancestor marker held.");
                if (SamePath(directory.TrimEnd('\\'), root.TrimEnd('\\'))) break;
                if (!directory.StartsWith(root.TrimEnd('\\') + "\\", StringComparison.OrdinalIgnoreCase)) throw new IOException("Source ancestor escaped root.");
                directory = Path.GetDirectoryName(directory);
            }
        }
        private static bool TemporaryName(string name)
        {
            string ext = Path.GetExtension(name);
            return name.StartsWith("Temporary_", StringComparison.OrdinalIgnoreCase) || ext.Equals(".tmp", StringComparison.OrdinalIgnoreCase) || ext.Equals(".part", StringComparison.OrdinalIgnoreCase) || ext.Equals(".partial", StringComparison.OrdinalIgnoreCase) || ext.Equals(".crdownload", StringComparison.OrdinalIgnoreCase);
        }
        private static bool RootSpotlightFile(string relative)
        {
            string[] parts = relative.Split(new char[] { '\\', '/' });
            return parts.Length > 1 && String.Equals(parts[0], ".Spotlight-V100", StringComparison.OrdinalIgnoreCase);
        }
        private static bool NativeThumbnail(string relative)
        {
            string[] parts = relative.Split(new char[] { '\\', '/' });
            if (parts.Length != 4 || parts[0] != "Astronomy" || parts[2] != "Thumbnail") return false;
            if (!System.Text.RegularExpressions.Regex.IsMatch(parts[1], @"^DWARF_RAW_(TELE|WIDE)_.+_EXP_[^_]+_GAIN_[^_]+_\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}-\d{3}$")) return false;
            string extension = Path.GetExtension(parts[3]);
            return extension.Equals(".jpg", StringComparison.OrdinalIgnoreCase) || extension.Equals(".jpeg", StringComparison.OrdinalIgnoreCase) || extension.Equals(".png", StringComparison.OrdinalIgnoreCase);
        }
        private static string StreamHash(Stream stream, CancellationToken cancellation)
        {
            using (var sha = SHA256.Create())
            {
                byte[] buffer = new byte[1024 * 1024]; int count;
                while ((count = stream.Read(buffer, 0, buffer.Length)) != 0) { cancellation.ThrowIfCancellationRequested(); sha.TransformBlock(buffer, 0, count, buffer, 0); }
                sha.TransformFinalBlock(new byte[0], 0, 0); return Hex(sha.Hash);
            }
        }
        private static string TextHash(string value) { using (var sha = SHA256.Create()) return Hex(sha.ComputeHash(Encoding.UTF8.GetBytes(value))); }
        private static string Hex(byte[] bytes) { return BitConverter.ToString(bytes).Replace("-", "").ToLowerInvariant(); }
        private static void Notify(Action<Progress> callback, string message, int done, int total)
        { if (callback != null) { try { callback(new Progress { Message = message, FilesDone = done, Total = total }); } catch { /* A closed UI must not corrupt a receipt transaction. */ } } }
    }
}
