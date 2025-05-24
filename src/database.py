from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
import uuid
import json

# Import models and get_db function from src.models
from src.models import get_db, ElementTypeEnum, StatusEnum, AIEventTypeEnum, Project, Element, Diagram, AIActivitySession, AIEvent

# Fonction helper pour générer un ID unique
def generate_element_id():
    return str(uuid.uuid4())

# Opérations CRUD pour les projets
def get_projects(db: Session):
    return db.query(Project).all()

def get_project(db: Session, project_id: int):
    return db.query(Project).filter(Project.id == project_id).first()

def create_project(db: Session, name: str, description: Optional[str] = None):
    db_project = Project(name=name, description=description)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

def update_project(db: Session, project_id: int, name: str, description: Optional[str] = None):
    db_project = get_project(db, project_id)
    if db_project:
        db_project.name = name
        if description is not None:
            db_project.description = description
        db_project.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_project)
    return db_project

def delete_project(db: Session, project_id: int):
    db_project = get_project(db, project_id)
    if db_project:
        db.delete(db_project)
        db.commit()
        return True
    return False

# Opérations CRUD pour les éléments
def get_element(db: Session, element_id: str):
    return db.query(Element).filter(Element.id == element_id).first()

def get_elements_by_project(db: Session, project_id: int, element_type: Optional[str] = None):
    query = db.query(Element).filter(Element.project_id == project_id)
    if element_type:
        query = query.filter(Element.type == element_type)
    return query.all()

def get_root_elements(db: Session, project_id: int):
    return db.query(Element).filter(
        Element.project_id == project_id,
        Element.parent_id == None
    ).all()

def get_element_children(db: Session, element_id: str):
    return db.query(Element).filter(Element.parent_id == element_id).all()

def create_element(
    db: Session, 
    project_id: int, 
    custom_id: str,
    element_type: ElementTypeEnum,
    title: str,
    description: Optional[str] = None,
    status: StatusEnum = StatusEnum.PENDING,
    parent_id: Optional[str] = None
):
    element_id = generate_element_id()
    db_element = Element(
        id=element_id,
        custom_id=custom_id,
        type=element_type,
        title=title,
        description=description,
        status=status,
        project_id=project_id,
        parent_id=parent_id
    )
    db.add(db_element)
    db.commit()
    db.refresh(db_element)
    return db_element

def update_element(
    db: Session,
    element_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[StatusEnum] = None,
    parent_id: Optional[str] = None
):
    db_element = get_element(db, element_id)
    if db_element:
        if title is not None:
            db_element.title = title
        if description is not None:
            db_element.description = description
        if status is not None:
            db_element.status = status
        if parent_id is not None:
            db_element.parent_id = parent_id
        db_element.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_element)
    return db_element

def delete_element(db: Session, element_id: str):
    db_element = get_element(db, element_id)
    if db_element:
        db.delete(db_element)
        db.commit()
        return True
    return False

# Opérations pour les diagrammes Mermaid
def create_diagram(db: Session, project_id: int, mermaid_code: str, objective: Optional[str] = None):
    db_diagram = Diagram(
        project_id=project_id,
        mermaid_code=mermaid_code,
        objective=objective
    )
    db.add(db_diagram)
    db.commit()
    db.refresh(db_diagram)
    return db_diagram

def get_latest_diagram(db: Session, project_id: int):
    return db.query(Diagram).filter(
        Diagram.project_id == project_id
    ).order_by(Diagram.created_at.desc()).first()

def get_project_diagrams(db: Session, project_id: int, limit: int = 5):
    return db.query(Diagram).filter(
        Diagram.project_id == project_id
    ).order_by(Diagram.created_at.desc()).limit(limit).all()

