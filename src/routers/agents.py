from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect, Body
from typing import List, Dict, Any, Optional, Union, Literal
from sqlalchemy.orm import Session
import json
import asyncio
import uuid as py_uuid

from src import schemas
from src import database
from src.models import get_db
from src.shared_state import conversation_store
from src.utils import clarify_prompt_with_agent, run_agent_async, run_agent
from src.websocket import AsyncAIActivitySessionManager

router = APIRouter(
    tags=["Agents"]
)

# Routes pour les agents
@router.get("/agents", response_model=List[schemas.Agent])
async def get_agents():
    """
    Get a list of all available agents.
    """
    return [
        {"name": "Epic Generator", "description": "Génère des Epics à partir d'une description"},
        {"name": "Feature Generator", "description": "Génère des Features à partir d'Epics"},
        {"name": "Story Generator", "description": "Génère des Stories à partir de Features"},
        {"name": "Requirement Generator", "description": "Génère des Requirements à partir de Stories"},
        {"name": "Diagram Generator", "description": "Génère un diagramme Mermaid à partir d'éléments"},
        {"name": "Conversation Agent", "description": "Agent conversationnel pour clarifier les besoins"}
    ]

@router.put("/agents/{agent_name}", response_model=schemas.Agent)
async def update_agent(agent_name: str, agent: schemas.Agent):
    """
    Update an agent configuration (placeholder for future feature).
    """
    return agent

