"""Exercise real Windows UI Automation against an editable/read-only TextBox."""
import json
from pathlib import Path
import tempfile
import time
from server.focus import FocusMonitor
from server.windows_runtime import powershell

FORM = r'''param([string]$Config)
$c=Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json
Add-Type -AssemblyName System.Windows.Forms
$form=New-Object Windows.Forms.Form
$form.Text='Sofa Remote focus test';$form.Width=400;$form.Height=200;$form.TopMost=$true
$box=New-Object Windows.Forms.TextBox;$box.Width=300;$form.Controls.Add($box)
$form.Add_Shown({$form.Activate();$box.Focus() | Out-Null})
$timer=New-Object Windows.Forms.Timer;$timer.Interval=250
$timer.Add_Tick({if(Test-Path -LiteralPath $c.Mode){$box.ReadOnly=$true}});$timer.Start()
[Windows.Forms.Application]::Run($form)
'''

def wait(check,seconds=30):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        if check():return
        time.sleep(.3)
    raise AssertionError('Windows UI Automation focus timeout')

def main():
    with tempfile.TemporaryDirectory() as tmp:
        state=Path(tmp);monitor=FocusMonitor(state);mode=state/'readonly'
        script=state/'form.ps1';script.write_text(FORM,encoding='utf-8-sig')
        config=state/'form.json';config.write_text(json.dumps({'Mode':str(mode)}))
        process=powershell(script,config)
        try:
            monitor.start()
            wait(lambda:bool(monitor.focused()))
            identity=monitor.focused();assert identity.startswith(str(process.pid)+':'),identity
            print('UI Automation detected real Windows TextBox focus',flush=True)
            mode.write_text('readonly');wait(lambda:monitor.focused() is None)
            print('UI Automation ignored read-only TextBox without reading its value',flush=True)
        except Exception:
            for file in state.glob('*.log'):print(file.name,file.read_text(errors='replace'))
            if monitor.file.exists():print(monitor.file.read_text())
            raise
        finally:
            monitor.close();process.terminate();process.wait(timeout=10)
if __name__=='__main__':main()
