using System;
using System.IO;
using System.Text;
using System.Diagnostics;
using System.Collections.Generic;

namespace PolarisStandalone
{
    internal static class RunReport
    {
        internal static void OpenSaved(string path, Action<string> launch)
        {
            CheckLocalPath(path);
            if (!String.Equals(Path.GetExtension(path), ".html", StringComparison.OrdinalIgnoreCase) || !File.Exists(path))
                throw new IOException("The saved HTML report is unavailable.");
            launch(path);
        }
        internal static void OpenSaved(string path)
        {
#if UI_OFFLINE_FIXTURE
            OpenSaved(path, delegate(string saved) { if (FailOpen) throw new IOException("Synthetic browser launch failure"); OpenCalls++; });
#else
            OpenSaved(path, delegate(string saved) { Process.Start(new ProcessStartInfo(saved) { UseShellExecute = true }); });
#endif
        }
#if UI_OFFLINE_FIXTURE
        internal static readonly string Folder = Path.Combine(Path.GetTempPath(), "PolarisOnConnectFixture-" + Guid.NewGuid().ToString("N"));
        internal static bool FailSave;
        internal static bool FailOpen;
        internal static int OpenCalls;
#else
        internal const string Folder = @"G:\Polaris_Workspace\StandaloneReports";
#endif
        internal static bool IsSuccessful(Summary imported, BatchSummary cleared, bool clearRequested)
        {
            return imported != null && !imported.Cancelled && imported.Held == imported.Deferred &&
                (!clearRequested || (cleared != null && !cleared.Cancelled && cleared.Held == 0));
        }
        internal static string Encode(string value)
        {
            return (value ?? "").Replace("&", "&amp;").Replace("<", "&lt;").Replace(">", "&gt;").Replace("\"", "&quot;").Replace("'", "&#39;");
        }
        internal static void CheckLocalPath(string path)
        {
            if (!Path.IsPathRooted(path) || path.StartsWith(@"\\") || new DriveInfo(Path.GetPathRoot(path)).DriveType != DriveType.Fixed)
                throw new IOException("Reports must use an ordinary local fixed-drive folder.");
            for (string part = path; !String.IsNullOrEmpty(part); part = Path.GetDirectoryName(part))
            {
                try { if ((File.GetAttributes(part) & FileAttributes.ReparsePoint) != 0) throw new IOException("Report path must not be redirected."); }
                catch (FileNotFoundException) { }
                catch (DirectoryNotFoundException) { }
            }
        }
        internal static string Save(string folder, string status, string details, TimeSpan duration, Summary imported, BatchSummary cleared, bool clearRequested, string log)
        {
#if UI_OFFLINE_FIXTURE
            if (FailSave) throw new IOException("Synthetic report write failure");
#endif
            CheckLocalPath(folder); Directory.CreateDirectory(folder); CheckLocalPath(folder);
            string path = Path.Combine(folder, "Polaris-import-" + DateTime.Now.ToString("yyyyMMdd-HHmmss") + "-" + Guid.NewGuid().ToString("N") + ".html");
            string content = Render(status, details, duration, imported, cleared, clearRequested, log);
            using (var file = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.Read))
            using (var writer = new StreamWriter(file, new UTF8Encoding(false))) { writer.Write(content); writer.Flush(); file.Flush(true); }
            return path;
        }
        internal static string Render(string status, string details, TimeSpan duration, Summary imported, BatchSummary cleared, bool clearRequested, string log)
        {
            var html = new StringBuilder("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><title>Project Polaris — Import report</title><link rel=\"icon\" href=\"");
            html.Append(PolarisMark.ImageDataUrl).Append("\"><style>body{margin:0;background:#050e15;color:#eef2ea;font:17px/1.6 system-ui,sans-serif}main{max-width:1000px;margin:36px auto;padding:24px}.brand{display:flex;align-items:center;gap:22px;margin:0 0 32px}.brand img{width:104px;height:104px;flex:none;border-radius:18px}.brand h1{margin:0;color:#eef2ea;font-size:36px;line-height:1.2;font-weight:600}.brand p{margin:9px 0 0;color:#53d8cd;font-size:13px;font-weight:600;letter-spacing:.1em}.brand .tagline{margin-left:auto;text-align:right;color:#80adbf;font-size:13px;letter-spacing:0}h2{color:#53d8cd;font-size:24px;margin-top:0}.panel{background:#081923;border:1px solid #1b454c;border-radius:12px;padding:24px;margin:20px 0}dl{display:grid;grid-template-columns:minmax(0,2fr) minmax(0,1fr);gap:12px 20px}dt,dd{margin:0}dd{text-align:right;font-variant-numeric:tabular-nums}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px;color:#80adbf}small,footer{color:#80adbf}summary{cursor:pointer;color:#53d8cd}footer{font-size:13px;margin:28px 0}@media(max-width:600px){main{margin:12px auto;padding:16px}.brand{gap:14px}.brand img{width:72px;height:72px;border-radius:12px}.brand h1{font-size:27px}.brand p{font-size:10px}.brand .tagline{display:none}.panel{padding:18px}dl{grid-template-columns:minmax(0,3fr) minmax(0,2fr);font-size:14px}}</style></head><body><main><header class=\"brand\"><img alt=\"Project Polaris North Star Orbit logo\" src=\"");
            html.Append(PolarisMark.ImageDataUrl).Append("\"><div><h1>Project Polaris</h1><p>DWARF INGESTION · IMPORT REPORT</p></div><p class=\"tagline\">COPY / VERIFY / CLEAR<br>Your imaging companion</p></header><section class=\"panel\"><h2>");
            html.Append(Encode(status)).Append("</h2><p>").Append(Encode(imported == null ? details : (IsSuccessful(imported, cleared, clearRequested) ? "Import complete." : "Open Needs attention below for the problem and next step."))).Append("</p><p>Report created: ").Append(Encode(DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss zzz"))).Append("<br>Elapsed: ").Append(Encode(duration.ToString(@"hh\:mm\:ss"))).Append("</p><dl>");
            if (imported != null)
            {
                Row(html,"New files copied and verified", imported.Copied.ToString("N0"));
            }
            else Row(html,"Import counts", "Unavailable; consult session details and receipts");
            if (cleared != null)
            {
                Row(html,"DWARF files freshly verified and cleared this run", cleared.Deleted.ToString("N0"));
            }
            else Row(html,"Telescope cleanup", clearRequested ? (imported != null && imported.Held > imported.Deferred ? "Not started — resolve the import issue first" : "Not confirmed — review required") : "Off — files retained on telescope");
            html.Append("</dl></section>");
            Attention(html, details, imported, cleared, clearRequested, log);
            html.Append("<section class=\"panel\"><h2>Your capture library</h2>");
            if (imported != null && (imported.Cancelled || imported.Held > imported.Deferred))
                html.Append("<p>This run did not organize new captures into the library. Successfully copied files remain in the NAS inbox. Resolve the import issue and run the importer again to finish.</p>");
            else html.Append("<p>Library location is shown below. See session details for this run's archive publication outcome.</p>");
            html.Append("<pre>").Append(Encode(ArchivePublisher.Library)).Append("</pre></section><details class=\"panel\"><summary>Technical details — routine counts and session log</summary><p>These routine counts do not require action by themselves. Reused files were recognized from saved records, not freshly rehashed. Routine skipped files remain on the telescope.</p><dl>");
            if (imported != null) {
                Row(html,"Previously recorded files reused — not rehashed", imported.Reused.ToString("N0"));
                Row(html,"Routine deferred files — retained on DWARF", imported.Deferred.ToString("N0"));
            }
            if (cleared != null) {
                Row(html,"Previously cleared files", cleared.AlreadyCleared.ToString("N0"));
                Row(html,"Cleared file bytes (not a measured free-space change)", cleared.BytesFreed.ToString("N0"));
            }
            html.Append("</dl><p>Existing NAS files are never replaced or deleted. Source clearing requires fresh verification against the NAS inbox. Receipts remain the record of individual operations.</p><h3>Session details</h3><pre>").Append(Encode(log)).Append("</pre></details><footer>Project Polaris · Your imaging companion</footer></main></body></html>");
            return html.ToString();
        }
        private static void Row(StringBuilder html, string label, string value)
        { html.Append("<dt>").Append(Encode(label)).Append("</dt><dd>").Append(Encode(value)).Append("</dd>"); }

        private static void Attention(StringBuilder html, string details, Summary imported, BatchSummary cleared, bool requested, string log)
        {
            int count = (imported == null ? 0 : Math.Max(0, imported.Held - imported.Deferred)) + (cleared == null ? 0 : cleared.Held);
            bool interrupted = imported == null || imported.Cancelled || (cleared != null && cleared.Cancelled);
            if (count == 0 && !interrupted && (!requested || cleared != null)) return;
            html.Append("<details class=\"panel attention\"><summary><strong>Needs attention");
            if (count > 0) html.Append(" — ").Append(count).Append(count == 1 ? " item" : " items");
            html.Append("</strong></summary><p>Copying and clearing are separate steps. A copied file does not mean its telescope copy was removed.</p>");
            var seen = new HashSet<string>(StringComparer.Ordinal);
            foreach (string line in (log ?? "").Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries))
            {
                int marker = line.IndexOf("  HOLD: ", StringComparison.Ordinal);
                if (line.StartsWith("HOLD: ", StringComparison.Ordinal)) marker = 0;
                bool cleanup = line.IndexOf("Cleanup HOLD:", StringComparison.Ordinal) >= 0 || line.IndexOf("Cleanup stopped (", StringComparison.Ordinal) >= 0;
                if (marker < 0 && !cleanup) continue;
                string evidence = marker >= 0 ? line.Substring(marker).Trim() : line.Trim();
                if (!seen.Add(evidence)) continue;
                string problem = "Polaris could not safely finish this item.";
                string resolution = "Keep the telescope files and NAS copies. Use the technical message below to review this item before retrying; do not delete or overwrite either copy.";
                if (evidence.IndexOf("Zero-length source held as incomplete.", StringComparison.Ordinal) >= 0)
                {
                    bool thumbnail = evidence.IndexOf("\\Thumbnail\\", StringComparison.OrdinalIgnoreCase) >= 0;
                    problem = thumbnail ? "The telescope created an empty preview image (thumbnail). This warning is about that preview, not a raw exposure." : "This file is empty, so Polaris cannot verify a complete copy.";
                    resolution = "Stop capture and let the telescope finish saving, then retry once. If the same file remains empty, have this exact file reviewed for recovery or safe quarantine before rerunning. Do not delete the imaging session or format the telescope.";
                }
                else if (evidence.IndexOf("metadata changed", StringComparison.OrdinalIgnoreCase) >= 0)
                { problem = "This file changed since its earlier import; the saved copy was preserved."; resolution = "Keep both versions. Review the changed file and preserve it as a separate version before retrying. Do not replace the NAS copy."; }
                else if (evidence.IndexOf("uncertain", StringComparison.OrdinalIgnoreCase) >= 0 || evidence.IndexOf("reservation", StringComparison.OrdinalIgnoreCase) >= 0)
                { problem = "Cleanup could not confirm the outcome of a previous operation."; resolution = "Keep the NAS copy. Have the cleanup receipts and this exact telescope path checked before another cleanup attempt; do not clear the history or force a retry."; }
                html.Append("<article><h3>What happened</h3><p>").Append(Encode(problem)).Append("</p><h3>What to do</h3><p>").Append(Encode(resolution)).Append("</p><details><summary>Affected file and technical message</summary><pre>").Append(Encode(evidence)).Append("</pre></details></article>");
            }
            if (seen.Count == 0 || count > seen.Count || interrupted)
                html.Append("<h3>Review the unfinished run</h3><p>The available log does not explain every unfinished step. Keep the telescope files and NAS copies, and share this report for review before clearing anything.</p><pre>").Append(Encode(details)).Append("</pre>");
            if (imported != null && imported.Held > imported.Deferred)
                html.Append("<p><strong>What is waiting:</strong> Archive organization and telescope cleanup did not start. Copied and verified files remain in the NAS inbox.</p>");
            else if (requested && cleared == null)
                html.Append("<p>Telescope cleanup has no completion summary. Check the session log before retrying.</p>");
            html.Append("</details>");
        }
    }
}

