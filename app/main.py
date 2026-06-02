from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.rag import ingest, answer, answer_stream

app = FastAPI()


class Q(BaseModel):
    question: str
    session_id: str | None = None  # pass same ID across turns to keep conversation history


@app.on_event("startup")
def _startup():
    ingest()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask")
def ask(q: Q):
    return {"answer": answer(q.question, q.session_id)}


@app.post("/ask/stream")
def ask_stream(q: Q):
    return StreamingResponse(
        answer_stream(q.question, q.session_id),
        media_type="text/event-stream",
    )
