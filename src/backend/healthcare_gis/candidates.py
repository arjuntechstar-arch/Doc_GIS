import math
from fastapi import APIRouter,Request,Depends,HTTPException,Query
from pydantic import Field
from pyproj import CRS,Transformer
from shapely.geometry import shape,Point,mapping
from shapely.ops import transform
from healthcare_gis.common import clean,oid
from healthcare_gis.data import Strict
from healthcare_gis.security import roles,current_user
from healthcare_gis.jobs import enqueue,HANDLERS
from healthcare_gis.spatial import center,distance,RoadGraph

router=APIRouter(prefix='/api/v1')
class Candidates(Strict):
    minPopulation:int=Field(default=5000,ge=0)
    minDemand:float=Field(default=1000,ge=0)
    minRoadAccessScore:float=Field(default=.5,ge=0,le=1)
    minDistanceFromExistingHospitalKm:float=Field(default=3,ge=0,le=50)
    excludedLandUse:list[str]=Field(default_factory=lambda:['water','protected_forest'])
    gridSpacingKm:float=Field(default=1.5,ge=.5,le=10)
    demandRunId:str|None=None

def generate(db,id,p,check):
    prediction=db.analysis_runs.find_one({'_id':oid(p['demandRunId']),'status':'COMPLETED','analysis_type':'predict'}) if p.get('demandRunId') else db.analysis_runs.find_one({'analysis_type':'predict','status':'COMPLETED'},sort=[('created_at',-1)])
    if not prediction:raise ValueError('Complete demand prediction before generating sites')
    demand={str(r['area_id']):r['predicted_demand'] for r in db.demand_predictions.find({'run_id':prediction['_id']})}
    boundaries=list(db.boundaries.find())
    if not boundaries:raise ValueError('Import study boundary and land-use exclusions before generating sites')
    excluded=[shape(r['geometry']) for r in boundaries if r['land_use'] in set(p['excludedLandUse'])|{'water'}]
    limits=[shape(r['geometry']) for r in boundaries if r['land_use']=='boundary']
    hospitals=list(db.hospitals.find({'status':'Active'}))
    graph=RoadGraph(list(db.roads.find()))
    areas=list(db.population_areas.find());accepted=[];rejections={'population':0,'demand':0,'land':0,'hospitalDistance':0,'roadAccess':0}
    for area in areas:
        check()
        if area['population']<p['minPopulation']:rejections['population']+=1;continue
        predicted=demand.get(str(area['_id']),0)
        if predicted<p['minDemand']:rejections['demand']+=1;continue
        lon,lat=center(area['geometry'])
        local=CRS.from_proj4(f'+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m')
        forward=Transformer.from_crs(4326,local,always_xy=True).transform
        backward=Transformer.from_crs(local,4326,always_xy=True).transform
        polygon=shape(area['geometry']); projected=transform(forward,polygon)
        west,south,east,north=projected.bounds
        step=p['gridSpacingKm']*1000
        points=[Point(0,0)]
        x=west+step/2
        while x<east:
            y=south+step/2
            while y<north:
                if len(points)>5000:raise ValueError('Candidate grid too dense; increase spacing')
                points.append(Point(x,y));y+=step
            x+=step
        for point in points:
            if not projected.covers(point):continue
            wgs=transform(backward,point);coords=[wgs.x,wgs.y]
            if (limits and not any(g.covers(wgs) for g in limits)) or any(g.intersects(wgs) for g in excluded):rejections['land']+=1;continue
            nearest=min((distance(coords,h['location']['coordinates']) for h in hospitals),default=math.inf)
            if nearest<p['minDistanceFromExistingHospitalKm']:rejections['hospitalDistance']+=1;continue
            _,offset=graph.snap(coords)
            road=max(0,1-offset/2)
            if road<p['minRoadAccessScore']:rejections['roadAccess']+=1;continue
            if any(distance(coords,c['location']['coordinates'])<.25 for c in accepted):continue
            accepted.append({'name':f"{area['name']} site {len(accepted)+1}",'location':{'type':'Point','coordinates':coords},'population_score':min(1,area['population']/20000),'demand_score':min(1,predicted/10000),'road_access_score':road,'land_suitability_score':1.,'cost_score':.5,'feasibility_status':'Feasible','generated_run_id':id,'area_id':area['_id'],'predicted_demand':predicted,'nearest_hospital_km':nearest,'estimated_cost_units':1.,'assumptions':['Uniform land cost: no parcel cost data supplied']})
            if len(accepted)>=1000:raise ValueError('More than 1000 feasible sites; increase grid spacing')
    check()
    if accepted:db.candidate_sites.insert_many(accepted)
    return {'count':len(accepted),'rejections':rejections,'demandRunId':str(prediction['_id']),'assumption':'Feasibility uses imported exclusions only; all sites have equal assumed cost'}
HANDLERS['candidates']=generate

@router.post('/candidate-sites/generate',status_code=202)
def start(body:Candidates,request:Request,user=Depends(roles('GISAnalyst'))):return {'id':str(enqueue(request.app.state.db,'candidates',body.model_dump(),user)),'status':'QUEUED'}
@router.get('/candidate-sites')
def candidates(request:Request,runId:str|None=None,page:int=Query(1,ge=1),pageSize:int=Query(100,ge=1,le=500),user=Depends(current_user)):
    query={'generated_run_id':oid(runId)} if runId else {}
    coll=request.app.state.db.candidate_sites
    return {'items':clean(list(coll.find(query).skip((page-1)*pageSize).limit(pageSize))),'total':coll.count_documents(query)}
@router.get('/candidate-sites/{id}')
def candidate(id:str,request:Request,user=Depends(current_user)):
    row=request.app.state.db.candidate_sites.find_one({'_id':oid(id)})
    if not row:raise HTTPException(404,'Site not found')
    return clean(row)
