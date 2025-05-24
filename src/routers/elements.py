from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from src import schemas
from src import database
from src.models import get_db, ElementTypeEnum, StatusEnum

router = APIRouter(
    prefix="/elements",
    tags=["Elements"]
)

# Route avec préfixe pour les éléments d'un projet
project_router = APIRouter(
    prefix="/projects/{project_id}/elements",
    tags=["Elements"]
)

# Models for API requests and responses
class Element(schemas.Element):
    pass

class ElementCreate(schemas.ElementCreate):
    pass

class ElementUpdate(schemas.ElementUpdate):
    pass

@project_router.get("", response_model=List[Element])
async def get_project_elements(
    project_id: int, 
    element_type: Optional[ElementTypeEnum] = None
):
    """
    Get all elements of a project, optionally filtered by type.
    """
    db = next(get_db())
    try:
        # Vérifier que le projet existe
        db_project = database.get_project(db, project_id)
        if db_project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return database.get_elements_by_project(db, project_id, element_type.value if element_type else None)
    finally:
        db.close()

@project_router.post("", response_model=Element)
async def create_element(project_id: int, element: ElementCreate):
    """
    Create a new element for a project.
    """
    db = next(get_db())
    try:
        # Vérifier que le projet existe
        db_project = database.get_project(db, project_id)
        if db_project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Vérifier que le parent existe si spécifié
        if element.parent_id:
            parent_element = database.get_element(db, element.parent_id)
            if parent_element is None or parent_element.project_id != project_id:
                raise HTTPException(status_code=404, detail="Parent element not found or not part of this project")
        
        return database.create_element(
            db=db,
            project_id=project_id,
            custom_id=element.custom_id,
            element_type=element.type,
            title=element.title,
            description=element.description,
            status=element.status if element.status else StatusEnum.PENDING,
            parent_id=element.parent_id
        )
    finally:
        db.close()

@router.get("/{element_id}", response_model=Element)
async def get_element(element_id: str):
    """
    Get a specific element by ID.
    """
    db = next(get_db())
    try:
        db_element = database.get_element(db, element_id)
        if db_element is None:
            raise HTTPException(status_code=404, detail="Element not found")
        return db_element
    finally:
        db.close()

@router.put("/{element_id}", response_model=Element)
async def update_element(element_id: str, element_update: ElementUpdate):
    """
    Update an element.
    """
    db = next(get_db())
    try:
        # Vérifier que l'élément existe
        db_element = database.get_element(db, element_id)
        if db_element is None:
            raise HTTPException(status_code=404, detail="Element not found")
        
        # Vérifier que le parent existe si spécifié
        if element_update.parent_id:
            parent_element = database.get_element(db, element_update.parent_id)
            if parent_element is None:
                raise HTTPException(status_code=404, detail="Parent element not found")
            
            # Éviter les cycles - ne pas mettre un parent qui serait déjà un descendant
            if parent_element.parent_id == element_id:
                raise HTTPException(status_code=400, detail="Cannot create cyclic parent-child relationship")
        
        updated_element = database.update_element(
            db=db,
            element_id=element_id,
            title=element_update.title,
            description=element_update.description,
            status=element_update.status,
            parent_id=element_update.parent_id
        )
        
        return updated_element
    finally:
        db.close()

@router.delete("/{element_id}")
async def delete_element(element_id: str):
    """
    Delete an element.
    """
    db = next(get_db())
    try:
        # Vérifier si l'élément a des enfants
        children = database.get_element_children(db, element_id)
        if children:
            raise HTTPException(
                status_code=400, 
                detail="Cannot delete an element with children. Please delete or reassign its children first."
            )
        
        success = database.delete_element(db, element_id)
        if not success:
            raise HTTPException(status_code=404, detail="Element not found")
        
        return {"status": "success", "message": f"Element {element_id} deleted"}
    finally:
        db.close()