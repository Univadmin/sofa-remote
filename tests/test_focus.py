from types import SimpleNamespace
import unittest
from server.focus import inspect_focus

class Element:
    CurrentControlType=50004
    CurrentIsEnabled=True
    CurrentIsKeyboardFocusable=True
    CurrentProcessId=100
    def __init__(self,readonly=False):self.readonly=readonly
    def GetRuntimeId(self):return (42,123)
    def GetCurrentPattern(self,kind):return self
    def QueryInterface(self,interface):return self
    @property
    def CurrentIsReadOnly(self):return self.readonly

class FocusTests(unittest.TestCase):
    def test_edit_metadata_and_readonly(self):
        uia=SimpleNamespace(UIA_ValuePatternId=10002,IUIAutomationValuePattern=object())
        data=inspect_focus(Element(),uia)
        self.assertTrue(data['active']);self.assertEqual(data['identity'],(100,(42,123)))
        data=inspect_focus(Element(True),uia)
        self.assertTrue(data['recognized']);self.assertFalse(data['active'])
    def test_non_edit_controls_do_not_trigger_keyboard(self):
        element=Element();element.CurrentControlType=50000
        self.assertFalse(inspect_focus(element,None)['recognized'])
