using System;
using System.IO;
using System.Reflection;
using System.Threading;
using System.Windows.Forms;
using PolarisStandalone;
internal static class OnConnectTests
{
    sealed class NativeIo : IOException { internal NativeIo(int code) { HResult=unchecked((int)0x80070000)|code; } }
    static int count;
    static void Check(bool yes,string name){if(!yes)throw new Exception(name);count++;Console.WriteLine("PASS "+name);}
    static object Get(object o,string n){return o.GetType().GetField(n,BindingFlags.Instance|BindingFlags.NonPublic).GetValue(o);}
    static void Set(object o,string n,object v){o.GetType().GetField(n,BindingFlags.Instance|BindingFlags.NonPublic).SetValue(o,v);}
    static object Call(object o,string n,params object[] a){return o.GetType().GetMethod(n,BindingFlags.Instance|BindingFlags.NonPublic).Invoke(o,a);}
    static void Pump(Func<bool> done){var deadline=DateTime.UtcNow.AddSeconds(15);while(!done()){Application.DoEvents();Thread.Sleep(10);if(DateTime.UtcNow>deadline)throw new Exception("Timed out");}Application.DoEvents();}
    static MainWindow Window(){var w=new MainWindow(false,false,false,true);w.ShowInTaskbar=false;w.StartPosition=FormStartPosition.Manual;w.Location=new System.Drawing.Point(-32000,-32000);w.Show();return w;}
    static void Reset(){ArchivePublisher.Fail=ArchivePublisher.Cancel=false;Importer.Fail=Importer.Block=CleanupBatch.Fail=CleanupBatch.Block=false;Importer.Result=new Summary{Copied=1,Reused=2,Held=1,Deferred=1};CleanupBatch.Result=new BatchSummary{Deleted=1,AlreadyCleared=2,BytesFreed=42};}
    static void Cycle(MainWindow w){Set(w,"clearThisRun",true);Set(w,"armed",true);Call(w,"BeginImport",new DeviceBinding());Pump(()=>!(bool)Get(w,"busy"));}
    [STAThread] static int Main()
    {
        try{
            Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);Reset();
            Check(OnConnectContext.DiscoverForPolling(delegate { throw new System.ComponentModel.Win32Exception(21); })==null,"eject not-ready is missing during idle poll");
            Check(OnConnectContext.DiscoverForPolling(delegate { throw new NativeIo(21); })==null,"IO not-ready race is missing during idle poll");
            Check(OnConnectContext.DiscoverForPolling(delegate { throw new NativeIo(1167); })==null,"disconnected device remains retryable");
            bool serious=false;try{OnConnectContext.DiscoverForPolling(delegate { throw new NativeIo(5); });}catch(IOException){serious=true;}Check(serious,"access denied is not hidden as eject");
            serious=false;try{OnConnectContext.DiscoverForPolling(delegate { throw new IOException("identity mismatch"); });}catch(IOException){serious=true;}Check(serious,"identity errors still stop detection");
            var bound=new DeviceBinding();Check(Object.ReferenceEquals(bound,OnConnectContext.DiscoverForPolling(delegate{return bound;})),"ready binding preserved");
            Check(RunReport.IsSuccessful(Importer.Result,CleanupBatch.Result,true),"routine deferrals allow success");
            Check(!RunReport.IsSuccessful(null,null,true),"missing summary cannot auto-close");
            Check(!RunReport.IsSuccessful(Importer.Result,null,true),"missing requested cleanup cannot auto-close");
            Check(!RunReport.IsSuccessful(new Summary{Held=2,Deferred=1},CleanupBatch.Result,true),"blocking import prevents auto-close");
            Check(!RunReport.IsSuccessful(Importer.Result,new BatchSummary{Held=1},true),"cleanup hold prevents auto-close");
            Check(!RunReport.IsSuccessful(Importer.Result,new BatchSummary{Cancelled=true},true),"cancel prevents auto-close");
            string html=RunReport.Render("<script>alert(1)</script>","A & B",TimeSpan.Zero,Importer.Result,CleanupBatch.Result,true,"<img src=x onerror=alert(1)>");
            Check(!html.Contains("<script>")&&!html.Contains("<img src=x onerror=alert(1)>"),"untrusted names/log text HTML escaped");
            Check(html.Contains("not rehashed")&&html.Contains("not a measured free-space change"),"report distinguishes cached evidence and payload bytes");
            bool rejected=false;try{RunReport.CheckLocalPath(@"\\server\share\report.html");}catch(IOException){rejected=true;}Check(rejected,"report writer rejects network path");
            string a=RunReport.Save(RunReport.Folder,"Success","test",TimeSpan.Zero,Importer.Result,CleanupBatch.Result,true,"fixture");
            string b=RunReport.Save(RunReport.Folder,"Success","test",TimeSpan.Zero,Importer.Result,CleanupBatch.Result,true,"fixture");
            Check(a!=b&&File.Exists(a)&&File.Exists(b),"reports create unique files without overwrite");
            using(var w=Window()){
                Check(!((CheckBox)Get(w,"watch")).Checked,"single import does not rearm watch");Cycle(w);
                Check(w.LastReportPath!=null&&File.Exists(w.LastReportPath),"success report written before close");
                Check(RunReport.OpenCalls==1,"saved report opens once before success closes");
                Check(Get(w,"closeTimer")!=null,"success schedules close");Pump(()=>w.IsDisposed);
            }
            Reset();Importer.Fail=true;
            using(var w=Window()){Cycle(w);Check(!w.IsDisposed&&Get(w,"closeTimer")==null,"import failure stays visible");Check(File.ReadAllText(w.LastReportPath).Contains("Import failed"),"failure report retains cause");}
            Reset();CleanupBatch.Result.Held=1;
            using(var w=Window()){Cycle(w);Check(!w.IsDisposed&&Get(w,"closeTimer")==null,"cleanup hold stays visible");}
            Reset();Importer.Result.Cancelled=true;
            using(var w=Window()){Cycle(w);Check(!w.IsDisposed&&Get(w,"closeTimer")==null,"cancelled import stays visible");}
            Reset();RunReport.FailSave=true;
            using(var w=Window()){Cycle(w);Check(!w.IsDisposed&&Get(w,"closeTimer")==null&&w.LastReportPath==null,"report failure prevents auto-close");Check(((Label)Get(w,"status")).Text.Contains("report needs attention"),"report failure is visible");}
            RunReport.FailSave=false;
            Reset();RunReport.FailOpen=true;
            using(var w=Window()){Cycle(w);Check(w.LastReportPath!=null&&File.Exists(w.LastReportPath),"browser failure preserves saved report");Check(!w.IsDisposed&&Get(w,"closeTimer")==null,"browser failure keeps import window visible");Check(((Label)Get(w,"detail")).Text.Contains("saved, but could not be opened"),"browser failure distinguished from save failure");}
            RunReport.FailOpen=false;
            Reset();ArchivePublisher.Fail=true;int cleanupBefore=CleanupBatch.Calls;
            using(var w=Window()){Cycle(w);Check(CleanupBatch.Calls==cleanupBefore,"archive failure prevents device cleanup");Check(Get(w,"closeTimer")==null,"archive failure prevents success auto-close");Check(File.ReadAllText(w.LastReportPath).Contains("Archive publication failed"),"archive failure saved in report");}
            Reset();ArchivePublisher.Cancel=true;cleanupBefore=CleanupBatch.Calls;
            using(var w=Window()){Cycle(w);Check(CleanupBatch.Calls==cleanupBefore,"archive cancellation prevents device cleanup");Check(Get(w,"closeTimer")==null,"archive cancellation stays visible");}
            Reset();Importer.Result.Held=2;int archiveBefore=ArchivePublisher.Calls;cleanupBefore=CleanupBatch.Calls;
            using(var w=Window()){Cycle(w);Check(ArchivePublisher.Calls==archiveBefore&&CleanupBatch.Calls==cleanupBefore,"import holds prevent archive and cleanup");}
            Reset();
            int launched=0;RunReport.OpenSaved(a,delegate(string p){Check(p==a,"launcher receives exact saved report path");launched++;});Check(launched==1,"report opener launches once");
            bool missing=false;try{RunReport.OpenSaved(a+".missing",delegate{launched++;});}catch(IOException){missing=true;}Check(missing&&launched==1,"missing report cannot launch");
            using(var notice=new BrandedNotice("Polaris needs attention","Device detection has paused","Sample notice — no device error.\n\nYour completed import and NAS files are unchanged.")){
                notice.ShowInTaskbar=false;notice.StartPosition=FormStartPosition.Manual;notice.Location=new System.Drawing.Point(-32000,-32000);notice.Show();Application.DoEvents();
                Check(notice.Icon!=null&&notice.AcceptButton!=null&&notice.CancelButton!=null,"branded notice has icon and keyboard dismissal");
                using(var image=new System.Drawing.Bitmap(notice.Width,notice.Height)){notice.DrawToBitmap(image,new System.Drawing.Rectangle(0,0,image.Width,image.Height));image.Save(Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"notice-preview.png"));}
            }
            Reset();DeviceIdentity.Enrollment=new DeviceEnrollment{AllowCleanup=true};DeviceIdentity.Binding=null;DeviceIdentity.Throw=false;
            using(var context=new OnConnectContext()){
                ((System.Windows.Forms.Timer)Get(context,"poll")).Stop();
                Call(context,"Poll");Check(Get(context,"window")==null,"detector has no idle main window");
                int before=Importer.Calls;DeviceIdentity.Binding=new DeviceBinding();Call(context,"Poll");Call(context,"Poll");Check(Get(context,"window")==null,"transient connection does not launch");Call(context,"Poll");
                var w=(MainWindow)Get(context,"window");Check(w!=null&&w.WindowState!=FormWindowState.Minimized,"stable enrolled device opens visible import window");
                Call(w,"Tick");Call(w,"Tick");Call(w,"Tick");Pump(()=>Get(context,"window")==null);
                Check(Importer.Calls==before+1,"one import for one connection");
                Call(context,"Poll");Call(context,"Poll");Call(context,"Poll");Check(Get(context,"window")==null&&Importer.Calls==before+1,"same connected device does not loop");
                DeviceIdentity.Binding=null;Call(context,"Poll");Call(context,"Poll");DeviceIdentity.Binding=new DeviceBinding();Call(context,"Poll");Call(context,"Poll");Call(context,"Poll");
                Check(Get(context,"window")!=null,"disconnect and reconnect opens next session");Call(context,"RequestExit");
                Check(Get(context,"window")==null,"detector exit closes idle import window gracefully");
            }
            Console.WriteLine("PASS TOTAL "+count+"; fixture artifacts: "+RunReport.Folder);return 0;
        }catch(Exception e){Console.Error.WriteLine(e);return 1;}
    }
}

