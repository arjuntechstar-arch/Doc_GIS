import json

def test_crud_geometry_import_and_bbox(api):
    http, db = api
    body={'name':'Test Hospital','bed_capacity':20,'location':{'type':'Point','coordinates':[80.25,13.05]}}
    created=http.post('/api/v1/hospitals',json=body)
    assert created.status_code==201,created.text
    id=created.json()['id']
    assert http.get('/api/v1/hospitals/'+id).status_code==200
    assert len(http.get('/api/v1/gis/hospitals?bbox=80.2,13,80.3,13.1').json()['features'])==1
    assert http.get('/api/v1/gis/hospitals?bbox=-180,-90,180,90').status_code==422
    body['location']['coordinates']=[200,13]
    assert http.post('/api/v1/hospitals',json=body).status_code==422
    roads=[{'external_id':'r1','speed_kmh':30,'length_km':1,'geometry':{'type':'LineString','coordinates':[[80.2,13],[80.3,13.1]]}}]
    assert http.post('/api/v1/roads/import',files={'file':('roads.json',json.dumps(roads),'application/json')}).status_code==201
    assert http.post('/api/v1/roads/import',files={'file':('roads.json',json.dumps(roads),'application/json')}).status_code==409
    assert db.roads.count_documents({})==1
    assert http.delete('/api/v1/hospitals/'+id).status_code==200
    assert http.get('/api/v1/gis/hospitals').json()['features']==[]
