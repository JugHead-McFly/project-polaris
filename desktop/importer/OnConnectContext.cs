using System;
using System.Diagnostics;
using System.ComponentModel;
using System.Drawing;
using System.IO;
using System.Windows.Forms;

namespace PolarisStandalone
{
    // No main window while idle. This detector never invokes copy or cleanup itself.
    internal sealed class OnConnectContext : ApplicationContext
    {
        private readonly Timer poll = new Timer { Interval = 2000 };
        private readonly ReconnectGate gate = new ReconnectGate();
        private readonly NotifyIcon tray;
        private readonly DeviceEnrollment enrollment;
        private MainWindow window;
        private bool exiting, stopped;
        private string latestReport;
        private StreamWriter activity;
        private DeviceState? lastDevice;
        internal OnConnectContext()
        {
            enrollment = DeviceIdentity.LoadEnrollment(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "device.xml"));
            if (enrollment == null || !enrollment.AllowCleanup) throw new InvalidOperationException("Approved import-and-clear enrollment is required. Nothing started.");
#if UI_OFFLINE_FIXTURE
            string logs = Path.Combine(RunReport.Folder, "fixture-logs");
#else
            string logs = @"G:\Polaris_Workspace\StandaloneWatcherLogs";
#endif
            RunReport.CheckLocalPath(logs); Directory.CreateDirectory(logs); RunReport.CheckLocalPath(logs);
            activity = new StreamWriter(new FileStream(Path.Combine(logs, "detector-" + DateTime.UtcNow.ToString("yyyyMMdd-HHmmss") + "-" + Guid.NewGuid().ToString("N") + ".log"), FileMode.CreateNew, FileAccess.Write, FileShare.Read));
            Record("Background detector started; no idle main window; approved source cleanup enabled. Detector never copies or deletes files.");
            tray = new NotifyIcon { Icon = PolarisMark.WindowIcon(), Text = "Polaris — waiting for DWARF", Visible = true };
            var menu = new ContextMenuStrip();
            menu.Items.Add("Show import status", null, delegate { ShowStatus(); });
            menu.Items.Add("Open latest HTML report", null, delegate { OpenReports(true); });
            menu.Items.Add("Open report folder", null, delegate { OpenReports(false); });
            menu.Items.Add("Exit Polaris detector", null, delegate { RequestExit(); });
            tray.ContextMenuStrip = menu;
            tray.DoubleClick += delegate { ShowStatus(); };
            poll.Tick += delegate { Poll(); };
            poll.Start();
        }
        private void Poll()
        {
            if (exiting || stopped || window != null) return;
            try
            {
                var binding = DiscoverForPolling(delegate { return DeviceIdentity.Discover(enrollment); });
                DeviceState state = binding == null ? DeviceState.Missing : DeviceState.Ready;
                if (lastDevice != state) { Record("Device status: " + state); lastDevice = state; }
                if (!gate.ShouldStart(state)) return;
                Record("Opening one import window for this connection.");
                window = new MainWindow(true, true, false, true);
                tray.Text = "Polaris — import window open";
                window.FormClosed += delegate
                {
                    latestReport = window.LastReportPath ?? latestReport;
                    Record("Import window closed; report: " + (window.LastReportPath ?? "none"));
                    window = null;
                    tray.Text = "Polaris — waiting for next connection";
                    if (exiting) ExitThread();
                };
                window.Show();
            }
            catch (Exception ex)
            {
                stopped = true; poll.Stop(); tray.Text = "Polaris — detector needs attention";
                Record("Detector stopped: " + ex.Message);
                BrandedNotice.Show("Polaris needs attention", "Device detection has paused", ex.Message + "\n\nYour completed import and NAS files are unchanged. Close this notice and restart Polaris after resolving the issue.");
            }
        }
        // Readiness can change between drive enumeration and identity inspection
        // during Windows eject. Suppress only these native disconnect conditions
        // in idle polling; import and cleanup validation remain strict.
        internal static DeviceBinding DiscoverForPolling(Func<DeviceBinding> discover)
        {
            try { return discover(); }
            catch (Win32Exception ex) { if (ex.NativeErrorCode == 21 || ex.NativeErrorCode == 1167) return null; throw; }
            catch (IOException ex) { int code = ex.HResult & 0xffff; if (code == 21 || code == 1167) return null; throw; }
        }
        private void ShowStatus()
        {
            if (window != null) { window.WindowState = FormWindowState.Normal; window.Activate(); return; }
            tray.ShowBalloonTip(5000, "Project Polaris", stopped ? "Detection stopped after an error. Restart only after resolving it." : "Waiting for the enrolled DWARF. No import window stays open while idle. Reports are available from this icon's menu.", ToolTipIcon.Info);
        }
        private void Record(string message)
        { if (activity != null) { try { activity.WriteLine(DateTime.Now.ToString("s") + "  " + message); activity.Flush(); } catch (IOException) { /* Detector logs are diagnostic, not copy receipts. */ } } }
        private void OpenReports(bool latest)
        {
            try
            {
                string path = latest && latestReport != null ? latestReport : RunReport.Folder;
                RunReport.CheckLocalPath(path);
                if (!File.Exists(path) && !Directory.Exists(path)) { BrandedNotice.Show("Project Polaris", "No reports yet", "Your report will open automatically after the next import finishes."); return; }
                if (latest && latestReport == null)
                {
                    var reports = new DirectoryInfo(path).GetFiles("Polaris-import-*.html");
                    Array.Sort(reports, delegate(FileInfo a, FileInfo b) { return b.LastWriteTimeUtc.CompareTo(a.LastWriteTimeUtc); });
                    if (reports.Length > 0) { path = reports[0].FullName; RunReport.CheckLocalPath(path); }
                }
                Process.Start(new ProcessStartInfo(path) { UseShellExecute = true });
            }
            catch (Exception ex) { BrandedNotice.Show("Project Polaris", "Cannot open reports", ex.Message); }
        }
        private void RequestExit()
        {
            exiting = true; poll.Stop();
            if (window == null) ExitThread();
            else window.Close(); // Existing form waits for in-progress file work to stop safely.
        }
        protected override void ExitThreadCore()
        {
            poll.Stop(); poll.Dispose(); tray.Visible = false;
            Record("Background detector exited by request."); if (activity != null) { activity.Dispose(); activity = null; }
            var icon = tray.Icon; tray.ContextMenuStrip.Dispose(); tray.Dispose(); icon.Dispose();
            base.ExitThreadCore();
        }
    }
}
