"""Optional system OUTPUT loopback capture -> audio WebSocket.
Requires: pip install soundcard soundfile websockets.
Usage: python -m aesthetics.capture --list-devices
       python -m aesthetics.capture --device 0 --preset streamer
"""
from __future__ import annotations
import argparse,asyncio,json,os
import numpy as np

async def capture(args):
    try:import soundcard as sc
    except ImportError:raise SystemExit('Install soundcard: pip install soundcard')
    loopbacks=sc.all_microphones(include_loopback=True)
    if args.list_devices:
        for i,dev in enumerate(loopbacks):print(i,dev.name,'[LOOPBACK]' if dev.isloopback else '')
        return
    if args.device<0 or args.device>=len(loopbacks):raise SystemExit('Pick --device from --list-devices')
    try:import websockets
    except ImportError:raise SystemExit('Install websockets: pip install websockets')
    uri=args.url
    if not (uri.startswith('ws://127.0.0.1:') or uri.startswith('ws://localhost:') or uri.startswith('wss://')):
        raise SystemExit('Use secure wss:// outside localhost')
    print('Streaming input',loopbacks[args.device].name,'to',uri)
    async with websockets.connect(uri,max_size=4*1024*1024) as ws:
        await ws.send(json.dumps({'type':'start','token':os.getenv('AESTHETICS_ACCESS_TOKEN',''),
            'preset':args.preset,'sample_rate':args.rate,'channels':1,'clef':args.clef,
            'pro_token':os.getenv('AESTHETICS_PRO_TOKEN','')}))
        print('server:',await ws.recv())
        async def listen():
            async for message in ws:
                if isinstance(message,str):
                    o=json.loads(message)
                    if o.get('type')=='alert':print('ALERT',o['label'],o['message'])
                    if o.get('type')=='ai_error':print('AI:',o['message'])
        listener=asyncio.create_task(listen())
        try:
            with loopbacks[args.device].recorder(samplerate=args.rate,channels=1,blocksize=int(args.rate*.1)) as mic:
                while not listener.done():
                    # Native recorder is blocking: preserve WebSocket event loop responsiveness.
                    audio=await asyncio.to_thread(mic.record,numframes=int(args.rate*.1))
                    pcm=(np.clip(audio,-1,1)*32767).astype('<i2').tobytes()
                    await ws.send(pcm)
        finally:listener.cancel()

def main():
    p=argparse.ArgumentParser(description='Capture system audio via OS loopback')
    p.add_argument('--list-devices',action='store_true');p.add_argument('--device',type=int,default=-1)
    p.add_argument('--url',default='ws://127.0.0.1:8788/ws/audio')
    p.add_argument('--rate',type=int,default=16000)
    p.add_argument('--preset',default='streamer');p.add_argument('--clef',choices=['off','local','cloud'],default='off')
    args=p.parse_args();asyncio.run(capture(args))
if __name__=='__main__':main()
