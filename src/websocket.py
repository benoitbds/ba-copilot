from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Dict, List, Set, Optional, Any, Union
import json
from datetime import datetime
import asyncio
from sqlalchemy.orm import Session

from src import models
from src import database
from src.models import get_db, AIEventTypeEnum

class ConnectionManager:
    """
    Gestionnaire de connexions WebSocket pour les événements AI en temps réel.
    """
    def __init__(self):
        # Connexions actives par session_id
        self.active_connections: Dict[int, List[WebSocket]] = {}
        # Set de toutes les connexions actives
        self.all_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket, session_id: Optional[int] = None):
        """
        Établit une connexion WebSocket et l'enregistre.
        """
        await websocket.accept()
        self.all_connections.add(websocket)
        
        if session_id is not None:
            if session_id not in self.active_connections:
                self.active_connections[session_id] = []
            self.active_connections[session_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, session_id: Optional[int] = None):
        """
        Ferme une connexion WebSocket et la supprime de la liste des connexions actives.
        """
        self.all_connections.discard(websocket)
        
        if session_id is not None and session_id in self.active_connections:
            self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
    
    async def broadcast_to_session(self, session_id: int, message: Dict[str, Any]):
        """
        Diffuse un message à toutes les connexions d'une session spécifique.
        """
        if session_id in self.active_connections:
            for connection in self.active_connections[session_id]:
                await self.send_message(connection, message)
    
    async def broadcast(self, message: Dict[str, Any]):
        """
        Diffuse un message à toutes les connexions actives.
        """
        for connection in self.all_connections:
            await self.send_message(connection, message)
    
    async def send_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """
        Envoie un message à une connexion WebSocket spécifique.
        """
        try:
            # Convertir les objets datetime en chaînes
            message_str = json.dumps(message, default=str)
            await websocket.send_text(message_str)
        except Exception as e:
            print(f"Erreur lors de l'envoi du message: {e}")

# Singleton pour gérer les connexions WebSocket
connection_manager = ConnectionManager()

async def handle_ai_activity_feed(
    websocket: WebSocket, 
    session_id: Optional[int] = None,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Gère une connexion WebSocket pour le flux d'activité IA.
    Si session_id est fourni, envoie uniquement les événements de cette session.
    Si project_id est fourni, envoie les événements de toutes les sessions du projet.
    """
    try:
        # Accepter la connexion
        await connection_manager.connect(websocket, session_id)
        
        # Envoyer les événements existants si session_id est fourni
        if session_id is not None:
            events = database.get_ai_events(db, session_id)
            for event in events:
                await connection_manager.send_message(websocket, {
                    "type": "event",
                    "data": {
                        "id": event.id,
                        "session_id": event.session_id,
                        "agent_name": event.agent_name,
                        "event_type": event.event_type.value,
                        "content": event.content,
                        "event_data": event.event_data,  # Utilisation du nouveau nom au lieu de metadata
                        "created_at": event.created_at.isoformat()
                    }
                })
        
        # Attendre que le client se déconnecte
        while True:
            data = await websocket.receive_text()
            # On ignore les données reçues, c'est un flux unidirectionnel
            # Mais on garde la connexion ouverte
    except WebSocketDisconnect:
        # Déconnecter le client
        connection_manager.disconnect(websocket, session_id)
    except Exception as e:
        print(f"Erreur WebSocket: {e}")
        connection_manager.disconnect(websocket, session_id)

async def notify_new_ai_event(
    session_id: int,
    agent_name: str,
    event_type: AIEventTypeEnum,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
    db: Session = None
):
    """
    Crée un nouvel événement IA et notifie les clients connectés.
    """
    try:
        # Créer l'événement dans la BD
        if db:
            new_event = database.add_ai_event(
                db,
                session_id,
                agent_name,
                event_type,
                content,
                metadata
            )
            
            if new_event:
                # Construire le message à envoyer
                message = {
                    "type": "event",
                    "data": {
                        "id": new_event.id,
                        "session_id": new_event.session_id,
                        "agent_name": new_event.agent_name,
                        "event_type": new_event.event_type.value,
                        "content": new_event.content,
                        "event_data": new_event.event_data,  # Utilisation du nouveau nom au lieu de metadata
                        "created_at": new_event.created_at.isoformat()
                    }
                }
                
                # Diffuser le message à tous les clients abonnés à cette session
                await connection_manager.broadcast_to_session(session_id, message)
                
                return new_event
        
        return None
    except Exception as e:
        print(f"Erreur lors de la notification d'un nouvel événement: {e}")
        return None

async def notify_session_completed(session_id: int, db: Session = None):
    """
    Marque une session comme terminée et notifie les clients connectés.
    """
    try:
        # Marquer la session comme terminée dans la BD
        if db:
            updated_session = database.complete_ai_activity_session(db, session_id)
            
            if updated_session:
                # Construire le message à envoyer
                message = {
                    "type": "session_completed",
                    "data": {
                        "id": updated_session.id,
                        "title": updated_session.title,
                        "action_type": updated_session.action_type,
                        "status": updated_session.status.value,
                        "completed_at": updated_session.completed_at.isoformat()
                    }
                }
                
                # Diffuser le message à tous les clients abonnés à cette session
                await connection_manager.broadcast_to_session(session_id, message)
                
                return updated_session
        
        return None
    except Exception as e:
        print(f"Erreur lors de la notification de fin de session: {e}")
        return None

class AsyncAIActivitySessionManager:
    """
    Version asynchrone du gestionnaire de session d'activité IA.
    """
    def __init__(
        self, 
        db: Session, 
        title: str, 
        action_type: str, 
        project_id: Optional[int] = None, 
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.db = db
        self.title = title
        self.action_type = action_type
        self.project_id = project_id
        self.session_metadata = metadata  # Renommé pour éviter les confusions
        self.session = None
    
    async def __aenter__(self):
        self.session = database.create_ai_activity_session(
            self.db, 
            self.title, 
            self.action_type, 
            self.project_id, 
            self.session_metadata  # Utilisation du nouveau nom d'attribut
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            # Si une exception s'est produite, ajouter un événement d'erreur
            if exc_type:
                await self.add_event(
                    "System", 
                    AIEventTypeEnum.ERROR, 
                    f"Erreur: {str(exc_val)}",
                    {"error_type": exc_type.__name__}
                )
            
            # Marquer la session comme terminée
            await notify_session_completed(self.session.id, self.db)
    
    async def add_event(
        self, 
        agent_name: str, 
        event_type: Union[AIEventTypeEnum, str], 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Ajoute un événement à la session et notifie les clients en temps réel.
        """
        if not self.session:
            return None
        
        # Convertir le type d'événement en enum si c'est une chaîne
        if isinstance(event_type, str):
            try:
                event_type = AIEventTypeEnum(event_type)
            except ValueError:
                event_type = AIEventTypeEnum.INFO
        
        # Ajouter l'événement et notifier les clients
        return await notify_new_ai_event(
            self.session.id,
            agent_name,
            event_type,
            content,
            metadata,
            self.db
        )
    
    @property
    def session_id(self):
        """
        Retourne l'ID de la session
        """
        return self.session.id if self.session else None