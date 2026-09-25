from healthcare_gis.database import seed_demo
from healthcare_gis.jobs import execute_one
from healthcare_gis.spatial import RoadGraph, distance, classify

def test_road_routing_and_disconnected():
    graph=RoadGraph([{'geometry':{'coordinates':[[80,13],[80.01,13],[80.01,13.01]]},'speed_kmh':30}])
    assert graph.minutes([80,13],[80.01,13.01]) > distance([80,13],[80.01,13.01])/30*60
    assert RoadGraph([]).minutes([80,13],[80.1,13]) is None
    assert classify(.249)=='Critical' and classify(.25)=='Poor' and classify(.75)=='Good'

def test_async_accessibility(api):
    http,db=api
    seed_demo(db)
    response=http.post('/api/v1/accessibility/analyze',json={})
    assert response.status_code==202,response.text
    execute_one(db)
    job=http.get('/api/v1/jobs/'+response.json()['id']).json()
    assert job['status']=='COMPLETED',job
    assert job['result']['population']==21000
    assert db.accessibility_results.count_documents({})==2
    assert http.get('/api/v1/gis/accessibility?runId='+job['id']).json()['features']
    assert http.post('/api/v1/accessibility/analyze',json={'weights':{'distance':2}}).status_code==422
