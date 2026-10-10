"""Timeout-bounded service calls; mutating operations are never retried blindly."""
import os
import uuid
import httpx

class MLClient:
    def __init__(self, correlation_id=None):
        self.correlation_id = correlation_id or str(uuid.uuid4())
    def call(self,path,payload=None):
        key=os.getenv('ML_SERVICE_KEY','')
        if len(key)<32:raise ValueError('Set ML_SERVICE_KEY (at least 32 characters) for both services')
        with httpx.Client(trust_env=False, base_url=os.getenv('ML_SERVICE_URL','http://localhost:8001'),timeout=httpx.Timeout(90,connect=5),headers={'X-Service-Key':key,'X-Correlation-ID':self.correlation_id}) as client:
            if payload is None:
                for attempt in range(2):
                    try:
                        response=client.get(path)
                        break
                    except httpx.TransportError:
                        if attempt:raise
            else:response=client.post(path,json=payload)
            if response.status_code>=400:raise ValueError('ML service rejected request: '+response.text[:400])
            return response.json()
