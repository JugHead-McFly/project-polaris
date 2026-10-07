#if UI_OFFLINE_FIXTURE
using System;
using System.IO;
using System.Drawing;
using System.Reflection;
using System.Threading;
using System.Windows.Forms;

namespace PolarisStandalone
{
    // This compile-only substitute performs no device, state, or network I/O.
    public sealed class DeviceEnrollment { public bool AllowCleanup; }
    public sealed class DeviceBinding
    {
        public string CurrentRoot = @"J:\", ReceiptRoot = @"I:\", NasRoot = "fixture NAS", StateRoot = "fixture state";
        public bool Invalid;
        public void ValidateCurrent() { if (Invalid) throw new InvalidOperationException("Device changed"); }
    }
    public static class DeviceIdentity
    {
        public static int Loads, Probes;
        public static DeviceEnrollment Enrollment;
        public static DeviceBinding Binding;
        public static bool Throw;
        public static DeviceEnrollment LoadEnrollment(string path) { Loads++; return Enrollment; }
        public static DeviceBinding Discover(DeviceEnrollment value)
        { Probes++; if (Throw) throw new InvalidOperationException("Ambiguous device"); return Binding; }
    }
    public sealed class Summary { public int Copied, Reused, Held, Deferred; public bool Cancelled; }
    public sealed class Progress { public string Message; public int Total, FilesDone; }
    public sealed class BatchSummary { public int Deleted, AlreadyCleared, Held; public long BytesFreed; public bool Cancelled; }
    public static class Importer
    {
        public static int Calls;
        public static Summary Result = new Summary();
        public static bool Fail, Block;
        public static Summary RunBound(DeviceBinding binding, CancellationToken token, Action<Progress> progress)
        {
            Calls++;
            if (Fail) throw new InvalidOperationException("Import failed");
            while (Block && !token.IsCancellationRequested) Thread.Sleep(5);
            if (token.IsCancellationRequested) return new Summary { Cancelled = true };
            progress(new Progress { Message = "Fixture copy", Total = 1, FilesDone = 1 }); return Result;
        }
    }
    public static class CleanupBatch
    {
        public static int Calls;
        public static bool Fail, Block;
        public static BatchSummary Result = new BatchSummary();
        public static BatchSummary Run(DeviceBinding binding, Summary imported, bool enabled, CancellationToken token, Action<Progress> progress)
        {
            Calls++;
            if (!enabled) throw new Exception("Not enabled");
            if (Fail) throw new InvalidOperationException("Cleanup failed");
            while (Block && !token.IsCancellationRequested) Thread.Sleep(5);
            if (token.IsCancellationRequested) return new BatchSummary { Cancelled = true, Deleted = 1, BytesFreed = 42 };
            progress(new Progress { Message = "Fixture cleanup", Total = 1, FilesDone = 1 }); return Result;
        }
    }
    public sealed class ArchiveSummary { public int Total=1; public string Evidence="fixture archive evidence"; public override string ToString(){return "Archive fixture passed";} }
    public static class ArchivePublisher {
        public const string Library="fixture organized archive";
        public static bool Fail, Cancel;
        public static int Calls;
        public static ArchiveSummary RunProduction(CancellationToken token,Action<Progress> progress,bool forceVerify){Calls++;if(Fail)throw new IOException("Archive publication failed");if(Cancel)throw new OperationCanceledException();return new ArchiveSummary();}
    }
}
#endif
