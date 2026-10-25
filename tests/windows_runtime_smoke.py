"""Run only on Windows after building UpdateFixture.exe."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from urllib.request import urlopen
from server.windows_runtime import WATCH_SCRIPT, powershell

def wait(predicate,seconds=150):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        try:
            result=predicate()
            if result:return result
        except (OSError,ValueError):pass
        time.sleep(.5)
    raise AssertionError('Windows runtime timeout')
def healthy(port):
    with urlopen(f'http://127.0.0.1:{port}/api/info',timeout=2) as r:return json.load(r)['service']=='sofa-remote'
def kill_tree(pid):subprocess.run(['taskkill','/PID',str(pid),'/T','/F'],capture_output=True)

def automatic_install_smoke():
    import winreg
    with tempfile.TemporaryDirectory(prefix="sofa install ' renamed ") as temp:
        root=Path(temp);state=root/'SofaRemote';target=state/'bin'/'SofaRemote.exe'
        env=dict(os.environ,LOCALAPPDATA=str(root))
        try:
            for name in ('Downloaded name (1).exe','Moved and renamed.exe'):
                source=root/name;shutil.copy2('dist/SofaRemote.exe',source)
                updates=state/'updates';updates.mkdir(parents=True,exist_ok=True)
                (updates/'SofaRemote-0.1.0.exe').write_bytes(b'obsolete')
                (updates/'SofaRemote-0.1.0.part').write_bytes(b'partial')
                launcher=subprocess.Popen([str(source)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                launcher.wait(timeout=40)
                assert launcher.returncode==0
                wait(lambda:healthy(8765) and not source.exists())
                wait(lambda:list(root.rglob('*.exe'))==[target])
                assert not list(root.rglob('*.previous'))
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
                    assert str(state/'watchdog.ps1') in winreg.QueryValueEx(key,'SofaRemote')[0]
                print('Automatic install: renamed download, canonical path, startup, previous process takeover and cleanup verified',flush=True)
        except Exception:
            print('Remaining files:',[str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()],flush=True)
            try:print('Server health:',healthy(8765),flush=True)
            except Exception as exc:print('Server health error:',repr(exc),flush=True)
            for path in state.rglob('*.log'):
                print(path.name,path.read_text(errors='replace')[-3000:],flush=True)
            raise
        finally:
            (state/'watchdog.stop').write_text('stop')
            cleanup="$root=$env:SOFA_CLEAN_ROOT; Get-CimInstance Win32_Process | Where-Object { ($_.ExecutablePath -and $_.ExecutablePath.StartsWith($root)) -or ($_.Name -eq 'powershell.exe' -and $_.CommandLine.Contains($root)) } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
            clean_env=dict(os.environ,SOFA_CLEAN_ROOT=str(root));clean_env.pop('PSModulePath',None)
            subprocess.run(['powershell.exe','-NoProfile','-Command',cleanup],env=clean_env,capture_output=True)
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
                try:winreg.DeleteValue(key,'SofaRemote')
                except FileNotFoundError:pass
            time.sleep(3)

def main():
    with tempfile.TemporaryDirectory(prefix="sofa update ' space ") as temp:
        state=Path(temp);exe=state/'SofaRemote.exe';shutil.copy2('dist/UpdateFixture.exe',exe)
        subprocess.run([str(exe),'--focus-check','--state',str(state)],check=True,timeout=25)
        port=18768;process=subprocess.Popen([str(exe),'--state',str(state),'--port',str(port)])
        try:
            print('Waiting for updated fixture',flush=True)
            try:wait(lambda:healthy(port),seconds=45)
            except Exception:
                for log in (state/'updates').glob('*'):
                    if log.suffix in ('.log','.json'):
                        print(log.name,log.read_text(errors='replace'),flush=True)
                raise
            data=json.loads((state/'started.json').read_text());assert data['phase']=='running'
            assert data['argv']==['--state',str(state),'--port',str(port)],data
            wait(lambda:'server healthy' in (state/'updates/update.log').read_text())
            wait(lambda:not Path(str(exe)+'.previous').exists() and not list((state/'updates').glob('SofaRemote-*.exe')))
            print('Onefile update: unlocked, replaced, restarted, original arguments preserved')
        finally:
            kill_tree(process.pid)
            if (state/'started.json').exists():kill_tree(json.loads((state/'started.json').read_text()).get('pid',process.pid))
        # A separate supervisor must survive crashes and ordinary process exits.
        watch=state/'watch';watch.mkdir();target=watch/'SofaRemote.exe';shutil.copy2('dist/UpdateFixture.exe',target)
        script=watch/'watchdog.ps1';script.write_text(WATCH_SCRIPT,encoding='utf-8-sig')
        config=watch/'watchdog.json';stop=watch/'stop'
        config.write_text(json.dumps({'Target':str(target),'Stop':str(stop),'Pause':str(watch/'pause'),'Health':f'http://127.0.0.1:{port}/api/info','Log':str(watch/'watchdog.log')}))
        os.environ.update(SOFA_TEST_STATE=str(watch),SOFA_TEST_PORT=str(port),SOFA_TEST_WATCH='1')
        worker=powershell(script,config)
        try:
            print('Waiting for supervisor fixture',flush=True)
            wait(lambda:healthy(port));pid=json.loads((watch/'started.json').read_text())['pid']
            for _ in range(2):
                print('Testing supervisor restart',_,flush=True)
                try:urlopen(f'http://127.0.0.1:{port}/crash',timeout=2)
                except OSError:pass
                data=wait(lambda:(d if (d:=json.loads((watch/'started.json').read_text()))['pid']!=pid and healthy(port) else None))
                pid=data['pid']
            print('Supervisor: server automatically restarted after two process exits')
        finally:
            stop.write_text('stop');kill_tree(worker.pid);worker.wait(timeout=10)
            if (watch/'started.json').exists():kill_tree(json.loads((watch/'started.json').read_text())['pid'])
            def remove_executable():
                target.unlink(missing_ok=True);return True
            wait(remove_executable,seconds=20)
    automatic_install_smoke()
if __name__=='__main__':main()
