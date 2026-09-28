from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request

from app.core.config import get_settings
from app.db.init_db import init_db
from app.db.session import get_db
from app.routers.assemblyai import router as assemblyai_router
from app.routers.auth import auth_router
from app.routers.candidate import (
    candidate_invitation_details,
    candidate_invitation_page,
    candidate_interview_start,
    router as candidate_router,
)
from app.routers.dashboard import router as dashboard_router
from app.routers.recruiter import router as recruiter_router
from app.routers.workflow import router as workflow_router
from app.seed import seed_demo_data

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(",") if settings.cors_origins else ["http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()
seed_demo_data()

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(dashboard_router, prefix="/api", tags=["dashboard"])
app.include_router(assemblyai_router, prefix="/api/assemblyai", tags=["assemblyai"])
app.include_router(candidate_router, prefix="/api", tags=["candidate"])
app.include_router(recruiter_router, prefix="/api", tags=["recruiter"])
app.include_router(workflow_router, prefix="/api", tags=["workflow"])

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/candidate/interview/{token}", response_class=HTMLResponse)
async def candidate_interview_public_page(token: str, request: Request):
    db = next(get_db())
    try:
        return await candidate_invitation_page(token, request, db)
    finally:
        db.close()


@app.get("/candidate/interview/{token}/details")
async def candidate_interview_public_details(token: str, request: Request):
    db = next(get_db())
    try:
        return await candidate_invitation_details(token, request, db)
    finally:
        db.close()


@app.post("/candidate/interview/{token}/start")
async def candidate_interview_public_start(token: str, request: Request):
    import json

    payload = await request.json()
    db = next(get_db())
    try:
        return await candidate_interview_start(token, payload, db)
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    with open("app/templates/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/interview", response_class=HTMLResponse)
async def interview_page(request: Request):
    with open("app/templates/interview.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/jobs", response_class=HTMLResponse)
async def jobs_page(request: Request):
    with open("app/templates/jobs.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.app_name}
