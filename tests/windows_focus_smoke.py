"""Verify real Windows UIA edit/read-only patterns and the focus worker lifecycle.
Hosted Windows runners do not guarantee an interactive foreground desktop.
"""
import json
from pathlib import Path
import tempfile
import time
from server.focus import FocusMonitor,UIA_HELPERS
from server.windows_runtime import powershell

FORM = r'''param([string]$Config)
$c=Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json
Add-Type -AssemblyName System.Windows.Forms
$form=New-Object Windows.Forms.Form
$form.Text='Sofa Remote focus test';$form.Width=400;$form.Height=200
$box=New-Object Windows.Forms.TextBox;$box.Width=300;$form.Controls.Add($box)
$form.Add_Shown({[IO.File]::WriteAllText($c.Ready,$box.Handle.ToInt64().ToString())})
$timer=New-Object Windows.Forms.Timer;$timer.Interval=250
$timer.Add_Tick({if(Test-Path -LiteralPath $c.Mode){$box.ReadOnly=$true}});$timer.Start()
[Windows.Forms.Application]::Run($form)
'''
PROBE = r'''param([string]$Config)
$ErrorActionPreference='Stop'
$c=Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json
''' + UIA_HELPERS + r'''
while($true) {
 $element=[System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]$c.Handle)
 $json=(Get-EditFocus $element) | ConvertTo-Json -Compress
 [IO.File]::WriteAllText($c.Output,$json)
 Start-Sleep -Milliseconds 300
}
'''

def wait(check,seconds=30):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        try:
            if check():return
        except (OSError,ValueError):pass
        time.sleep(.3)
    raise AssertionError('Windows UI Automation probe timeout')

def main():
    with tempfile.TemporaryDirectory() as tmp:
        state=Path(tmp);monitor=FocusMonitor(state);mode=state/'readonly';ready=state/'handle'
        script=state/'form.ps1';script.write_text(FORM,encoding='utf-8-sig')
        config=state/'form.json';config.write_text(json.dumps({'Mode':str(mode),'Ready':str(ready)}))
        process=powershell(script,config);probe=None;output=state/'probe.json'
        try:
            wait(ready.exists)
            probe_script=state/'probe.ps1';probe_script.write_text(PROBE,encoding='utf-8-sig')
            probe_config=state/'probe-config.json';probe_config.write_text(json.dumps({'Handle':int(ready.read_text()),'Output':str(output)}))
            probe=powershell(probe_script,probe_config,mta=True)
            monitor.start();wait(lambda:monitor.file.exists() and json.loads(output.read_text()).get('active'))
            data=json.loads(output.read_text());assert data['identity'].startswith(str(process.pid)+':'),data
            assert monitor.process.poll() is None
            print('UI Automation recognized real Windows TextBox; background focus worker running',flush=True)
            mode.write_text('readonly');wait(lambda:json.loads(output.read_text()).get('active') is False)
            print('UI Automation ignored read-only TextBox without reading its value',flush=True)
        except Exception:
            for file in state.glob('*.log'):print(file.name,file.read_text(errors='replace'))
            if output.exists():print(output.read_text())
            raise
        finally:
            monitor.close()
            if probe:probe.terminate();probe.wait(timeout=10)
            process.terminate();process.wait(timeout=10)
if __name__=='__main__':main()
