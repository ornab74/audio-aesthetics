"""Launch localhost audio monitor. Never exposes raw mic traffic to the Internet by default."""
import os,uvicorn
if __name__=='__main__':
    host=os.getenv('AESTHETICS_HOST','127.0.0.1')
    if host not in ('localhost','127.0.0.1','::1') and not os.getenv('AESTHETICS_ACCESS_TOKEN'):
        raise SystemExit('Set AESTHETICS_ACCESS_TOKEN before binding to a non-loopback interface')
    uvicorn.run('aesthetics.server:app',host=host,port=int(os.getenv('AESTHETICS_PORT','8788')))
