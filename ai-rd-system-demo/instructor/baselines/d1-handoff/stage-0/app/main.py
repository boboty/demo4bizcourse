from pathlib import Path
from fastapi import FastAPI, Header, HTTPException, Query
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
    page: int = Query(1, ge=1),
    page_size: int = Query(5, ge=1, le=100),
    x_user: str = Header("alice"),
):
    try:
        return list_applications(user=x_user, page=page, page_size=page_size)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get("/api/export-jobs/{job_id}")
def get_export_job(job_id: str):
    job = export_queue.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job.as_dict()