# Fonction pour construire la structure complète d'un projet
def get_project_structure(db: Session, project_id: int):
    # Récupérer le projet
    project = get_project(db, project_id)
    if not project:
        return None
    
    # Récupérer tous les éléments du projet
    elements = get_elements_by_project(db, project_id)
    
    # Organiser les éléments en une structure hiérarchique
    element_dict = {element.id: {
        "id": element.id,
        "custom_id": element.custom_id,
        "type": element.type.value,
        "title": element.title,
        "description": element.description,
        "status": element.status.value,
        "created_at": element.created_at.isoformat(),
        "updated_at": element.updated_at.isoformat(),
        "children": []
    } for element in elements}
    
    # Construire la hiérarchie
    structure = []
    for element in elements:
        if element.parent_id is None:
            # C'est un élément racine
            structure.append(element_dict[element.id])
        else:
            # Ajouter aux enfants du parent
            if element.parent_id in element_dict:
                element_dict[element.parent_id]["children"].append(element_dict[element.id])
    
    result = {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
        "elements": structure
    }
    
    # Ajouter le dernier diagramme si disponible
    latest_diagram = get_latest_diagram(db, project_id)
    if latest_diagram:
        result["latest_diagram"] = {
            "id": latest_diagram.id,
            "objective": latest_diagram.objective,
            "mermaid_code": latest_diagram.mermaid_code,
            "created_at": latest_diagram.created_at.isoformat()
        }
    
    return result

# Fonction pour extraire les éléments depuis un diagramme Mermaid et les ajouter à la BD
def process_mermaid_diagram(db: Session, project_id: int, mermaid_code: str, objective: Optional[str] = None):
    # Créer le diagramme dans la BD
    db_diagram = create_diagram(db, project_id, mermaid_code, objective)
    
    # Parser le diagramme pour extraire les éléments
    elements = parse_mermaid_diagram(mermaid_code)
    
    # Ajouter chaque élément à la BD
    created_elements = []
    for element in elements:
        # Vérifier si l'élément existe déjà (par custom_id)
        existing_element = db.query(Element).filter(
            Element.project_id == project_id,
            Element.custom_id == element["custom_id"]
        ).first()
        
        if existing_element:
            # Mettre à jour l'élément existant
            updated_element = update_element(
                db,
                existing_element.id,
                title=element["title"],
                parent_id=element["parent_id"]
            )
            created_elements.append(updated_element)
        else:
            # Créer un nouvel élément
            new_element = create_element(
                db,
                project_id=project_id,
                custom_id=element["custom_id"],
                element_type=element["type"],
                title=element["title"],
                parent_id=element["parent_id"]
            )
            created_elements.append(new_element)
    
    return db_diagram, created_elements

# Fonction pour parser un diagramme Mermaid et extraire les éléments
def parse_mermaid_diagram(mermaid_code: str):
    """
    Parse un diagramme Mermaid (mindmap) et extrait tous les éléments.
    Retourne une liste de dictionnaires représentant chaque élément.
    """
    elements = []
    parent_stack = [{"id": None, "level": -1}]
    
    # Nettoyer le code Mermaid
    lines = mermaid_code.strip().split("\n")
    if lines and lines[0].strip() == "mindmap":
        lines = lines[1:]  # Enlever la première ligne si c'est "mindmap"
    
    for line in lines:
        line = line.rstrip()
        if not line.strip():
            continue
        
        # Déterminer le niveau d'indentation
        indent = len(line) - len(line.lstrip())
        level = indent // 2  # Approximation de l'indentation
        
        # Nettoyer la ligne et extraire les informations
        cleaned_line = line.strip()
        
        # Extraction du custom_id et du type
        custom_id = "unknown"
        element_type = "epic"  # Par défaut
        title = cleaned_line
        
        # Patterns pour les différents types d'éléments
        patterns = {
            "root": r"root\(\((.*?)\)\)",
            "epic": r"Epic\s+(\d+)(?:\.\d+)*\s*\((.*?)\)",
            "feature": r"Feature\s+(\d+\.\d+)(?:\.\d+)*\s*\((.*?)\)",
            "story": r"Story\s+(\d+\.\d+\.\d+)(?:\.\d+)*\s*\((.*?)\)",
            "usecase": r"(?:UC|Use Case)\s+(\d+\.\d+\.\d+\.\d+)(?:\.\d+)*\s*\((.*?)\)",
            "requirement": r"(?:Req|Requirement)\s+(\d+\.\d+\.\d+\.\d+\.\d+)(?:\.\d+)*\s*\((.*?)\)"
        }
        
        import re
        for elem_type, pattern in patterns.items():
            match = re.search(pattern, cleaned_line)
            if match:
                if elem_type == "root":
                    custom_id = "root"
                    title = match.group(1)
                else:
                    custom_id = match.group(1)
                    title = match.group(2)
                element_type = elem_type
                break
        
        # Si le custom_id n'a pas été identifié, essayer un pattern générique pour les IDs
        if custom_id == "unknown":
            id_match = re.search(r"(\d+(?:\.\d+)*)(?:\s*\(|\s+)", cleaned_line)
            if id_match:
                custom_id = id_match.group(1)
                # Déduire le type en fonction du nombre de segments dans l'ID
                segments = custom_id.count(".")
                if segments == 0:
                    element_type = "epic"
                elif segments == 1:
                    element_type = "feature"
                elif segments == 2:
                    element_type = "story"
                elif segments == 3:
                    element_type = "usecase"
                elif segments >= 4:
                    element_type = "requirement"
        
        # Nettoyage final du titre si nécessaire
        title_match = re.search(r"\((.*?)\)$", title)
        if title_match:
            title = title_match.group(1)
        
        # Déterminer le parent en fonction de l'indentation
        while parent_stack[-1]["level"] >= level:
            parent_stack.pop()
        
        parent_id = parent_stack[-1]["id"]
        
        # Ajouter l'élément à la liste
        element = {
            "custom_id": custom_id,
            "type": element_type,
            "title": title.strip(),
            "parent_id": parent_id
        }
        
        elements.append(element)
        
        # Ajouter cet élément à la pile des parents potentiels
        parent_stack.append({"id": custom_id, "level": level})
    
    return elements

