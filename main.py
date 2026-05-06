"""
tududi Bridge — FastAPI service.

Endpoints:
  POST /sync      Read OS config JSON → create Areas/Projects/Tasks in tududi
  GET  /health    Liveness probe
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from task_templates import default_tasks_for
from tududi_client import TududiClient

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="tududi Bridge",
    description="Syncs OS config Areas/Projects/Tasks into a running tududi instance.",
    version="0.1.0",
)

# ── Config from env ─────────────────────────────────────────────────────────

def _tududi_url() -> str:
    return os.environ.get("TUDUDI_URL", "http://tududi:3000")

def _tududi_email() -> str:
    v = os.environ.get("TUDUDI_EMAIL", "")
    if not v:
        raise RuntimeError("TUDUDI_EMAIL env var is required")
    return v

def _tududi_password() -> str:
    v = os.environ.get("TUDUDI_PASSWORD", "")
    if not v:
        raise RuntimeError("TUDUDI_PASSWORD env var is required")
    return v


# ── Pydantic models ──────────────────────────────────────────────────────────

class UserProfile(BaseModel):
    name: str
    bazi_element: str
    archetype: str
    archetype_descriptor: str


class Bucket(BaseModel):
    id: str
    label: str
    description: str
    archetype_focus: str
    initial_projects: list[str] = Field(default_factory=list)


class OSConfig(BaseModel):
    schema_version: str
    user: UserProfile
    buckets: list[Bucket]
    tone: str
    generated_at: datetime


class SyncResult(BaseModel):
    synced_at: datetime
    user: str
    archetype: str
    areas_created: int
    areas_existed: int
    projects_created: int
    projects_existed: int
    tasks_created: int
    tasks_existed: int
    details: list[dict[str, Any]]


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/sync", response_model=SyncResult)
def sync(config: OSConfig) -> SyncResult:
    """
    Idempotently create Areas → Projects → Tasks in tududi from OS config JSON.
    Safe to call multiple times; existing entities are skipped, not duplicated.
    """
    try:
        url = _tududi_url()
        email = _tududi_email()
        password = _tududi_password()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    element = config.user.bazi_element

    areas_created = 0
    areas_existed = 0
    projects_created = 0
    projects_existed = 0
    tasks_created = 0
    tasks_existed = 0
    details: list[dict] = []

    try:
        with TududiClient(url, email, password) as client:
            for bucket in config.buckets:
                # 1. Area
                area_name = bucket.id  # e.g. "BUILD", "THINK", …
                area, area_new = client.find_or_create_area(area_name)
                area_id: int = area["id"]
                if area_new:
                    areas_created += 1
                    logger.info("Created area '%s' (id=%s)", area_name, area_id)
                else:
                    areas_existed += 1
                    logger.info("Area '%s' already exists (id=%s)", area_name, area_id)

                bucket_detail: dict[str, Any] = {
                    "area": area_name,
                    "area_id": area_id,
                    "area_created": area_new,
                    "projects": [],
                }

                # 2. Projects from initial_projects list
                for project_name in bucket.initial_projects:
                    # tududi enforces ≤6 words; truncate long AI-generated names
                    words = project_name.split()
                    if len(words) > 6:
                        project_name = " ".join(words[:6])
                    proj, proj_new = client.find_or_create_project(project_name, area_id)
                    project_id: int = proj["id"]
                    if proj_new:
                        projects_created += 1
                        logger.info("  Created project '%s' (id=%s)", project_name, project_id)
                    else:
                        projects_existed += 1
                        logger.info("  Project '%s' exists (id=%s)", project_name, project_id)

                    project_detail: dict[str, Any] = {
                        "project": project_name,
                        "project_id": project_id,
                        "project_created": proj_new,
                        "tasks": [],
                    }

                    # 3. Tasks — archetype-appropriate defaults for this bucket
                    starter_tasks = default_tasks_for(element, bucket.id)
                    for task_name in starter_tasks:
                        task, task_new = client.find_or_create_task(task_name, project_id)
                        if task_new:
                            tasks_created += 1
                            logger.info("    Created task '%s'", task_name)
                        else:
                            tasks_existed += 1
                        project_detail["tasks"].append({
                            "name": task_name,
                            "created": task_new,
                        })

                    bucket_detail["projects"].append(project_detail)

                details.append(bucket_detail)

    except RuntimeError as exc:
        logger.exception("Sync failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return SyncResult(
        synced_at=datetime.now(tz=timezone.utc),
        user=config.user.name,
        archetype=config.user.archetype,
        areas_created=areas_created,
        areas_existed=areas_existed,
        projects_created=projects_created,
        projects_existed=projects_existed,
        tasks_created=tasks_created,
        tasks_existed=tasks_existed,
        details=details,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
