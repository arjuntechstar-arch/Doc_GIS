from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import Field
from healthcare_gis.common import clean,oid
from healthcare_gis.security import roles,current_user
from healthcare_gis.data import Strict
from healthcare_gis.jobs import HANDLERS,enqueue
from healthcare_gis.ml_client import MLClient
from healthcare_gis.spatial import center,distance,RoadGraph

router=APIRouter(prefix='/api/v1')
FEATURES=['population','population_density','population_growth','elderly_ratio','child_ratio','historical_demand','hospital_count','total_beds','nearest_hospital_distance','nearest_hospital_travel_time','emergency_coverage']

def base_features(area,hospitals,graph):
    point=center(area['geometry'])
    nearest=min(hospitals,key=lambda h:distance(point,h['location']['coordinates']),default=None)
    if nearest is None:raise ValueError('Import hospitals first')
    minutes=graph.minutes(point,nearest['location']['coordinates'])
    return {'population':area['population'],'population_density':area['population_density'],'population_growth':0.,
        'elderly_ratio':area['age_60_plus']/max(area['population'],1),'child_ratio':area['age_0_14']/max(area['population'],1),
        'hospital_count':len(hospitals),'total_beds':sum(h['bed_capacity'] for h in hospitals),
        'nearest_hospital_distance':distance(point,nearest['location']['coordinates']),
        'nearest_hospital_travel_time':minutes if minutes is not None else 240.,'emergency_coverage':float(nearest['emergency_available'])}

def dataset(db):
    hospitals=list(db.hospitals.find({'status':'Active'}))
    graph=RoadGraph(list(db.roads.find()))
    rows=[]
    for area in db.population_areas.find():
        observations=list(db.healthcare_demand.find({'area_id':area['_id']}).sort('period',1))
        base=base_features(area,hospitals,graph)
        for previous,current in zip(observations,observations[1:]):
            rows.append(base|{'historical_demand':previous['demand_value'],'target':current['demand_value'],'year':current['period'].year,
                             'area_id':str(area['_id']),'synthetic':current['source'].startswith('DEMO')})
    return rows

class Train(Strict):
    seed:int=42
class Predict(Strict):
    modelVersion:str
    predictionYear:int=Field(ge=2000,le=2200)
    populationGrowth:float=Field(default=.015,ge=-.1,le=.2)

def train_job(db,id,p,check):
    rows=dataset(db)
    check()
    metadata=MLClient(str(id)).call('/train',{'rows':rows,'seed':p['seed']})
    check()
    db.models.update_one({'model_version':metadata['model_version']},{'$set':metadata},upsert=True)
    return metadata

def predict_job(db,id,p,check):
    hospitals=list(db.hospitals.find({'status':'Active'}));graph=RoadGraph(list(db.roads.find()))
    areas=list(db.population_areas.find()); rows=[]
    for area in areas:
        latest=db.healthcare_demand.find_one({'area_id':area['_id']},sort=[('period',-1)])
        if latest is None:raise ValueError('Each population area needs historical demand')
        if p['predictionYear']<=latest['period'].year:raise ValueError('Prediction year must follow observed demand')
        # Recursive forecasts preserve lag semantics over multiple forecast years.
        rows.append(base_features(area,hospitals,graph)|{'historical_demand':latest['demand_value'],'lastYear':latest['period'].year})
    for year in range(min(r['lastYear'] for r in rows)+1,p['predictionYear']+1):
        check()
        indices=[i for i,r in enumerate(rows) if year>r['lastYear']]
        features=[]
        for i in indices:
            r=rows[i]; r['population']*=1+p['populationGrowth'];r['population_density']*=1+p['populationGrowth'];r['population_growth']=p['populationGrowth']
            features.append({f:r[f] for f in FEATURES})
        response=MLClient(str(id)).call('/predict',{'model_version':p['modelVersion'],'rows':features})
        for i,predicted in zip(indices,response['predictions']):rows[i]['historical_demand']=predicted
    check()
    for area,row in zip(areas,rows):
        db.demand_predictions.insert_one({'area_id':area['_id'],'prediction_period':datetime(p['predictionYear'],1,1,tzinfo=timezone.utc),'predicted_demand':row['historical_demand'],'model_version':p['modelVersion'],'run_id':id})
    return {'modelVersion':p['modelVersion'],'predictionYear':p['predictionYear'],'totalPredictedDemand':sum(r['historical_demand'] for r in rows),'areas':len(areas),'synthetic':response['synthetic']}
HANDLERS['train']=train_job
HANDLERS['predict']=predict_job

@router.post('/demand/train',status_code=202)
def train(body:Train,request:Request,user=Depends(roles('HealthcarePlanner'))):return {'id':str(enqueue(request.app.state.db,'train',body.model_dump(),user)),'status':'QUEUED'}
@router.post('/demand/predict',status_code=202)
def predict(body:Predict,request:Request,user=Depends(roles('HealthcarePlanner'))):return {'id':str(enqueue(request.app.state.db,'predict',body.model_dump(),user)),'status':'QUEUED'}
@router.get('/demand/models')
def models(request:Request,user=Depends(current_user)):return {'items':clean(list(request.app.state.db.models.find().sort('created_at',-1).limit(100)))}
@router.get('/demand/predictions')
def predictions(runId:str,request:Request,user=Depends(current_user)):return {'items':clean(list(request.app.state.db.demand_predictions.find({'run_id':oid(runId)}).limit(5000)))}
