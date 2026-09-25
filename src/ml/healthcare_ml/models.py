"""Reproducible chronological training, held-out evaluation and versioned artifacts."""
import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
import joblib
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.inspection import permutation_importance
from xgboost import XGBRegressor

FEATURES=['population','population_density','population_growth','elderly_ratio','child_ratio','historical_demand','hospital_count','total_beds','nearest_hospital_distance','nearest_hospital_travel_time','emergency_coverage']

def storage():
    path=Path(os.getenv('MODEL_STORAGE','./var/models')).resolve()
    path.mkdir(parents=True,exist_ok=True)
    return path

def metrics(y,p):
    mask=y!=0
    return {'mae':float(mean_absolute_error(y,p)),'rmse':float(np.sqrt(mean_squared_error(y,p))),
            'r2':float(r2_score(y,p)) if len(y)>1 and float(np.var(y))>0 else None,
            'mape':float(np.mean(np.abs((y[mask]-p[mask])/y[mask]))*100) if mask.any() else None}

def train(rows,seed=42):
    years=sorted({row['year'] for row in rows})
    if len(rows)<24 or len(years)<5:raise ValueError('Need at least 24 records across 5 years for train/validation/test splits')
    train_end=max(1,int(len(years)*.6)); val_end=max(train_end+1,int(len(years)*.8))
    groups=[years[:train_end],years[train_end:val_end],years[val_end:]]
    sets=[]
    for group in groups:
        selected=[r for r in rows if r['year'] in group]
        x=np.array([[r[f] for f in FEATURES] for r in selected],dtype=float)
        y=np.array([r['target'] for r in selected],dtype=float)
        if not np.isfinite(x).all() or not np.isfinite(y).all():raise ValueError('Features and targets must be finite')
        sets.append((x,y))
    (x,y),(vx,vy),(tx,ty)=sets
    models={
        'linear_regression':LinearRegression(),
        'random_forest':RandomForestRegressor(n_estimators=80,max_depth=8,random_state=seed,n_jobs=1),
        'xgboost':XGBRegressor(n_estimators=100,max_depth=3,learning_rate=.08,random_state=seed,n_jobs=1,objective='reg:squarederror'),
    }
    comparisons={}
    for name,model in models.items():
        model.fit(x,y)
        comparisons[name]={'validation':metrics(vy,np.maximum(0,model.predict(vx))), 'test':metrics(ty,np.maximum(0,model.predict(tx)))}
    selected=min(models,key=lambda name:comparisons[name]['validation']['rmse'])
    model=models[selected]
    importance=permutation_importance(model,vx,vy,scoring='neg_mean_absolute_error',random_state=seed,n_repeats=5,n_jobs=1)
    version=uuid.uuid4().hex
    metadata={
        'model_version':version,'training_data_version':hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest(),
        'feature_schema_version':'1','features':FEATURES,'algorithm':selected,
        'hyperparameters':model.get_params(),'metrics':comparisons[selected]['test'],'comparison':comparisons,
        'feature_importance':dict(zip(FEATURES,map(float,importance.importances_mean))),
        'created_at':datetime.now(timezone.utc).isoformat(),'split_years':{'train':groups[0],'validation':groups[1],'test':groups[2]},
        'seed':seed,'records':len(rows), 'synthetic':any(r.get('synthetic',False) for r in rows)}
    joblib.dump(model,storage()/(version+'.joblib'))
    (storage()/(version+'.json')).write_text(json.dumps(metadata,default=str))
    return metadata

def metadata(version):
    if not re.fullmatch(r'[0-9a-f]{32}',version):raise ValueError('Invalid model version')
    path=storage()/(version+'.json')
    if not path.exists():raise ValueError('Model not found')
    return json.loads(path.read_text())

def predict(version,rows):
    info=metadata(version)
    model=joblib.load(storage()/(version+'.joblib'))
    x=np.array([[r[f] for f in FEATURES] for r in rows],dtype=float)
    if not len(x) or not np.isfinite(x).all():raise ValueError('Supply finite feature rows')
    predictions=np.maximum(0,model.predict(x))
    return {'model_version':version,'predictions':list(map(float,predictions)), 'synthetic':info['synthetic']}
