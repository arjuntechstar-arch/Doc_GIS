from fastapi import APIRouter, Request, Depends, HTTPException, Query
from pydantic import Field, model_validator
from healthcare_gis.data import Strict
from healthcare_gis.common import oid, clean
from healthcare_gis.security import roles, current_user
from healthcare_gis.jobs import enqueue, HANDLERS
from healthcare_gis.spatial import RoadGraph, analyze, summarize

router=APIRouter(prefix="/api/v1")
class Accessibility(Strict):
    analysisName: str=Field(default="Accessibility baseline",min_length=1,max_length=200)
    areaIds: list[str]=Field(default_factory=list,max_length=5000)
    travelMode: str="road"
    weights: dict[str,float]=Field(default_factory=lambda:{"distance":.3,"travelTime":.3,"capacity":.2,"emergency":.2})
    travelTimeThreshold: float=Field(default=30,gt=0,le=180)
    @model_validator(mode="after")
    def valid(self):
        if self.travelMode not in ("road","distance"):raise ValueError("Travel mode must be road or distance")
        if set(self.weights)!={"distance","travelTime","capacity","emergency"} or any(v<0 or v>1 for v in self.weights.values()) or abs(sum(self.weights.values())-1)>1e-6:raise ValueError("Four non-negative weights must sum to 1")
        if self.travelMode=="distance" and self.weights["travelTime"]==1:raise ValueError("Distance mode needs non-travel-time weights")
        for id in self.areaIds:oid(id)
        return self

def run_accessibility(db,id,p,check):
    query={"_id":{"$in":[oid(i) for i in p["areaIds"]]}} if p["areaIds"] else {}
    areas=list(db.population_areas.find(query).limit(5000))
    hospitals=list(db.hospitals.find({"status":"Active"}).limit(10000))
    roads=list(db.roads.find().limit(100000))
    if not areas or not hospitals:raise ValueError("Import population areas and active hospitals first")
    if p["travelMode"]=="road" and not roads:raise ValueError("Import a connected road network first")
    graph=RoadGraph(roads)
    results=[]
    for area in areas:
        check()
        rows=analyze([area],hospitals,graph,p["weights"],p["travelMode"],p["travelTimeThreshold"])
        results.extend(rows)
    check()
    for row in results:
        # MongoDB optional numeric fields are omitted for unreachable locations.
        db.accessibility_results.insert_one({k:v for k,v in row.items() if v is not None}|{"analysis_run_id":id})
    return summarize(results,areas)
HANDLERS["accessibility"]=run_accessibility

@router.post("/accessibility/analyze",status_code=202)
def start_analysis(body:Accessibility,request:Request,user=Depends(roles("GISAnalyst"))):
    return {"id":str(enqueue(request.app.state.db,"accessibility",body.model_dump(),user)),"status":"QUEUED"}

@router.get("/jobs/{id}")
@router.get("/accessibility/runs/{id}")
@router.get("/demand/runs/{id}")
@router.get("/optimization/runs/{id}")
def job(id:str,request:Request,user=Depends(current_user)):
    row=request.app.state.db.jobs.find_one({"_id":oid(id)})
    if not row:raise HTTPException(404,"Job not found")
    return clean(row)

@router.post("/jobs/{id}/cancel")
def cancel(id:str,request:Request,user=Depends(current_user)):
    db=request.app.state.db
    row=db.jobs.find_one({"_id":oid(id)})
    if not row:raise HTTPException(404,"Job not found")
    if row["created_by"]!=user["_id"] and user["role"]!="Admin":raise HTTPException(403,"Only the creator or Admin may cancel")
    if not db.jobs.update_one({"_id":oid(id),"status":{"$in":["QUEUED","RUNNING"]}},{"$set":{"status":"CANCELLED"}}).modified_count:raise HTTPException(409,"Job is already terminal")
    db.analysis_runs.update_one({"_id":oid(id)},{"$set":{"status":"CANCELLED"}})
    return {"status":"CANCELLED"}

@router.get("/accessibility/results")
def results(runId:str,request:Request,page:int=Query(1,ge=1),pageSize:int=Query(100,ge=1,le=500),user=Depends(current_user)):
    query={"analysis_run_id":oid(runId)}
    coll=request.app.state.db.accessibility_results
    return {"items":clean(list(coll.find(query).skip((page-1)*pageSize).limit(pageSize))),"total":coll.count_documents(query)}

@router.get("/accessibility/summary")
def summary(runId:str,request:Request,user=Depends(current_user)):
    row=request.app.state.db.analysis_runs.find_one({"_id":oid(runId),"analysis_type":"accessibility","status":"COMPLETED"})
    if not row:raise HTTPException(404,"Completed accessibility run not found")
    return clean(row["result"])

@router.get("/analysis/history")
def history(request:Request,user=Depends(current_user),page:int=Query(1,ge=1)):
    db=request.app.state.db
    return {"items":clean(list(db.analysis_runs.find().sort("created_at",-1).skip((page-1)*50).limit(50))),"total":db.analysis_runs.count_documents({})}
