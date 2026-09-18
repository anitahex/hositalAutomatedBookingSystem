"""Regression coverage for FULL_SYSTEM_AUDIT.md P1 #11: GET /appointments/departments,
/doctors, /slots, and /available had no auth dependency, allowing anonymous scraping
of doctor schedules/availability.

Unlike this repo's usual convention (call the route function directly, no TestClient),
verifying "an unauthenticated HTTP request is actually rejected" requires real ASGI
dispatch — Depends() resolution doesn't happen when you call the plain Python function
directly. Scoped to a minimal app (just this router) so no DB/lifespan startup work runs;
the 401 is raised by the current_user dependency before any service function executes.
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.appointments import router as appointments_router

app = FastAPI()
app.include_router(appointments_router)
client = TestClient(app)


def test_departments_requires_auth():
    response = client.get("/departments")
    assert response.status_code == 401


def test_doctors_requires_auth():
    response = client.get("/doctors", params={"department": "Cardiology"})
    assert response.status_code == 401


def test_slots_requires_auth():
    response = client.get("/slots", params={"doctor_id": "doc-1"})
    assert response.status_code == 401


def test_available_requires_auth():
    response = client.get("/available")
    assert response.status_code == 401
