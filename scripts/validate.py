"""Run the complete Python suite against an explicitly selected test MongoDB server."""
import os
from pathlib import Path
import subprocess
import sys
root=Path(__file__).resolve().parents[1]
if not os.getenv('HEALTHCARE_GIS_TEST_MONGO_URI'):
    raise SystemExit('Set HEALTHCARE_GIS_TEST_MONGO_URI to a MongoDB server where disposable *_test databases may be created and deleted.')
env=os.environ.copy();env['PYTHONPATH']=os.pathsep.join([str(root/'src/backend'),str(root/'src/ml')])
raise SystemExit(subprocess.call([sys.executable,'-m','pytest','tests/backend','tests/ml','-q'],cwd=root,env=env))
