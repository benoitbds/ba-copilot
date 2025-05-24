from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from src import schemas
from src import database
from src.models import get_db

router = APIRouter(
    prefix="/projects/{project_id}/diagrams",
    tags=["Diagrams"]
)

# Models for API requests and responses
class DiagramBase(schemas.DiagramBase):
    pass

class DiagramCreate(schemas.DiagramCreate):
    pass

class Diagram(schemas.Diagram):
    pass

@router.get("", response_model=List[Diagram])
async def get_project_diagrams(project_id: int, limit: int = 5):
    """
    Get the diagrams of a project.
    """
    db = next(get_db())
    try:
        db_project = database.get_project(db, project_id)
        if db_project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        
        diagrams = database.get_project_diagrams(db, project_id, limit)
        return diagrams
    finally:
        db.close()

@router.post("", response_model=Diagram)
async def create_diagram(project_id: int, diagram: DiagramCreate):
    """
    Create a new diagram for a project.
    """
    db = next(get_db())
    try:
        db_project = database.get_project(db, project_id)
        if db_project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Création du diagramme et traitement des éléments extraits
        try:
            db_diagram, elements = database.process_mermaid_diagram(
                db=db,
                project_id=project_id,
                mermaid_code=diagram.mermaid_code,
                objective=diagram.objective
            )
            return db_diagram
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing diagram: {str(e)}")
    finally:
        db.close()