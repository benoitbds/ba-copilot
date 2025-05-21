from typing import Dict, Any
from utils import run_agent

def generate(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a specification using the GenerateAgent.
    
    Args:
        state: The current workflow state
        
    Returns:
        Updated state with the generated specification
    """
    # Get the prompt from state or use a default
    prompt = state.get("prompt", "Create a detailed specification for the requested feature")
    
    # Call the GenerateAgent to create the specification
    spec = run_agent("GenerateAgent", prompt)
    
    # Update the state with the generated specification
    state["spec"] = spec
    
    return state

def validate(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate the specification using the ValidateAgent.
    
    Args:
        state: The current workflow state containing the specification
        
    Returns:
        Updated state with validation results
    """
    # Get the specification from state
    spec = state.get("spec", "")
    
    # Prepare prompt for validation
    prompt = f"Validate the following specification:\n\n{spec}"
    
    # Call the ValidateAgent to validate the specification
    validation_result = run_agent("ValidateAgent", prompt)
    
    # Process the validation result
    # In a real implementation, you might parse the validation_result more intelligently
    if "PASS" in validation_result or "VALID" in validation_result:
        state["validation_passed"] = True
        state["validation_message"] = "Specification passed validation"
    else:
        state["validation_passed"] = False
        state["validation_message"] = validation_result
    
    return state

def review(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Review and suggest improvements for a specification that failed validation.
    
    Args:
        state: The current workflow state containing the specification and validation message
        
    Returns:
        Updated state with review suggestions
    """
    # Get the specification and validation message from state
    spec = state.get("spec", "")
    validation_message = state.get("validation_message", "")
    
    # Prepare prompt for review
    prompt = f"""
    Review the following specification that failed validation:
    
    SPECIFICATION:
    {spec}
    
    VALIDATION ISSUES:
    {validation_message}
    
    Please suggest corrections or identify missing elements.
    """
    
    # Call the ReviewAgent to review the specification
    review_suggestions = run_agent("ReviewAgent", prompt)
    
    # Update the state with the review suggestions
    state["review_suggestions"] = review_suggestions
    
    # You might want to automatically update the spec based on suggestions
    # For now, we'll leave that as a future enhancement
    
    return state

def persist(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Persist the final specification and related data.
    In this basic version, just print the spec and validation status for debugging.
    
    Args:
        state: The current workflow state
        
    Returns:
        Updated state with persistence information
    """
    # Get relevant information from state
    spec = state.get("spec", "")
    validation_passed = state.get("validation_passed", False)
    validation_message = state.get("validation_message", "")
    review_suggestions = state.get("review_suggestions", "")
    
    # In a real implementation, this might save to a database, file, etc.
    # For now, just print for debugging
    print("\n=== WORKFLOW RESULT ===")
    print(f"Specification: {spec[:100]}..." if len(spec) > 100 else f"Specification: {spec}")
    print(f"Validation: {'Passed' if validation_passed else 'Failed'}")
    print(f"Validation Message: {validation_message}")
    
    if review_suggestions:
        print(f"Review Suggestions: {review_suggestions[:100]}..." if len(review_suggestions) > 100 
              else f"Review Suggestions: {review_suggestions}")
    
    # Add a timestamp or other metadata for persistence
    state["persisted"] = True
    
    return state