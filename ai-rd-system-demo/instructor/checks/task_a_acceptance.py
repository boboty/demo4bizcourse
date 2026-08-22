import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = REPO_ROOT / "workspaces" / "demo2-five-elements"
sys.path.insert(0, str(WORKSPACE))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
problems=[]

def check(name, cond, detail=""):
    print(("PASS" if cond else "BLOCKER"), name, detail)
    if not cond: problems.append(name)

# 1. single customer filter
r=client.get("/api/financing-applications?customer_name=华星", headers={"X-User":"alice"})
check("customer filter endpoint", r.status_code==200)
if r.status_code==200:
    body=r.json(); check("customer filter result", body["total"]==2 and all("华星" in x["customer_name"] for x in body["items"]))

# 2. status filter
r=client.get("/api/financing-applications?status=APPROVED", headers={"X-User":"alice"})
check("status filter endpoint", r.status_code==200)
if r.status_code==200:
    body=r.json(); check("status filter result", body["total"]==2 and all(x["status"]=="APPROVED" for x in body["items"]))

# 3. combination + empty result
r=client.get("/api/financing-applications?customer_name=华星&status=APPROVED", headers={"X-User":"alice"})
check("combined filters", r.status_code==200 and r.json().get("total")==1)
r=client.get("/api/financing-applications?customer_name=不存在", headers={"X-User":"alice"})
check("empty result", r.status_code==200 and r.json().get("total")==0)

# 4. permission cannot be bypassed by filter
r=client.get("/api/financing-applications?customer_name=南湾", headers={"X-User":"alice"})
check("permission preserved", r.status_code==200 and r.json().get("total")==0)

# 5. async export uses existing channel and carries filters
r=client.post("/api/financing-applications/export?customer_name=华星&status=APPROVED", headers={"X-User":"alice"})
check("async export endpoint", r.status_code in (200,202))
if r.status_code in (200,202):
    body=r.json(); job_id=body.get("id") or body.get("job_id")
    check("export returns job id", bool(job_id))
    if job_id:
        j=client.get(f"/api/export-jobs/{job_id}")
        check("job in existing queue", j.status_code==200)
        if j.status_code==200:
            payload=j.json().get("payload",{})
            check("export keeps customer filter", payload.get("customer_name")=="华星")
            check("export keeps status filter", payload.get("status")=="APPROVED")
            check("export keeps user scope", payload.get("user")=="alice")
            check("export fields match list", payload.get("fields")==["id", "customer_name", "status", "amount"])

# 6. frontend has functional controls without binding to implementation names
html=(WORKSPACE / "static/index.html").read_text(encoding="utf-8")
check(
    "frontend customer filter behavior",
    "客户名称" in html
    and "customer_name" in html
    and "/api/financing-applications" in html,
)
check(
    "frontend status filter behavior",
    ("融资状态" in html or "全部状态" in html)
    and "status" in html
    and "APPROVED" in html,
)
check(
    "frontend export behavior",
    "导出" in html
    and "/api/financing-applications/export" in html
    and "POST" in html,
)

if problems:
    print()
    print("OVERALL: BLOCKER", problems)
    raise SystemExit(1)
print()
print("OVERALL: PASS")
