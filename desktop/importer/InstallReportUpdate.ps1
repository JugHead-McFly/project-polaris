$ErrorActionPreference = 'Stop'
$runtime = 'G:\Polaris_Runtime\StandaloneOnConnect-Calibration-20261006'
$target = Join-Path $runtime 'PolarisStandalone.exe'
$candidate = Join-Path $PSScriptRoot 'PolarisStandalone.exe'
$expected = 'C8791AA603991B144AAFF038102B482764D79F164D4E3025EDF2BECD4F106709'
if ((Get-FileHash $candidate).Hash -ne $expected) { throw 'Build differs from tested candidate' }
$task = Get-ScheduledTask -TaskName 'Project Polaris Standalone Inbox Watcher'
if ($task.Actions.Execute -ne $target) { throw 'Unexpected installed task target' }
$backup = Join-Path $runtime 'PolarisStandalone-before-report-20261007.exe.bak'
if (Test-Path -LiteralPath $backup) { throw 'Update already staged; inspect before replay' }
$processes = @(Get-Process PolarisStandalone -ErrorAction SilentlyContinue)
if ($processes.Count -gt 1) { throw 'Multiple importer processes; cannot safely update' }
Add-Type @'
using System; using System.Collections.Generic; using System.Runtime.InteropServices; using System.Text;
public static class PolarisReportUpdate {
 delegate bool Callback(IntPtr h, IntPtr p);
 [DllImport("user32.dll")] static extern bool EnumChildWindows(IntPtr h, Callback cb, IntPtr p);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr h,StringBuilder text,int size);
 public static bool Finished(IntPtr window) {
  bool found=false;
  EnumChildWindows(window,delegate(IntPtr h,IntPtr p){var text=new StringBuilder(1024);GetWindowText(h,text,1024);if(text.ToString()=="Finished — needs attention")found=true;return true;},IntPtr.Zero);
  return found;
 }
}
'@
. (Join-Path $PSScriptRoot 'CutoverNative.ps1')
$lock = [IO.File]::Open('G:\Polaris_Workspace\StandaloneHistory\import.lock',[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
try {
    if ($processes.Count -eq 1) {
        $process = $processes[0]
        if ($process.Path -ne $target) { throw 'Unexpected running importer' }
        if ($process.MainWindowHandle -ne 0) {
            if (-not [PolarisReportUpdate]::Finished($process.MainWindowHandle)) { throw 'Importer is not showing its completed report; leave it untouched' }
            if (-not $process.CloseMainWindow()) { throw 'Could not close completed window' }
            Start-Sleep -Milliseconds 800
            $process.Refresh()
        }
        if (-not $process.HasExited) {
            $thread = [PolarisCutoverNative]::IdleUiThread([uint32]$process.Id)
            if (-not [PolarisCutoverNative]::PostThreadMessage($thread,0x12,[intptr]::Zero,[intptr]::Zero)) { throw 'Could not request idle detector exit' }
            if (-not $process.WaitForExit(10000)) { throw 'Detector did not exit; no forced termination' }
        }
    }
    [IO.File]::Copy($target,$backup,$false)
    try {
        [IO.File]::Copy($candidate,$target,$true)
        if ((Get-FileHash $target).Hash -ne $expected) { throw 'Installed executable differs' }
    } catch { [IO.File]::Copy($backup,$target,$true); throw }
} finally { $lock.Dispose() }
# Do not launch: a connected telescope would trigger another import automatically.
[pscustomobject]@{Installed=$target;Backup=$backup;Hash=$expected;RestartRequired=$true;TaskAndEnrollmentUnchanged=$true} | ConvertTo-Json
