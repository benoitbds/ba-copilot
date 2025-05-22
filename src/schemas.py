from typing import List, Optional, Dict, Any, Union, Literal
from pydantic import BaseModel
from datetime import datetime
from enum import Enum

class StatusEnum(str, Enum):
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress' 
    COMPLETED = 'completed'

class ElementTypeEnum(str, Enum):
    EPIC = 'epic'
    FEATURE = 'feature'
    STORY = 'story'
    USECASE = 'usecase'
    REQUIREMENT = 'requirement'
    ROOT = 'root'

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(ProjectBase):
    name: Optional[str] = None

class Project(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ElementBase(BaseModel):
    custom_id: str
    type: ElementTypeEnum
    title: str
    description: Optional[str] = None
    status: StatusEnum = StatusEnum.PENDING

class ElementCreate(ElementBase):
    parent_id: Optional[str] = None
    project_id: int

class ElementUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[StatusEnum] = None
    parent_id: Optional[str] = None

class Element(ElementBase):
    id: str
    project_id: int
    parent_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ElementWithChildren(Element):
    children: List["ElementWithChildren"] = []
    
    class Config:
        from_attributes = True

# Pour résoudre la référence récursive
ElementWithChildren.update_forward_refs()

class DiagramBase(BaseModel):
    objective: Optional[str] = None
    mermaid_code: str

class DiagramCreate(DiagramBase):
    project_id: int

class Diagram(DiagramBase):
    id: int
    project_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ProjectStructure(Project):
    elements: List[ElementWithChildren] = []
    latest_diagram: Optional[Diagram] = None
    
    class Config:
        from_attributes = True

class GenerateMermaidRequest(BaseModel):
    project_id: int
    objective: str

class NodeUpdate(BaseModel):
    project_id: int
    node: Dict[str, Any]

# Nouveau schéma pour la génération de hiérarchie
class GenerateHierarchyRequest(BaseModel):
    project_id: int
    prompt: str

class FeatureWithStories(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    stories: List[Dict[str, Any]] = []

class EpicWithFeatures(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    features: List[FeatureWithStories] = []

class HierarchyResponse(BaseModel):
    epics: List[EpicWithFeatures] = []

# Schémas pour l'API d'activité IA
class AIEventBase(BaseModel):
    agent_name: str
    event_type: str
    content: str
    event_data: Optional[Dict[str, Any]] = None  # Renommé de metadata

# Schemas for Conversational AI Flow

class AIClarificationQuestion(BaseModel):
    question_id: str # e.g., "q1", "q2"
    text: str

class AIProcessingResponse(BaseModel):
    status: Literal["processing"]
    message: str
    activity_session_id: Optional[int] = None

class AIClarificationResponse(BaseModel):
    status: Literal["clarification_needed"]
    questions: List[AIClarificationQuestion]
    conversation_id: str # A temporary ID to track this Q&A exchange
    activity_session_id: Optional[int] = None

class AIGenericResult(BaseModel):
    content_type: str # e.g., "mermaid", "specification", "text"
    data: Any # The actual generated content

class AISuccessResponse(BaseModel):
    status: Literal["success"]
    result: AIGenericResult
    activity_session_id: Optional[int] = None
    elements_extracted: Optional[int] = None
    elements_info: Optional[str] = None

AgentResponseType = Union[AIProcessingResponse, AIClarificationResponse, AISuccessResponse]

class AIClarificationAnswer(BaseModel):
    answer_id: str # Corresponds to question_id
    text: str

class AISubmitAnswersRequest(BaseModel):
    conversation_id: str
    answers: List[AIClarificationAnswer]
    project_id: int # To maintain context
    original_prompt: str # The very first prompt from the user for this task

class AIEventCreate(AIEventBase):
    pass

class AIEvent(AIEventBase):
    id: int
    session_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class AIActivitySessionBase(BaseModel):
    title: str
    action_type: str
    project_id: Optional[int] = None
    session_data: Optional[Dict[str, Any]] = None  # Renommé de metadata

class AIActivitySessionCreate(AIActivitySessionBase):
    pass

class AIActivitySession(AIActivitySessionBase):
    id: int
    status: StatusEnum
    created_at: datetime
    completed_at: Optional[datetime] = None
    events: List[AIEvent] = []
    
    class Config:
        from_attributes = True

class AIEventUpdate(BaseModel):
    agent_name: str
    event_type: str
    content: str
    event_data: Optional[Dict[str, Any]] = None  # Renommé de metadata