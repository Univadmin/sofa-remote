"""Read Windows edit focus metadata through the system UI Automation provider."""
import json
import os
from pathlib import Path
import time

FOCUS_SCRIPT = r'''param([string]$Config)
$ErrorActionPreference = 'Stop'
$c=Get-Content -LiteralPath $Config -Raw -Encoding UTF8 | ConvertFrom-Json
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$parent=Get-Process -Id $c.ProcessId
while (!$parent.HasExited) {
  $active=$false; $identity='';$kind='';$errorType=''
  try {
    $element=[System.Windows.Automation.AutomationElement]::FocusedElement
    if ($element) { $kind=$element.Current.ControlType.ProgrammaticName }
    if ($element -and $element.Current.IsEnabled -and $element.Current.IsKeyboardFocusable) {
      $type=$element.Current.ControlType
      if ($type -eq [System.Windows.Automation.ControlType]::Edit -or $type -eq [System.Windows.Automation.ControlType]::ComboBox -or $type -eq [System.Windows.Automation.ControlType]::Document) {
        $pattern=$null
        if ($element.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$pattern)) {
          $active=!$pattern.Current.IsReadOnly
        } elseif ($type -eq [System.Windows.Automation.ControlType]::Edit) {
          $active=$true
        } elseif ($element.TryGetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern,[ref]$pattern)) {
          $readOnly=$pattern.DocumentRange.GetAttributeValue([System.Windows.Automation.TextPattern]::IsReadOnlyAttribute)
          $active=($readOnly -is [bool] -and !$readOnly)
        }
        if ($active) { $identity=($element.Current.ProcessId.ToString()+':'+($element.GetRuntimeId() -join '.')) }
      }
    }
  } catch { $errorType=$_.Exception.Message }
  # No names, field values or password contents are queried.
  $json=@{active=$active;identity=$identity;controlType=$kind;error=$errorType} | ConvertTo-Json -Compress
  try {
    [IO.File]::WriteAllText($c.State+'.tmp',$json,(New-Object Text.UTF8Encoding($false)))
    Move-Item -LiteralPath ($c.State+'.tmp') -Destination $c.State -Force
  } catch {}
  Start-Sleep -Milliseconds 400
  $parent.Refresh()
}
'''

class FocusMonitor:
    def __init__(self,state):
        self.state=Path(state);self.file=self.state/'focus.json';self.process=None
    def start(self):
        if os.name!='nt':return
        from .windows_runtime import powershell
        self.state.mkdir(parents=True,exist_ok=True)
        self.file.unlink(missing_ok=True)
        script=self.state/'focus.ps1';script.write_text(FOCUS_SCRIPT,encoding='utf-8-sig')
        config=self.state/'focus-config.json';config.write_text(json.dumps({'ProcessId':os.getpid(),'State':str(self.file)}),encoding='utf-8')
        self.process=powershell(script,config)
    def focused(self):
        try:
            if time.time()-self.file.stat().st_mtime>4:return None
            data=json.loads(self.file.read_text(encoding='utf-8-sig'))
            return data['identity'] if data.get('active') is True else None
        except (OSError,ValueError,KeyError):return None
    def close(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=3)
            except Exception:pass
