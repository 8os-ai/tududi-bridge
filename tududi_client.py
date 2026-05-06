"""tududi REST API client with session-based auth and idempotent create helpers."""

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class TududiClient:
    """Session-based client for the chrisvel/tududi Rails API."""

    def __init__(self, base_url: str, email: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.password = password
        self._client: Optional[httpx.Client] = None

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def __enter__(self) -> "TududiClient":
        self._client = httpx.Client(base_url=self.base_url, timeout=30.0, follow_redirects=True)
        self._login()
        return self

    def __exit__(self, *_) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def _login(self) -> None:
        resp = self._client.post(
            "/api/login",
            json={"email": self.email, "password": self.password},
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"tududi login failed: {resp.status_code} {resp.text[:200]}"
            )
        logger.info("Logged in to tududi as %s", self.email)

    def _get(self, path: str) -> list | dict:
        resp = self._client.get(path, headers={"Accept": "application/json"})
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, body: dict) -> dict:
        resp = self._client.post(
            path,
            json=body,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"POST {path} failed: {resp.status_code} {resp.text[:300]}"
            )
        return resp.json()

    # ── Areas ──────────────────────────────────────────────────────────────

    def list_areas(self) -> list[dict]:
        data = self._get("/api/areas")
        return data if isinstance(data, list) else data.get("areas", [])

    def find_or_create_area(self, name: str) -> tuple[dict, bool]:
        """Return (area, created). Created=False if area already existed."""
        for area in self.list_areas():
            if area.get("name", "").strip().lower() == name.strip().lower():
                return area, False
        self._post("/api/areas", {"name": name})
        # Re-fetch list to get full area object including numeric id
        for area in self.list_areas():
            if area.get("name", "").strip().lower() == name.strip().lower():
                return area, True
        raise RuntimeError(f"Area '{name}' not found after creation")

    # ── Projects ───────────────────────────────────────────────────────────

    def list_projects(self, area_id: Optional[int] = None) -> list[dict]:
        path = "/api/projects"
        if area_id is not None:
            path += f"?area_id={area_id}"
        data = self._get(path)
        return data if isinstance(data, list) else data.get("projects", [])

    def find_or_create_project(self, name: str, area_id: int) -> tuple[dict, bool]:
        for proj in self.list_projects(area_id=area_id):
            if proj.get("name", "").strip().lower() == name.strip().lower():
                return proj, False
        proj = self._post(
            "/api/project",
            {"name": name, "area_id": area_id},
        )
        return proj, True

    # ── Tasks ──────────────────────────────────────────────────────────────

    def list_tasks(self, project_id: Optional[int] = None) -> list[dict]:
        path = "/api/tasks"
        if project_id is not None:
            path += f"?project_id={project_id}"
        data = self._get(path)
        return data if isinstance(data, list) else data.get("tasks", [])

    def find_or_create_task(self, name: str, project_id: int) -> tuple[dict, bool]:
        for task in self.list_tasks(project_id=project_id):
            if task.get("name", "").strip().lower() == name.strip().lower():
                return task, False
        task = self._post(
            "/api/task",
            {"name": name, "project_id": project_id},
        )
        return task, True
