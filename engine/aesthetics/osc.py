"""Optional local OSC alert bridge for lighting/control software."""
import os,socket,struct

def _osc_str(text):
    raw=text.encode('utf8')+b'\0'
    return raw+b'\0'*((-len(raw))%4)

def send_osc_alert(event):
    port=os.getenv('AESTHETICS_OSC_PORT')
    if not port:return
    # Localhost only. Intentionally no arbitrary user-specified outgoing addresses.
    payload=_osc_str('/aesthetics/alert')+_osc_str(',ssf')
    payload+=_osc_str(str(event['id']))+_osc_str(str(event.get('severity','warning')))
    payload+=struct.pack('>f',float(event.get('probability',1.0)))
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
        sock.sendto(payload,('127.0.0.1',int(port)))
