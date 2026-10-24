import ipaddress

NETWORKS = tuple(ipaddress.ip_network(n) for n in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16','127.0.0.0/8','::1/128','fc00::/7','fe80::/10'))
def local_address(value):
    try:
        ip = ipaddress.ip_address(value.split('%')[0])
        if getattr(ip,'ipv4_mapped',None): ip=ip.ipv4_mapped
        return any(ip.version == net.version and ip in net for net in NETWORKS)
    except (ValueError, AttributeError): return False
