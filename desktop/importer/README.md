# Windows importer

Source baseline copied from the locally installed October 6 calibration build.
The report change does not modify copy, archive, verification, or cleanup policy.
`RunReport.cs` explains blocking holds and next steps, keeps routine reuse/deferral
counts in a collapsed technical section, and distinguishes inbox copying from
archive organization and telescope cleanup. Unknown failures retain their original
message and require review; they are never presented as routine skips.

Build: `./Build.ps1` using the installed Windows .NET Framework compiler.
Run `ReportTests.exe` and `OnConnectTests.exe` for report and lifecycle coverage.
ReportPreview is a read-only converter specifically pinned to the reviewed October
7 run, not a general importer. Original reports remain immutable.

InstallReportUpdate pins the tested executable hash, backs up the installed binary,
checks for a finished/idle importer, closes it gracefully, and updates the existing
installation. It preserves enrollment and scheduled-task/shortcut settings. It does
not restart the detector because a connected telescope would trigger another run.
Reopen Polaris when ready for the next import. No files on the DWARF or NAS are
modified by this update.
