from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from app.rag import ingest, answer

load_dotenv()  # loads .env locally; on ECS the env var comes from Secrets Manager
app = FastAPI()

class Q(BaseModel):
    question: str

@app.on_event("startup")
def _startup():
    ingest()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ask")
def ask(q: Q):
    return {"answer": answer(q.question)}