# ------------------ Fonctions pour les Activités IA ------------------

def create_ai_activity_session(
    db: Session, 
    title: str, 
    action_type: str, 
    project_id: Optional[int] = None, 
    metadata: Optional[Dict[str, Any]] = None
) -> AIActivitySession:
    """
    Crée une nouvelle session d'activité IA
    """
    db_session = AIActivitySession(
        title=title,
        action_type=action_type,
        project_id=project_id,
        session_data=metadata,  # Utilisation du nouveau nom session_data au lieu de metadata
        status=StatusEnum.IN_PROGRESS
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

def get_ai_activity_session(db: Session, session_id: int) -> Optional[AIActivitySession]:
    """
    Récupère une session d'activité IA par son ID avec ses événements
    """
    # Utiliser joinedload pour charger les événements en une seule requête
    from sqlalchemy.orm import joinedload
    return db.query(AIActivitySession).options(
        joinedload(AIActivitySession.events)
    ).filter(AIActivitySession.id == session_id).first()

def get_ai_activity_sessions(
    db: Session, 
    project_id: Optional[int] = None, 
    action_type: Optional[str] = None,
    status: Optional[StatusEnum] = None,
    skip: int = 0, 
    limit: int = 100
) -> List[AIActivitySession]:
    """
    Récupère les sessions d'activité IA, avec filtres optionnels
    """
    from sqlalchemy.orm import joinedload
    query = db.query(AIActivitySession).options(
        joinedload(AIActivitySession.events)
    )
    
    if project_id is not None:
        query = query.filter(AIActivitySession.project_id == project_id)
    
    if action_type is not None:
        query = query.filter(AIActivitySession.action_type == action_type)
    
    if status is not None:
        query = query.filter(AIActivitySession.status == status)
    
    return query.order_by(AIActivitySession.created_at.desc()).offset(skip).limit(limit).all()

def complete_ai_activity_session(db: Session, session_id: int) -> Optional[AIActivitySession]:
    """
    Marque une session d'activité IA comme terminée
    """
    db_session = get_ai_activity_session(db, session_id)
    if db_session:
        db_session.status = StatusEnum.COMPLETED
        db_session.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(db_session)
    return db_session

def add_ai_event(
    db: Session,
    session_id: int,
    agent_name: str,
    event_type: AIEventTypeEnum,
    content: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Optional[AIEvent]:
    """
    Ajoute un événement à une session d'activité IA
    """
    # Vérifier que la session existe
    db_session = get_ai_activity_session(db, session_id)
    if not db_session:
        return None
    
    # Créer l'événement
    db_event = AIEvent(
        session_id=session_id,
        agent_name=agent_name,
        event_type=event_type,
        content=content,
        event_data=metadata  # Utilisation du nouveau nom event_data au lieu de metadata
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

def get_ai_events(
    db: Session,
    session_id: int,
    event_type: Optional[AIEventTypeEnum] = None,
    agent_name: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[AIEvent]:
    """
    Récupère les événements d'une session d'activité IA
    """
    query = db.query(AIEvent).filter(AIEvent.session_id == session_id)
    
    if event_type is not None:
        query = query.filter(AIEvent.event_type == event_type)
    
    if agent_name is not None:
        query = query.filter(AIEvent.agent_name == agent_name)
    
    return query.order_by(AIEvent.created_at.asc()).offset(skip).limit(limit).all()

# Classe pour gérer les sessions d'activité IA avec un context manager
class AIActivitySessionManager:
    """
    Gestionnaire de session d'activité IA avec support du context manager
    Exemple d'utilisation:
    
    with AIActivitySessionManager(db, "Génération de spécifications", "generate", project_id=1) as session:
        session.add_event("GenerateAgent", "start", "Début de la génération")
        # ... code ...
        session.add_event("GenerateAgent", "prompt", "Prompt envoyé à l'agent")
        # ... code ...
        session.add_event("GenerateAgent", "response", "Réponse de l'agent")
    # La session est automatiquement marquée comme terminée à la sortie du bloc
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
    
    def __enter__(self):
        self.session = create_ai_activity_session(
            self.db, 
            self.title, 
            self.action_type, 
            self.project_id, 
            self.session_metadata  # Utilisation du nouveau nom d'attribut
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            # Si une exception s'est produite, ajouter un événement d'erreur
            if exc_type:
                self.add_event(
                    "System", 
                    AIEventTypeEnum.ERROR, 
                    f"Erreur: {str(exc_val)}",
                    {"error_type": exc_type.__name__}
                )
            
            # Marquer la session comme terminée
            complete_ai_activity_session(self.db, self.session.id)
    
    def add_event(
        self, 
        agent_name: str, 
        event_type: Union[AIEventTypeEnum, str], 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Ajoute un événement à la session
        """
        if not self.session:
            return None
        
        # Convertir le type d'événement en enum si c'est une chaîne
        if isinstance(event_type, str):
            try:
                event_type = AIEventTypeEnum(event_type)
            except ValueError:
                event_type = AIEventTypeEnum.INFO
        
        return add_ai_event(
            self.db,
            self.session.id,
            agent_name,
            event_type,
            content,
            metadata
        )
    
    @property
    def session_id(self):
        """
        Retourne l'ID de la session
        """
        return self.session.id if self.session else None

# Fonction pour synthétiser le contexte d'un projet pour les agents IA
def synthesize_project_context(db: Session, project_id: int) -> str:
    """
    Synthétise le contexte du projet en un format concis pour le prompt.
    """
    project = get_project(db, project_id)
    if not project:
        return "Projet non trouvé."
    
    # Récupérer les éléments du projet
    elements = get_elements_by_project(db, project_id)
    
    # Construire le contexte
    context = f"Projet: {project.name}\n"
    
    if project.description:
        context += f"Description: {project.description}\n\n"
    else:
        context += "\n"
    
    # Organiser les éléments par type
    epics = [e for e in elements if e.type == ElementTypeEnum.EPIC]
    features = [e for e in elements if e.type == ElementTypeEnum.FEATURE]
    stories = [e for e in elements if e.type == ElementTypeEnum.STORY]
    usecases = [e for e in elements if e.type == ElementTypeEnum.USECASE]
    requirements = [e for e in elements if e.type == ElementTypeEnum.REQUIREMENT]
    
    # Ajouter les epics
    if epics:
        context += "Epics:\n"
        for epic in epics:
            context += f"- {epic.custom_id}: {epic.title}\n"
        context += "\n"
    
    # Ajouter les features
    if features:
        context += "Features:\n"
        for feature in features:
            context += f"- {feature.custom_id}: {feature.title}\n"
        context += "\n"
    
    # Limiter les détails pour les autres types d'éléments
    if stories:
        context += f"Stories: {len(stories)}\n"
    
    if usecases:
        context += f"Use Cases: {len(usecases)}\n"
    
    if requirements:
        context += f"Requirements: {len(requirements)}\n"
    
    # Ajouter le dernier diagramme si disponible
    latest_diagram = get_latest_diagram(db, project_id)
    if latest_diagram:
        context += "\nDernier objectif de diagramme: " + latest_diagram.objective if latest_diagram.objective else "N/A"
    
    return context