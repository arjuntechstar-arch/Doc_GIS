"""Start the local API, ML service and Angular development server."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from dotenv import load_dotenv
root=Path(__file__).resolve().parents[1]
load_dotenv(root/'.env')
env=os.environ.copy();env['PYTHONPATH']=os.pathsep.join([str(root/'src/backend'),str(root/'src/ml')])
npm=shutil.which('npm')
if not npm:raise SystemExit('Install Node.js 24 and npm first')
commands=[([sys.executable,'-m','uvicorn','healthcare_ml.app:app','--host','127.0.0.1','--port','8001'],root),([sys.executable,'-m','uvicorn','healthcare_gis.app:app','--host','127.0.0.1','--port','8000'],root),([npm,'start','--','--host','127.0.0.1'],root/'src/frontend/healthcare-gis-web')]
processes=[]
try:
    for command,cwd in commands:processes.append(subprocess.Popen(command,cwd=cwd,env=env))
    print('Open http://localhost:4200 · API docs http://localhost:8000/docs')
    while all(p.poll() is None for p in processes):time.sleep(.5)
    if any(p.returncode for p in processes):raise SystemExit('A service stopped; inspect its error above')
except KeyboardInterrupt:pass
finally:
    for process in processes:
        if process.poll() is None:process.terminate()
    for process in processes:
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill()