# Route pour la conversation
@router.post("/conversation/start", response_model=schemas.ConversationResponse, tags=["Agents"])
async def start_conversation(
    data: schemas.ConversationRequest,
    db: Session = Depends(get_db)
):
    """
    Démarre une nouvelle conversation avec l'agent.
    """
    # Générer un ID unique pour cette conversation
    conversation_id = str(py_uuid.uuid4())
    
    # Récupérer le contexte du projet si un project_id est fourni
    project_context = None
    if data.project_id:
        # Vérifier que le projet existe
        project = database.get_project(db, data.project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Synthétiser le contexte du projet
        project_context = database.synthesize_project_context(db, data.project_id)
    
    # Stocker l'état initial de la conversation
    conversation_store[conversation_id] = {
        "messages": [],
        "project_id": data.project_id,
        "project_context": project_context
    }
    
    # Répondre avec l'ID de conversation
    return schemas.ConversationResponse(
        conversation_id=conversation_id,
        message="Conversation initialisée avec succès"
    )

@router.post("/conversation/{conversation_id}/message", response_model=schemas.AIMessage, tags=["Agents"])
async def send_message(
    conversation_id: str,
    data: schemas.UserMessage,
    db: Session = Depends(get_db)
):
    """
    Envoie un message à l'agent conversationnel et récupère sa réponse.
    """
    # Vérifier que la conversation existe
    if conversation_id not in conversation_store:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Récupérer le contexte de la conversation
    conversation = conversation_store[conversation_id]
    
    # Ajouter le message de l'utilisateur à l'historique
    conversation["messages"].append({
        "role": "user",
        "content": data.message
    })
    
    # Créer une session d'activité AI pour cette interaction
    async with AsyncAIActivitySessionManager(
        db,
        title="Conversation avec l'agent",
        action_type="conversation",
        project_id=conversation.get("project_id")
    ) as session:
        # Ajouter le message utilisateur comme événement
        await session.add_event(
            "User",
            "message",
            data.message
        )
        
        # Intégrer le contexte du projet dans le prompt
        project_context = conversation.get("project_context", "")
        messages_history = conversation["messages"]
        
        # Appel à l'agent
        try:
            # Journaliser le début de l'appel
            await session.add_event(
                "ConversationAgent",
                "start",
                "Début du traitement du message par l'agent"
            )
            
            # Appeler l'agent avec le message et l'historique
            response = await clarify_prompt_with_agent(
                message=data.message,
                project_context=project_context,
                conversation_history=messages_history
            )
            
            # Journaliser la réponse
            await session.add_event(
                "ConversationAgent",
                "response",
                response
            )
            
            # Ajouter la réponse de l'agent à l'historique
            conversation["messages"].append({
                "role": "assistant",
                "content": response
            })
            
            # Retourner la réponse
            return schemas.AIMessage(
                message=response,
                conversation_id=conversation_id
            )
            
        except Exception as e:
            # En cas d'erreur, journaliser et retourner un message d'erreur
            error_message = f"Erreur lors du traitement du message: {str(e)}"
            await session.add_event(
                "ConversationAgent",
                "error",
                error_message
            )
            raise HTTPException(status_code=500, detail=error_message)

# Endpoints de génération spécialisés
@router.post("/generate/hierarchy", response_model=schemas.HierarchyResponse, tags=["Agents"])
async def generate_hierarchy(request: schemas.HierarchyRequest):
    """
    Génère une hiérarchie de backlog basée sur un prompt.
    """
    try:
        agent_prompt = (
        f"Génère une hiérarchie de backlog Agile à partir du besoin suivant : {request.prompt}\n\n"
        "Réponds uniquement avec un objet JSON contenant la hiérarchie des éléments de backlog:\n"
        "- Epics: Liste d'objets Epic, chacun avec un title, description, et features\n"
        "- Features: Pour chaque Epic, liste d'objets Feature, chacun avec un title, description, et stories\n"
        "- Stories: Pour chaque Feature, liste d'objets Story, chacun avec un title et description\n\n"
        "Format attendu:\n"
        "{\n"
        '  "epics": [\n'
        "    {\n"
        '      "title": "Titre de l\'Epic 1",\n'
        '      "description": "Description de l\'Epic 1",\n'
        '      "features": [\n'
        "        {\n"
        '          "title": "Titre de la Feature 1.1",\n'
        '          "description": "Description de la Feature 1.1",\n'
        '          "stories": [\n'
        "            {\n"
        '              "title": "Titre de la Story 1.1.1",\n'
        '              "description": "Description de la Story 1.1.1"\n'
        "            }\n"
        "          ]\n"
        "        }\n"
        "      ]\n"
        "    }\n"
        "  ]\n"
        "}"
    )
        
        # Utiliser l'agent pour générer la hiérarchie
        response = run_agent(agent_prompt)
        
        # Essayer de trouver et parser le JSON dans la réponse
        try:
            # Chercher du contenu JSON dans la réponse
            import re
            json_match = re.search(r'({[\s\S]*})', response)
            if json_match:
                json_content = json_match.group(1)
                hierarchy = json.loads(json_content)
                
                # Créer les objets Epic, Feature, Story
                epics = []
                for epic_data in hierarchy.get('epics', []):
                    features = []
                    for feature_data in epic_data.get('features', []):
                        stories = []
                        for story_data in feature_data.get('stories', []):
                            stories.append(schemas.Story(
                                title=story_data.get('title', ''),
                                description=story_data.get('description', '')
                            ))
                        
                        features.append(schemas.Feature(
                            title=feature_data.get('title', ''),
                            description=feature_data.get('description', ''),
                            stories=stories
                        ))
                    
                    epics.append(schemas.Epic(
                        title=epic_data.get('title', ''),
                        description=epic_data.get('description', ''),
                        features=features
                    ))
                
                return schemas.HierarchyResponse(epics=epics)
            else:
                raise HTTPException(status_code=500, detail="Failed to parse JSON in agent response")
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Failed to parse JSON in agent response")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating hierarchy: {str(e)}")

# Endpoint pour la génération de texte - Cette fois avec un POST normal
@router.post("/agents/generate_text_conversation", tags=["Agents"])
async def generate_text_conversation(
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    """
    Endpoint pour initier une génération de texte. 
    Retourne des données qui permettront au client de se connecter au WebSocket.
    """
    prompt = data.get('prompt', '')
    project_id = data.get('project_id')
    
    # Créer une session d'activité IA
    session = database.create_ai_activity_session(
        db, 
        title="Génération de texte", 
        action_type="text_generation", 
        project_id=project_id
    )
    
    # Ajouter le prompt initial comme événement
    database.add_ai_event(
        db,
        session.id,
        "User",
        "prompt",
        prompt
    )
    
    # Retourner les informations pour se connecter au WebSocket
    return {
        "status": "processing",
        "message": "Traitement en cours. Veuillez vous connecter au WebSocket pour les mises à jour en temps réel.",
        "activity_session_id": session.id,
        "websocket_url": f"/ws/ai-activity/{session.id}"
    }