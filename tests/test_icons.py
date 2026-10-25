import unittest
from server.icons import Icons, IconLinks
from server.app import safe_favicon
class IconTests(unittest.TestCase):
    def test_html_declared_site_icon(self):
        parser=IconLinks();parser.feed('<link rel="stylesheet" href="x.css"><link rel="shortcut icon" href="/assets/site.png"><link rel="apple-touch-icon" href="https://cdn.example.com/apple.png">')
        self.assertEqual(parser.icons,['/assets/site.png','https://cdn.example.com/apple.png'])
    def test_public_web_only(self):
        for url in ['http://127.0.0.1/favicon.ico','http://192.168.1.1/','http://169.254.169.254/','file:///etc/passwd','https://user:pass@example.com/','https://example.com:8080/','http://[::1]/']:
            with self.assertRaises(ValueError):Icons.valid(url)
        self.assertEqual(Icons.valid('https://example.com/icon.png'),'https://example.com/icon.png')
    def test_reject_active_icon_schemes(self):
        self.assertEqual(safe_favicon('javascript:alert(1)'), '')
        self.assertEqual(safe_favicon('data:text/html,bad'), '')
        self.assertEqual(safe_favicon('https://example.com/icon.png'),'https://example.com/icon.png')
