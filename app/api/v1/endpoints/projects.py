from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import Principal, require_roles, resolve_project_scopes
from app.db.models import Project as ProjectModel
from app.db.session import get_db
from app.repositories.project_repository import ProjectRepository
from app.repositories.trace_repository import TraceRepository
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectDetailResponse,
    ProjectResponse,
)

router = APIRouter(prefix="", tags=["projects"])


@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("viewer", "analyst", "admin")),
) -> list[ProjectResponse]:
    repo = ProjectRepository(db)
    trace_repo = TraceRepository()
    projects = repo.list_all()
    result: list[ProjectResponse] = []
    for p in projects:
        stats = await trace_repo.get_project_stats(p.name)
        result.append(
            ProjectResponse(
                id=p.id,
                name=p.name,
                description=p.description,
                created_at=p.created_at,
                total_tokens=stats["total_tokens"],
                total_traces=stats["total_traces"],
                models_used=stats["models"],
            )
        )
    return result


@router.get("/projects/{project_name}", response_model=ProjectDetailResponse)
async def get_project_detail(
    project_name: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("viewer", "analyst", "admin")),
) -> ProjectDetailResponse:
    resolve_project_scopes(principal, project_name)
    repo = ProjectRepository(db)
    project = repo.get_by_name(project_name)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    trace_repo = TraceRepository()
    stats = await trace_repo.get_project_stats(project_name)
    total = stats["total_traces"]
    success_rate = (stats["success_count"] / total * 100) if total > 0 else 0.0

    return ProjectDetailResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        total_tokens=stats["total_tokens"],
        total_cost=stats["total_cost"],
        total_traces=stats["total_traces"],
        success_rate=round(success_rate, 2),
        average_latency_ms=round(stats["avg_latency"], 2),
        models_used=stats["models"],
        first_trace_at=stats["first_trace"],
    )


@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreateRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("admin", "analyst")),
) -> ProjectResponse:
    repo = ProjectRepository(db)
    existing = repo.get_by_name(payload.name)
    if existing:
        raise HTTPException(status_code=409, detail="Project already exists")
    project = ProjectModel(name=payload.name, description=payload.description)
    project = repo.create(project)
    db.commit()
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
    )


@router.delete("/projects/{project_name}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_project(
    project_name: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("admin")),
) -> None:
    repo = ProjectRepository(db)
    trace_repo = TraceRepository()
    if not repo.delete_by_name(project_name):
        raise HTTPException(status_code=404, detail="Project not found")
    await trace_repo.delete_by_project(project_name)
    db.commit()
