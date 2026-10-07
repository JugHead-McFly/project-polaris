using System;
using PolarisStandalone;
class ReportTests {
    static int count;
    static void Check(bool ok, string name) { if (!ok) throw new Exception(name); Console.WriteLine("PASS " + name); count++; }
    static void Main() {
        var imported = new Summary { Copied=2022, Reused=133, Held=15, Deferred=14 };
        string log = "2026-10-07T08:04:57  HOLD: Astronomy\\session\\Thumbnail\\failed_<M31>.jpg — Zero-length source held as incomplete.\nDEFERRED (still held): routine";
        string html = RunReport.Render("Finished — needs attention", "Cleanup did not run", TimeSpan.Zero, imported, null, true, log);
        Check(html.Contains("Needs attention — 1 item"), "only genuine hold counted");
        Check(html.Contains("empty preview image") && html.Contains("What to do"), "thumbnail issue explained with next step");
        Check(html.Contains("Archive organization and telescope cleanup did not start"), "archive blockage explicit");
        Check(html.IndexOf("Previously recorded files reused") > html.IndexOf("Technical details —"), "routine counts in technical disclosure");
        Check(!html.Contains("<M31>") && html.Contains("&lt;M31&gt;"), "filename escaped");
        Check(!html.Contains("<details open"), "disclosures collapsed");
        imported.Held=imported.Deferred;
        html=RunReport.Render("Success","done",TimeSpan.Zero,imported,new BatchSummary(),true,"");
        Check(!html.Contains("class=\"panel attention\""), "routine skips do not create attention section");
        html=RunReport.Render("Stopped","unknown failure",TimeSpan.Zero,null,null,true,"");
        Check(html.Contains("Review the unfinished run") && html.Contains("unknown failure"), "unknown errors retained without inventing a cause");
        html=RunReport.Render("Stopped","cancelled",TimeSpan.Zero,new Summary{Cancelled=true},null,false,"");
        Check(html.Contains("Review the unfinished run"), "cancelled run requires review");
        html=RunReport.Render("Stopped","cleanup held",TimeSpan.Zero,imported,new BatchSummary{Held=1},true,"Cleanup stopped (Uncertain): receipt write failed");
        Check(html.Contains("could not confirm") && html.Contains("do not clear the history"), "uncertain cleanup requires receipt review");
        Console.WriteLine("PASS TOTAL " + count);
    }
}
