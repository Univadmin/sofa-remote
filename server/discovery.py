"""Small UDP discovery responder; only announces the service, never executes commands."""
import asyncio
import json
import socket
from .version import VERSION

class Discovery(asyncio.DatagramProtocol):
    def __init__(self, port): self.port = port
    def connection_made(self, transport): self.transport = transport
    def datagram_received(self, data, addr):
        if data != b'SOFA_REMOTE_DISCOVER_V1': return
        from .network import local_address
        if not local_address(addr[0]): return
        message = {'service':'sofa-remote','protocol':1,'name':socket.gethostname(),'port':self.port,'version':VERSION}
        self.transport.sendto(json.dumps(message).encode(), addr)

async def start_discovery(port):
    loop = asyncio.get_running_loop()
    transport, _ = await loop.create_datagram_endpoint(lambda:Discovery(port), local_addr=('0.0.0.0',8766), allow_broadcast=True)
    return transport
