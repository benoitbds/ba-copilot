from typing import Annotated, Dict, Any
from langgraph.graph import StateGraph
from agents import generate, validate, review, persist

def create_workflow():
    """
    Creates a workflow using LangGraph with Generate, Validate, Review, and Persist nodes.
    The flow transitions from:
    - Generate -> Validate
    - Validate -> Persist (if validation passes)
    - Validate -> Review (if validation fails)
    - Review -> Persist (always)
    """
    # Create a new graph
    graph = StateGraph(Dict[str, Any])
    
    # Add nodes to the graph
    graph.add_node("Generate", generate)
    graph.add_node("Validate", validate)
    graph.add_node("Review", review)
    graph.add_node("Persist", persist)
    
    # Define the workflow
    graph.set_entry_point("Generate")
    
    # Add edges between nodes
    graph.add_edge("Generate", "Validate")
    
    # Conditional edge from Validate: if validation passes, go to Persist, otherwise go to Review
    def validation_router(state: Dict[str, Any]) -> str:
        # Check validation result in the state
        if state.get("validation_passed", False):
            return "Persist"
        else:
            return "Review"
    
    graph.add_conditional_edges("Validate", validation_router, 
                                {"Persist": "Persist", "Review": "Review"})
    
    # From Review, always go to Persist
    graph.add_edge("Review", "Persist")
    
    # Compile the graph
    workflow = graph.compile()
    
    return workflow

# Create the workflow
workflow = create_workflow()

if __name__ == "__main__":
    # Example usage - would be modified based on the actual implementation needs
    initial_state = {"prompt": "Rédige un Epic SAFe pour la gestion de remboursements clients dans une banque en ligne."}
    workflow.invoke(initial_state)
