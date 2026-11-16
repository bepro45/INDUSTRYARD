import json, sqlite3
from pathlib import Path
from uuid import uuid4
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from .config import get_settings

s = get_settings()
DB = Path(s.database_path)
DATA = Path(__file__).resolve().parents[2] / "sample_data" / "incidents.json"

def db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
    c.execute("CREATE TABLE IF NOT EXISTS incidents (incident_id TEXT PRIMARY KEY,machine_id TEXT,occurred_at TEXT,incident_type TEXT,symptom TEXT,operating_duration_minutes INTEGER,operating_condition TEXT,temperature_celsius REAL,action_taken TEXT,outcome TEXT,status TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS outcomes (id INTEGER PRIMARY KEY,incident_id TEXT,feedback TEXT,details TEXT)")
    return c

class Incident(BaseModel):
    incident_id: Optional[str]=None
    machine_id: str
    occurred_at: str
    incident_type: str="Near Miss"
    symptom: str=Field(min_length=3)
    operating_duration_minutes: Optional[int]=None
    operating_condition: Optional[str]=None
    temperature_celsius: Optional[float]=None
    action_taken: Optional[str]=None
    outcome: Optional[str]=None
    status: str="Open"
class Investigation(BaseModel):
    machine_id: str
    symptom: str
    operating_condition: Optional[str]=None
    operating_duration_minutes: Optional[int]=None
    temperature_celsius: Optional[float]=None
    use_memory: bool=True
class Outcome(BaseModel):
    incident_id: str
    feedback: str
    details: str

class Memory:
    def __init__(self):
        self.client=None
        if s.hindsight_api_key:
            try:
                from hindsight_client import Hindsight
                self.client=Hindsight(base_url=s.hindsight_base_url,api_key=s.hindsight_api_key)
            except Exception as e: print("Hindsight init:",e)
    def bank(self):
        if not self.client: return
        try: self.client.create_bank(bank_id=s.hindsight_bank_id,name="NearMiss AI Experience Memory",background="Synthetic incident experiences; recall is advisory evidence.")
        except Exception as e:
            if not any(k in str(e).lower() for k in ["exists","already","409"]): print("Hindsight bank:",e)
    def retain(self,text,meta):
        if not self.client: return {"stored":False,"reason":"Hindsight not configured"}
        try:
            self.client.retain(bank_id=s.hindsight_bank_id,content=text,context="NearMiss AI experience",metadata=meta)
            return {"stored":True}
        except Exception as e: return {"stored":False,"reason":str(e)}
    def recall(self,q):
        if not self.client: return {"available":False,"memories":[],"reason":"Hindsight not configured"}
        try:
            r=self.client.recall(bank_id=s.hindsight_bank_id,query=q,budget="mid")
            return {"available":True,"memories":[{"type":getattr(x,"type","memory"),"text":getattr(x,"text",str(x))} for x in (r.results or [])]}
        except Exception as e: return {"available":False,"memories":[],"reason":str(e)}
    def incident(self,d):
        text=(f"Incident {d['incident_id']} machine {d['machine_id']} date {d['occurred_at']}; "
              f"symptom {d['symptom']}; duration {d.get('operating_duration_minutes')}; "
              f"condition {d.get('operating_condition')}; temperature C {d.get('temperature_celsius')}; "
              f"action {d.get('action_taken')}; outcome {d.get('outcome')}; status {d.get('status')}. "
              "Reported observation, not established root cause.")
        return self.retain(text,{"incident_id":d["incident_id"],"machine_id":d["machine_id"]})
memory=Memory()

def llm(current, memories):
    if not s.groq_api_key:
        return "Groq is not configured. Review the report and retrieved evidence with qualified personnel. Follow site procedures. This prototype cannot diagnose equipment or authorize restart.", "fallback"
    try:
        from groq import Groq
        c=Groq(api_key=s.groq_api_key)
        system=("Assist qualified safety personnel to organize evidence. You are not a diagnostic system or safety authority. "
                "Separate observations from hypotheses; never invent facts or thresholds; never authorize restart. "
                "Explain uncertainty and recommend site procedures and qualified review.")
        prompt=f"Current report: {current}\nRetrieved memories: {memories}\nProvide observations, relevant evidence, uncertainty, and safe review steps. Do not diagnose."
        r=c.chat.completions.create(model=s.groq_model,temperature=0.2,messages=[{"role":"system","content":system},{"role":"user","content":prompt}])
        return r.choices[0].message.content,s.groq_model
    except Exception as e: return f"LLM unavailable: {e}. Review evidence manually.", "fallback"

