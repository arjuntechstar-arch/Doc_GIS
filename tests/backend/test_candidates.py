from datetime import datetime,timezone
from healthcare_gis.database import seed_demo
from healthcare_gis.jobs import execute_one

def test_candidates_respect_land_exclusion(api):
    http,db=api;seed_demo(db)
    user=db.users.find_one({'username':'admin'})
    run=db.analysis_runs.insert_one({'analysis_type':'predict','parameters':{},'status':'COMPLETED','created_at':datetime.now(timezone.utc),'created_by':user['_id']}).inserted_id
    for area in db.population_areas.find():
        db.demand_predictions.insert_one({'area_id':area['_id'],'prediction_period':datetime(2027,1,1,tzinfo=timezone.utc),'predicted_demand':2000.,'model_version':'test','run_id':run})
        db.boundaries.insert_one({'name':'water','land_use':'water','geometry':area['geometry']})
    result=http.post('/api/v1/candidate-sites/generate',json={'minDistanceFromExistingHospitalKm':0,'minRoadAccessScore':0})
    assert result.status_code==202
    execute_one(db)
    job=http.get('/api/v1/jobs/'+result.json()['id']).json()
    assert job['status']=='COMPLETED',job
    assert job['result']['count']==0
    assert job['result']['rejections']['land']>0
