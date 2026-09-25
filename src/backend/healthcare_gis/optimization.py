import math
from fastapi import APIRouter,Request,Depends,HTTPException
from pydantic import Field,model_validator
from healthcare_gis.data import Strict
from healthcare_gis.common import clean,oid
from healthcare_gis.security import roles,current_user,now
from healthcare_gis.jobs import enqueue,HANDLERS
from healthcare_gis.spatial import center,RoadGraph,analyze,summarize
from healthcare_gis.ml_client import MLClient

router=APIRouter(prefix='/api/v1')
class Optimization(Strict):
    numberOfHospitals:int=Field(default=3,ge=1,le=50)
    candidateRunId:str|None=None
    objectiveWeights:dict[str,float]=Field(default_factory=lambda:{'populationCoverage':.35,'demandCoverage':.25,'accessibilityImprovement':.25,'roadAccess':.1,'cost':.05})
    populationSize:int=Field(default=60,ge=10,le=300)
    generations:int=Field(default=60,ge=1,le=500)
    mutationRate:float=Field(default=.05,ge=0,le=1)
    seed:int=42
    proposedBedCapacity:int=Field(default=150,ge=1,le=10000)
    @model_validator(mode='after')
    def weights(self):
        if set(self.objectiveWeights)!={'populationCoverage','demandCoverage','accessibilityImprovement','roadAccess','cost'} or any(v<0 or not math.isfinite(v) for v in self.objectiveWeights.values()) or abs(sum(self.objectiveWeights.values())-1)>1e-6:raise ValueError('Objective weights must be finite, nonnegative and sum to 1')
        return self

def run_optimization(db,id,p,check):
    source=db.analysis_runs.find_one({'_id':oid(p['candidateRunId']),'status':'COMPLETED','analysis_type':'candidates'}) if p.get('candidateRunId') else db.analysis_runs.find_one({'analysis_type':'candidates','status':'COMPLETED'},sort=[('created_at',-1)])
    if not source:raise ValueError('Generate candidate sites first')
    candidates=list(db.candidate_sites.find({'generated_run_id':source['_id'],'feasibility_status':'Feasible'}))
    if len(candidates)<p['numberOfHospitals']:raise ValueError('Not enough feasible candidate sites')
    areas=list(db.population_areas.find());hospitals=list(db.hospitals.find({'status':'Active'}));graph=RoadGraph(list(db.roads.find()))
    weights={'distance':.3,'travelTime':.3,'capacity':.2,'emergency':.2}
    baseline=analyze(areas,hospitals,graph,weights)
    demand_run=oid(source['result']['demandRunId'])
    demand={str(r['area_id']):r['predicted_demand'] for r in db.demand_predictions.find({'run_id':demand_run})}
    matrix=[]
    for candidate in candidates:
        check()
        matrix.append([graph.minutes(center(a['geometry']),candidate['location']['coordinates']) for a in areas])
    # Unreachable routes receive a documented 240-minute fitness penalty only; actual reports retain nulls.
    payload={k:p[k] for k in ['numberOfHospitals','objectiveWeights','populationSize','generations','mutationRate','seed']}
    payload.update(candidates=[{'road_access_score':c['road_access_score'],'cost_score':c['cost_score']} for c in candidates],population=[a['population'] for a in areas],demand=[demand.get(str(a['_id']),0) for a in areas],baselineMinutes=[r.get('travel_time_minutes') if r.get('travel_time_minutes') is not None else 240 for r in baseline],candidateMinutes=[[v if v is not None else 240 for v in row] for row in matrix])
    optimized=MLClient(str(id)).call('/optimize',payload);check()
    # Rank selected sites by their standalone population-weighted road-time savings.
    # The GA's fitness remains a score for the entire selected set.
    base_minutes=payload['baselineMinutes']
    ranked=[]
    for index in optimized['selectedIndices']:
        savings=sum(a['population']*max(0,old-new) for a,old,new in zip(areas,base_minutes,payload['candidateMinutes'][index]))
        ranked.append((savings,index))
    ranked.sort(key=lambda item:(-item[0],str(candidates[item[1]]['_id'])))
    selected=[candidates[index] for _,index in ranked]
    proposed=[{'_id':c['_id'],'location':c['location'],'bed_capacity':p['proposedBedCapacity'],'emergency_available':True} for c in selected]
    after=analyze(areas,hospitals+proposed,graph,weights)
    before_summary=summarize(baseline,areas);after_summary=summarize(after,areas)
    db.optimization_runs.insert_one({'_id':id,'number_of_sites':p['numberOfHospitals'],'objective_configuration':p['objectiveWeights'],'status':'COMPLETED','started_at':now(),'completed_at':now()})
    for rank,(standalone_savings,index) in enumerate(ranked,1):
        candidate=candidates[index]
        db.recommendations.insert_one({'optimization_run_id':id,'candidate_site_id':candidate['_id'],'rank':rank,'total_score':optimized['fitness'],
            'estimated_population_served':sum(a['population'] for a,row in zip(areas,after) if row.get('nearest_hospital_id')==candidate['_id']),
            'estimated_avg_travel_time':after_summary['averageTravelTimeMinutes'] or 0.,
            'accessibility_improvement':after_summary['meanAccessibilityIndex']-before_summary['meanAccessibilityIndex'],
            'explanation':{'primaryFactors':['Feasible land and hospital separation','Population and predicted demand coverage','Road-network travel improvement'],'objectiveContributions':optimized['contributions'],'standalonePopulationWeightedMinutesSaved':standalone_savings,'assumptions':['Equal site costs','Proposed hospitals provide emergency care',f"{p['proposedBedCapacity']} beds per proposed hospital"],'jointFitness':True}})
    return {'before':before_summary,'after':after_summary,'fitness':optimized['fitness'],'contributions':optimized['contributions'],'convergence':optimized['history'],'selectedIds':[str(c['_id']) for c in selected],'estimatedCostUnits':sum(c['estimated_cost_units'] for c in selected),'candidateRunId':str(source['_id']),'limitation':'Genetic algorithm heuristic; not a proof of global optimality. Unreachable routes have a 240-minute fitness penalty.'}
HANDLERS['optimization']=run_optimization

@router.post('/optimization/runs',status_code=202)
def start(body:Optimization,request:Request,user=Depends(roles('HealthcarePlanner'))):return {'id':str(enqueue(request.app.state.db,'optimization',body.model_dump(),user)),'status':'QUEUED'}
@router.get('/optimization/runs/{id}/recommendations')
def recommendations(id:str,request:Request,user=Depends(current_user)):
    return {'items':clean(list(request.app.state.db.recommendations.find({'optimization_run_id':oid(id)}).sort('rank',1)))}
