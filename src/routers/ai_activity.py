from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from src import schemas
from src import database
from src.models import get_db, StatusEnum, AIEventTypeEnum

router = APIRouter(
    prefix="/ai-activity",
    tags=["AI Activity"]
)

@router.get("/sessions", response_model=List[schemas.AIActivitySession])
async def get_ai_activity_sessions(
    project_id: Optional[int] = None,
    action_type: Optional[str] = None,
    status: Optional[StatusEnum] = None,
    skip: int = 0,
    limit: int = 100
):
    """
    Get AI activity sessions with optional filters
    """
    db = next(get_db())
    try:
        sessions = database.get_ai_activity_sessions(
            db=db,
            project_id=project_id,
            action_type=action_type,
            status=status,
            skip=skip,
            limit=limit
        )
        return sessions
    finally:
        db.close()

@router.get("/sessions/{session_id}", response_model=schemas.AIActivitySession)
async def get_ai_activity_session(session_id: int):
    """
    Get a specific AI activity session by ID
    """
    db = next(get_db())
    try:
        session = database.get_ai_activity_session(db, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="AI activity session not found")
        return session
    finally:
        db.close()

@router.get("/sessions/{session_id}/events", response_model=List[schemas.AIEvent])
async def get_ai_activity_session_events(
    session_id: int,
    event_type: Optional[AIEventTypeEnum] = None,
    agent_name: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
):
    """
    Get events for a specific AI activity session
    """
    db = next(get_db())
    try:
        # Vérifier que la session existe
        session = database.get_ai_activity_session(db, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="AI activity session not found")
        
        events = database.get_ai_events(
            db=db,
            session_id=session_id,
            event_type=event_type,
            agent_name=agent_name,
            skip=skip,
            limit=limit
        )
        return events
    finally:
        db.close()

@router.post("/sessions/{session_id}/complete", response_model=schemas.AIActivitySession)
async def complete_ai_activity_session(session_id: int):
    """
    Mark an AI activity session as completed
    """
    db = next(get_db())
    try:
        updated_session = database.complete_ai_activity_session(db, session_id)
        if updated_session is None:
            raise HTTPException(status_code=404, detail="AI activity session not found")
        return updated_session
    finally:
        db.close()

@router.post("/sessions", response_model=schemas.AIActivitySession)
async def create_ai_activity_session(session_data: schemas.AIActivitySessionCreate):
    """
    Create a new AI activity session
    """
    db = next(get_db())
    try:
        # Vérifier que le projet existe si un project_id est fourni
        if session_data.project_id is not None:
            project = database.get_project(db, session_data.project_id)
            if project is None:
                raise HTTPException(status_code=404, detail="Project not found")
        
        session = database.create_ai_activity_session(
            db=db,
            title=session_data.title,
            action_type=session_data.action_type,
            project_id=session_data.project_id,
            metadata=session_data.metadata
        )
        return session
    finally:
        db.close()

@router.post("/sessions/{session_id}/events", response_model=schemas.AIEvent)
async def add_ai_event(session_id: int, event_data: schemas.AIEventCreate):
    """
    Add an event to an AI activity session
    """
    db = next(get_db())
    try:
        # Vérifier que la session existe
        session = database.get_ai_activity_session(db, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="AI activity session not found")
        
        event = database.add_ai_event(
            db=db,
            session_id=session_id,
            agent_name=event_data.agent_name,
            event_type=event_data.event_type,
            content=event_data.content,
            metadata=event_data.metadata
        )
        return event
    finally:
        db.close()