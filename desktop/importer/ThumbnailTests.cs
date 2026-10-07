using System;
using System.IO;
using System.Threading;
using PolarisStandalone;
class ThumbnailTests {
 static int count;
 static string root,source,nas,state;
 const string session=@"Astronomy\DWARF_RAW_TELE_M 31_EXP_30_GAIN_50_2026-10-06-19-22-07-716";
 static void Check(bool value,string message){if(!value)throw new Exception(message);Console.WriteLine("PASS "+message);count++;}
 static void Setup(){root=Path.Combine(Path.GetTempPath(),"PolarisThumbnailFixture-"+Guid.NewGuid().ToString("N"));source=Path.Combine(root,"source");nas=Path.Combine(root,"nas");state=Path.Combine(root,"state");foreach(string p in new[]{source,nas,state})Directory.CreateDirectory(p);}
 static void Put(string path,string text){path=Path.Combine(source,path);Directory.CreateDirectory(Path.GetDirectoryName(path));File.WriteAllText(path,text);}
 static Summary Run(){return Importer.Run(source,nas,state,CancellationToken.None,null);}
 static void Main(){
  Setup();string thumb=session+@"\Thumbnail\failed_M31.jpg";Put(thumb,"");Put(session+@"\M31.fits","raw frame");var r=Run();
  Check(r.Copied==1 && r.Held==1 && r.Deferred==1,"empty native thumbnail does not block raw copy");
  Check(File.Exists(Path.Combine(source,thumb)) && !File.Exists(Path.Combine(nas,thumb)),"thumbnail retained, never copied or deleted");
  Check(ReceiptPlan.LoadForCleanup(state,source,nas).Count==1,"only copied raw frame admitted to cleanup plan");
  r=Run();Check(r.Reused==1 && r.Held==r.Deferred,"repeat deferral remains nonblocking");
  Put(thumb,"preview");r=Run();Check(r.Copied==1 && r.Held==0,"later nonempty thumbnail imported normally");
  Setup();Put(thumb,"");Put(session+@"\.active","active");r=Run();Check(r.Held>r.Deferred,"active capture remains blocking");
  foreach(string bad in new[]{session+@"\empty.fits",session+@"\Thumbnail\empty.fits",@"Astronomy\unknown\Thumbnail\empty.jpg",session+@"\elsewhere\empty.jpg"}){Setup();Put(bad,"");r=Run();Check(r.Held==1&&r.Deferred==0,"other empty file still blocks: "+bad);}
  Setup();Put(thumb,"");string dest=Path.Combine(nas,thumb);Directory.CreateDirectory(Path.GetDirectoryName(dest));File.WriteAllText(dest,"existing");r=Run();Check(r.Held==1&&r.Deferred==0,"existing unverified destination still blocks");
  Console.WriteLine("PASS TOTAL "+count);
 }
}
