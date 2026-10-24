import json
import unittest
from server.discovery import Discovery

class Transport:
    def __init__(self):self.messages=[]
    def sendto(self,data,address):self.messages.append((data,address))
class DiscoveryTests(unittest.TestCase):
    def test_only_known_probe_from_lan(self):
        d=Discovery(8765);transport=Transport();d.connection_made(transport)
        d.datagram_received(b'random',('192.168.1.2',123))
        d.datagram_received(b'SOFA_REMOTE_DISCOVER_V1',('8.8.8.8',123))
        self.assertFalse(transport.messages)
        d.datagram_received(b'SOFA_REMOTE_DISCOVER_V1',('192.168.1.2',123))
        data,address=transport.messages[0];self.assertEqual(address,('192.168.1.2',123));self.assertEqual(json.loads(data)['service'],'sofa-remote');self.assertEqual(json.loads(data)['port'],8765)
