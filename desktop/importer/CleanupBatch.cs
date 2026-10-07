using System;
using System.Threading;

namespace PolarisStandalone
{
    public sealed class BatchSummary
    {
        public int Deleted, AlreadyCleared, Held;
        public bool Cancelled;
        public long BytesFreed;
    }

    public static class CleanupBatch
    {
        public static BatchSummary Run(DeviceBinding binding, Summary imported, bool enabled, CancellationToken cancellation, Action<Progress> progress)
        {
            var result = new BatchSummary();
            // No binding, root, history, device, or progress access when disabled.
            if (!enabled) return result;
            try
            {
                cancellation.ThrowIfCancellationRequested();
                if (imported == null || imported.Cancelled || imported.Held < imported.Deferred || imported.Held > imported.Deferred)
                {
                    result.Cancelled = imported != null && imported.Cancelled;
                    if (!result.Cancelled) result.Held++;
                    Emit(progress, "Cleanup blocked: copying did not complete without blocking holds.", result, 0);
                    return result;
                }
                if (binding == null) throw new ArgumentNullException("binding");
                binding.ValidateCurrent();
                Emit(progress, "Calibration library retained on DWARF; cleanup applies to capture files only.", result, 0);
                var requests = ReceiptPlan.LoadBound(binding); // One paired-receipt inventory per batch.
                foreach (CleanupRequest request in requests)
                {
                    cancellation.ThrowIfCancellationRequested();
                    binding.ValidateCurrent();
                    CleanupResult previous = CleanupCore.InspectCompleted(request);
                    if (previous.Status == "AlreadyCleared")
                    {
                        result.AlreadyCleared++;
                        Emit(progress, "Already cleared: " + request.RelativePath, result, requests.Count);
                        continue;
                    }
                    if (previous.Status != "NotCleared")
                    {
                        result.Held++; Emit(progress, "Cleanup HOLD: " + previous.Message, result, requests.Count); break;
                    }
                    cancellation.ThrowIfCancellationRequested();
                    // Enabled policy and successful import gate authorize derivation;
                    // DeleteOne performs exactly one fresh source/NAS proof, no Assess pass.
                    string approval = CleanupCore.ApprovalFor(request);
                    CleanupResult deleted = CleanupCore.DeleteOne(request, approval, cancellation);
                    if (deleted.Status == "Deleted")
                    {
                        result.Deleted++; result.BytesFreed = checked(result.BytesFreed + request.ExpectedLength);
                        Emit(progress, "Cleared verified source: " + request.RelativePath, result, requests.Count);
                    }
                    else
                    {
                        result.Cancelled = deleted.Status == "Cancelled" || cancellation.IsCancellationRequested;
                        // UNCERTAIN remains a genuine hold, even when cancellation caused it.
                        if (deleted.Status != "Cancelled") result.Held++;
                        Emit(progress, "Cleanup stopped (" + deleted.Status + "): " + deleted.Message, result, requests.Count);
                        break;
                    }
                }
            }
            catch (OperationCanceledException) { result.Cancelled = true; }
            catch (Exception ex)
            {
                result.Held++;
                // Observers cannot turn a fault into a success or cause a retry.
                try { Emit(progress, "Cleanup HOLD: " + ex.GetType().Name + ": " + ex.Message, result, 0); } catch { }
            }
            return result;
        }

        private static void Emit(Action<Progress> observer, string message, BatchSummary summary, int total)
        { if (observer != null) observer(new Progress { Message = message, FilesDone = summary.Deleted + summary.AlreadyCleared, Total = total }); }
    }
}
