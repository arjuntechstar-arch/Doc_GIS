"""Persistent, atomically claimed jobs with cancellation and expiring leases."""
import logging
import threading
from datetime import timedelta
from pymongo import ReturnDocument
from healthcare_gis.security import now
from healthcare_gis.common import audit

HANDLERS={}
class Cancelled(Exception): pass

def enqueue(db,kind,parameters,user):
    row={"analysis_type":kind,"parameters":parameters,"status":"QUEUED","created_by":user["_id"],"created_at":now()}
    id=db.analysis_runs.insert_one(row).inserted_id
    try:db.jobs.insert_one({"_id":id,"kind":kind,"parameters":parameters,"status":"QUEUED","created_by":user["_id"],"created_at":now()})
    except Exception:
        db.analysis_runs.delete_one({'_id':id})
        raise
    audit(db,user,"enqueue",kind,id)
    return id

def cleanup(db,id):
    for collection,key in [('accessibility_results','analysis_run_id'),('demand_predictions','run_id'),('candidate_sites','generated_run_id'),('recommendations','optimization_run_id'),('optimization_runs','_id')]:
        db[collection].delete_many({key:id})

def execute_one(db):
    for expired in db.jobs.find({"status":"RUNNING","lease_until":{"$lt":now()}}):
        state={"status":"FAILED","error":"Worker lease expired; submit a new run","completed_at":now()}
        if db.jobs.update_one({'_id':expired['_id'],'status':'RUNNING','lease_until':{'$lt':now()}},{'$set':state}).modified_count:
            cleanup(db,expired['_id']);db.analysis_runs.update_one({'_id':expired['_id']},{'$set':state})
    job=db.jobs.find_one_and_update({"status":"QUEUED"},{"$set":{"status":"RUNNING","started_at":now(),"lease_until":now()+timedelta(seconds=120)}},sort=[("created_at",1)],return_document=ReturnDocument.AFTER)
    if not job:return False
    id=job["_id"]
    db.analysis_runs.update_one({"_id":id},{"$set":{"status":"RUNNING"}})
    def check():
        if not db.jobs.update_one({"_id":id,"status":"RUNNING"},{"$set":{"lease_until":now()+timedelta(seconds=120)}}).matched_count:raise Cancelled()
    try:
        result=HANDLERS[job["kind"]](db,id,job["parameters"],check)
        check()
        state={"status":"COMPLETED","result":result,"completed_at":now()}
    except Cancelled:
        state={"status":"CANCELLED","completed_at":now()}
    except Exception as exc:
        logging.error("Job %s failed: %s",str(id),type(exc).__name__)
        state={"status":"FAILED","error":str(exc)[:500] if isinstance(exc,ValueError) else "Operation failed; check service availability and input data","completed_at":now()}
    result=db.jobs.update_one({"_id":id,'status':'RUNNING'},{"$set":state})
    if not result.matched_count:
        current=db.jobs.find_one({'_id':id})
        state={k:current[k] for k in ('status','error','completed_at') if k in current}
    if state['status']!='COMPLETED':cleanup(db,id)
    db.analysis_runs.update_one({"_id":id},{"$set":state})
    return True

def start_worker(db):
    stop=threading.Event()
    def loop():
        while not stop.is_set():
            try: did_work=execute_one(db)
            except Exception:
                logging.error("Job polling failed")
                did_work=False
            if not did_work: stop.wait(.5)
    thread=threading.Thread(target=loop,daemon=True)
    thread.start()
    return stop,thread
