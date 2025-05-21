from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum, create_engine, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import enum
import os

# Créer une base SQLite dans le répertoire du projet
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'ba_copilot.db')}"

# Créer l'engine SQLAlchemy
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Créer la base déclarative pour les modèles
Base = declarative_base()

# Enum pour les statuts
class StatusEnum(str, enum.Enum):
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'

# Enum pour les types d'éléments
class ElementTypeEnum(str, enum.Enum):
    EPIC = 'epic'
    FEATURE = 'feature'
    STORY = 'story'
    USECASE = 'usecase'
    REQUIREMENT = 'requirement'
    ROOT = 'root'

# Enum pour les types d'événements IA
class AIEventTypeEnum(str, enum.Enum):
    PROMPT = 'prompt'          # Demande envoyée à l'agent
    RESPONSE = 'response'      # Réponse de l'agent
    THINKING = 'thinking'      # Étape de réflexion intermédiaire
    ERROR = 'error'            # Erreur rencontrée
    INFO = 'info'              # Information générale
    START = 'start'            # Début d'une opération
    COMPLETE = 'complete'      # Fin d'une opération
    WARNING = 'warning'        # Avertissement

class Project(Base):
    """Modèle pour les projets"""
    __tablename__ = 'projects'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relation: Un projet peut avoir plusieurs éléments
    elements = relationship("Element", back_populates="project", cascade="all, delete-orphan")
    
    # Relation: Un projet peut avoir plusieurs diagrammes
    diagrams = relationship("Diagram", back_populates="project", cascade="all, delete-orphan")
    
    # Relation: Un projet peut avoir plusieurs activités d'agents
    agent_activities = relationship("AIActivitySession", back_populates="project", cascade="all, delete-orphan")

class Element(Base):
    """Modèle pour les éléments (Epic, Feature, Story, UseCase, Requirement)"""
    __tablename__ = 'elements'
    
    id = Column(String, primary_key=True)
    custom_id = Column(String, nullable=False, index=True)  # ID utilisateur comme "1.2.3"
    type = Column(Enum(ElementTypeEnum), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(StatusEnum), nullable=False, default=StatusEnum.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Clé étrangère vers le projet parent
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    project = relationship("Project", back_populates="elements")
    
    # Clé étrangère vers l'élément parent (self-relation)
    parent_id = Column(String, ForeignKey('elements.id'), nullable=True)
    children = relationship("Element", 
                            back_populates="parent", 
                            cascade="all, delete-orphan",
                            foreign_keys="Element.parent_id")
    parent = relationship("Element", 
                          back_populates="children", 
                          remote_side=[id],
                          foreign_keys="Element.parent_id")

class Diagram(Base):
    """Modèle pour les diagrammes Mermaid"""
    __tablename__ = 'diagrams'
    
    id = Column(Integer, primary_key=True, index=True)
    objective = Column(Text, nullable=True)
    mermaid_code = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Clé étrangère vers le projet parent
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    project = relationship("Project", back_populates="diagrams")
    
    class Config:
        from_attributes = True

class AIActivitySession(Base):
    """Modèle pour une session d'activité IA (regroupement d'événements liés)"""
    __tablename__ = 'ai_activity_sessions'
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    action_type = Column(String, nullable=False, index=True)  # Type d'action: 'generate', 'mermaid', etc.
    status = Column(Enum(StatusEnum), nullable=False, default=StatusEnum.IN_PROGRESS, index=True)
    session_data = Column(JSON, nullable=True)  # Métadonnées additionnelles au format JSON (renommé de metadata)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Clé étrangère vers le projet parent
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=True)
    project = relationship("Project", back_populates="agent_activities")
    
    # Relation: Une session peut avoir plusieurs événements
    events = relationship("AIEvent", back_populates="session", cascade="all, delete-orphan", order_by="AIEvent.created_at")
    
    def add_event(self, db, agent_name, event_type, content, metadata=None):
        """Helper pour ajouter facilement un événement à cette session"""
        event = AIEvent(
            session_id=self.id,
            agent_name=agent_name,
            event_type=event_type,
            content=content,
            event_data=metadata  # Utilisation du nouveau nom dans le modèle AIEvent
        )
        db.add(event)
        db.commit()
        return event
    
    def complete(self, db):
        """Marquer la session comme terminée"""
        self.status = StatusEnum.COMPLETED
        self.completed_at = datetime.utcnow()
        db.commit()

class AIEvent(Base):
    """Modèle pour un événement d'activité IA individuel"""
    __tablename__ = 'ai_events'
    
    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String, nullable=False, index=True)
    event_type = Column(Enum(AIEventTypeEnum), nullable=False, index=True)
    content = Column(Text, nullable=False)
    event_data = Column(JSON, nullable=True)  # Métadonnées additionnelles au format JSON (renommé de metadata)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Clé étrangère vers la session parent
    session_id = Column(Integer, ForeignKey('ai_activity_sessions.id'), nullable=False)
    session = relationship("AIActivitySession", back_populates="events")

# Fonction pour initialiser la base de données
def init_db():
    Base.metadata.create_all(bind=engine)

# Fonction pour obtenir une session de base de données
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()