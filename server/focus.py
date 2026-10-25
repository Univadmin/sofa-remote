"""Read Windows edit focus metadata through the system UI Automation provider."""
import json
import os
from pathlib import Path
import time

UIA_HELPERS = r'''Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
# Load the standard Win32/Windows Forms client-side accessibility providers.
try {
 Add-Type -AssemblyName UIAutomationClientsideProviders
 $proxy=[AppDomain]::CurrentDomain.GetAssemblies() | Where-Object { $_.GetName().Name -eq 'UIAutomationClientsideProviders' } | Select-Object -First 1
 if($proxy){[System.Windows.Automation.ClientSettings]::RegisterClientSideProviderAssembly($proxy.GetName())}
} catch {}
function Get-EditFocus($Element) {
  $active=$false;$identity='';$kind='';$errorType=''
  try {
    if ($Element) { $kind=$Element.Current.ControlType.ProgrammaticName }
    if ($Element -and $Element.Current.IsEnabled -and $Element.Current.IsKeyboardFocusable) {
      $type=$Element.Current.ControlType
      if ($type -eq [System.Windows.Automation.ControlType]::Edit -or $type -eq [System.Windows.Automation.ControlType]::ComboBox -or $type -eq [System.Windows.Automation.ControlType]::Document) {
        $pattern=$null
        if ($Element.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$pattern)) {
          $active=!$pattern.Current.IsReadOnly
        } elseif ($type -eq [System.Windows.Automation.ControlType]::Edit) {
          $active=$true
        } elseif ($Element.TryGetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern,[ref]$pattern)) {
          $readOnly=$pattern.DocumentRange.GetAttributeValue([System.Windows.Automation.TextPattern]::IsReadOnlyAttribute)
          $active=($readOnly -is [bool] -and !$readOnly)
        }
        if ($active) { $identity=($Element.Current.ProcessId.ToString()+':'+($Element.GetRuntimeId() -join '.')) }
      }
    }
  } catch { $errorType=$_.Exception.Message }
  # No names, field values or password contents are queried.
  return @{active=$active;identity=$identity;controlType=$kind;error=$errorType}
}
'''

FOCUS_SCRIPT = r'''param([string]$Config)
$ErrorActionPreference = 'Stop'
$c=Get-Content -LiteralPath $Config -Raw -Encoding UTF8 | ConvertFrom-Json
''' + UIA_HELPERS + r'''
$parent=Get-Process -Id $c.ProcessId
while (!$parent.HasExited) {
  try { $state=Get-EditFocus ([System.Windows.Automation.AutomationElement]::FocusedElement) }
  catch { $state=@{active=$false;identity='';error=$_.Exception.Message} }
  $json=$state | ConvertTo-Json -Compress
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
        self.process=powershell(script,config,mta=True)
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
