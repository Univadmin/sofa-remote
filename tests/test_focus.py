import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from server.focus import FocusMonitor

class FocusTests(unittest.TestCase):
    def test_metadata_only_and_stale_focus_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            monitor=FocusMonitor(tmp)
            monitor.file.write_text(json.dumps({'active':True,'identity':'100:42'}))
            self.assertEqual(monitor.focused(),'100:42')
            os.utime(monitor.file,(time.time()-10,time.time()-10));self.assertIsNone(monitor.focused())
            monitor.file.write_text(json.dumps({'active':False,'identity':''}));self.assertIsNone(monitor.focused())
