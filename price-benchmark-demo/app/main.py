from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from .pricing import anomaly_results, normal_results

BASE = Path(__file__).resolve().parent
app = FastAPI(title="今日采购价格对标", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(BASE / "static" / "index.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


@app.get("/api/normal")
def normal():
    return {"items": normal_results()}


@app.get("/api/anomaly")
def anomaly():
    return anomaly_results()
