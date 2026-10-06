$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$python=Join-Path $root '.venv\Scripts\python.exe'
$source=Join-Path $PSScriptRoot 'sync_nas_capture_history.py'
$runtime='G:\Polaris_Runtime\HostedLibrarySync-20261006'
$state='G:\Polaris_Workspace\HostedLibrarySync'
$taskName='Project Polaris NAS History Sync'
if(-not (Test-Path -LiteralPath $python)){throw 'Project Python environment missing'}
if(-not (Test-Path -LiteralPath (Join-Path $state 'credential.dpapi'))){throw 'Pair this PC before installing automatic sync'}
if(Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue){throw 'Task already exists; review before replacing'}
if(Test-Path -LiteralPath $runtime){throw 'Runtime directory already exists; review before replacing'}
New-Item -ItemType Directory -Path $runtime | Out-Null
Copy-Item -LiteralPath $source -Destination (Join-Path $runtime 'sync_nas_capture_history.py')
$escapedPython=$python.Replace("'","''")
$script=@"
`$ErrorActionPreference='Stop'
try {
  & '$escapedPython' '$runtime\sync_nas_capture_history.py' 2>&1 | Out-File -LiteralPath '$state\last-run.log' -Encoding utf8
  exit `$LASTEXITCODE
} catch {
  'Sync could not start; review runtime paths and Windows account access.' | Out-File -LiteralPath '$state\last-run.log' -Encoding utf8
  exit 1
}
"@
[IO.File]::WriteAllText((Join-Path $runtime 'Run.ps1'),$script,[Text.UTF8Encoding]::new($false))
$user=[Security.Principal.WindowsIdentity]::GetCurrent().Name
$action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "'+$runtime+'\Run.ps1"') -WorkingDirectory $runtime
$triggers=@((New-ScheduledTaskTrigger -AtLogOn -User $user),(New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(5) -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration (New-TimeSpan -Days 365)))
$settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 4) -StartWhenAvailable
$principal=New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $triggers -Settings $settings -Principal $principal -Description 'Sync verified NAS raw-exposure summaries to the paired Polaris account; no NAS/device mutation.' | Out-Null
Start-ScheduledTask -TaskName $taskName
[pscustomobject]@{Task=$taskName;Runtime=$runtime;IntervalMinutes=5;RunLevel='Limited';Account=$user;Payload='Session summaries only'} | ConvertTo-Json
