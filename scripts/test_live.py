"""Run the Python test suite against a disposable local MongoDB process."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from pymongo import MongoClient

root=Path(__file__).resolve().parents[1]
exe=os.getenv('MONGOD_BINARY') or shutil.which('mongod')
if not exe:raise SystemExit('Set MONGOD_BINARY to your local mongod executable')
with tempfile.TemporaryDirectory(prefix='docgis-mongo-') as data:
    log=Path(data)/'mongod.log'
    with log.open('w') as output:
        process=subprocess.Popen([exe,'--dbpath',data,'--port','27018','--bind_ip','127.0.0.1','--nounixsocket','--setParameter','diagnosticDataCollectionEnabled=false','--setParameter','processUmask=077'],stdout=output,stderr=subprocess.STDOUT)
        try:
            for _ in range(60):
                try:
                    MongoClient('mongodb://localhost:27018/',serverSelectionTimeoutMS=500).admin.command('ping')
                    break
                except Exception:
                    if process.poll() is not None:raise RuntimeError('MongoDB failed to start: '+log.read_text()[-2000:])
                    time.sleep(.2)
            else:raise RuntimeError('MongoDB did not start: '+log.read_text()[-2000:])
            env=os.environ.copy()
            env.update(HEALTHCARE_GIS_TEST_MONGO_URI='mongodb://localhost:27018/',HEALTHCARE_GIS_MONGO_URI='mongodb://localhost:27018/',HEALTHCARE_GIS_MONGO_DB='dog_gis_test',PYTHONPATH=os.pathsep.join([str(root/'src/backend'),str(root/'src/ml')]))
            code=subprocess.call([sys.executable,'-m','pytest','-q','tests/backend','tests/ml'],cwd=root,env=env)
        finally:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill()
    raise SystemExit(code)
