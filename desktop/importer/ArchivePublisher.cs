using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Web.Script.Serialization;

namespace PolarisStandalone
{
    public sealed class ArchiveSummary
    {
        public int Copied, VerifiedExisting, MetadataReused, Versions, Total;
        public string Evidence;
        public override string ToString() { return String.Format("Archive: {0} added, {1} existing verified, {2} previously verified unchanged, {3} differing versions preserved", Copied, VerifiedExisting, MetadataReused, Versions); }
    }
    // An additional create-only publication stage. It never edits the import journal,
    // deletes inbox/archive files, touches the device, or supplies deletion evidence.
    public static class ArchivePublisher
    {
        public const string Root = @"\\Synology_NAS\Astrophotography";
        public const string Library = Root + @"\10_Raw_Archive\DWARF_Mini\Astronomy\Deep_Sky";
        public const string State = @"G:\Polaris_Workspace\ArchiveHistory";
        public sealed class Entry { public string Relative, Source, Destination, Hash; public long Length; }
        public sealed class Proof { public string Relative, Source, BaseDestination, Destination, Hash; public long Length, SourceTicks, DestinationTicks; }
        static readonly JavaScriptSerializer Json = new JavaScriptSerializer { MaxJsonLength = 32 * 1024 * 1024 };
        public static string Route(string relative)
        {
            Legal(relative);
            string[] p = relative.Replace('/', '\\').Split('\\');
            if (p.Length < 3 || p[0] != "Astronomy") throw new IOException("Not an astronomy file: " + relative);
            if (p[1] == "CALI_FRAME") return @"20_Calibration_Library\DWARF_Mini\CALI_FRAME\" + Join(p, 2);
            if (p[1] == "DWARF_DARK") return @"20_Calibration_Library\DWARF_Mini\DWARF_DARK\" + Join(p, 2);
            if (p[1] == "Solving_Failed") return @"10_Raw_Archive\DWARF_Mini\Astronomy\Solving_Failed\" + Join(p, 2);
            bool restacked = p[1] == "RESTACKED";
            int sessionIndex = restacked ? 2 : 1;
            if (p.Length <= sessionIndex + 1) throw new IOException("Missing capture session/file.");
            string session = p[sessionIndex];
            Match m = restacked
                ? Regex.Match(session, @"^RESTACKED_DWARF_RAW_(?:TELE|WIDE)_(.+)_[^_]+_(\d{8}-\d{9})$")
                : Regex.Match(session, @"^DWARF_RAW_(?:TELE|WIDE)_(.+)_EXP_[^_]+_GAIN_[^_]+_(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}-\d{3})$");
            if (!m.Success) throw new IOException("Unrecognized astronomy session; retained for routing review: " + session);
            DateTime capture;
            string format = restacked ? "yyyyMMdd-HHmmssfff" : "yyyy-MM-dd-HH-mm-ss-fff";
            if (!DateTime.TryParseExact(m.Groups[2].Value, format, CultureInfo.InvariantCulture, DateTimeStyles.None, out capture)) throw new IOException("Invalid capture timestamp.");
            string target = Target(m.Groups[1].Value);
            string route = @"10_Raw_Archive\DWARF_Mini\Astronomy\Deep_Sky\" + target + "\\" + capture.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture) + "\\" + session + "\\" + Join(p, sessionIndex + 1);
            Legal(route); return route;
        }
        static string Target(string target)
        {
            string clean = Regex.Replace(target.Trim(), @"\s+", " ");
            switch (clean.ToUpperInvariant().Replace(" ", ""))
            {
                case "M31": case "ANDROMEDAGALAXY": return "Andromeda Galaxy";
                case "M27": case "DUMBBELLNEBULA": return "Dumbbell Nebula";
                case "M57": case "RINGNEBULA": return "Ring Nebula";
                case "C20": case "NGC7000": case "NORTHAMERICANEBULA": return "North America Nebula";
            }
            // Preserve an unfamiliar object's device-supplied name; never guess it
            // from coordinates, a substring, or the name of a different target.
            Legal(clean); return clean;
        }
        static string Join(string[] parts, int start) { return String.Join("\\", parts, start, parts.Length - start); }
        public static List<Entry> Plan()
        {
            var entries = new List<Entry>();
            foreach (CleanupRequest r in ReceiptPlan.Load(DeviceIdentity.ApprovedState, DeviceIdentity.HistoricalReceiptRoot, DeviceIdentity.ApprovedNas))
                if (r.RelativePath.StartsWith("Astronomy\\", StringComparison.Ordinal))
                    entries.Add(new Entry { Relative = r.RelativePath, Source = r.CopyDestination, Destination = Under(Root, Route(r.CopyDestination.Substring(DeviceIdentity.ApprovedNas.TrimEnd('\\').Length + 1))), Hash = r.ExpectedSha256, Length = r.ExpectedLength });
            return entries;
        }
        public static ArchiveSummary RunProduction(CancellationToken token, Action<Progress> progress, bool forceVerify)
        {
            Chain(DeviceIdentity.ApprovedState); Chain(State);
            using (var importLock = new FileStream(Path.Combine(DeviceIdentity.ApprovedState, "import.lock"), FileMode.Open, FileAccess.ReadWrite, FileShare.None))
            {
                var plan = Plan();
                // Completeness: unknown/unreceipted astronomy content is not silently
                // omitted from a successful archive run. This inventory does not hash.
                var known = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                foreach (Entry e in plan) known.Add(e.Source);
                foreach (string file in Files(Under(DeviceIdentity.ApprovedNas, "Astronomy")))
                    if (!known.Contains(file)) throw new IOException("Astronomy inbox file lacks accepted copy receipt: " + file);
                return Publish(plan, State, token, progress, forceVerify);
            }
        }
        internal static ArchiveSummary Publish(List<Entry> plan, string state, CancellationToken token, Action<Progress> progress, bool forceVerify)
        {
            Chain(state);
            if (state.StartsWith(@"\\") || new DriveInfo(Path.GetPathRoot(state)).DriveType != DriveType.Fixed) throw new IOException("Archive evidence must be fixed-local.");
            // All routing validation precedes any archive publication.
            var destinations = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            foreach (Entry e in plan)
            {
                Legal(e.Relative);
                if (!Regex.IsMatch(e.Hash ?? "", "^[a-f0-9]{64}$") || e.Length <= 0) throw new IOException("Invalid accepted hash/length.");
                Chain(e.Source); Chain(e.Destination);
                string previous;
                if (destinations.TryGetValue(e.Destination, out previous) && previous != e.Hash) throw new IOException("Ambiguous many-to-one archive route.");
                destinations[e.Destination] = e.Hash;
            }
            token.ThrowIfCancellationRequested();
            Directory.CreateDirectory(state); Chain(state);
            var result = new ArchiveSummary { Total = plan.Count };
            using (var archiveLock = new FileStream(Path.Combine(state, "archive.lock"), FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None))
            {
                string evidence = Path.Combine(state, "run-" + DateTime.UtcNow.ToString("yyyyMMdd-HHmmss") + "-" + Guid.NewGuid().ToString("N") + ".jsonl");
                result.Evidence = evidence;
                using (var output = new FileStream(evidence, FileMode.CreateNew, FileAccess.Write, FileShare.Read))
                using (var writer = new StreamWriter(output, new UTF8Encoding(false)))
                {
                    try
                    {
                        for (int i = 0; i < plan.Count; i++)
                        {
                            token.ThrowIfCancellationRequested();
                            Entry e = plan[i];
                            string action;
                            Proof proof = PublishOne(e, state, token, forceVerify, out action);
                            if (action == "copied") result.Copied++;
                            else if (action == "verified-existing") result.VerifiedExisting++;
                            else result.MetadataReused++;
                            if (!Same(proof.Destination, e.Destination)) result.Versions++;
                            writer.WriteLine(Json.Serialize(new { status = action, proof = proof })); writer.Flush(); output.Flush(true);
                            if (progress != null) progress(new Progress { Message = "Archive " + action + ": " + e.Relative, FilesDone = i + 1, Total = plan.Count });
                        }
                        writer.WriteLine(Json.Serialize(new { status = "Complete", summary = result })); writer.Flush(); output.Flush(true);
                    }
                    catch (Exception ex)
                    {
                        writer.WriteLine(Json.Serialize(new { status = "Stopped", error = ex.Message, summary = result })); writer.Flush(); output.Flush(true); throw;
                    }
                }
            }
            return result;
        }
        static Proof PublishOne(Entry e, string state, CancellationToken token, bool forceVerify, out string action)
        {
            string proofFile = Path.Combine(state, "proof-" + HashText(e.Source.ToUpperInvariant() + "\n" + e.Destination.ToUpperInvariant() + "\n" + e.Hash) + ".json");
            Chain(e.Source); Chain(e.Destination); Chain(proofFile);
            Proof prior = null;
            if (File.Exists(proofFile))
            {
                if (new FileInfo(proofFile).Length > 32768) throw new IOException("Oversized archive proof.");
                prior = Json.Deserialize<Proof>(File.ReadAllText(proofFile));
                if (prior == null || !Same(prior.Source, e.Source) || !Same(prior.BaseDestination, e.Destination) || prior.Relative != e.Relative || prior.Hash != e.Hash || prior.Length != e.Length ||
                    !(Same(prior.Destination, e.Destination) || Same(prior.Destination, VersionPath(e)))) throw new IOException("Archive proof binding mismatch.");
                Chain(prior.Destination);
                var si = new FileInfo(e.Source); var di = new FileInfo(prior.Destination);
                if (!forceVerify && si.Exists && di.Exists && si.Length == e.Length && di.Length == e.Length && si.LastWriteTimeUtc.Ticks == prior.SourceTicks && di.LastWriteTimeUtc.Ticks == prior.DestinationTicks)
                { action = "metadata-reused-not-rehashed"; return prior; }
            }
            using (var input = new FileStream(e.Source, FileMode.Open, FileAccess.Read, FileShare.Read, 1024 * 1024, FileOptions.SequentialScan))
            {
                long ticks = File.GetLastWriteTimeUtc(e.Source).Ticks;
                if (input.Length != e.Length || Hash(input, token) != e.Hash) throw new IOException("Inbox differs from accepted copy proof: " + e.Relative);
                string destination = prior == null ? e.Destination : prior.Destination;
                if (Directory.Exists(destination)) throw new IOException("Archive file path occupied by directory.");
                if (File.Exists(destination) && !Matches(destination, e, token))
                {
                    if (prior != null || File.Exists(IntentPath(state, destination))) throw new IOException("Previously reserved/verified archive file changed; retained for review: " + destination);
                    destination = VersionPath(e); Chain(destination);
                    if (Directory.Exists(destination) || (File.Exists(destination) && !Matches(destination, e, token))) throw new IOException("Version path is occupied by different content; no overwrite.");
                }
                bool exists = File.Exists(destination);
                if (!exists)
                {
                    if (prior != null || File.Exists(IntentPath(state, destination))) throw new IOException("Previously reserved/verified archive file missing; no automatic repair.");
                    WriteNew(IntentPath(state, destination), new { source = e.Source, destination = destination, hash = e.Hash, length = e.Length });
                    token.ThrowIfCancellationRequested();
                    string parent = Path.GetDirectoryName(destination); Chain(parent); Directory.CreateDirectory(parent); Chain(parent);
                    input.Position = 0;
                    using (var target = new FileStream(destination, FileMode.CreateNew, FileAccess.Write, FileShare.None, 1024 * 1024, FileOptions.SequentialScan))
                    {
                        byte[] buffer = new byte[1024 * 1024]; int n;
                        while ((n = input.Read(buffer, 0, buffer.Length)) != 0) { token.ThrowIfCancellationRequested(); target.Write(buffer, 0, n); }
                        target.Flush(true);
                    }
                    File.SetLastWriteTimeUtc(destination, new DateTime(ticks, DateTimeKind.Utc));
                }
                // Fresh proof for new, existing, and safely recovered complete copies.
                if (!Matches(destination, e, token) || input.Length != e.Length || File.GetLastWriteTimeUtc(e.Source).Ticks != ticks) throw new IOException("Archive publication verification failed.");
                Chain(e.Source); Chain(destination);
                var proof = new Proof { Relative = e.Relative, Source = e.Source, BaseDestination = e.Destination, Destination = destination, Hash = e.Hash, Length = e.Length, SourceTicks = ticks, DestinationTicks = File.GetLastWriteTimeUtc(destination).Ticks };
                if (prior == null) WriteNew(proofFile, proof);
                action = exists ? "verified-existing" : "copied";
                return proof;
            }
        }
        static string VersionPath(Entry e) { return Path.Combine(Path.GetDirectoryName(e.Destination), Path.GetFileNameWithoutExtension(e.Destination) + "__sha256-" + e.Hash.Substring(0, 16) + Path.GetExtension(e.Destination)); }
        static string IntentPath(string state, string destination) { return Path.Combine(state, "intent-" + HashText(destination.ToUpperInvariant()) + ".json"); }
        static bool Matches(string file, Entry e, CancellationToken token)
        {
            Chain(file);
            using (var stream = new FileStream(file, FileMode.Open, FileAccess.Read, FileShare.Read, 1024 * 1024, FileOptions.SequentialScan)) return stream.Length == e.Length && Hash(stream, token) == e.Hash;
        }
        internal static string Hash(Stream stream, CancellationToken token)
        {
            using (var sha = SHA256.Create())
            {
                byte[] buffer = new byte[1024 * 1024]; int n;
                while ((n = stream.Read(buffer, 0, buffer.Length)) != 0) { token.ThrowIfCancellationRequested(); sha.TransformBlock(buffer, 0, n, buffer, 0); }
                sha.TransformFinalBlock(new byte[0], 0, 0); return BitConverter.ToString(sha.Hash).Replace("-", "").ToLowerInvariant();
            }
        }
        static string HashText(string value) { using (var m = new MemoryStream(Encoding.UTF8.GetBytes(value))) return Hash(m, CancellationToken.None); }
        static void WriteNew(string path, object value)
        {
            Chain(path);
            using (var f = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.Read))
            using (var w = new StreamWriter(f, new UTF8Encoding(false))) { w.Write(Json.Serialize(value)); w.Flush(); f.Flush(true); }
        }
        static IEnumerable<string> Files(string root)
        {
            Chain(root);
            foreach (string f in Directory.GetFiles(root)) { Chain(f); yield return f; }
            foreach (string d in Directory.GetDirectories(root)) foreach (string f in Files(d)) yield return f;
        }
        static bool Same(string a, string b) { return String.Equals(a, b, StringComparison.OrdinalIgnoreCase); }
        internal static string Under(string root, string relative)
        {
            Legal(relative); string prefix = Path.GetFullPath(root).TrimEnd('\\') + "\\";
            string result = Path.GetFullPath(Path.Combine(prefix, relative));
            if (!result.StartsWith(prefix, StringComparison.OrdinalIgnoreCase)) throw new IOException("Path escaped root.");
            return result;
        }
        static void Legal(string relative)
        {
            if (String.IsNullOrWhiteSpace(relative) || Path.IsPathRooted(relative)) throw new IOException("Relative path required.");
            foreach (string p in relative.Replace('/', '\\').Split('\\'))
                if (p.Length == 0 || p == "." || p == ".." || p.EndsWith(".") || p.EndsWith(" ") || p.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0 || Regex.IsMatch(p, @"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", RegexOptions.IgnoreCase)) throw new IOException("Unsafe archive path component.");
        }
        internal static void Chain(string path)
        {
            if (!Path.IsPathRooted(path) || path.StartsWith(@"\\?\") || path.StartsWith(@"\\.\")) throw new IOException("Ordinary absolute paths required.");
            for (string p = path; !String.IsNullOrEmpty(p); p = Path.GetDirectoryName(p))
            {
                try { if ((File.GetAttributes(p) & FileAttributes.ReparsePoint) != 0) throw new IOException("Redirected archive path refused: " + p); }
                catch (FileNotFoundException) { } catch (DirectoryNotFoundException) { }
            }
        }
    }
}
