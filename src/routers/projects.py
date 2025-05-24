from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from src import schemas
from src import database
from src.models import get_db

router = APIRouter(
    prefix="/projects",
    tags=["Projects"]
)

# Models for API requests and responses
class Project(schemas.Project):
    pass

class ProjectCreate(schemas.ProjectCreate):
    pass

class ProjectUpdate(schemas.ProjectUpdate):
    pass

class ProjectStructure(schemas.ProjectStructure):
    pass

@router.get("", response_model=List[Project])
async def get_projects():
    """
    Get a list of all projects.
    """
    db = next(get_db())
    try:
        return database.get_projects(db)
    finally:
        db.close()

@router.post("", response_model=Project, status_code=201)
async def create_project(project: ProjectCreate):
    """
    Create a new project.
    """
    db = next(get_db())
    try:
        return database.create_project(db, name=project.name, description=project.description)
    finally:
        db.close()

@router.get("/{project_id}", response_model=Project)
async def get_project(project_id: int):
    """
    Get a specific project by ID.
    """
    db = next(get_db())
    try:
        db_project = database.get_project(db, project_id)
        if db_project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return db_project
    finally:
        db.close()

@router.put("/{project_id}", response_model=Project)
async def update_project(project_id: int, project_update: ProjectUpdate):
    """
    Update a project.
    """
    db = next(get_db())
    try:
        db_project = database.update_project(
            db, 
            project_id=project_id, 
            name=project_update.name, 
            description=project_update.description
        )
        if db_project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return db_project
    finally:
        db.close()

@router.delete("/{project_id}")
async def delete_project(project_id: int):
    """
    Delete a project.
    """
    db = next(get_db())
    try:
        success = database.delete_project(db, project_id)
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"status": "success", "message": f"Project {project_id} deleted"}
    finally:
        db.close()

@router.get("/{project_id}/structure", response_model=ProjectStructure)
async def get_project_structure(project_id: int):
    """
    Get the complete structure of a project, including all elements organized hierarchically.
    """
    db = next(get_db())
    try:
        structure = database.get_project_structure(db, project_id)
        if structure is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return structure
    finally:
        db.close()