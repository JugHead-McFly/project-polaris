using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace PolarisStandalone
{
    internal static class Program
    {
        [STAThread]
        private static void Main(string[] args)
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            if ((args.Length == 2 && args[0] == "--preview") || (args.Length == 3 && args[0] == "--preview-state"))
            {
                string output = args[args.Length - 1];
                string previewState = args.Length == 3 ? args[1] : "waiting";
                if (previewState != "waiting" && previewState != "copying" && previewState != "clearing" && previewState != "completed" && previewState != "error") { Console.Error.WriteLine("Unknown synthetic preview state. Nothing started."); Environment.ExitCode = 2; return; }
                using (MainWindow preview = new MainWindow(false, false, true))
                using (Bitmap bitmap = new Bitmap(preview.Width, preview.Height))
                {
                    preview.SetPreviewState(previewState);
                    preview.ShowInTaskbar = false;
                    preview.StartPosition = FormStartPosition.Manual;
                    preview.Location = new Point(-32000, -32000);
                    preview.Show();
                    preview.ClearPreviewSelection();
                    Application.DoEvents();
                    preview.DrawToBitmap(bitmap, new Rectangle(0, 0, bitmap.Width, bitmap.Height));
                    using (FileStream file = new FileStream(output, FileMode.CreateNew, FileAccess.Write))
                        bitmap.Save(file, System.Drawing.Imaging.ImageFormat.Png);
                }
                return;
            }
            bool onConnect = args.Length == 1 && args[0] == "--on-connect-approved-inbox-and-clear";
            bool clear = args.Length == 1 && args[0] == "--watch-approved-inbox-and-clear";
            bool automatic = clear || (args.Length == 1 && args[0] == "--watch-approved-inbox");
            if (args.Length != 0 && !automatic && !onConnect) { MessageBox.Show("Unrecognized startup option. Nothing started."); return; }
            bool first;
            using (Mutex singleton = new Mutex(true, "Local\\PolarisStandaloneRev1", out first))
            {
                if (!first) { MessageBox.Show("Polaris is already open."); return; }
                try
                {
                    if (onConnect) Application.Run(new OnConnectContext());
                    else Application.Run(new MainWindow(automatic, clear));
                }
                finally { singleton.ReleaseMutex(); }
            }
        }
    }

    internal enum DeviceState { Missing, Unready, Ready }
    internal sealed class PolarisCheckBox : CheckBox
    {
        protected override void OnPaint(PaintEventArgs e)
        {
            e.Graphics.Clear(BackColor);
            Rectangle glyph = new Rectangle(0, Math.Max(0, (Height - 14) / 2), 14, 14);
            using (var pen = new Pen(Color.FromArgb(83, 216, 205))) e.Graphics.DrawRectangle(pen, glyph);
            if (Checked) using (var pen = new Pen(Color.FromArgb(83, 216, 205), 2)) e.Graphics.DrawLines(pen, new Point[] { new Point(3,glyph.Top+7), new Point(6,glyph.Top+10), new Point(11,glyph.Top+4) });
            TextRenderer.DrawText(e.Graphics, Text, Font, new Rectangle(22,0,Width-22,Height), Enabled ? ForeColor : Color.FromArgb(128,173,191), TextFormatFlags.Left | TextFormatFlags.VerticalCenter | TextFormatFlags.WordBreak);
            if (Focused && ShowFocusCues) ControlPaint.DrawFocusRectangle(e.Graphics,new Rectangle(19,1,Width-21,Height-2),ForeColor,BackColor);
        }
    }
    internal sealed class PolarisButton : Button
    {
        protected override void OnPaint(PaintEventArgs e)
        {
            Color background=Enabled?BackColor:Color.FromArgb(8,25,35), foreground=Enabled?ForeColor:Color.FromArgb(128,173,191);
            e.Graphics.Clear(background);using(var pen=new Pen(Color.FromArgb(27,69,76)))e.Graphics.DrawRectangle(pen,0,0,Width-1,Height-1);
            TextRenderer.DrawText(e.Graphics,Text,Font,ClientRectangle,foreground,TextFormatFlags.HorizontalCenter|TextFormatFlags.VerticalCenter);
            if(Focused&&ShowFocusCues)ControlPaint.DrawFocusRectangle(e.Graphics,new Rectangle(4,4,Width-8,Height-8),foreground,background);
        }
    }
    internal sealed class PolarisProgress : ProgressBar
    {
        public PolarisProgress(){SetStyle(ControlStyles.UserPaint|ControlStyles.AllPaintingInWmPaint|ControlStyles.OptimizedDoubleBuffer,true);}
        protected override void OnPaint(PaintEventArgs e)
        { e.Graphics.Clear(Color.FromArgb(22,49,56));int fill=Maximum<=Minimum?0:(int)((long)(Value-Minimum)*Width/(Maximum-Minimum));using(var brush=new SolidBrush(Color.FromArgb(83,216,205)))e.Graphics.FillRectangle(brush,0,0,fill,Height); }
    }
    internal sealed class BorderedTable : TableLayoutPanel
    {
        public BorderedTable() { DoubleBuffered = true; }
        protected override void OnPaint(PaintEventArgs e)
        {
            base.OnPaint(e); e.Graphics.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.AntiAlias;
            using (var pen = new Pen(Color.FromArgb(27, 69, 76)))
            using (var path = new System.Drawing.Drawing2D.GraphicsPath())
            { int r = 14, w = Math.Max(15, Width - 1), h = Math.Max(15, Height - 1); path.AddArc(0, 0, r, r, 180, 90); path.AddArc(w-r,0,r,r,270,90); path.AddArc(w-r,h-r,r,r,0,90); path.AddArc(0,h-r,r,r,90,90); path.CloseFigure(); e.Graphics.DrawPath(pen,path); }
        }
    }
    internal sealed class ReconnectGate
    {
        private int present, absent;
        private bool handled;
        public void Reset() { present = absent = 0; handled = false; }
        public bool ShouldStart(DeviceState state)
        {
            if (state == DeviceState.Missing)
            { present = 0; if (++absent >= 2) handled = false; return false; }
            absent = 0;
            if (state != DeviceState.Ready) { present = 0; return false; }
            if (handled || ++present < 3) return false;
            handled = true; return true;
        }
    }

    internal sealed class MainWindow : Form
    {
        private readonly TextBox source = new TextBox();
        private readonly TextBox destination = new TextBox();
        private readonly TextBox history = new TextBox();
        private readonly CheckBox watch = new PolarisCheckBox();
        private readonly CheckBox cleanup = new PolarisCheckBox();
        private readonly Label policy = new Label();
        private readonly Label safety = new Label();
        private readonly Button start = new PolarisButton();
        private readonly Button stop = new PolarisButton();
        private readonly Label status = new Label();
        private readonly Label detail = new Label();
        private readonly Label elapsed = new Label();
        private readonly ProgressBar bar = new PolarisProgress();
        private readonly TextBox log = new TextBox();
        private readonly System.Windows.Forms.Timer timer = new System.Windows.Forms.Timer();
        private readonly Stopwatch clock = new Stopwatch();
        private CancellationTokenSource cancellation;
        private bool armed, busy, closeAfterStop;
        private readonly ReconnectGate connection = new ReconnectGate();
        private DeviceState? lastDevice;
        private StreamWriter sessionLog;
        private DeviceEnrollment enrollment;
        private DeviceBinding readyBinding;
        private bool clearThisRun;
        private string probeError;
        private readonly bool previewOnly;
        private readonly bool oneShot;
        private System.Windows.Forms.Timer closeTimer;
        internal string LastReportPath { get; private set; }
        private readonly Label progressCount = new Label();
        private readonly Label phase = new Label();
        private static readonly Color Navy = Color.FromArgb(5, 14, 21), Surface = Color.FromArgb(8, 25, 35), Muted = Color.FromArgb(128, 173, 191), Cyan = Color.FromArgb(83, 216, 205);

        private sealed class CycleResult
        {
            public Summary Import;
            public BatchSummary Cleanup;
        }

        public MainWindow() : this(false, false) { }
        public MainWindow(bool automatic) : this(automatic, false) { }
        public MainWindow(bool automatic, bool automaticClear) : this(automatic, automaticClear, false) { }
        public MainWindow(bool automatic, bool automaticClear, bool previewOnly) : this(automatic, automaticClear, previewOnly, false) { }
        internal MainWindow(bool automatic, bool automaticClear, bool previewOnly, bool oneShot)
        {
            this.previewOnly = previewOnly;
            this.oneShot = oneShot;
            Text = "Project Polaris — DWARF Ingestion";
            Icon = PolarisMark.WindowIcon();
            ClientSize = new Size(1100, 850);
            MinimumSize = new Size(920, 810);
            StartPosition = FormStartPosition.CenterScreen;
            AutoScaleMode = AutoScaleMode.Dpi;
            Font = new Font("Segoe UI", 10F);
            BackColor = Navy; ForeColor = Color.FromArgb(238, 242, 234);
            Padding = new Padding(24, 18, 24, 18);
            var layout = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 1, RowCount = 6, Margin = Padding.Empty, BackColor = Navy };
            foreach (float height in new float[] { 104, 184, 76, 120, 94 }) layout.RowStyles.Add(new RowStyle(SizeType.Absolute, height));
            layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100)); Controls.Add(layout);
            var header = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 2, Margin = Padding.Empty };
            header.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 65)); header.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 35));
            var title = new TableLayoutPanel { Dock = DockStyle.Fill, RowCount = 2, Margin = Padding.Empty };
            title.RowStyles.Add(new RowStyle(SizeType.Absolute, 58)); title.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
            title.Controls.Add(new Label { Text = "Project Polaris", Font = new Font("Segoe UI Semibold", 28, FontStyle.Bold), ForeColor = ForeColor, Dock = DockStyle.Fill, Margin = Padding.Empty }, 0, 0);
            title.Controls.Add(new Label { Text = "DWARF INGESTION", Font = new Font("Segoe UI", 10, FontStyle.Bold), ForeColor = Cyan, Dock = DockStyle.Fill, Margin = new Padding(3, 0, 0, 0) }, 0, 1);
            var brand = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 2, Margin = Padding.Empty };
            brand.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 82)); brand.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            brand.Controls.Add(new PolarisMark { Dock = DockStyle.Fill, Margin = new Padding(0, 3, 12, 22) }, 0, 0);
            brand.Controls.Add(title, 1, 0); header.Controls.Add(brand, 0, 0);
            var artwork = new PictureBox { Dock = DockStyle.Fill, SizeMode = PictureBoxSizeMode.Zoom, AccessibleName = "Polaris project artwork", Margin = new Padding(16, 0, 0, 10), TabStop = false };
            using (Stream art = System.Reflection.Assembly.GetExecutingAssembly().GetManifestResourceStream("Polaris.Artwork"))
                if (art != null) using (Image original = Image.FromStream(art)) artwork.Image = new Bitmap(original);
            if (artwork.Image != null) header.Controls.Add(artwork, 1, 0);
            else { artwork.Dispose(); header.Controls.Add(new Label { Text = "COPY  /  VERIFY  /  CLEAR\nYour imaging companion", TextAlign = ContentAlignment.MiddleRight, ForeColor = Muted, Dock = DockStyle.Fill, Margin = new Padding(0, 0, 0, 18) }, 1, 0); }
            layout.Controls.Add(header, 0, 0);
            var policyPanel = StackPanel(2, new float[] { 29, 31 });
            policy.Font = new Font("Segoe UI Semibold", 12, FontStyle.Bold); policy.ForeColor = Color.White;
            safety.ForeColor = Color.FromArgb(145, 223, 204);
            FillLabel(policy); FillLabel(safety); policyPanel.Controls.Add(policy, 0, 0); policyPanel.Controls.Add(safety, 0, 1); layout.Controls.Add(policyPanel, 0, 2);
            UpdatePolicy(false);
            var routes = new BorderedTable { Dock = DockStyle.Fill, ColumnCount = 2, RowCount = 3, Padding = new Padding(16, 9, 16, 9), Margin = new Padding(0, 0, 0, 10), BackColor = Surface };
            routes.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 162)); routes.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            AddRoute(routes, "DWARF device", source, "Automatic — enrolled DWARF", 0);
            AddRoute(routes, "Capture archive", destination, ArchivePublisher.Library, 1);
            AddRoute(routes, "Import history", history, @"G:\Polaris_Workspace\StandaloneHistory", 2);
            layout.Controls.Add(routes, 0, 3);
            source.ReadOnly = destination.ReadOnly = history.ReadOnly = true;
            var actions = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 2, RowCount = 1, Margin = Padding.Empty };
            actions.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100)); actions.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 250));
            var options = StackPanel(2, new float[] { 35, 35 }); options.Padding = Padding.Empty;
            watch.Text = "Keep watching for the DWARF after this import";
            watch.Checked = !oneShot;
            if (oneShot) { watch.Text = "Close after success and saving the HTML report"; watch.Enabled = false; }
            watch.Dock = DockStyle.Fill; watch.Margin = Padding.Empty; watch.AccessibleName = "Keep watching for reconnect"; options.Controls.Add(watch, 0, 0);
            if (oneShot) { options.Controls.Remove(watch); options.Controls.Add(new Label { Text = "Automatic import — closes after success and HTML report", ForeColor = Cyan, Dock = DockStyle.Fill, TextAlign = ContentAlignment.MiddleLeft }, 0, 0); }
            cleanup.Text = "Clear verified DWARF files after import (not enabled yet)";
            cleanup.Checked = false; cleanup.Enabled = false; cleanup.Dock = DockStyle.Fill; cleanup.Margin = Padding.Empty;
            cleanup.CheckedChanged += delegate { if (!armed && !busy) UpdatePolicy(cleanup.Checked); };
            options.Controls.Add(cleanup, 0, 1); actions.Controls.Add(options, 0, 0);
            var buttons = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 2, Padding = new Padding(0, 15, 0, 20), Margin = Padding.Empty };
            buttons.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 50)); buttons.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 50));
            StyleButton(start, "Start", Cyan, Navy); StyleButton(stop, "Stop", Surface, Color.White); stop.Enabled = false;
            start.Click += delegate { Arm(false, false); }; stop.Click += delegate { StopWork(); }; buttons.Controls.Add(start, 0, 0); buttons.Controls.Add(stop, 1, 0); actions.Controls.Add(buttons, 1, 0); layout.Controls.Add(actions, 0, 4);
            var progressPanel = new BorderedTable { Dock = DockStyle.Fill, ColumnCount = 2, RowCount = 4, BackColor = Surface, Padding = new Padding(16, 10, 16, 12), Margin = new Padding(0, 0, 0, 12) };
            progressPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 75)); progressPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 25));
            foreach (float h in new float[] { 21, 42, 60, 18 }) progressPanel.RowStyles.Add(new RowStyle(SizeType.Absolute, h));
            phase.Text = "SESSION STATUS"; phase.ForeColor = Cyan; phase.Font = new Font("Segoe UI", 9, FontStyle.Bold); FillLabel(phase); progressPanel.Controls.Add(phase, 0, 0);
            elapsed.TextAlign = ContentAlignment.MiddleRight; elapsed.Text = "Elapsed: 00:00:00"; elapsed.ForeColor = Muted; FillLabel(elapsed); progressPanel.Controls.Add(elapsed, 1, 0);
            status.Text = "Not started"; status.Font = new Font("Segoe UI Semibold", 20, FontStyle.Bold); FillLabel(status); progressPanel.Controls.Add(status, 0, 1); progressPanel.SetColumnSpan(status, 2);
            detail.Text = "Start checks the approved device identity, not its drive letter. Cleanup is off by default.";
            detail.ForeColor = Muted; FillLabel(detail); progressPanel.Controls.Add(detail, 0, 2); progressPanel.SetColumnSpan(detail, 2);
            bar.Dock = DockStyle.Fill; bar.Margin = new Padding(0, 3, 14, 3); bar.AccessibleName = "File progress"; progressPanel.Controls.Add(bar, 0, 3);
            progressCount.Text = "Ready when you are"; progressCount.TextAlign = ContentAlignment.MiddleRight; progressCount.Font = new Font("Segoe UI", 9); FillLabel(progressCount); progressPanel.Controls.Add(progressCount, 1, 3); layout.Controls.Add(progressPanel, 0, 1);
            var logs = StackPanel(2, new float[] { 28 }); logs.RowStyles.Add(new RowStyle(SizeType.Percent, 100)); logs.Padding = Padding.Empty;
            logs.Controls.Add(new Label { Text = "SESSION DETAILS", Dock = DockStyle.Fill, ForeColor = Muted, Font = new Font("Segoe UI", 9, FontStyle.Bold), Margin = Padding.Empty }, 0, 0);
            log.Dock = DockStyle.Fill; log.Margin = Padding.Empty; log.Multiline = true; log.ReadOnly = true; log.ScrollBars = ScrollBars.Vertical; log.BackColor = Surface; log.ForeColor = Color.FromArgb(200, 218, 233); log.BorderStyle = BorderStyle.FixedSingle; log.Font = new Font("Consolas", 9.5F); log.AccessibleName = "Read-only session detail log"; logs.Controls.Add(log, 0, 1); layout.Controls.Add(logs, 0, 5);
            status.TextChanged += delegate { RefreshStatusColor(); };
            timer.Interval = 1000;
            timer.Tick += delegate { Tick(); };
            FormClosing += OnClosing;
            if (automatic && !previewOnly) Shown += delegate { Arm(true, automaticClear); if (armed && !oneShot) WindowState = FormWindowState.Minimized; };
        }

        private static TableLayoutPanel StackPanel(int rows, float[] heights)
        { var panel = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 1, RowCount = rows, Margin = Padding.Empty, Padding = new Padding(2, 4, 2, 4) }; foreach (float height in heights) panel.RowStyles.Add(new RowStyle(SizeType.Absolute, height)); return panel; }
        private static void FillLabel(Label label) { label.Dock = DockStyle.Fill; label.Margin = Padding.Empty; }
        private static void StyleButton(Button button, string text, Color background, Color foreground)
        { button.Text = text; button.AccessibleName = text + " watcher"; button.Dock = DockStyle.Fill; button.Margin = new Padding(8, 0, 0, 0); button.FlatStyle = FlatStyle.Flat; button.FlatAppearance.BorderColor = Color.FromArgb(27, 69, 76); button.BackColor = background; button.ForeColor = foreground; button.Font = new Font("Segoe UI", 11, FontStyle.Bold); button.UseVisualStyleBackColor = false; }
        private static void AddRoute(TableLayoutPanel panel, string caption, TextBox box, string value, int row)
        { panel.RowStyles.Add(new RowStyle(SizeType.Percent, 33.333F)); panel.Controls.Add(new Label { Text = caption, ForeColor = Muted, Dock = DockStyle.Fill, TextAlign = ContentAlignment.MiddleLeft, Margin = Padding.Empty }, 0, row); box.Text = value; box.Dock = DockStyle.Fill; box.Margin = new Padding(0, 5, 0, 0); box.BorderStyle = BorderStyle.None; box.BackColor = Surface; box.ForeColor = Color.FromArgb(238, 242, 234); box.AccessibleName = caption; panel.Controls.Add(box, 1, row); }
        private void RefreshStatusColor()
        { string value = status.Text.ToLowerInvariant(); status.ForeColor = value.Contains("attention") || value.Contains("error") ? Color.FromArgb(247, 189, 124) : value.Contains("finished") ? Color.FromArgb(115, 211, 159) : Color.FromArgb(238, 242, 234); }
        internal void SetPreviewState(string state)
        {
            if (!previewOnly) throw new InvalidOperationException("Synthetic states require isolated preview mode.");
            if (state != "waiting" && state != "copying" && state != "clearing" && state != "completed" && state != "error") throw new ArgumentException("Unknown preview state.");
            timer.Stop(); armed = busy = false; start.Enabled = stop.Enabled = watch.Enabled = cleanup.Enabled = false;
            phase.Text = "DESIGN PREVIEW — SIMULATED DATA / NO DEVICE ACCESS";
            elapsed.Text = "Elapsed: " + (state == "waiting" ? "00:00:00" : "00:04:32");
            bar.Maximum = 120; bar.Value = state == "waiting" ? 0 : state == "completed" ? 120 : 78;
            status.Text = state == "waiting" ? "Waiting for the DWARF" : state == "copying" ? "Importing" : state == "clearing" ? "Verifying and clearing DWARF files" : state == "completed" ? "Import finished" : "Stopped — needs attention";
            detail.Text = state == "waiting" ? "No copying is happening. Connect a fully booted DWARF with capture stopped." : state == "copying" ? "Copying: Astronomy\\Imaging session\\frame_0078.fits\nNew files are copied and freshly verified. Existing NAS files are never replaced." : state == "clearing" ? "Freshly comparing each eligible source with its NAS copy before source-only deletion." : state == "completed" ? "120 copied and verified · 0 metadata reused (not rehashed) · 0 deferred · 0 need attention. Source cleanup off. Waiting for the next disconnect/reconnect." : "Example HOLD: source and NAS hashes differ. Source retained. Nothing else will be cleared.";
            cleanup.Checked = state == "clearing"; cleanup.Text = "Clear verified DWARF files after import" + (state == "clearing" ? " (simulated)" : " (not enabled yet)");
            UpdatePolicy(state == "clearing"); progressCount.Text = state == "waiting" ? "Waiting · no files in progress" : bar.Value + " / 120 files"; bar.Invalidate();
            log.Text = "PREVIEW ONLY — synthetic session. No watcher is armed." + Environment.NewLine + "18:42:00  Enrolled-device identity check (simulated)." + Environment.NewLine + "18:42:03  " + status.Text + Environment.NewLine + "18:42:04  Existing NAS content remains protected.";
        }
        internal void ClearPreviewSelection() { if (previewOnly) { ActiveControl = log; source.DeselectAll(); destination.DeselectAll(); history.DeselectAll(); log.DeselectAll(); } }

        private void AddLabel(string text, int x, int y, int width, int height, float size, Color color)
        {
            Label label = new Label { Text = text, ForeColor = color, Font = new Font("Segoe UI", size) };
            label.SetBounds(x, y, width, height); Controls.Add(label);
        }
        private void AddInput(TextBox input, string value, int x, int y)
        { input.Text = value; input.SetBounds(x, y, 640, 30); Controls.Add(input); }
        private void SetEditing(bool enabled)
        {
            bool permitted = enrollment != null && enrollment.AllowCleanup;
            watch.Enabled = enabled && !oneShot; start.Enabled = enabled; cleanup.Enabled = enabled && permitted; stop.Enabled = !enabled;
            cleanup.Text = "Clear verified DWARF files after import" + (permitted ? "" : " (not enabled yet)");
        }
        private void UpdatePolicy(bool enabled)
        {
            policy.Text = enabled ? "Copy, freshly verify, then clear approved DWARF files." : "Copy new pictures. Keep your originals.";
            safety.Text = enabled ? "Only verified source files can be cleared. No replacing or deleting existing NAS files." : "No source deletion. No replacing or deleting existing NAS files.";
        }
        private void AddLog(string text)
        {
            string line = DateTime.Now.ToString("s") + "  " + text;
            log.AppendText(line + Environment.NewLine);
            if (sessionLog != null)
            {
                try { sessionLog.WriteLine(line); sessionLog.Flush(); }
                catch (IOException) { /* Copy receipts remain authoritative if the UI log disk fails. */ }
            }
        }
        private static void CheckLogPath(string path)
        {
            for (string part = path; !String.IsNullOrEmpty(part); part = Path.GetDirectoryName(part))
            {
                try { if ((File.GetAttributes(part) & FileAttributes.ReparsePoint) != 0) throw new IOException("Watcher log path must not be redirected."); }
                catch (FileNotFoundException) { }
                catch (DirectoryNotFoundException) { }
            }
        }
        private void Arm(bool automatic, bool automaticClear)
        {
            if (previewOnly) return;
            try
            {
                enrollment = DeviceIdentity.LoadEnrollment(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "device.xml"));
                if (enrollment == null) throw new InvalidOperationException("Approved DWARF enrollment is missing. Nothing started.");
                clearThisRun = automatic ? automaticClear : cleanup.Checked;
                if (clearThisRun && !enrollment.AllowCleanup)
                    throw new InvalidOperationException("Automatic source cleanup has not been approved in this device enrollment. Nothing started.");
                cleanup.Checked = clearThisRun; UpdatePolicy(clearThisRun); SetEditing(true);
                if (!automatic && MessageBox.Show(this, "Polaris will find only the enrolled DWARF, even if its drive letter changes.\n\nDestination: " + destination.Text +
                    "\n\nExisting NAS files will never be replaced or deleted.\n" + (clearThisRun ?
                    "Eligible DWARF originals will be deleted only after a fresh source-versus-NAS hash match. Temporary, system, and uncertain files stay put." :
                    "All originals stay on the DWARF; source cleanup is off.") + "\n\nStart?",
                    clearThisRun ? "Confirm import and source clearing" : "Confirm source-preserving import", MessageBoxButtons.YesNo, MessageBoxIcon.Question, MessageBoxDefaultButton.Button2) != DialogResult.Yes) return;
                if (sessionLog == null)
                {
#if UI_OFFLINE_FIXTURE
                    string logFolder = Path.Combine(RunReport.Folder, "fixture-logs");
#else
                    string logFolder = @"G:\Polaris_Workspace\StandaloneWatcherLogs";
#endif
                    CheckLogPath(logFolder); Directory.CreateDirectory(logFolder); CheckLogPath(logFolder);
                    string logFile = Path.Combine(logFolder, "watcher-" + DateTime.UtcNow.ToString("yyyyMMdd-HHmmss") + "-" + Guid.NewGuid().ToString("N") + ".log");
                    sessionLog = new StreamWriter(new FileStream(logFile, FileMode.CreateNew, FileAccess.Write, FileShare.Read));
                }
                armed = true; readyBinding = null; connection.Reset(); lastDevice = null; clock.Reset(); SetEditing(false); timer.Start();
                status.Text = "Waiting for the DWARF"; detail.Text = "The app is active. Connect a fully booted DWARF with capture stopped.";
                AddLog("Watching started; enrolled device identity required; source cleanup " + (clearThisRun ? "approved and enabled" : "OFF") + "; no files copied yet.");
            }
            catch (Exception ex)
            {
                armed = false; clearThisRun = false; cleanup.Checked = false; UpdatePolicy(false); timer.Stop(); SetEditing(true);
                status.Text = "Not watching — needs attention"; detail.Text = ex.Message; AddLog("START FAILED: " + ex.Message);
                if (!automatic) MessageBox.Show(this, ex.Message, "Cannot start", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
        }
        private DeviceState ProbeDevice()
        {
            if (previewOnly) return DeviceState.Missing;
            readyBinding = null; probeError = null;
            try
            {
                DeviceBinding binding = DeviceIdentity.Discover(enrollment);
                if (binding == null) { source.Text = "Automatic — enrolled DWARF not connected"; return DeviceState.Missing; }
                binding.ValidateCurrent(); readyBinding = binding;
                source.Text = "Automatic — enrolled DWARF on " + binding.CurrentRoot;
                destination.Text = ArchivePublisher.Library; history.Text = binding.StateRoot;
                return DeviceState.Ready;
            }
            catch (Exception ex) { probeError = ex.Message; return DeviceState.Unready; }
        }
        private void Tick()
        {
            if (previewOnly) return;
            elapsed.Text = "Elapsed: " + clock.Elapsed.ToString(@"hh\:mm\:ss");
            if (!armed || busy) return;
            DeviceState device = ProbeDevice();
            if (lastDevice != device) { AddLog("Device status: " + device); lastDevice = device; }
            bool begin = connection.ShouldStart(device);
            if (device == DeviceState.Unready)
            {
                armed = false; timer.Stop(); SetEditing(true);
                status.Text = "Stopped — device needs attention";
                detail.Text = "DWARF identity or readiness is uncertain. " + probeError;
                AddLog(status.Text + ": " + detail.Text); return;
            }
            if (device != DeviceState.Ready)
            {
                status.Text = "Waiting for the DWARF";
                detail.Text = "No copying is happening. This window is waiting for a ready DWARF drive."; return;
            }
            if (begin) BeginImport(readyBinding);
        }
        private void ReportProgress(Progress p)
        {
            if (IsDisposed || !IsHandleCreated) return;
            BeginInvoke((Action)delegate
            {
                detail.Text = p.Message;
                if (p.Message.StartsWith("HOLD:", StringComparison.Ordinal) || p.Message.StartsWith("DEFERRED (still held):", StringComparison.Ordinal) ||
                    p.Message.IndexOf("cleanup", StringComparison.OrdinalIgnoreCase) >= 0 &&
                    (p.Message.IndexOf("hold", StringComparison.OrdinalIgnoreCase) >= 0 || p.Message.IndexOf("stopped", StringComparison.OrdinalIgnoreCase) >= 0)) AddLog(p.Message);
                bar.Maximum = Math.Max(1, p.Total); bar.Value = Math.Min(bar.Maximum, Math.Max(0, p.FilesDone));
                bar.Invalidate();
                progressCount.Text = p.Total > 0 ? bar.Value.ToString("N0") + " / " + p.Total.ToString("N0") + " files" : "File total unavailable";
            });
        }
        private void BeginImport(DeviceBinding binding)
        {
            if (previewOnly) return;
            busy = true; clock.Restart(); cancellation = new CancellationTokenSource();
            CancellationToken token = cancellation.Token;
            status.Text = "Importing"; detail.Text = "Checking files and copying new ones…"; AddLog("Import started.");
            Task.Factory.StartNew(delegate
            {
                if (binding == null) throw new IOException("The enrolled device binding is unavailable.");
                binding.ValidateCurrent();
                CycleResult result = new CycleResult();
                result.Import = Importer.RunBound(binding, token, ReportProgress);
                if (!result.Import.Cancelled && result.Import.Held == result.Import.Deferred)
                {
                    if (!IsDisposed) BeginInvoke((Action)delegate
                    {
                        status.Text = "Organizing capture archive";
                        detail.Text = "Publishing verified captures by target, capture date and session…";
                        AddLog("Archive publication started. Inbox safety copies and existing archive files are preserved.");
                    });
                    ArchiveSummary archived = ArchivePublisher.RunProduction(token, ReportProgress, false);
                    ReportProgress(new Progress { Message = archived.ToString() + ". Evidence: " + archived.Evidence, FilesDone = archived.Total, Total = archived.Total });
                }
                if (clearThisRun && !result.Import.Cancelled && result.Import.Held == result.Import.Deferred)
                {
                    if (!IsDisposed) BeginInvoke((Action)delegate
                    {
                        status.Text = "Verifying and clearing DWARF files";
                        detail.Text = "Freshly comparing each eligible source with its NAS copy before source-only deletion.";
                        AddLog("Source cleanup phase started. Fresh hashes are required; metadata reuse is not deletion evidence.");
                    });
                    result.Cleanup = CleanupBatch.Run(binding, result.Import, true, token, ReportProgress);
                }
                return result;
            }, token).ContinueWith(delegate(Task<CycleResult> work)
            {
                if (IsDisposed) return;
                BeginInvoke((Action)delegate
                {
                    busy = false; clock.Stop(); cancellation.Dispose(); cancellation = null;
                    if (work.IsFaulted)
                    { status.Text = "Stopped — needs attention"; detail.Text = work.Exception.GetBaseException().Message; armed = false; }
                    else if (work.IsCanceled || work.Result.Import.Cancelled || (work.Result.Cleanup != null && work.Result.Cleanup.Cancelled))
                    {
                        status.Text = "Stopped";
                        detail.Text = "Stopped. Completed actions remain recorded; any uncertain cleanup outcome needs review.";
                        if (!work.IsCanceled && work.Result.Cleanup != null) detail.Text += " " + CleanupText(work.Result.Cleanup);
                        armed = false;
                    }
                    else
                    {
                        Summary s = work.Result.Import;
                        BatchSummary cleared = work.Result.Cleanup;
                        int blocking = s.Held - s.Deferred;
                        detail.Text = String.Format("{0} copied and verified · {1} metadata reused (not rehashed) · {2} deferred · {3} need attention", s.Copied, s.Reused, s.Deferred, blocking);
                        if (cleared != null) { detail.Text += ". " + CleanupText(cleared); blocking += cleared.Held; }
                        else detail.Text += clearThisRun ? ". Cleanup did not run." : ". Source cleanup off.";
                        status.Text = blocking > 0 ? "Finished — needs attention" : "Import finished";
                        if (blocking > 0 || !watch.Checked) armed = false;
                        else detail.Text += ". Waiting for the next disconnect/reconnect.";
                    }
                    AddLog(status.Text + ": " + detail.Text);
                    if (!armed) { timer.Stop(); clock.Stop(); SetEditing(true); }
                    if (oneShot && !previewOnly)
                    {
                        armed = false; timer.Stop();
                        bool complete = !work.IsFaulted && !work.IsCanceled;
                        CycleResult outcome = complete ? work.Result : null;
                        bool succeeded = complete && RunReport.IsSuccessful(outcome.Import, outcome.Cleanup, clearThisRun);
                        try
                        {
                            LastReportPath = RunReport.Save(RunReport.Folder, status.Text, detail.Text, clock.Elapsed,
                                outcome == null ? null : outcome.Import, outcome == null ? null : outcome.Cleanup,
                                clearThisRun, log.Text);
                            AddLog("HTML report saved: " + LastReportPath);
                            try { RunReport.OpenSaved(LastReportPath); AddLog("Opened saved HTML report."); }
                            catch (Exception openError)
                            {
                                succeeded = false;
                                status.Text = "Finished — report needs attention";
                                detail.Text = "Your HTML report was saved, but could not be opened. " + openError.Message + " Report: " + LastReportPath;
                                AddLog(detail.Text);
                            }
                            if (succeeded && !closeAfterStop)
                            {
                                detail.Text += ". HTML report opened. Closing in 5 seconds; you may eject the DWARF.";
                                start.Enabled = stop.Enabled = cleanup.Enabled = false;
                                closeTimer = new System.Windows.Forms.Timer { Interval = 5000 };
                                closeTimer.Tick += delegate { closeTimer.Stop(); Close(); };
                                closeTimer.Start();
                            }
                        }
                        catch (Exception ex)
                        {
                            status.Text = "Finished — report needs attention";
                            detail.Text = "The HTML report could not be saved. " + ex.Message;
                            AddLog(detail.Text);
                        }
                    }
                    if (closeAfterStop) Close();
                });
            });
        }
        private static string CleanupText(BatchSummary result)
        {
            return String.Format("{0} cleared · {1} already cleared · {2} cleanup holds · {3:N0} bytes freed", result.Deleted, result.AlreadyCleared, result.Held, result.BytesFreed);
        }
        private void StopWork()
        {
            armed = false;
            if (cancellation != null) { cancellation.Cancel(); status.Text = "Stopping…"; detail.Text = "Waiting for the current file operation to close safely."; }
            else { timer.Stop(); clock.Stop(); SetEditing(true); status.Text = "Stopped"; detail.Text = "Nothing is running."; }
        }
        private void OnClosing(object sender, FormClosingEventArgs e)
        {
            if (busy) { e.Cancel = true; closeAfterStop = true; StopWork(); }
            else { if (closeTimer != null) { closeTimer.Stop(); closeTimer.Dispose(); } timer.Stop(); timer.Dispose(); if (sessionLog != null) { AddLog(oneShot ? "Import window closed; background detector handles the next connection." : "Window closed; monitoring stopped."); sessionLog.Dispose(); sessionLog = null; } }
        }
    }
}
