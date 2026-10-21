"""Optional stage-safe-ish alert-light bridge: OSC -> WLED (LAN-only).

No strobing. Applies a temporary 3-second color, then restores previous device
state. Test with --dry-run before connecting any venue lights.
"""
from __future__ import annotations
import argparse,asyncio,ipaddress,struct
import httpx


def osc_string(data:bytes,pos:int):
    end=data.find(b'\0',pos)
    if end<0 or end-pos>160:raise ValueError('Invalid OSC string')
    s=data[pos:end].decode('utf8')
    return s, ((end+4)//4)*4

def decode_alert(data:bytes)->dict:
    if len(data)>4096:raise ValueError('Oversized OSC packet')
    address,pos=osc_string(data,0)
    tags,pos=osc_string(data,pos)
    if address!='/aesthetics/alert' or tags!=',ssf':raise ValueError('Not an Audio Aesthetics alert')
    fault,pos=osc_string(data,pos)
    severity,pos=osc_string(data,pos)
    if pos+4>len(data):raise ValueError('Truncated probability')
    prob=struct.unpack('>f',data[pos:pos+4])[0]
    if severity not in ('warning','critical','info'):raise ValueError('Invalid severity')
    return {'id':fault,'severity':severity,'probability':round(float(prob),3)}

class LightBridge(asyncio.DatagramProtocol):
    def __init__(self,ip:str|None,dry_run:bool=True):
        if ip:
            addr=ipaddress.ip_address(ip)
            if not (addr.is_private or addr.is_loopback):
                raise ValueError('WLED must be on a private LAN IP')
        self.ip=ip;self.dry_run=dry_run or not ip
        self.lock=asyncio.Lock();self.active=set()
    def datagram_received(self,data,addr):
        # Receive ONLY from same host. No inbound untrusted network control.
        if addr[0] not in ('127.0.0.1','::1'):return
        try:event=decode_alert(data)
        except (UnicodeDecodeError,ValueError):return
        print('Light alert:',event,flush=True)
        if self.dry_run:return
        task=asyncio.create_task(self.light(event));self.active.add(task);task.add_done_callback(self.active.discard)
    async def light(self,event):
        async with self.lock:
            url=f'http://{self.ip}/json/state'
            async with httpx.AsyncClient(timeout=4) as client:
                try:
                    prior=await client.get(url);prior.raise_for_status();before=prior.json()
                    # Smooth warm amber for warnings, static red for critical; never strobe.
                    rgb=[233,100,60] if event['severity']=='critical' else [232,167,83]
                    await client.post(url,json={'on':True,'bri':110,'transition':10,'seg':[{'col':[rgb]}]})
                    await asyncio.sleep(3)
                    await client.post(url,json=before)
                except Exception as e:print('Lighting bridge error:',e,flush=True)

async def main():
    p=argparse.ArgumentParser(description='OSC event light bridge for WLED on private LAN')
    p.add_argument('--ip',help='IPv4 local WLED address, e.g. 192.168.1.48')
    p.add_argument('--port',type=int,default=9000)
    p.add_argument('--dry-run',action='store_true',help='Print events, do not affect lights')
    args=p.parse_args()
    loop=asyncio.get_running_loop()
    transport,_=await loop.create_datagram_endpoint(
        lambda:LightBridge(args.ip,args.dry_run),local_addr=('127.0.0.1',args.port))
    print('OSC listener active on 127.0.0.1:',args.port,' WLED:',args.ip or 'DRY RUN',flush=True)
    try:await asyncio.Event().wait()
    finally:transport.close()
if __name__=='__main__':asyncio.run(main())
