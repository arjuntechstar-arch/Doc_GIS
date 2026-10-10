"""Start the entire local stack against a disposable MongoDB and run Playwright."""
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
import httpx
from pymongo import MongoClient

root=Path(__file__).resolve().parents[1]
exe=os.getenv('MONGOD_BINARY') or shutil.which('mongod')
if not exe:raise SystemExit('Set MONGOD_BINARY to mongod')
frontend=root/'src/frontend/healthcare-gis-web'
with tempfile.TemporaryDirectory(prefix='docgis-browser-') as data:
    logs=[];processes=[]
    password=secrets.token_urlsafe(24)
    env=os.environ|{'HEALTHCARE_GIS_MONGO_URI':'mongodb://localhost:27018/','HEALTHCARE_GIS_MONGO_DB':'dog_gis_e2e',
                    'E2E_ADMIN_PASSWORD':password,'JWT_SECRET':secrets.token_hex(32),'ML_SERVICE_KEY':secrets.token_hex(32),
                    'ML_SERVICE_URL':'http://127.0.0.1:8001','MODEL_STORAGE':str(Path(data)/'models'),
                    'PYTHONPATH':os.pathsep.join([str(root/'src/backend'),str(root/'src/ml')])}
    def spawn(name,command,cwd=root):
        log=(Path(data)/(name+'.log')).open('w');logs.append(log)
        proc=subprocess.Popen(command,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT);processes.append(proc)
        return proc
    def ready(url):
        for _ in range(300):
            try:
                if httpx.get(url,trust_env=False,timeout=1).status_code==200:return
            except httpx.TransportError:pass
            if any(p.poll() is not None for p in processes):
                raise RuntimeError('Server exited: '+''.join((Path(data)/(n+'.log')).read_text()[-1500:] for n in ['mongo','ml','api','web'] if (Path(data)/(n+'.log')).exists()))
            time.sleep(.2)
        raise RuntimeError('Timed out waiting for '+url)
    try:
        spawn('mongo',[exe,'--dbpath',data,'--port','27018','--bind_ip','127.0.0.1','--nounixsocket','--setParameter','diagnosticDataCollectionEnabled=false','--setParameter','processUmask=077'])
        for _ in range(100):
            try:
                client=MongoClient('mongodb://localhost:27018/',serverSelectionTimeoutMS=500)
                client.admin.command('ping');break
            except Exception:time.sleep(.2)
        else:raise RuntimeError('MongoDB did not start')
        from dotenv import load_dotenv
        from argon2 import PasswordHasher
        client.dog_gis_e2e.users.insert_one({'username':'admin','email':'admin@demo.test','password_hash':PasswordHasher().hash(password),'role':'Admin','is_active':True,'created_at':__import__('datetime').datetime.now(__import__('datetime').timezone.utc),'updated_at':__import__('datetime').datetime.now(__import__('datetime').timezone.utc)})
        spawn('ml',[sys.executable,'-m','uvicorn','healthcare_ml.app:app','--host','127.0.0.1','--port','8001'])
        ready('http://127.0.0.1:8001/health')
        spawn('api',[sys.executable,'-m','uvicorn','healthcare_gis.app:app','--host','127.0.0.1','--port','8000'])
        ready('http://127.0.0.1:8000/health')
        spawn('web',['npm','start','--','--host','127.0.0.1'],frontend)
        ready('http://127.0.0.1:4200/')
        code=subprocess.call(['npx','playwright','test','e2e/flow.spec.ts','--reporter=line'],cwd=frontend,env=env)
        if code:
            print('Browser test failed. Service logs:',file=sys.stderr)
            for name in ['mongo','ml','api','web']:
                print(name+': '+(Path(data)/(name+'.log')).read_text()[-2500:],file=sys.stderr)
        raise SystemExit(code)
    finally:
        for process in reversed(processes):
            if process.poll() is None:process.terminate()
        for process in processes:
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill()
        for log in logs:log.close()
