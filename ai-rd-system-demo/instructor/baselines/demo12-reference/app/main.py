from __future__ import annotations

from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Header, HTTPException, Query, Response
from fastapi.responses import FileResponse
from app.common.export_jobs import export_queue
from app.financing.service import list_applications

app = FastAPI(title="AI R&D System Demo", version="0.1.0")
_STATIC = Path(__file__).resolve().parent.parent / "static" / "index.html"

@app.get("/")
def home():
    return FileResponse(_STATIC)

@app.get("/api/financing-applications")
def financing_applications(
    page: int = Query(1, ge=1), page_size: int = Query(5, ge=1, le=100),
    customer_name: Optional[str] = None, status: Optional[str] = None,
    x_user: str = Header("alice"),
):
    try:
        return list_applications(user=x_user, page=page, page_size=page_size, customer_name=customer_name, status=status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.post("/api/financing-applications/export", status_code=202)
def export_financing_applications(customer_name: Optional[str] = None, status: Optional[str] = None, x_user: str = Header("alice")):
    job = export_queue.enqueue("FINANCING_APPLICATION_EXPORT", {
        "user": x_user,
        "customer_name": customer_name,
        "status": status,
        "fields": ["id", "customer_name", "status", "amount"],
    })
    return job.as_dict()

@app.get("/api/export-jobs/{job_id}")
def get_export_job(job_id: str):
    job = export_queue.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job.as_dict()
