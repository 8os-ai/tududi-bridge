"""Unit tests for the tududi bridge — no live tududi required."""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app
from task_templates import default_tasks_for

client = TestClient(app)

# ── Fixtures ──────────────────────────────────────────────────────────────────

HEIDI_OS_CONFIG = {
    "schema_version": "0.1",
    "user": {
        "name": "Heidi",
        "bazi_element": "Metal",
        "archetype": "Strategic Commander",
        "archetype_descriptor": "Precision-driven leader",
    },
    "buckets": [
        {
            "id": "BUILD",
            "label": "Build",
            "description": "Construct strategic systems",
            "archetype_focus": "High-leverage creation",
            "initial_projects": ["Core infrastructure", "Flagship product features"],
        },
        {
            "id": "FIX",
            "label": "Fix",
            "description": "Eliminate friction",
            "archetype_focus": "Root-cause elimination",
            "initial_projects": ["Critical bug triage"],
        },
        {
            "id": "IMPROVE",
            "label": "Improve",
            "description": "Sharpen what works",
            "archetype_focus": "Performance",
            "initial_projects": ["Optimization sprints"],
        },
        {
            "id": "OPERATE",
            "label": "Operate",
            "description": "Run the machine",
            "archetype_focus": "Cadence",
            "initial_projects": ["Weekly reviews"],
        },
        {
            "id": "THINK",
            "label": "Think",
            "description": "Strategic analysis",
            "archetype_focus": "Intel gathering",
            "initial_projects": ["Competitive landscape"],
        },
        {
            "id": "PERSONAL",
            "label": "Personal",
            "description": "Maintain peak readiness",
            "archetype_focus": "Physical discipline",
            "initial_projects": ["Health protocols"],
        },
    ],
    "tone": "battlefield intelligence officer",
    "generated_at": "2026-05-06T00:00:00Z",
}


# ── Health ────────────────────────────────────────────────────────────────────

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── Task templates ────────────────────────────────────────────────────────────

def test_metal_build_tasks():
    tasks = default_tasks_for("Metal", "BUILD")
    assert len(tasks) >= 1
    assert all(isinstance(t, str) for t in tasks)


def test_fallback_tasks():
    tasks = default_tasks_for("UnknownElement", "BUILD")
    assert len(tasks) >= 1


# ── Sync (mocked tududi) ──────────────────────────────────────────────────────

def _make_mock_client():
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)

    area_id_counter = {"n": 1}
    proj_id_counter = {"n": 100}
    task_id_counter = {"n": 1000}

    def fake_find_or_create_area(name):
        i = area_id_counter["n"]
        area_id_counter["n"] += 1
        return {"id": i, "name": name}, True

    def fake_find_or_create_project(name, area_id):
        i = proj_id_counter["n"]
        proj_id_counter["n"] += 1
        return {"id": i, "name": name, "area_id": area_id}, True

    def fake_find_or_create_task(name, project_id):
        i = task_id_counter["n"]
        task_id_counter["n"] += 1
        return {"id": i, "name": name, "project_id": project_id}, True

    mock.find_or_create_area.side_effect = fake_find_or_create_area
    mock.find_or_create_project.side_effect = fake_find_or_create_project
    mock.find_or_create_task.side_effect = fake_find_or_create_task
    return mock


def test_sync_creates_all_areas(monkeypatch):
    monkeypatch.setenv("TUDUDI_EMAIL", "test@example.com")
    monkeypatch.setenv("TUDUDI_PASSWORD", "secret")

    mock_client = _make_mock_client()
    with patch("main.TududiClient", return_value=mock_client):
        resp = client.post("/sync", json=HEIDI_OS_CONFIG)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["areas_created"] == 6
    assert body["projects_created"] == 7  # BUILD has 2, others 1 each
    assert body["tasks_created"] > 0
    assert body["user"] == "Heidi"
    assert body["archetype"] == "Strategic Commander"


def test_sync_idempotent(monkeypatch):
    """Second call: client returns existing=True for everything — counts should be zero."""
    monkeypatch.setenv("TUDUDI_EMAIL", "test@example.com")
    monkeypatch.setenv("TUDUDI_PASSWORD", "secret")

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    mock_client.find_or_create_area.return_value = ({"id": 1, "name": "BUILD"}, False)
    mock_client.find_or_create_project.return_value = ({"id": 10, "name": "proj"}, False)
    mock_client.find_or_create_task.return_value = ({"id": 100, "name": "task"}, False)

    with patch("main.TududiClient", return_value=mock_client):
        resp = client.post("/sync", json=HEIDI_OS_CONFIG)

    assert resp.status_code == 200
    body = resp.json()
    assert body["areas_created"] == 0
    assert body["areas_existed"] == 6
    assert body["projects_created"] == 0
    assert body["tasks_created"] == 0


def test_sync_missing_env_returns_503(monkeypatch):
    monkeypatch.delenv("TUDUDI_EMAIL", raising=False)
    monkeypatch.delenv("TUDUDI_PASSWORD", raising=False)
    resp = client.post("/sync", json=HEIDI_OS_CONFIG)
    assert resp.status_code == 503
