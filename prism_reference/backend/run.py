import os
from server.state import state
import uvicorn
if __name__=='__main__':
    print('\nHUMOID // PRISM OS\nAPI URL: http://127.0.0.1:8765\n')
    print('API token (copy into Flutter Connection settings):\n'+state.token+'\n')
    print('Loopback only. Keep this token secret. Set HUMOID_API_TOKEN for a persistent token.\n',flush=True)
    uvicorn.run('server.app:app',host='127.0.0.1',port=8765,workers=1,reload=False)
