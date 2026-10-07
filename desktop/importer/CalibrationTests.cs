using System;
using System.IO;
using System.Text;
using System.Xml;
using System.Threading;
using System.Security.Cryptography;
using PolarisStandalone;
class CalibrationTests
{
    static int count;
    static string root, source, nas, state;
    const string relative = @"Astronomy\CALI_FRAME\dark\cam_0\dark.fits";
    static void Check(bool condition, string text) { if (!condition) throw new Exception(text); Console.WriteLine("PASS " + text); count++; }
    static string Hash(string text) { using(var s = SHA256.Create()) return BitConverter.ToString(s.ComputeHash(Encoding.UTF8.GetBytes(text))).Replace("-", "").ToLowerInvariant(); }
    static void Setup() { root=Path.Combine(Path.GetTempPath(),"PolarisCalibrationFixture-"+Guid.NewGuid().ToString("N")); source=Path.Combine(root,"source"); nas=Path.Combine(root,"nas"); state=Path.Combine(root,"state"); foreach(string p in new[]{source,nas,state}) Directory.CreateDirectory(p); Directory.CreateDirectory(Path.GetDirectoryName(Path.Combine(source,relative))); }
    static void Put(string text) { File.WriteAllText(Path.Combine(source,relative),text,new UTF8Encoding(false)); }
    static Summary Run() { return Importer.Run(source,nas,state,CancellationToken.None,null); }
    static void OldReceipt(string operation,string id,string text)
    {
        string src=Path.Combine(source,relative), dst=Path.Combine(nas,relative);
        using(var w=XmlWriter.Create(Path.Combine(state,"receipt-"+Guid.NewGuid().ToString("N")+".xml")))
        {
            w.WriteStartElement("PolarisCopyReceipt"); w.WriteAttributeString("version","1");
            string[] names={"Operation","Id","Key","Source","Destination","Relative","Length","SourceTicks","DestinationTicks","Hash","Message"};
            string[] values={operation,id,Hash(source.ToUpperInvariant()+"\n"+nas.ToUpperInvariant()+"\n"+relative.ToUpperInvariant()),src,dst,relative,new FileInfo(dst).Length.ToString(),File.GetLastWriteTimeUtc(src).Ticks.ToString(),operation=="confirmed"?File.GetLastWriteTimeUtc(dst).Ticks.ToString():"0",operation=="confirmed"?Hash(text):"","legacy fixture"};
            for(int i=0;i<names.Length;i++) w.WriteElementString(names[i],values[i]); w.WriteEndElement();
        }
    }
    static int Main()
    {
        try {
            Setup(); Put("old calibration"); Directory.CreateDirectory(Path.GetDirectoryName(Path.Combine(nas,relative))); File.Copy(Path.Combine(source,relative),Path.Combine(nas,relative)); string id=Guid.NewGuid().ToString("N"); OldReceipt("intent",id,"old calibration"); OldReceipt("confirmed",id,"old calibration");
            Put("new calibration"); var r=Run(); string version=CalibrationVersions.Destination(nas,relative,Hash("new calibration"));
            Check(r.Copied==1 && r.Held==0,"changed legacy calibration imports as version");
            Check(File.ReadAllText(Path.Combine(nas,relative))=="old calibration" && File.ReadAllText(version)=="new calibration","both generations preserved");
            Check(File.Exists(Path.Combine(source,relative)),"source retained");
            var plan=ReceiptPlan.Load(state,source,nas); Check(plan.Count==2 && plan.Exists(x=>x.CopyDestination==version),"old and new receipts plan exact archive destinations");
            Check(ReceiptPlan.LoadForCleanup(state,source,nas).Count==0,"all calibration generations excluded from cleanup");
            r=Run(); Check(r.Reused==1 && r.Copied==0 && r.Held==0,"repeat version reused without extra copies");
            File.SetLastWriteTimeUtc(Path.Combine(source,relative),DateTime.UtcNow.AddHours(-1)); r=Run(); Check(r.Reused==1 && r.Held==0,"timestamp-only source change reuses identical version");
            Put("third calibration"); r=Run(); Check(r.Copied==1 && r.Held==0 && File.ReadAllText(version)=="new calibration","third generation preserves first two");
            File.WriteAllText(Path.Combine(nas,relative),"corrupted old backup"); r=Run(); Check(r.Held==1 && r.Copied==0,"altered legacy backup blocks import");
            Setup(); Put("one"); r=Run(); version=CalibrationVersions.Destination(nas,relative,Hash("one")); Check(r.Copied==1 && File.Exists(version),"new calibration starts versioned");
            File.WriteAllText(version,"bad"); r=Run(); Check(r.Held==1 && File.ReadAllText(version)=="bad","corrupt version held without overwrite");
            Setup(); Put("one"); r=Run(); version=CalibrationVersions.Destination(nas,relative,Hash("one")); File.Delete(version); r=Run(); Check(r.Held==1 && !File.Exists(version),"missing accepted version not silently repaired");
            Setup(); Put("one"); version=CalibrationVersions.Destination(nas,relative,Hash("one")); Directory.CreateDirectory(Path.GetDirectoryName(version)); File.WriteAllText(version,"one"); r=Run(); Check(r.Held==1 && r.Copied==0,"unreceipted matching version still held");
            Setup(); Put("one"); var cancel=new CancellationTokenSource(); r=Importer.Run(source,nas,state,cancel.Token,delegate(Progress p){if(p.Message.StartsWith("Reserved:"))cancel.Cancel();}); Check(r.Cancelled && r.Held==1,"cancelled reservation remains held"); r=Run(); Check(r.Held==1 && r.Copied==0,"interrupted version cannot retry");
            Setup(); Put("one"); File.WriteAllText(Path.Combine(source,"Astronomy",".active"),"active"); r=Run(); Check(r.Held==1 && r.Copied==0,"active subtree blocks calibration");
            Check(!CalibrationVersions.IsCalibration(@"Astronomy\CALI_FRAME_fake\x.fits"),"lookalike calibration prefix excluded");
            bool rejected=false; try { CalibrationVersions.ValidateDestination(nas,relative,Path.Combine(root,"escape.fits")); } catch(InvalidDataException) { rejected=true; } Check(rejected,"escaped version route rejected");
            Setup(); string capture=Path.Combine(source,@"Astronomy\capture\frame.fits"); Directory.CreateDirectory(Path.GetDirectoryName(capture)); File.WriteAllText(capture,"capture"); r=Run(); File.WriteAllText(capture,"changed"); r=Run(); Check(r.Held==1 && r.Copied==0,"capture changes still held, not versioned");
            Console.WriteLine("PASS TOTAL "+count); return 0;
        } catch(Exception e) {Console.Error.WriteLine(e);return 1;}
    }
}
