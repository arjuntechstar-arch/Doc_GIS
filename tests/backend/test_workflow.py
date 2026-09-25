import os
import subprocess
import sys
import time
import json
from pathlib import Path
import pytest
import httpx
from healthcare_gis.jobs import execute_one

@pytest.fixture
def ml_server(tmp_path,monkeypatch):
    monkeypatch.setenv('ML_SERVICE_KEY','test-service-key-'+('x'*40))
    monkeypatch.setenv('ML_SERVICE_URL','http://127.0.0.1:8101')
    env=os.environ|{'MODEL_STORAGE':str(tmp_path),'PYTHONPATH':'src/ml'}
    log=(tmp_path/'ml.log').open('w')
    process=subprocess.Popen([sys.executable,'-m','uvicorn','healthcare_ml.app:app','--host','127.0.0.1','--port','8101'],env=env,stdout=log,stderr=log)
    for _ in range(100):
        try:
            if httpx.get('http://127.0.0.1:8101/health',trust_env=False).status_code==200:break
        except httpx.TransportError:time.sleep(.1)
    else:raise AssertionError('ML server failed to start')
    yield
    process.terminate();process.wait(timeout=10);log.close()

def test_complete_workflow_scenarios_exports(api,ml_server):
    http,db=api
    assert http.post('/api/v1/admin/demo').status_code==200
    assert http.post('/api/v1/admin/demo').json()['areas']==16
    def run(path,body):
        start=http.post(path,json=body)
        assert start.status_code==202,start.text
        id=start.json()['id'];execute_one(db)
        job=http.get('/api/v1/jobs/'+id).json()
        assert job['status']=='COMPLETED',job
        return job
    baseline=run('/api/v1/accessibility/analyze',{})
    trained=run('/api/v1/demand/train',{})
    version=trained['result']['model_version']
    predicted=run('/api/v1/demand/predict',{'modelVersion':version,'predictionYear':2027})
    candidates=run('/api/v1/candidate-sites/generate',{'demandRunId':predicted['id']})
    assert candidates['result']['count']>=5,candidates
    scenarios=[]
    for n in [1,3,5]:
        optimized=run('/api/v1/optimization/runs',{'numberOfHospitals':n,'candidateRunId':candidates['id'],'populationSize':20,'generations':10})
        assert optimized['result']['after']['coveredPopulation']>=optimized['result']['before']['coveredPopulation']
        assert len(http.get('/api/v1/optimization/runs/'+optimized['id']+'/recommendations').json()['items'])==n
        scenarios.append({'newHospitals':n,**optimized['result']})
    compared=http.get('/api/v1/reports/scenarios').json()
    assert [item['newHospitals'] for item in compared['scenarios']]==[1,3,5]
    for format in ['csv','geojson','pdf']:
        response=http.get('/api/v1/reports/export/'+optimized['id']+'?format='+format)
        assert response.status_code==200,response.text[:300]
        if format=='pdf':assert response.content.startswith(b'%PDF')
    assert len(http.get('/api/v1/gis/recommendations?runId='+optimized['id']).json()['features'])==5
    assert http.get('/api/v1/dashboard').json()['population']>0
    output=Path('var/evaluation');output.mkdir(parents=True,exist_ok=True)
    (output/'workflow.json').write_text(json.dumps({'dataset':'DEMO-CITY-v2','baseline':baseline['result'],'models':trained['result'],'scenarios':scenarios},indent=2))
