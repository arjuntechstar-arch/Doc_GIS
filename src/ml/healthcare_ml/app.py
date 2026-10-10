import os
import secrets
from fastapi import FastAPI, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from healthcare_ml import models

app=FastAPI(title='Healthcare ML service',version='1.0.0')
def authorize(x_service_key: str=Header(default='')):
    expected=os.getenv('ML_SERVICE_KEY','')
    if len(expected)<32 or not secrets.compare_digest(x_service_key,expected):raise HTTPException(401,'Invalid service credentials')

class Training(BaseModel):
    rows:list[dict]=Field(min_length=24,max_length=50000)
    seed:int=42
class Prediction(BaseModel):
    model_version:str
    rows:list[dict]=Field(min_length=1,max_length=5000)

@app.get('/health')
def health():return {'status':'ok'}

@app.post('/train',dependencies=[Depends(authorize)])
def train(body:Training):
    try:return models.train(body.rows,body.seed)
    except (ValueError,KeyError) as exc:raise HTTPException(422,str(exc))

@app.post('/predict',dependencies=[Depends(authorize)])
def predict(body:Prediction):
    try:return models.predict(body.model_version,body.rows)
    except (ValueError,KeyError) as exc:raise HTTPException(422,str(exc))

@app.get('/explain/{version}',dependencies=[Depends(authorize)])
def explain(version:str):
    try:return models.metadata(version)
    except ValueError as exc:raise HTTPException(404,str(exc))

class Optimization(BaseModel):
    candidates:list[dict]=Field(min_length=1,max_length=1000)
    numberOfHospitals:int=Field(ge=1,le=50)
    population:list[float]
    demand:list[float]
    baselineMinutes:list[float]
    candidateMinutes:list[list[float]]
    objectiveWeights:dict[str,float]
    populationSize:int=Field(default=100,ge=10,le=300)
    generations:int=Field(default=150,ge=1,le=500)
    mutationRate:float=Field(default=.05,ge=0,le=1)
    seed:int=42
    threshold:float=30

@app.post('/optimize',dependencies=[Depends(authorize)])
def optimize(body:Optimization):
    from healthcare_ml.optimization import optimize
    try:return optimize(body.model_dump())
    except (ValueError,KeyError) as exc:raise HTTPException(422,str(exc))
