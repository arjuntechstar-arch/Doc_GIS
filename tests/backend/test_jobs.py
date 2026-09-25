from datetime import timedelta
from healthcare_gis.jobs import enqueue,execute_one,HANDLERS
from healthcare_gis.security import now

def test_cancel_and_recover_expired_job(api):
    http,db=api
    user=db.users.find_one({'username':'admin'})
    id=enqueue(db,'accessibility',{},user)
    assert http.post('/api/v1/jobs/'+str(id)+'/cancel').status_code==200
    assert not execute_one(db)
    assert http.post('/api/v1/jobs/'+str(id)+'/cancel').status_code==409
    id=enqueue(db,'accessibility',{},user)
    db.jobs.update_one({'_id':id},{'$set':{'status':'RUNNING','lease_until':now()-timedelta(minutes=1)}})
    assert not execute_one(db)
    assert db.analysis_runs.find_one({'_id':id})['status']=='FAILED'
