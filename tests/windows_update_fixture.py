"""Windows CI-only onefile executable exercising the real update worker."""
import argparse
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import shutil
import sys
from server.updater import Updater
from server.version import VERSION

p=argparse.ArgumentParser();p.add_argument('--focus-check',action='store_true');p.add_argument('--state',default=os.environ.get('SOFA_TEST_STATE'));p.add_argument('--port',type=int,default=int(os.environ.get('SOFA_TEST_PORT','18768')))
a=p.parse_args();state=Path(a.state);state.mkdir(parents=True,exist_ok=True)
if a.focus_check:
    import time
    from server.focus import FocusMonitor
    monitor=FocusMonitor(state);monitor.start()
    try:
        deadline=time.monotonic()+15
        while monitor.sample() is None and time.monotonic()<deadline:time.sleep(.2)
        assert monitor.sample() is not None,monitor.error
        print('Frozen native UI Automation worker ready',flush=True)
    finally:monitor.close()
    sys.exit(0)
marker=state/'started.json'
if not marker.exists() and not os.environ.get('SOFA_TEST_WATCH'):
    marker.write_text(json.dumps({'phase':'first'}))
    updater=Updater(state);shutil.copy2(sys.executable,updater.state/f'SofaRemote-{VERSION}.exe')
    updater.status.update(ready=True,latest=VERSION)
    updater.health_url=f'http://127.0.0.1:{a.port}/api/info'
    asyncio.run(updater.install());os._exit(0)
marker.write_text(json.dumps({'phase':'running','pid':os.getpid(),'argv':sys.argv[1:]}))
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path=='/crash':os._exit(9)
        self.send_response(200);self.end_headers();self.wfile.write(json.dumps({'service':'sofa-remote','version':VERSION}).encode())
    def log_message(self,*args):pass
HTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
