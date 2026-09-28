"""FastAPI surface for DejaOps."""

from __future__ import annotations

from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel, Field

import agent
import memory
import seed

load_dotenv()

app = FastAPI(title="DejaOps", version="0.1.0")


class DiagnoseRequest(BaseModel):
    id: str | None = None
    title: str
    service: str | None = None
    severity: str | None = "SEV-2"
    symptoms: str
    tags: list[str] = Field(default_factory=list)
    persist: bool = False


class RecallRequest(BaseModel):
    query: str
    limit: int = 8


class ReflectRequest(BaseModel):
    query: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "bank_id": memory.bank_id()}


@app.post("/seed")
def seed_memory() -> dict[str, Any]:
    return seed.seed_all()


@app.post("/diagnose")
def diagnose(payload: DiagnoseRequest) -> dict[str, Any]:
    incident = payload.model_dump(exclude={"persist"})
    return agent.diagnose(incident, persist=payload.persist)


@app.post("/recall")
def recall(payload: RecallRequest) -> dict[str, Any]:
    return {"query": payload.query, "results": memory.recall(payload.query, limit=payload.limit)}


@app.post("/reflect")
def reflect(payload: ReflectRequest) -> dict[str, Any]:
    return {"query": payload.query, "answer": memory.reflect(payload.query)}
