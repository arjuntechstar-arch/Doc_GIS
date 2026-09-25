"""Generate local configuration without overwriting existing secrets."""
from pathlib import Path
import secrets
root=Path(__file__).resolve().parents[1]
path=root/'.env'
if path.exists():
    print('.env already exists; leaving it unchanged')
else:
    path.write_text('HEALTHCARE_GIS_MONGO_URI=mongodb://localhost:27017/\nHEALTHCARE_GIS_MONGO_DB=dog_gis\nJWT_SECRET='+secrets.token_hex(32)+'\nML_SERVICE_KEY='+secrets.token_hex(32)+'\nML_SERVICE_URL=http://127.0.0.1:8001\nMODEL_STORAGE=./var/models\nCORS_ORIGINS=http://localhost:4200\n')
    print('Created .env with generated local secrets')
