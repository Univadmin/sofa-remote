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

def main():
    with tempfile.TemporaryDirectory(prefix="sofa update ' space ") as temp:
        state=Path(temp);exe=state/'SofaRemote.exe';shutil.copy2('dist/UpdateFixture.exe',exe)
        port=18768;process=subprocess.Popen([str(exe),'--state',str(state),'--port',str(port)])
        try:
            wait(lambda:healthy(port));data=json.loads((state/'started.json').read_text());assert data['phase']=='running'
            assert data['argv']==['--state',str(state),'--port',str(port)],data
            wait(lambda:'server healthy' in (state/'updates/update.log').read_text())
            assert Path(str(exe)+'.previous').exists()
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
            wait(lambda:healthy(port));pid=json.loads((watch/'started.json').read_text())['pid']
            for _ in range(2):
                try:urlopen(f'http://127.0.0.1:{port}/crash',timeout=2)
                except OSError:pass
                data=wait(lambda:(d if (d:=json.loads((watch/'started.json').read_text()))['pid']!=pid and healthy(port) else None))
                pid=data['pid']
            print('Supervisor: server automatically restarted after two process exits')
        finally:
            stop.write_text('stop');worker.terminate();kill_tree(worker.pid)
            if (watch/'started.json').exists():kill_tree(json.loads((watch/'started.json').read_text())['pid'])
if __name__=='__main__':main()
