using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Threading;
using PolarisStandalone;
internal static class ArchiveTests
{
    static int checks;
    static string root;
    static void Check(bool yes, string name) { if (!yes) throw new Exception(name); checks++; Console.WriteLine("PASS " + name); }
    static void Reject(Action action, string name) { bool rejected = false; try { action(); } catch (IOException) { rejected = true; } Check(rejected, name); }
    static string Hash(string content) { using (var m = new MemoryStream(Encoding.UTF8.GetBytes(content))) return ArchivePublisher.Hash(m, CancellationToken.None); }
    static ArchivePublisher.Entry Entry(string test, string content)
    {
        string dir = Path.Combine(root, test); Directory.CreateDirectory(dir);
        string source = Path.Combine(dir, "inbox.fits"); File.WriteAllText(source, content, new UTF8Encoding(false));
        return new ArchivePublisher.Entry { Relative = "Astronomy\\fixture\\frame.fits", Source = source, Destination = Path.Combine(dir, "archive", "frame.fits"), Length = new FileInfo(source).Length, Hash = Hash(content) };
    }
    static ArchiveSummary Run(ArchivePublisher.Entry e, bool force) { return ArchivePublisher.Publish(new List<ArchivePublisher.Entry> { e }, Path.Combine(Path.GetDirectoryName(e.Source), "state"), CancellationToken.None, null, force); }
    static int Main()
    {
        try
        {
            root = Path.Combine(Path.GetTempPath(), "PolarisArchiveFixture-" + Guid.NewGuid().ToString("N")); Directory.CreateDirectory(root);
            string session = "DWARF_RAW_TELE_M 31_EXP_15_GAIN_60_2026-08-25-00-39-33-653";
            string route = ArchivePublisher.Route("Astronomy\\" + session + "\\Thumbnail\\frame.jpg");
            Check(route == "10_Raw_Archive\\DWARF_Mini\\Astronomy\\Deep_Sky\\Andromeda Galaxy\\2026-08-25\\" + session + "\\Thumbnail\\frame.jpg", "matches historical target/date/session route and preserves thumbnails");
            Check(ArchivePublisher.Route("Astronomy\\" + session.Replace("M 31", "NGC 1234") + "\\a.fits").Contains("\\NGC 1234\\"), "unknown target uses exact device designation");
            Check(ArchivePublisher.Route("Astronomy\\" + session.Replace("M 31", "M 310") + "\\a.fits").Contains("\\M 310\\"), "target mapping never uses substring matches");
            Check(ArchivePublisher.Route("Astronomy\\" + session.Replace("M 31", "C 20") + "\\a.fits").Contains("\\North America Nebula\\"), "C20 joins existing historical target");
            Check(ArchivePublisher.Route("Astronomy\\RESTACKED\\RESTACKED_DWARF_RAW_TELE_M 57_Duo-Band_20260825-054629295\\a.fits").Contains("\\Ring Nebula\\2026-08-25\\RESTACKED_"), "restacked images stay separate from raw sessions under same target");
            Check(ArchivePublisher.Route("Astronomy\\CALI_FRAME\\dark\\cam_0\\dark__20260911_hash.fits").EndsWith("CALI_FRAME\\dark\\cam_0\\dark__20260911_hash.fits"), "calibration versions and camera hierarchy preserved");
            Check(ArchivePublisher.Route("Astronomy\\DWARF_DARK\\session\\a.fits").StartsWith("20_Calibration_Library"), "dark frames use calibration library");
            Reject(delegate { ArchivePublisher.Route("Astronomy\\..\\a.fits"); }, "traversal rejected");
            Reject(delegate { ArchivePublisher.Route("Astronomy\\" + session.Replace("2026-08-25", "2026-02-31") + "\\a.fits"); }, "invalid capture date rejected");
            Reject(delegate { ArchivePublisher.Route("Astronomy\\unrecognized\\a.fits"); }, "unknown session layout holds instead of silently omitting");
            Reject(delegate { ArchivePublisher.Route("Astronomy\\" + session + "\\a.fits:stream"); }, "alternate streams rejected");
            Reject(delegate { ArchivePublisher.Route("Astronomy\\" + session.Replace("M 31", "CON") + "\\a.fits"); }, "reserved target names rejected");
            var first = Entry("new", "original FITS fixture"); var summary = Run(first, false);
            Check(summary.Copied == 1 && File.ReadAllText(first.Destination) == File.ReadAllText(first.Source), "new archive file copied and verified");
            Check(File.Exists(first.Source), "inbox original retained");
            summary = Run(first, false); Check(summary.MetadataReused == 1 && summary.Copied == 0, "repeat publication is idempotent and metadata reuse explicit");
            summary = Run(first, true); Check(summary.VerifiedExisting == 1 && summary.MetadataReused == 0, "forced fixture check freshly verifies existing proof");
            File.WriteAllText(first.Destination, "changed archive content");
            Reject(delegate { Run(first, false); }, "changed previously verified archive holds without replacement");
            Check(File.ReadAllText(first.Destination) == "changed archive content", "changed archive preserved");
            var exact = Entry("exact", "same bytes"); Directory.CreateDirectory(Path.GetDirectoryName(exact.Destination)); File.WriteAllText(exact.Destination, "same bytes", new UTF8Encoding(false));
            long existingTicks = File.GetLastWriteTimeUtc(exact.Destination).Ticks;
            summary = Run(exact, false); Check(summary.VerifiedExisting == 1 && summary.Copied == 0 && File.GetLastWriteTimeUtc(exact.Destination).Ticks == existingTicks, "existing exact historical file verified without mutation");
            var conflict = Entry("conflict", "new generation"); Directory.CreateDirectory(Path.GetDirectoryName(conflict.Destination)); File.WriteAllText(conflict.Destination, "old generation");
            summary = Run(conflict, false); Check(summary.Copied == 1 && summary.Versions == 1 && File.ReadAllText(conflict.Destination) == "old generation", "differing existing generation preserved with separate hashed version");
            summary = Run(conflict, false); Check(summary.MetadataReused == 1 && Directory.GetFiles(Path.GetDirectoryName(conflict.Destination)).Length == 2, "version publication stable on next run");
            var bad = Entry("bad", "tampered source"); bad.Hash = Hash("expected bytes");
            Reject(delegate { Run(bad, false); }, "inbox hash mismatch blocks publication"); Check(!File.Exists(bad.Destination), "bad inbox cannot create archive payload");
            var interrupted = Entry("interrupted", "expected complete bytes"); string state = Path.Combine(Path.GetDirectoryName(interrupted.Source), "state"); Directory.CreateDirectory(state); Directory.CreateDirectory(Path.GetDirectoryName(interrupted.Destination));
            File.WriteAllText(interrupted.Destination, "partial"); File.WriteAllText(Path.Combine(state, "intent-" + Hash(interrupted.Destination.ToUpperInvariant()) + ".json"), "fixture intent");
            Reject(delegate { Run(interrupted, false); }, "interrupted partial publication held without alternate retry");
            Check(Directory.GetFiles(Path.GetDirectoryName(interrupted.Destination)).Length == 1 && File.ReadAllText(interrupted.Source) == "expected complete bytes", "interruption preserves both source and partial evidence");
            var cancel = Entry("cancel", "not copied"); var cancelled = new CancellationToken(true); bool stopped = false;
            try { ArchivePublisher.Publish(new List<ArchivePublisher.Entry>{cancel}, Path.Combine(Path.GetDirectoryName(cancel.Source), "state"), cancelled, null, false); } catch(OperationCanceledException) { stopped = true; }
            Check(stopped && !File.Exists(cancel.Destination), "pre-cancel performs no archive publication");
            Console.WriteLine("PASS TOTAL " + checks + "; fixtures retained: " + root); return 0;
        }
        catch(Exception ex) { Console.Error.WriteLine(ex); return 1; }
    }
}
