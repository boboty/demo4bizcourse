from __future__ import annotations

from dataclasses import dataclass, asdict
from uuid import uuid4

@dataclass
class ExportJob:
    id: str
    job_type: str
    payload: dict
    status: str = "QUEUED"

    def as_dict(self) -> dict:
        return asdict(self)


class ExportQueue:
    def __init__(self) -> None:
        self._jobs: dict[str, ExportJob] = {}

    def enqueue(self, job_type: str, payload: dict) -> ExportJob:
        job = ExportJob(id=str(uuid4()), job_type=job_type, payload=payload)
        self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> ExportJob | None:
        return self._jobs.get(job_id)


export_queue = ExportQueue()
