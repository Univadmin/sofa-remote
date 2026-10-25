"""Per-user Windows startup supervisor and independent update worker."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

UPDATE_SCRIPT = r'''param([string]$Config)
$ErrorActionPreference = 'Stop'
$c = Get-Content -LiteralPath $Config -Raw -Encoding UTF8 | ConvertFrom-Json
function Log($Text) { Add-Content -LiteralPath $c.Log -Value ((Get-Date -Format o) + ' ' + $Text) }
function Start-App {
  $env:PYINSTALLER_RESET_ENVIRONMENT = '1'
  $params = @{FilePath=$c.Target; WorkingDirectory=(Split-Path -Parent $c.Target); PassThru=$true}
  if ($c.Arguments) { $params.ArgumentList = $c.Arguments }
  return Start-Process @params
}
function Wait-Healthy {
  for ($n=0; $n -lt 60; $n++) {
    Start-Sleep -Seconds 2
    try {
      $info = Invoke-RestMethod -Uri $c.Health -TimeoutSec 2
      if ($info.service -eq 'sofa-remote' -and $info.version -eq $c.Version) { return $true }
    } catch {}
  }
  return $false
}
$backup = $c.Target + '.previous'
$replaced = $false
$backedUp = $false
try {
  Set-Content -LiteralPath $c.Ready -Value 'ready'
  $old = Get-Process -Id $c.ProcessId -ErrorAction SilentlyContinue
  if ($old) { $old.WaitForExit() }
  # A onefile bootloader may still hold the executable after its Python child exits.
  for ($n=0; $n -lt 60; $n++) {
    try {
      $lock = [IO.File]::Open($c.Target,'Open','ReadWrite','None'); $lock.Close()
      if (!$backedUp) { Copy-Item -LiteralPath $c.Target -Destination $backup -Force; $backedUp = $true }
      Copy-Item -LiteralPath $c.Staged -Destination $c.Target -Force
      $replaced = $true; break
    } catch { Log $_.Exception.Message; Start-Sleep -Seconds 1 }
  }
  if (!$replaced) { throw 'Executable remained locked; update not installed' }
  Log 'Starting updated application'
  $app = Start-App
  if (!(Wait-Healthy)) {
    & taskkill.exe /PID $app.Id /T /F 2>$null | Out-Null
    Start-Sleep -Seconds 2
    throw 'Updated server did not become healthy'
  }
  Log 'Update completed; server healthy'
} catch {
  Log ('Update failed: ' + $_.Exception.Message)
  if ($backedUp -and (Test-Path -LiteralPath $backup)) {
    for ($n=0; $n -lt 30; $n++) {
      try { Copy-Item -LiteralPath $backup -Destination $c.Target -Force; break }
      catch { Start-Sleep -Seconds 1 }
    }
  }
  try { $app = Start-App; Log 'Previous application restarted' } catch { Log $_.Exception.Message }
} finally { Remove-Item -LiteralPath $c.Pause -Force -ErrorAction SilentlyContinue }
'''

WATCH_SCRIPT = r'''param([string]$Config)
$ErrorActionPreference = 'Stop'
$c = Get-Content -LiteralPath $Config -Raw -Encoding UTF8 | ConvertFrom-Json
$mutex = New-Object Threading.Mutex($false, 'Local\SofaRemoteSupervisor')
try { $owned = $mutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $owned = $true }
if (!$owned) { $mutex.Dispose(); exit }
try {
 while (!(Test-Path -LiteralPath $c.Stop)) {
  if (Test-Path -LiteralPath $c.Pause) {
   $age = ((Get-Date).ToUniversalTime() - (Get-Item -LiteralPath $c.Pause).LastWriteTimeUtc).TotalSeconds
   if ($age -lt 300) { Start-Sleep -Seconds 2; continue }
   Remove-Item -LiteralPath $c.Pause -Force -ErrorAction SilentlyContinue
  }
  try {
   $healthy = $false
   try { $info=Invoke-RestMethod -Uri $c.Health -TimeoutSec 2; $healthy=$info.service -eq 'sofa-remote' } catch {}
   if ($healthy) { Start-Sleep -Seconds 3; continue }
   $env:PYINSTALLER_RESET_ENVIRONMENT = '1'
   $app = Start-Process -FilePath $c.Target -WorkingDirectory (Split-Path -Parent $c.Target) -WindowStyle Hidden -PassThru
   $app.WaitForExit()
  } catch { Add-Content -LiteralPath $c.Log -Value ((Get-Date -Format o)+' '+$_.Exception.Message) }
  Start-Sleep -Seconds 3
 }
} finally { $mutex.ReleaseMutex(); $mutex.Dispose() }
'''

def powershell(script, config):
    env=dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT='1')
    # Windows propagates PyInstaller's DLL search directory to child processes.
    # External system tools must use Windows DLLs, not bundled application DLLs.
    kernel=None
    if os.name=='nt' and getattr(sys,'frozen',False):
        import ctypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.SetDllDirectoryW.argtypes=[ctypes.c_wchar_p]
        kernel.SetDllDirectoryW(None)
    try:
        with script.with_suffix('.launch.log').open('ab') as log:
            return subprocess.Popen(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(script),str(config)],
                cwd=str(script.parent),env=env,creationflags=0x00000200|0x08000000,
                stdin=subprocess.DEVNULL,stdout=log,stderr=log,close_fds=True)
    finally:
        if kernel:kernel.SetDllDirectoryW(getattr(sys,'_MEIPASS',None))

def configure_startup(enabled, state):
    if os.name!='nt' or not getattr(sys,'frozen',False):raise ValueError('Paketli Windows EXE gereklidir')
    import winreg
    state=Path(state);state.mkdir(parents=True,exist_ok=True)
    stop=state/'watchdog.stop'
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
        if not enabled:
            stop.write_text('disabled')
            try:winreg.DeleteValue(key,'SofaRemote')
            except FileNotFoundError:pass
            print('Otomatik açılış ve yeniden başlatma kapatıldı.');return
        target=state/'bin'/'SofaRemote.exe';target.parent.mkdir(parents=True,exist_ok=True)
        if Path(sys.executable).resolve()!=target.resolve():shutil.copy2(sys.executable,target)
        script=state/'watchdog.ps1';script.write_text(WATCH_SCRIPT,encoding='utf-8-sig')
        config=state/'watchdog.json';config.write_text(json.dumps({'Target':str(target),'Stop':str(stop),'Pause':str(state/'updates'/'installing'),'Health':'http://127.0.0.1:8765/api/info','Log':str(state/'watchdog.log')}),encoding='utf-8')
        stop.unlink(missing_ok=True)
        command=subprocess.list2cmdline(['powershell.exe','-NoProfile','-NonInteractive','-WindowStyle','Hidden','-ExecutionPolicy','Bypass','-File',str(script),str(config)])
        winreg.SetValueEx(key,'SofaRemote',0,winreg.REG_SZ,command)
    powershell(script,config)
    print('Kuruldu. Windows oturumu açıldığında başlar; kapanırsa yeniden açılır.\nDosya: '+str(target))