@asynccontextmanager
async def lifespan(app):
    c=db(); c.close()
    if memory.client: memory.bank()
    yield
app=FastAPI(title="NearMiss AI API",version="0.1.0",lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=s.origins,allow_methods=["*"],allow_headers=["*"])

@app.get("/")
def home(): return {"name":"NearMiss AI","docs":"/docs","safety":"Prototype only"}
@app.get("/health")
def health(): return {"status":"ok","hindsight_configured":bool(memory.client)}
@app.get("/incidents")
def incidents():
    c=db(); rows=[dict(x) for x in c.execute("SELECT * FROM incidents ORDER BY occurred_at DESC")]; c.close(); return rows
@app.get("/machines/{machine_id}")
def machine(machine_id:str):
    c=db(); rows=[dict(x) for x in c.execute("SELECT * FROM incidents WHERE machine_id=? ORDER BY occurred_at",(machine_id,))]; c.close(); return rows
def save(d):
    c=db()
    try:
        c.execute("INSERT INTO incidents VALUES (?,?,?,?,?,?,?,?,?,?,?)",tuple(d.get(k) for k in ["incident_id","machine_id","occurred_at","incident_type","symptom","operating_duration_minutes","operating_condition","temperature_celsius","action_taken","outcome","status"]))
        c.commit()
    finally: c.close()
@app.post("/incidents")
def create(p:Incident):
    d=p.model_dump(); d["incident_id"]=d["incident_id"] or "INC-"+uuid4().hex[:8].upper()
    try: save(d)
    except Exception as e: raise HTTPException(409,str(e))
    return {"incident":d,"memory":memory.incident(d)}
@app.post("/investigate")
def investigate(p:Investigation):
    d=p.model_dump()
    q=f"Previous near-miss incidents for machine {p.machine_id}; symptom {p.symptom}; condition {p.operating_condition}; duration {p.operating_duration_minutes}; interventions and outcomes."
    recalled=memory.recall(q) if p.use_memory else {"available":False,"memories":[],"reason":"Memory disabled"}
    answer,model=llm(d,recalled["memories"])
    return {"analysis":answer,"model":model,"memory_enabled":p.use_memory,"hindsight_available":recalled["available"],"memory_status":recalled.get("reason","Recall completed"),"memories":recalled["memories"],"notice":"Advisory prototype only. Follow site procedures and qualified personnel instructions."}
@app.post("/outcomes")
def outcome(p:Outcome):
    c=db(); row=c.execute("SELECT * FROM incidents WHERE incident_id=?",(p.incident_id,)).fetchone()
    if not row: c.close(); raise HTTPException(404,"Incident not found")
    d=dict(row); c.execute("INSERT INTO outcomes (incident_id,feedback,details) VALUES (?,?,?)",(p.incident_id,p.feedback,p.details)); c.commit(); c.close()
    text=f"Follow-up for {p.incident_id} machine {d['machine_id']}. Feedback {p.feedback}. Details {p.details}. User-reported; verify."
    return {"saved":True,"memory":memory.retain(text,{"incident_id":p.incident_id,"machine_id":d["machine_id"]})}
@app.post("/demo/seed")
def seed():
    items=json.loads(DATA.read_text()); inserted=retained=0
    for d in items:
        c=db(); exists=c.execute("SELECT 1 FROM incidents WHERE incident_id=?",(d["incident_id"],)).fetchone(); c.close()
        if exists: continue
        save(d); inserted+=1
        if memory.incident(d).get("stored"): retained+=1
    return {"inserted":inserted,"retained_in_hindsight":retained,"dataset":"synthetic"}
