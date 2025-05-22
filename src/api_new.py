from fastapi import FastAPI, HTTPException, Body, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional # Ensure Dict and Any are imported
from datetime import datetime
import re
import uuid # For conversation_id

import models
import schemas
import database
from models import get_db, init_db
from schemas import (
    AIClarificationQuestion, AIProcessingResponse, 
    AIClarificationResponse, AIGenericResult, AISuccessResponse, 
    AgentResponseType, # This might be complex for endpoint return type hint, consider Any or a wrapper
    AISubmitAnswersRequest, AIClarificationAnswer
)
from utils import clarify_prompt_with_agent, run_agent_async, run_agent # Assuming run_agent_async exists or adapt run_agent
from shared_state import conversation_store # Import the shared conversation store

# Initialize FastAPI app
app = FastAPI(title="BA-Copilot API", description="API for Business Analysis Copilot")

# Add CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize the database at startup
@app.on_event("startup")
def on_startup():
    init_db()

# Project routes
@app.get("/projects", response_model=List[schemas.Project], tags=["Projects"])
async def get_projects(db: Session = Depends(get_db)):
    """
    Get a list of all projects.
    """
    return database.get_projects(db)

@app.post("/projects", response_model=schemas.Project, status_code=201, tags=["Projects"])
async def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db)):
    """
    Create a new project.
    """
    return database.create_project(db, name=project.name, description=project.description)

