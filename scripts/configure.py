"""Generate local configuration and repair missing or invalid local secrets."""
from pathlib import Path
import secrets
root=Path(__file__).resolve().parents[1]
path=root/'.env'
defaults={
    'HEALTHCARE_GIS_MONGO_URI':'mongodb://localhost:27017/',
    'HEALTHCARE_GIS_MONGO_DB':'dog_gis',
    'JWT_SECRET':secrets.token_hex(32),
    'ML_SERVICE_KEY':secrets.token_hex(32),
    'ML_SERVICE_URL':'http://127.0.0.1:8001',
    'MODEL_STORAGE':'./var/models',
    'CORS_ORIGINS':'http://localhost:4200',
}
values={}
if path.exists():
    for line in path.read_text().splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            name,value=line.split('=',1); values[name]=value
changed=[]
for name,default in defaults.items():
    invalid=not values.get(name) or (name in {'JWT_SECRET','ML_SERVICE_KEY'} and len(values[name])<32)
    if invalid:
        values[name]=default; changed.append(name)
content='\n'.join(f'{name}={values.get(name, default)}' for name,default in defaults.items())+'\n'
for name,value in values.items():
    if name not in defaults: content+=f'{name}={value}\n'
path.write_text(content)
print('Created .env with generated local secrets' if not changed else 'Configured: '+', '.join(changed))
