"""Reproducible synthetic city: 16 areas, connected roads, and 14 years of demand."""
from datetime import datetime,timezone
from healthcare_gis.spatial import GEOD
from healthcare_gis.security import now

def load_demo(db):
    if db.population_areas.count_documents({'area_code':{'$not':{'$regex':'^DEMO-'}}}):
        raise ValueError('Use a separate database for demo data; non-demo population areas already exist')
    for n,coords in enumerate([[80.20,13.00],[80.24,13.04]],1):
        db.hospitals.update_one({'external_id':f'DEMO-CITY-H{n}'},{'$setOnInsert':{'name':f'Demo city hospital {n}','hospital_type':'General','bed_capacity':120,'specialty_count':5,'emergency_available':n==1,'location':{'type':'Point','coordinates':coords},'status':'Active','created_at':now(),'updated_at':now()}},upsert=True)
    for x in range(4):
        for y in range(4):
            w,s=80.2+x*.04,13+y*.04;e,n=w+.04,s+.04
            ring=[[w,s],[e,s],[e,n],[w,n],[w,s]]
            pop=8000+x*2000+y*1500
            area_m2=abs(GEOD.polygon_area_perimeter([c[0] for c in ring],[c[1] for c in ring])[0])
            db.population_areas.update_one({'area_code':f'DEMO-CITY-{x}-{y}','year':2025},{'$setOnInsert':{'name':f'Demo district {x+1}-{y+1}','population':pop,'population_density':pop/(area_m2/1e6),'age_0_14':pop//5,'age_15_59':pop*7//10,'age_60_plus':pop//10,'geometry':{'type':'MultiPolygon','coordinates':[[ring]]}}},upsert=True)
            area=db.population_areas.find_one({'area_code':f'DEMO-CITY-{x}-{y}','year':2025})
            for year in range(2012,2026):
                value=pop*.12*(1.025**(year-2012))+x*40+y*30+((year+x+y)%3)*20
                db.healthcare_demand.update_one({'area_id':area['_id'],'period':datetime(year,1,1,tzinfo=timezone.utc),'source':'DEMO-CITY-v2'},{'$setOnInsert':{'demand_value':value,'created_at':datetime(2026,1,1,tzinfo=timezone.utc)}},upsert=True)
    # Upgrade the earlier two-area demonstration without deleting or altering its records.
    for area in db.population_areas.find({'area_code': {'$in': ['DEMO-A1', 'DEMO-A2']}}):
        for year in range(2012,2026):
            db.healthcare_demand.update_one({'area_id':area['_id'],'period':datetime(year,1,1,tzinfo=timezone.utc),'source':'DEMO-CITY-v2'}, {'$setOnInsert':{'demand_value':area['population']*.12*1.025**(year-2012),'created_at':datetime(2026,1,1,tzinfo=timezone.utc)}},upsert=True)
    for axis in range(2):
        for line in range(9):
            coords=[[80.2+(line if axis else i)*.02,13+(i if axis else line)*.02] for i in range(9)]
            length=sum(abs(GEOD.inv(*a,*b)[2])/1000 for a,b in zip(coords,coords[1:]))
            db.roads.update_one({'external_id':f'DEMO-CITY-R{axis}-{line}'},{'$setOnInsert':{'road_type':'primary','speed_kmh':30.,'length_km':length,'geometry':{'type':'LineString','coordinates':coords}}},upsert=True)
    ring=[[80.19,12.99],[80.37,12.99],[80.37,13.17],[80.19,13.17],[80.19,12.99]]
    db.boundaries.update_one({'name':'Demo study boundary'},{'$setOnInsert':{'land_use':'boundary','geometry':{'type':'Polygon','coordinates':[ring]}}},upsert=True)
    water=[[80.33,13.13],[80.35,13.13],[80.35,13.15],[80.33,13.15],[80.33,13.13]]
    db.boundaries.update_one({'name':'Demo lake'},{'$setOnInsert':{'land_use':'water','geometry':{'type':'Polygon','coordinates':[water]}}},upsert=True)
    return {'synthetic':True,'version':'DEMO-CITY-v2','areas':db.population_areas.count_documents({}),'hospitals':db.hospitals.count_documents({}),'roads':db.roads.count_documents({}),'demandRecords':db.healthcare_demand.count_documents({})}
