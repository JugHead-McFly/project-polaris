$ErrorActionPreference='Stop'
$compiler='C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
Push-Location $PSScriptRoot
try {
    $backend=@('Core.cs','CalibrationVersions.cs','CleanupCore.cs','CleanupBatch.cs','DeviceIdentity.cs','ReceiptPlan.cs')
    $ui=@('Program.cs','OnConnectContext.cs','RunReport.cs','BrandedNotice.cs','PolarisMark.cs')
    & $compiler /nologo /target:winexe /out:PolarisStandalone.exe /win32icon:polaris-taskbar.ico /reference:System.Drawing.dll /reference:System.Windows.Forms.dll /reference:System.Web.Extensions.dll @backend @ui ArchivePublisher.cs
    if($LASTEXITCODE){throw 'Desktop build failed'}
    & $compiler /nologo /target:exe /out:ArchiveTool.exe /reference:System.Web.Extensions.dll @backend ArchivePublisher.cs ArchiveTool.cs
    if($LASTEXITCODE){throw 'Archive tool build failed'}
    & $compiler /nologo /target:exe /out:ArchiveTests.exe /reference:System.Web.Extensions.dll @backend ArchivePublisher.cs ArchiveTests.cs
    if($LASTEXITCODE){throw 'Archive tests build failed'}
    & $compiler /nologo /target:exe /out:CalibrationTests.exe @backend CalibrationTests.cs
    if($LASTEXITCODE){throw 'Calibration tests build failed'}
    & $compiler /nologo /target:exe /out:OnConnectTests.exe /define:UI_OFFLINE_FIXTURE /main:OnConnectTests /win32icon:polaris-taskbar.ico /reference:System.Drawing.dll /reference:System.Windows.Forms.dll @ui UiStubs.cs OnConnectTests.cs
    if($LASTEXITCODE){throw 'UI tests build failed'}
    & $compiler /nologo /target:exe /out:ReportTests.exe /main:ReportTests /reference:System.Drawing.dll /reference:System.Windows.Forms.dll /reference:System.Web.Extensions.dll @backend @ui ArchivePublisher.cs ReportTests.cs
    if($LASTEXITCODE){throw 'Report tests build failed'}
    & $compiler /nologo /target:exe /out:ReportPreview.exe /main:ReportPreview /reference:System.Drawing.dll /reference:System.Windows.Forms.dll /reference:System.Web.Extensions.dll @backend @ui ArchivePublisher.cs ReportPreview.cs
    if($LASTEXITCODE){throw 'Report preview build failed'}
} finally { Pop-Location }
