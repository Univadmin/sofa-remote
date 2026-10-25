"""Per-user Windows startup supervisor and independent update worker."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

INSTALL_SCRIPT = r'''param([string]$Config)
$ErrorActionPreference = 'Stop'
$c = Get-Content -LiteralPath $Config -Raw -Encoding UTF8 | ConvertFrom-Json
$mutex = New-Object Threading.Mutex($false, 'Local\SofaRemoteInstaller')
try { $owned = $mutex.WaitOne(120000) } catch [Threading.AbandonedMutexException] { $owned = $true }
if (!$owned) { throw 'Another installation is still running' }
$backup = $c.Target + '.previous'
$replaced = $false
$backedUp = $false
$legacy = $null
function Log($Text) { Add-Content -LiteralPath $c.Log -Value ((Get-Date -Format o)+' '+$Text) }
function Start-App {
 $env:PYINSTALLER_RESET_ENVIRONMENT = '1'
 return Start-Process -FilePath $c.Target -WorkingDirectory (Split-Path -Parent $c.Target) -WindowStyle Hidden -PassThru
}
try {
 Set-Content -LiteralPath $c.Ready -Value 'ready'
 $launcher = Get-Process -Id $c.ProcessId -ErrorAction SilentlyContinue
 if ($launcher) { $launcher.WaitForExit() }
 # Pause the existing supervisor before replacing its executable.
 Set-Content -LiteralPath $c.Pause -Value 'install'
 try { $info = Invoke-RestMethod -Uri $c.Health -TimeoutSec 2 } catch { $info = $null }
 if ($info -and $info.service -eq 'sofa-remote') {
  if ([version]$info.version -gt [version]$c.Version) { throw 'A newer Sofa Remote is already installed' }
  $ownerId = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction Stop | Select-Object -First 1 -ExpandProperty OwningProcess
  $process = Get-CimInstance Win32_Process -Filter "ProcessId=$ownerId"
  $legacy = $process.ExecutablePath
  $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($process.ParentProcessId)"
  if ($parent -and $parent.ExecutablePath -eq $legacy) { $ownerId = $parent.ProcessId }
  & taskkill.exe /PID $ownerId /T /F 2>$null | Out-Null
 }
 for ($n=0; $n -lt 90; $n++) {
  try {
   if (Test-Path -LiteralPath $c.Target) {
    $lock=[IO.File]::Open($c.Target,'Open','ReadWrite','None');$lock.Close()
    if (!$backedUp) { Copy-Item -LiteralPath $c.Target -Destination $backup -Force; $backedUp=$true }
   }
   Copy-Item -LiteralPath $c.Staged -Destination $c.Target -Force
   $replaced=$true;break
  } catch { Start-Sleep -Seconds 1 }
 }
 if (!$replaced) { throw 'Installed executable remained locked' }
 $app=Start-App
 $healthy=$false
 for ($n=0; $n -lt 60; $n++) {
  Start-Sleep -Seconds 1
  try {
   $info=Invoke-RestMethod -Uri $c.Health -TimeoutSec 2
   if ($info.service -eq 'sofa-remote' -and $info.version -eq $c.Version) { $healthy=$true;break }
  } catch {}
 }
 if (!$healthy) { & taskkill.exe /PID $app.Id /T /F 2>$null | Out-Null; throw 'Installed server did not start' }
 Remove-Item -LiteralPath $backup -Force -ErrorAction SilentlyContinue
 # Delete only the launch file we copied, after checking it was not changed.
 if ($c.Source -ne $c.Target -and (Test-Path -LiteralPath $c.Source)) {
  for ($n=0; $n -lt 30; $n++) {
   try {
    if ((Get-FileHash -LiteralPath $c.Source -Algorithm SHA256).Hash -eq $c.Digest) { Remove-Item -LiteralPath $c.Source -Force;Log 'Downloaded launch file removed' }
    else { Log 'Launch file changed; preserved' }
    break
   } catch { Log $_.Exception.Message;Start-Sleep -Seconds 1 }
  }
 }
 if ($legacy -and $legacy -ne $c.Target -and $legacy -ne $c.Source) {
  Remove-Item -LiteralPath $legacy -Force -ErrorAction SilentlyContinue
  Remove-Item -LiteralPath ($legacy+'.previous') -Force -ErrorAction SilentlyContinue
 }
 Get-ChildItem -LiteralPath (Split-Path -Parent $c.Pause) -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^SofaRemote-.*\.(exe|part)$' } | Remove-Item -Force -ErrorAction SilentlyContinue
 Log 'Installation completed; server healthy; obsolete packages removed'
 Remove-Item -LiteralPath $c.Staged -Force -ErrorAction SilentlyContinue
 Remove-Item -LiteralPath ($c.Source+'.previous') -Force -ErrorAction SilentlyContinue
} catch {
 Log ('Installation failed: '+$_.Exception.Message)
 if ($replaced -and (Test-Path -LiteralPath $backup)) {
  Start-Sleep -Seconds 2
  Copy-Item -LiteralPath $backup -Destination $c.Target -Force
  $app=Start-App
 }
} finally {
 Remove-Item -LiteralPath $c.Pause -Force -ErrorAction SilentlyContinue
 $mutex.ReleaseMutex();$mutex.Dispose()
}
'''

def automatic_install(state):
    """Return True after handing a downloaded executable to the independent installer."""
    if os.name!='nt' or not getattr(sys,'frozen',False):return False
    from .version import VERSION
    import hashlib
    state=Path(state);target=state/'bin'/'SofaRemote.exe'
    source=Path(sys.executable).resolve()
    if source==target.resolve():
        if not acquire_instance():return True
        # A background process needs its own streams after the download launcher exits.
        log=(state/'app.log').open('a',encoding='utf-8',buffering=1)
        sys.stdout=log;sys.stderr=log
        configure_startup(True,state)
        return False
    target.parent.mkdir(parents=True,exist_ok=True)
    folder=state/'install';folder.mkdir(parents=True,exist_ok=True)
    token=uuid.uuid4().hex
    staged=folder/(token+'.exe');shutil.copy2(source,staged)
    script=folder/'install.ps1';script.write_text(INSTALL_SCRIPT,encoding='utf-8-sig')
    config=folder/(token+'.json');ready=folder/(token+'.ready')
    pause=state/'updates'/'installing';pause.parent.mkdir(parents=True,exist_ok=True)
    config.write_text(json.dumps({'Source':str(source),'Target':str(target),'Staged':str(staged),
        'Digest':hashlib.sha256(staged.read_bytes()).hexdigest().upper(),'Version':VERSION,
        'ProcessId':os.getpid(),'Ready':str(ready),'Pause':str(pause),
        'Health':'http://127.0.0.1:8765/api/info','Log':str(folder/'install.log')}),encoding='utf-8')
    process=powershell(script,config)
    for _ in range(1500):
        if ready.exists():return True
        if process.poll() is not None:break
        time.sleep(.1)
    raise RuntimeError('Otomatik kurulum başlayamadı: '+str(folder/'install.log'))

_instance_handle=None
def acquire_instance():
    import ctypes
    from ctypes import wintypes
    global _instance_handle
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR]
    kernel.CreateMutexW.restype=wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.CreateMutexW(None,False,'Local\\SofaRemoteServer')
    if not handle:raise ctypes.WinError(ctypes.get_last_error())
    if kernel.WaitForSingleObject(handle,0) not in (0,0x80):
        kernel.CloseHandle(handle);return False
    _instance_handle=handle
    return True

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
  Remove-Item -LiteralPath $backup -Force -ErrorAction SilentlyContinue
  Get-ChildItem -LiteralPath (Split-Path -Parent $c.Staged) -File | Where-Object { $_.Name -match '^SofaRemote-.*\.(exe|part)$' } | Remove-Item -Force -ErrorAction SilentlyContinue
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

def powershell(script, config, *, mta=False):
    env=dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT='1')
    # PowerShell 7's inherited module path can hide Windows PowerShell 5 modules.
    env={key:value for key,value in env.items() if key.upper()!='PSMODULEPATH'}
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
            return subprocess.Popen(['powershell.exe',*(['-Mta'] if mta else []),'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(script),str(config)],
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
