"""Windows UI Automation focus metadata, queried off the server thread."""
import os
from pathlib import Path
import threading
import time

EDIT,COMBOBOX,DOCUMENT=50004,50003,50030

def inspect_focus(element,uia):
    result={'active':False,'identity':None,'recognized':False}
    if not element:return result
    kind=element.CurrentControlType
    result['recognized']=kind in (EDIT,COMBOBOX,DOCUMENT)
    if not result['recognized'] or not element.CurrentIsEnabled or not element.CurrentIsKeyboardFocusable:return result
    editable=False
    try:
        value=element.GetCurrentPattern(uia.UIA_ValuePatternId).QueryInterface(uia.IUIAutomationValuePattern)
        editable=not value.CurrentIsReadOnly
    except Exception:
        if kind==EDIT:editable=True
        elif kind==DOCUMENT:
            try:
                text=element.GetCurrentPattern(uia.UIA_TextPatternId).QueryInterface(uia.IUIAutomationTextPattern)
                readonly=text.DocumentRange.GetAttributeValue(uia.UIA_IsReadOnlyAttributeId)
                editable=isinstance(readonly,bool) and not readonly
            except Exception:pass
    if editable:
        # Runtime IDs identify fields without reading names, values or passwords.
        identity=tuple(element.GetRuntimeId() or (element.CurrentNativeWindowHandle,))
        result.update(active=True,identity=(element.CurrentProcessId,identity))
    return result

class FocusMonitor:
    def __init__(self,state):
        self.state=Path(state);self._sample=None;self._sample_time=0
        self.stop=threading.Event();self.thread=None;self.error=''
    def start(self):
        if os.name!='nt':return
        try:
            # Import on the main thread so comtypes' default COM initialization
            # stays there; the worker explicitly owns its MTA apartment.
            import comtypes
        except ImportError:
            self.error='UI Automation unavailable';return
        self.thread=threading.Thread(target=self._run,name='sofa-focus',daemon=True);self.thread.start()
    def _run(self):
        import comtypes
        comtypes.CoInitializeEx(0)
        try:
            from comtypes.client import GetModule,CreateObject
            uia=GetModule(str(Path(os.environ['SystemRoot'])/'System32'/'UIAutomationCore.dll'))
            automation=CreateObject(uia.CUIAutomation,interface=uia.IUIAutomation)
            while not self.stop.is_set():
                try:
                    sample=inspect_focus(automation.GetFocusedElement(),uia);self.error=''
                except Exception as exc:
                    sample=None;self.error=type(exc).__name__
                self._sample=sample;self._sample_time=time.monotonic()
                self.stop.wait(.4)
        except Exception as exc:
            self.error=type(exc).__name__
        finally:comtypes.CoUninitialize()
    def sample(self):
        return self._sample if time.monotonic()-self._sample_time<4 else None
    def focused(self):
        sample=self.sample()
        return sample.get('identity') if sample and sample.get('active') else None
    def close(self):
        self.stop.set()
        if self.thread:self.thread.join(timeout=1)
