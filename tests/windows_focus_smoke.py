"""Verify real Windows UIA edit/read-only patterns and the focus worker lifecycle.
Hosted Windows runners do not guarantee an interactive foreground desktop.
"""
import json
from pathlib import Path
import tempfile
import time
from server.focus import FocusMonitor,inspect_focus
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
        process=powershell(script,config)
        try:
            wait(ready.exists)
            from comtypes.client import GetModule,CreateObject
            uia=GetModule('UIAutomationCore.dll');automation=CreateObject(uia.CUIAutomation,interface=uia.IUIAutomation)
            element=automation.ElementFromHandle(int(ready.read_text()))
            wait(lambda:inspect_focus(element,uia)['active'])
            data=inspect_focus(element,uia);assert data['identity'][0]==process.pid,data
            monitor.start();wait(lambda:monitor.sample() is not None)
            assert monitor.thread.is_alive(),monitor.error
            print('Native UI Automation recognized real Windows TextBox; focus worker running',flush=True)
            mode.write_text('readonly');wait(lambda:inspect_focus(element,uia)['active'] is False)
            print('Native UI Automation ignored read-only TextBox without reading its value',flush=True)
        except Exception:
            for file in state.glob('*.log'):print(file.name,file.read_text(errors='replace'))
            try:print('Native control type:',element.CurrentControlType,'focusable:',element.CurrentIsKeyboardFocusable)
            except Exception:pass
            raise
        finally:
            monitor.close();process.terminate();process.wait(timeout=10)
if __name__=='__main__':main()
