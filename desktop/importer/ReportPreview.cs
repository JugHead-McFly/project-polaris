using System;
using System.IO;
using System.Net;
using PolarisStandalone;
// Read-only rendering of the operator's reviewed 2026-10-07 report.
class ReportPreview {
    static void Main(string[] args) {
        string original=File.ReadAllText(args[0]);
        const string marker="<summary>Session details</summary><pre>";
        int start=original.IndexOf(marker,StringComparison.Ordinal);
        if(start<0) throw new Exception("Original session log not found");
        start+=marker.Length;
        int end=original.IndexOf("</pre>",start,StringComparison.Ordinal);
        string log=WebUtility.HtmlDecode(original.Substring(start,end-start));
        if(!log.Contains("2022 copied and verified · 133 metadata reused (not rehashed) · 14 deferred · 1 need attention")) throw new Exception("Unexpected run; counts require review");
        string report=RunReport.Render("Finished — needs attention", "Original run: 2026-10-07 08:05:50 -07:00. Cleanup did not run.", new TimeSpan(0,5,33), new Summary{Copied=2022,Reused=133,Held=15,Deferred=14},null,true,log);
        report=report.Replace("Report created:","Report regenerated (original run: October 7, 08:05 Arizona):");
        using(var file=new FileStream(args[1],FileMode.CreateNew)) using(var writer=new StreamWriter(file)) writer.Write(report);
    }
}
