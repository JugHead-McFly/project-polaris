using System;
using System.Threading;
using System.Web.Script.Serialization;
using PolarisStandalone;
internal static class ArchiveTool
{
    static int Main(string[] args)
    {
        try
        {
            if (args.Length == 1 && args[0] == "--plan")
            { Console.WriteLine(new JavaScriptSerializer { MaxJsonLength = 32 * 1024 * 1024 }.Serialize(ArchivePublisher.Plan())); return 0; }
            if (args.Length != 1 || args[0] != "--publish-approved-archive")
            { Console.WriteLine("OFF: specify --plan or --publish-approved-archive. No device operations."); return 2; }
            var result = ArchivePublisher.RunProduction(CancellationToken.None, delegate(Progress p) { if (p.FilesDone % 100 == 0 || p.FilesDone == p.Total) Console.WriteLine(p.FilesDone + "/" + p.Total + " " + p.Message); }, false);
            Console.WriteLine(new JavaScriptSerializer().Serialize(result)); return 0;
        }
        catch (Exception e) { Console.Error.WriteLine(e); return 1; }
    }
}