@app.get("/projects/{project_id}", response_model=schemas.Project, tags=["Projects"])
async def get_project(project_id: int, db: Session = Depends(get_db)):
    """
    Get a specific project by ID.
    """
    db_project = database.get_project(db, project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_project

@app.put("/projects/{project_id}", response_model=schemas.Project, tags=["Projects"])
async def update_project(
    project_id: int, 
    project_update: schemas.ProjectUpdate, 
    db: Session = Depends(get_db)
):
    """
    Update a project.
    """
    db_project = database.update_project(
        db, 
        project_id=project_id, 
        name=project_update.name, 
        description=project_update.description
    )
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_project

@app.delete("/projects/{project_id}", tags=["Projects"])
async def delete_project(project_id: int, db: Session = Depends(get_db)):
    """
    Delete a project.
    """
    success = database.delete_project(db, project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "success", "message": f"Project {project_id} deleted successfully"}

# Elements routes
@app.get("/projects/{project_id}/elements", response_model=List[schemas.Element], tags=["Elements"])
async def get_project_elements(
    project_id: int, 
    element_type: Optional[schemas.ElementTypeEnum] = None, 
    db: Session = Depends(get_db)
):
    """
    Get all elements of a project, optionally filtered by type.
    """
    db_project = database.get_project(db, project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return database.get_elements_by_project(db, project_id, element_type.value if element_type else None)

@app.post("/projects/{project_id}/elements", response_model=schemas.Element, tags=["Elements"])
async def create_element(
    project_id: int,
    element: schemas.ElementCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new element for a project.
    """
    # Vérifier que le projet existe
    db_project = database.get_project(db, project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Vérifier que le parent existe si spécifié
    if element.parent_id:
        parent_element = database.get_element(db, element.parent_id)
        if parent_element is None:
            raise HTTPException(status_code=404, detail=f"Parent element {element.parent_id} not found")
        if parent_element.project_id != project_id:
            raise HTTPException(status_code=400, detail="Parent element does not belong to this project")
    
    # Créer l'élément
    return database.create_element(
        db,
        project_id=project_id,
        custom_id=element.custom_id,
        element_type=element.type,
        title=element.title,
        description=element.description,
        status=element.status,
        parent_id=element.parent_id
    )

@app.get("/elements/{element_id}", response_model=schemas.Element, tags=["Elements"])
async def get_element(element_id: str, db: Session = Depends(get_db)):
    """
    Get a specific element by ID.
    """
    db_element = database.get_element(db, element_id)
    if db_element is None:
        raise HTTPException(status_code=404, detail="Element not found")
    return db_element

@app.put("/elements/{element_id}", response_model=schemas.Element, tags=["Elements"])
async def update_element(
    element_id: str,
    element_update: schemas.ElementUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an element.
    """
    # Vérifier que l'élément existe
    db_element = database.get_element(db, element_id)
    if db_element is None:
        raise HTTPException(status_code=404, detail="Element not found")
    
    # Vérifier que le parent existe si spécifié
    if element_update.parent_id:
        parent_element = database.get_element(db, element_update.parent_id)
        if parent_element is None:
            raise HTTPException(status_code=404, detail=f"Parent element {element_update.parent_id} not found")
        if parent_element.project_id != db_element.project_id:
            raise HTTPException(status_code=400, detail="Parent element does not belong to this project")
    
    # Mettre à jour l'élément
    return database.update_element(
        db,
        element_id=element_id,
        title=element_update.title,
        description=element_update.description,
        status=element_update.status,
        parent_id=element_update.parent_id
    )

@app.delete("/elements/{element_id}", tags=["Elements"])
async def delete_element(element_id: str, db: Session = Depends(get_db)):
    """
    Delete an element.
    """
    success = database.delete_element(db, element_id)
    if not success:
        raise HTTPException(status_code=404, detail="Element not found")
    return {"status": "success", "message": f"Element {element_id} deleted successfully"}

# Structure complète du projet
@app.get("/projects/{project_id}/structure", response_model=schemas.ProjectStructure, tags=["Projects"])
async def get_project_structure(project_id: int, db: Session = Depends(get_db)):
    """
    Get the complete structure of a project, including all elements organized hierarchically.
    """
    structure = database.get_project_structure(db, project_id)
    if structure is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return structure

# Diagrammes routes
@app.get("/projects/{project_id}/diagrams", response_model=List[schemas.Diagram], tags=["Diagrams"])
async def get_project_diagrams(project_id: int, limit: int = 5, db: Session = Depends(get_db)):
    """
    Get the diagrams of a project.
    """
    db_project = database.get_project(db, project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return database.get_project_diagrams(db, project_id, limit)

@app.post("/projects/{project_id}/diagrams", response_model=schemas.Diagram, tags=["Diagrams"])
async def create_diagram(
    project_id: int,
    diagram: schemas.DiagramCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new diagram for a project.
    """
    db_project = database.get_project(db, project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return database.create_diagram(
        db,
        project_id=project_id,
        mermaid_code=diagram.mermaid_code,
        objective=diagram.objective
    )

# Agent endpoints
@app.post("/agents/generate_mermaid", response_model=Any, tags=["Agents"]) # Changed response_model to Any for now due to Union
async def generate_mermaid_diagram_conversation(
    data: schemas.GenerateMermaidRequest, 
    db: Session = Depends(get_db)
):
    project_id = data.project_id
    objective = data.objective # This is the user's initial prompt

    db_project = database.get_project(db, project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # Synthesize project context (ensure this function is defined in your database.py or equivalent)
    project_context = synthesize_project_context(db, project_id) 

    # Conceptual: active_session = start_ai_activity_session(db, project_id, "ClarifyAndGenerateMermaid")
    # For now, active_session handling is conceptual. clarify_prompt_with_agent and run_agent_async
    # might handle their own session logging if db and project_id are passed.

    clarification_result = clarify_prompt_with_agent(
        initial_prompt=objective,
        project_context=project_context,
        db=db, 
        project_id=project_id
        # active_session=active_session # Pass the session if managed here
    )

    if clarification_result != "CLEAR":
        # Questions were returned
        conversation_id = str(uuid.uuid4())
        conversation_store[conversation_id] = {
            "original_prompt": objective,
            "project_context": project_context,
            "project_id": project_id,
            "agent_type": "GenerateMermaidAgent"
        }
        
        questions_structured = [
            AIClarificationQuestion(question_id=f"q{i+1}", text=q_text) 
            for i, q_text in enumerate(clarification_result) # clarification_result is List[str] here
        ]

        # Conceptual: log_questions_to_activity(active_session, questions_structured)
        # Conceptual: update_ai_activity_status(active_session, "AWAITING_USER_INPUT")

        return AIClarificationResponse(
            status="clarification_needed",
            questions=questions_structured,
            conversation_id=conversation_id
            # activity_session_id=active_session.session_id if active_session else None
        )
    else:
        # Prompt is clear, proceed to generate Mermaid diagram
        # Conceptual: log_clarity_confirmed(active_session)
        
        full_prompt_for_mermaid = f"""Objectif: {objective}

Contexte du projet:
{project_context}

Générer un diagramme Mermaid mindmap représentant la cartographie fonctionnelle du projet.
"""
        # Assuming run_agent_async is available and works similarly to run_agent but async
        # If run_agent_async is not fully implemented for async session management,
        # this part may need adjustment or use synchronous run_agent.
        # For the purpose of this subtask, we use await assuming run_agent_async is async.
        mermaid_response_text = await run_agent_async( 
            role="GenerateMermaidAgent",
            prompt=full_prompt_for_mermaid,
            db=db,
            project_id=project_id
            # active_session=active_session
        )
        
        mermaid_code = extract_mermaid_code(mermaid_response_text) 

        if mermaid_code and "mindmap" in mermaid_code:
            database.process_mermaid_diagram(db, project_id, mermaid_code, objective)
            # Conceptual: log_success(active_session)
            # Conceptual: complete_ai_activity_session(active_session)
            return AISuccessResponse(
                status="success",
                result=AIGenericResult(content_type="mermaid", data=mermaid_code)
                # activity_session_id=active_session.session_id if active_session else None
            )
        else:
            # Conceptual: log_error(active_session, "Failed to generate valid Mermaid")
            # Conceptual: complete_ai_activity_session(active_session, status="ERROR")
            raise HTTPException(status_code=500, detail="Failed to generate valid Mermaid diagram after clarification.")

@app.post("/agents/submit_answers", response_model=Any, tags=["Agents"]) # Changed response_model to Any
async def submit_answers_and_generate(
    data: AISubmitAnswersRequest,
    db: Session = Depends(get_db)
):
    conversation_id = data.conversation_id
    user_answers = data.answers
    
    stored_context = conversation_store.pop(conversation_id, None)
    if not stored_context:
        raise HTTPException(status_code=404, detail="Conversation not found or already processed.")

    original_prompt = stored_context["original_prompt"]
    project_context = stored_context["project_context"]
    project_id = stored_context["project_id"]
    agent_type = stored_context["agent_type"]

    answers_formatted = "\n".join([f"- Answer to '{ans.answer_id}': {ans.text}" for ans in user_answers])
    refined_prompt = (
        f"Original Request: \"{original_prompt}\"\n\n"
        f"User provided the following clarifications:\n{answers_formatted}\n\n"
        f"Project Context:\n{project_context}\n\n"
        f"Based on all the above, please now proceed with the original request to generate the diagram/specification." # Made prompt more generic
    )

    # Conceptual: Start or continue AI Activity Session for the generation part
    # active_session = start_or_get_ai_activity_session(...)
    # log_refined_prompt(active_session, refined_prompt)

    if agent_type == "GenerateMermaidAgent":
        mermaid_response_text = await run_agent_async( 
            role="GenerateMermaidAgent",
            prompt=refined_prompt,
            db=db,
            project_id=project_id
            # active_session=active_session
        )
        mermaid_code = extract_mermaid_code(mermaid_response_text)

        if mermaid_code and "mindmap" in mermaid_code:
            database.process_mermaid_diagram(db, project_id, mermaid_code, original_prompt) 
            # Conceptual: log_success(active_session)
            # Conceptual: complete_ai_activity_session(active_session)
            return AISuccessResponse(
                status="success",
                result=AIGenericResult(content_type="mermaid", data=mermaid_code)
            )
        else:
            # Conceptual: log_error(...)
            raise HTTPException(status_code=500, detail="Failed to generate Mermaid diagram even after answers.")
    elif agent_type == "GenerateAgent": 
        # This part is illustrative for when we modify a similar endpoint for general specifications
        spec_response_text = await run_agent_async(
            role="GenerateAgent", # A generic agent for specifications
            prompt=refined_prompt,
            db=db,
            project_id=project_id
            # active_session=active_session
        )
        # Here you would typically parse spec_response_text to extract structured elements (Epics, Features, etc.)
        # and save them to the database, similar to how process_mermaid_diagram works.
        # For this example, we just return the raw text.
        # database.process_specification(db, project_id, spec_response_text, original_prompt) # Hypothetical function
        return AISuccessResponse(
            status="success",
            result=AIGenericResult(content_type="specification", data=spec_response_text)
             # elements_extracted and elements_info could be populated here after processing
        )
    elif agent_type == "GenerateAgentSimplified":
        spec_response_text = await run_agent_async(
            role="GenerateAgent", # The underlying AI role is still "GenerateAgent"
            prompt=refined_prompt,
            db=db,
            project_id=project_id
            # active_session=active_session # Pass session if used
        )
        return AISuccessResponse(
            status="success",
            result=AIGenericResult(content_type="text", data=spec_response_text)
        )
    else:
        # Conceptual: log_error(...)
        raise HTTPException(status_code=500, detail=f"Unknown agent type: {agent_type}")

@app.post("/nodes/update", tags=["Elements"])
async def update_node(data: schemas.NodeUpdate, db: Session = Depends(get_db)):
    """
    Update a node in the project.
    This endpoint is a compatibility layer for the existing frontend.
    """
    project_id = data.project_id
    node = data.node
    
    if not project_id or not node:
        raise HTTPException(status_code=400, detail="project_id et node sont requis")
    
    # Vérifier que les propriétés requises sont présentes
    required_fields = ["id", "type", "title"]
    if not all(field in node for field in required_fields):
        raise HTTPException(status_code=400, detail="Les champs id, type et title sont requis dans l'objet node")
    
    # Vérifier que le projet existe
    db_project = database.get_project(db, project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Rechercher l'élément par custom_id
    custom_id = node["id"]
    element = db.query(models.Element).filter(
        models.Element.project_id == project_id,
        models.Element.custom_id == custom_id
    ).first()
    
    if element:
        # Mettre à jour l'élément existant
        element.title = node["title"]
        element.description = node.get("description", "")
        element.status = node.get("status", "pending")
        element.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(element)
        
        updated_node = {
            "id": element.id,
            "custom_id": element.custom_id,
            "type": element.type,
            "title": element.title,
            "description": element.description,
            "status": element.status,
            "updated_at": element.updated_at.isoformat()
        }
    else:
        # Créer un nouvel élément
        new_element = models.Element(
            id=str(uuid.uuid4()),
            custom_id=custom_id,
            type=node["type"],
            title=node["title"],
            description=node.get("description", ""),
            status=node.get("status", "pending"),
            project_id=project_id
        )
        db.add(new_element)
        db.commit()
        db.refresh(new_element)
        
        updated_node = {
            "id": new_element.id,
            "custom_id": new_element.custom_id,
            "type": new_element.type,
            "title": new_element.title,
            "description": new_element.description,
            "status": new_element.status,
            "updated_at": new_element.updated_at.isoformat()
        }
    
    return {
        "success": True,
        "updated_node": updated_node
    }

@app.get("/nodes/{project_id}/{node_id}", tags=["Elements"])
async def get_node(project_id: int, node_id: str, db: Session = Depends(get_db)):
    """
    Get a node from the project.
    This endpoint is a compatibility layer for the existing frontend.
    """
    # Vérifier que le projet existe
    db_project = database.get_project(db, project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Rechercher l'élément par custom_id
    element = db.query(models.Element).filter(
        models.Element.project_id == project_id,
        models.Element.custom_id == node_id
    ).first()
    
    if not element:
        # Si le nœud n'existe pas, retourner un nœud par défaut
        return {
            "id": node_id,
            "type": "unknown",
            "title": f"Nœud {node_id}",
            "description": "",
            "status": "pending"
        }
    
    return {
        "id": element.custom_id,
        "type": element.type,
        "title": element.title,
        "description": element.description,
        "status": element.status
    }


def synthesize_project_context(db: Session, project_id: int):
    """
    Synthesize project context for the AI agent prompt.
    """
    # Get project details
    project = database.get_project(db, project_id)
    if not project:
        return "Nouveau projet sans contexte existant."
    
    # Get project elements
    elements = database.get_elements_by_project(db, project_id)
    
    # Organize elements by type
    elements_by_type: Dict[str, List[models.Element]] = {} # Added type hint for clarity
    for element in elements:
        if element.type.value not in elements_by_type: # Ensure element.type is ElementTypeEnum
            elements_by_type[element.type.value] = []
        elements_by_type[element.type.value].append(element)
    
    # Build context string
    context_parts = []
    
    # Project description
    if project.description:
        context_parts.append(f"Description: {project.description}")
    
    # Elements summary by type
    for element_type, type_elements in elements_by_type.items():
        context_parts.append(f"{element_type.capitalize()}s ({len(type_elements)}):")
        for element in type_elements[:5]:  # Limit to 5 elements per type
            status_str = f" [{element.status.value}]"
            context_parts.append(f"- {element.title}{status_str}")
        if len(type_elements) > 5:
            context_parts.append(f"  ... et {len(type_elements) - 5} autres {element_type}s")
    
    # Recent diagrams
    diagrams = database.get_project_diagrams(db, project_id, 3)  # Get last 3 diagrams
    if diagrams:
        context_parts.append("Derniers diagrammes:")
        for diagram in diagrams:
            created_at = diagram.created_at.date().isoformat()
            context_parts.append(f"- [{created_at}] {diagram.objective or 'Sans objectif'}")
    
    # Combine and limit size
    context = "\n\n".join(context_parts)
    if len(context) > 2000:
        context = context[:1950] + "...\n(Contexte tronqué pour limiter la taille)"
    
    return context

def extract_mermaid_code(response):
    """
    Extrait le code Mermaid de la réponse de l'agent.
    Prend en charge différents formats de réponse.
    """
    # Si la réponse est un dictionnaire contenant directement le code Mermaid
    if isinstance(response, dict) and "mermaid" in response:
        return response["mermaid"]
    
    # Si la réponse est une chaîne de caractères contenant le code Mermaid
    if isinstance(response, str):
        # Recherche du code Mermaid entre des marqueurs de code
        import re
        
        # Cas 1: Code entre ```mermaid et ```
        mermaid_pattern = r"```mermaid\s*([\s\S]*?)\s*```"
        matches = re.search(mermaid_pattern, response)
        if matches:
            return matches.group(1).strip()
        
        # Cas 2: Code entre ```mindmap et ```
        mindmap_pattern = r"```mindmap\s*([\s\S]*?)\s*```"
        matches = re.search(mindmap_pattern, response)
        if matches:
            return "mindmap\n" + matches.group(1).strip()
        
        # Cas 3: Si la réponse commence directement par "mindmap" ou contient majoritairement du code Mermaid
        # Ensure 'mindmap' is a keyword that guarantees it's a mermaid diagram
        if response.strip().startswith("mindmap") or ("mindmap" in response and "root" in response): # Added check for "root" for mindmaps
            # Nettoyer les éventuels préfixes/suffixes de texte
            lines = response.split("\n")
            # Find the line that actually starts the mindmap content
            start_idx = 0
            for i, line in enumerate(lines):
                if line.strip().lower().startswith("mindmap"): # Use lower() for case-insensitivity
                    start_idx = i
                    break
            return "\n".join(lines[start_idx:]).strip()
            
    # If no code block is found, and it's not starting with mindmap, return error or the response itself if it might be valid
    # For this implementation, returning an error string is safer if expecting a block.
    return "Erreur: Aucun diagramme Mermaid n'a pu être généré ou le format n'est pas reconnu."


# Ensure this is the last part of the file
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_new:app", host="0.0.0.0", port=8000, reload=True)