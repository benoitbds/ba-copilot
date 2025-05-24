from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from typing import Optional
from src.models import get_db
from src.websocket import handle_ai_activity_feed
from src.utils import run_agent_async

router = APIRouter(
    tags=["WebSockets"]
)

@router.websocket("/ws/ai-activity")
async def websocket_ai_activity(websocket: WebSocket, db: Session = Depends(get_db)):
    """
    WebSocket pour le flux d'activité IA global
    """
    await handle_ai_activity_feed(websocket, db=db)

@router.websocket("/ws/ai-activity/{session_id}")
async def websocket_ai_activity_session(
    websocket: WebSocket, 
    session_id: int, 
    db: Session = Depends(get_db)
):
    """
    WebSocket pour le flux d'activité d'une session spécifique
    """
    await handle_ai_activity_feed(websocket, session_id=session_id, db=db)

@router.websocket("/ws/ai-activity/project/{project_id}")
async def websocket_ai_activity_project(
    websocket: WebSocket, 
    project_id: int, 
    db: Session = Depends(get_db)
):
    """
    WebSocket pour le flux d'activité d'un projet spécifique
    """
    await handle_ai_activity_feed(websocket, project_id=project_id, db=db)

@router.websocket("/ws/generate_text/{session_id}")
async def websocket_generate_text(
    websocket: WebSocket,
    session_id: int,
    db: Session = Depends(get_db)
):
    """
    WebSocket pour la génération de texte en temps réel
    """
    from src.websocket import AsyncAIActivitySessionManager
    
    await websocket.accept()
    
    try:
        # Récupérer la session et le prompt initial
        session = db.query("AIActivitySession").filter_by(id=session_id).first()
        if not session:
            await websocket.send_json({"error": "Session not found"})
            return
        
        # Récupérer le dernier prompt
        prompt_event = db.query("AIEvent").filter_by(
            session_id=session_id,
            event_type="prompt"
        ).order_by("created_at").first()
        
        if not prompt_event:
            await websocket.send_json({"error": "No prompt found in session"})
            return
        
        # Envoyer un message de démarrage
        await websocket.send_json({
            'event': 'start',
            'data': {'session_id': session_id}
        })
        
        # Récupérer le contexte du projet si un project_id est fourni
        project_context = None
        if session.project_id:
            from src.database import synthesize_project_context
            project_context = synthesize_project_context(db, session.project_id)
        
        # Lancer la génération en temps réel
        async with AsyncAIActivitySessionManager(
            db, 
            f"Génération de texte", 
            "text_generation", 
            session.project_id
        ) as activity_session:
            
            # Enregistrer le contexte utilisé si disponible
            if project_context:
                await activity_session.add_event(
                    "System", 
                    "context", 
                    f"Contexte du projet utilisé: {project_context}"
                )
            
            # Générer la réponse de manière asynchrone
            response_generator = run_agent_async(prompt_event.content, project_context)
            
            async for partial_response in response_generator:
                # Enregistrer la réponse partielle
                await activity_session.add_event(
                    "TextGenerator",
                    "partial_response",
                    partial_response
                )
                
                # Envoyer la réponse partielle au client
                await websocket.send_json({
                    'event': 'update',
                    'data': {'text': partial_response}
                })
                
                # Petite pause pour ne pas surcharger la connexion
                import asyncio
                await asyncio.sleep(0.1)
            
            # Envoyer un message de fin
            await websocket.send_json({
                'event': 'end',
                'data': {'session_id': activity_session.session_id}
            })
            
    except WebSocketDisconnect:
        # Gérer la déconnexion du client
        pass
    except Exception as e:
        # Envoyer un message d'erreur avant de fermer
        try:
            await websocket.send_json({
                'event': 'error',
                'data': {'message': str(e)}
            })
        except:
            pass