import csv
import io
import json
from fastapi import APIRouter,Request,Depends,HTTPException
from fastapi.responses import Response
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
from xml.sax.saxutils import escape
from healthcare_gis.security import roles,current_user
from healthcare_gis.common import clean,oid,audit
from healthcare_gis.demo import load_demo

router=APIRouter(prefix='/api/v1')
@router.post('/admin/demo')
def demo(request:Request,user=Depends(roles())):
    try:result=load_demo(request.app.state.db)
    except ValueError as exc:raise HTTPException(409,str(exc))
    audit(request.app.state.db,user,'seed','demo',metadata=result)
    return result

@router.get('/dashboard')
def dashboard(request:Request,user=Depends(current_user)):
    db=request.app.state.db
    hospitals=list(db.hospitals.find({'status':'Active'}))
    latest={}
    for kind in ['accessibility','predict','optimization','candidates','train']:
        latest[kind]=clean(db.analysis_runs.find_one({'analysis_type':kind,'status':'COMPLETED'},sort=[('created_at',-1)]))
    result=(latest['accessibility'] or {}).get('result',{})
    return {'totalHospitals':len(hospitals),'totalBeds':sum(h['bed_capacity'] for h in hospitals),
        'population':sum(a['population'] for a in db.population_areas.find()),
        'underservedPopulation':result.get('underservedPopulation'),'criticalAreas':result.get('criticalAreas'),
        'latest':latest,'synthetic':db.healthcare_demand.count_documents({'source':{'$regex':'^DEMO'}})>0}

@router.get('/reports/scenarios')
def scenarios(request:Request,user=Depends(current_user)):
    """Latest completed +1/+3/+5 hospital runs using a common baseline."""
    db=request.app.state.db
    entries=[]
    for count in (1,3,5):
        row=db.analysis_runs.find_one({'analysis_type':'optimization','status':'COMPLETED',
            'parameters.numberOfHospitals':count},sort=[('created_at',-1)])
        if row:
            result=row['result']
            entries.append({'newHospitals':count,'runId':str(row['_id']),
                'before':result['before'],'after':result['after'],
                'estimatedCostUnits':result['estimatedCostUnits']})
    return {'scenarios':clean(entries),'synthetic':db.healthcare_demand.count_documents({'source':{'$regex':'^DEMO'}})>0}

@router.get('/reports/accessibility/{runId}')
@router.get('/reports/optimization/{runId}')
def report(runId:str,request:Request,user=Depends(current_user)):
    row=request.app.state.db.analysis_runs.find_one({'_id':oid(runId),'status':'COMPLETED'})
    if not row:raise HTTPException(404,'Completed run not found')
    return clean(row)

@router.get('/reports/export/{runId}')
def export(runId:str,request:Request,format:str='csv',user=Depends(roles('HealthcarePlanner','GISAnalyst'))):
    db=request.app.state.db
    run=db.analysis_runs.find_one({'_id':oid(runId),'status':'COMPLETED'})
    if not run:raise HTTPException(404,'Completed run not found')
    collections={'accessibility':('accessibility_results','analysis_run_id'),'optimization':('recommendations','optimization_run_id'),'predict':('demand_predictions','run_id'),'candidates':('candidate_sites','generated_run_id')}
    if run['analysis_type'] not in collections:raise HTTPException(422,'This run has no spatial export')
    coll,key=collections[run['analysis_type']]
    rows=list(db[coll].find({key:run['_id']}))
    if format=='csv':
        prepared=clean(rows)
        fields=sorted({k for row in prepared for k in row})
        out=io.StringIO();writer=csv.DictWriter(out,fieldnames=fields);writer.writeheader()
        for row in prepared:
            for k,v in row.items():
                if isinstance(v,(dict,list)):row[k]=json.dumps(v)
                elif isinstance(v,str) and v.startswith(('=','+','-','@')):row[k]="'"+v
            writer.writerow(row)
        content=out.getvalue();mime='text/csv'
    elif format=='geojson':
        features=[]
        for row in rows:
            source=row if 'location' in row else db.candidate_sites.find_one({'_id':row['candidate_site_id']}) if 'candidate_site_id' in row else db.population_areas.find_one({'_id':row['area_id']})
            if source:features.append({'type':'Feature','geometry':source.get('location',source.get('geometry')),'properties':clean(row)})
        content=json.dumps({'type':'FeatureCollection','features':features});mime='application/geo+json'
    elif format=='pdf':
        out=io.BytesIO();styles=getSampleStyleSheet();story=[Paragraph('Healthcare GIS planning report',styles['Title']),Spacer(1,16),Paragraph('Decision support only. Synthetic demo inputs do not represent observed healthcare conditions. Recommendations require independent feasibility review.',styles['BodyText']),Spacer(1,16)]
        story.append(Paragraph('Run: '+escape(runId)+' · '+escape(run['analysis_type']),styles['Heading2']))
        for name,value in clean(run.get('result',{})).items():
            if name=='convergence':continue
            story.append(Paragraph(escape(name)+': '+escape(json.dumps(value)),styles['BodyText']));story.append(Spacer(1,8))
        SimpleDocTemplate(out).build(story);content=out.getvalue();mime='application/pdf'
    else:raise HTTPException(422,'Use csv, geojson or pdf')
    audit(db,user,'export',run['analysis_type'],run['_id'],{'format':format})
    return Response(content,media_type=mime,headers={'Content-Disposition':f'attachment; filename="healthcare-{runId}.{format}"'})
