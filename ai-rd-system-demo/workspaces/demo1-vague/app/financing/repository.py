import json
from pathlib import Path
from app.common.security import allowed_tenants

_DATA = Path(__file__).with_name("data.json")


def all_applications_for_user(user: str) -> list[dict]:
    records = json.loads(_DATA.read_text(encoding="utf-8"))
    allowed = allowed_tenants(user)
    return [row for row in records if row["tenant"] in allowed]
