import os,re
from fastapi import FastAPI,Header,HTTPException
from pydantic import BaseModel,Field
from engine import record
app=FastAPI(title='RunbookMemory Local Ingestion API',version='0.3.0')
class Event(BaseModel):
    service:str=Field(min_length=1,max_length=120)
    signal:str=Field(min_length=1,max_length=200)
    details:str=Field(min_length=1,max_length=10000)
    source:str=Field(default='external',max_length=80)
    event_type:str=Field(default='alert',max_length=80)
def scrub(value):
    value=re.sub(r'(?i)(password|token|secret|api[_-]?key)\s*[:=]\s*[^\s,;]+',r'\1=[REDACTED]',value)
    value=re.sub(r'(?i)Bearer\s+\S+','Bearer [REDACTED]',value)
    return value
@app.get('/health')
def health():return {'status':'ok','engine':'rule-based prototype'}
@app.post('/api/v1/events',status_code=201)
def ingest(event:Event,x_api_key:str|None=Header(default=None)):
    key=os.environ.get('RBM_API_KEY')
    if not key:raise HTTPException(status_code=503,detail='RBM_API_KEY must be configured')
    import secrets
    if not x_api_key or not secrets.compare_digest(x_api_key,key):raise HTTPException(status_code=401,detail='Invalid API key')
    return record(event.service,event.signal,scrub(event.details),event.source,event.event_type)
