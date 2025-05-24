import os
import openai
import asyncio
import re # Added for parse_clarification_response
from typing import Optional, Dict, Any, Union, Callable, List, Literal # Added List, Literal
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from src import models
from src.websocket import AsyncAIActivitySessionManager
from src.models import AIEventTypeEnum

# Load environment variables from .env file if present
load_dotenv()

def parse_clarification_response(response_text: str) -> Union[Literal["CLEAR"], List[str]]:
    # Parses the AI's response. If it's "CLEAR", returns "CLEAR".
    # Otherwise, it extracts questions.
    # Example: Response might be "CLEAR" or "Q1: What is X?
# Q2: How about Y?"
    if response_text.strip().upper() == "CLEAR":
        return "CLEAR"
    
    questions = []
    # Basic parsing: split by newline, filter out empty.
    # More robust parsing might be needed based on AI's output format.
    for line in response_text.splitlines():
        if line.strip() and re.match(r"^(Q\d+[:\.\-]?\s*|[\*\-]\s+)", line.strip(), re.IGNORECASE):
            questions.append(re.sub(r"^(Q\d+[:\.\-]?\s*|[\*\-]\s+)", "", line.strip()))
        elif line.strip(): # if no specific prefix, but line is not empty, consider it a question
            questions.append(line.strip())
    return questions if questions else "CLEAR" # if parsing fails to find questions but not CLEAR, assume clear.


def clarify_prompt_with_agent(
    initial_prompt: str,
    project_context: str, # This would be synthesized as it is for GenerateMermaidAgent
    db: Optional[Session] = None, # db is not used in the provided snippet, but kept for consistency
    project_id: Optional[int] = None, # project_id is not used, kept for consistency
    active_session: Optional[AsyncAIActivitySessionManager] = None
) -> Union[Literal["CLEAR"], List[str]]: # Returns "CLEAR" or a list of question strings
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        if active_session:
             # Log error if session available
            asyncio.run(active_session.add_event(
                "ClarificationAgent", AIEventTypeEnum.ERROR, "Error: OPENAI_API_KEY environment variable not set", {}))
        return ["Error: OPENAI_API_KEY environment variable not set"]

    client = openai.OpenAI(api_key=api_key)
    
    clarification_agent_role = "ClarificationAgent"
    system_message = (
        f"You are a {clarification_agent_role} for requirements engineering. "
        "Your task is to analyze the user's request and project context. "
        "If the request is clear and sufficient for processing, respond with the single word 'CLEAR'. "
        "Otherwise, formulate 1-3 specific questions for the user to resolve ambiguities or gather missing critical details. "
        "Phrase questions clearly. Do not ask for information already present in the context if substantial. "
        "Prefix each question with 'Qn: ' (e.g., 'Q1: Question text?'). If only one question, you can omit the prefix."
    )
    
    full_prompt_for_clarification = (
        f"User Request: \"{initial_prompt}\"\n\n"
        f"Project Context:\n{project_context}\n\n"
        "Based on the request and context, are there any clarifying questions needed? "
        "If clear, respond 'CLEAR'. Otherwise, list the questions."
    )
    
    # Full system and user messages for logging
    system_prompt = {"role": "system", "content": system_message}
    user_prompt = {"role": "user", "content": full_prompt_for_clarification}
    full_prompt = [system_prompt, user_prompt]

    # Log start, prompt for clarification agent (if session is available)
    if active_session:
        asyncio.run(active_session.add_event(
            clarification_agent_role, AIEventTypeEnum.START, "Starting clarification phase", {}))
        asyncio.run(active_session.add_event(
            clarification_agent_role, 
            AIEventTypeEnum.PROMPT, 
            full_prompt_for_clarification, 
            {
                "full_prompt": full_prompt,
                "system_message": system_message
            }
        ))

    try:
        # Prepare request parameters
        request_params = {
            "model": "gpt-4o", # Or a faster/cheaper model if suitable for clarification
            "messages": full_prompt,
            "temperature": 0.3, # Lower temperature for more deterministic clarification
            "max_tokens": 300
        }
        
        # Make the API call
        response = client.chat.completions.create(**request_params)
        ai_response_text = response.choices[0].message.content.strip()

        if active_session:
            asyncio.run(active_session.add_event(
                clarification_agent_role, 
                AIEventTypeEnum.RESPONSE, 
                ai_response_text, 
                {
                    "request_params": request_params,
                    "response_metadata": {
                        "model": response.model,
                        "usage": {
                            "prompt_tokens": response.usage.prompt_tokens,
                            "completion_tokens": response.usage.completion_tokens,
                            "total_tokens": response.usage.total_tokens
                        }
                    }
                }
            ))

        return parse_clarification_response(ai_response_text)

    except Exception as e:
        if active_session:
            asyncio.run(active_session.add_event(
                clarification_agent_role, AIEventTypeEnum.ERROR, str(e), {}))
        return [f"Error during clarification: {str(e)}"] # Return error as a list of questions

def run_agent(
    role: str, 
    prompt: str, 
    db: Optional[Session] = None,
    project_id: Optional[int] = None,
    active_session: Optional[AsyncAIActivitySessionManager] = None
) -> str:
    """
    Run an OpenAI agent with a specific role and prompt.
    
    Args:
        role: The role of the agent (e.g., "GenerateAgent", "ValidateAgent")
        prompt: The instruction prompt to send to the agent
        db: Optional database session for logging events
        project_id: Optional project ID for associating events with a project
        active_session: Optional existing activity session to use
        
    Returns:
        The complete text response from the agent
    """
    # Get API key from environment variable
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        if db and active_session:
            # Log the error event
            asyncio.run(active_session.add_event(
                "System",
                AIEventTypeEnum.ERROR,
                "Error: OPENAI_API_KEY environment variable not set",
                {"error": "Missing API key"}
            ))
        return "Error: OPENAI_API_KEY environment variable not set"
    
    # Configure the OpenAI client
    client = openai.OpenAI(api_key=api_key)
    
    # Prepare the system message with the agent's role
    system_message = f"You are a {role} for requirements engineering. Follow the provided instructions."
    
    # Log the starting event if we have a database session
    try:
        # If we have a database session but no active session, create one
        should_close_session = False
        
        if db and not active_session:
            # Create a new activity session
            active_session = AsyncAIActivitySessionManager(
                db,
                f"Agent {role}",
                "agent_run",
                project_id,
                {"role": role}
            )
            # Enter the context manager
            active_session = asyncio.run(active_session.__aenter__())
            should_close_session = True
        
        if active_session:
            # Log the start event
            asyncio.run(active_session.add_event(
                role,
                AIEventTypeEnum.START,
                f"Starting {role}",
                {"role": role}
            ))
            
            # Log the prompt
            asyncio.run(active_session.add_event(
                role,
                AIEventTypeEnum.PROMPT,
                prompt,
                {"role": role}
            ))
        
        # Make the API call to OpenAI
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        # Extract the text response
        result = response.choices[0].message.content
        
        # Log the response if we have an active session
        if active_session:
            asyncio.run(active_session.add_event(
                role,
                AIEventTypeEnum.RESPONSE,
                result,
                {"role": role}
            ))
            
            # Complete the session if we created it
            if should_close_session:
                asyncio.run(active_session.__aexit__(None, None, None))
        
        return result
    
    except Exception as e:
        # Log the error if we have an active session
        if active_session:
            asyncio.run(active_session.add_event(
                role,
                AIEventTypeEnum.ERROR,
                f"Error calling OpenAI API: {str(e)}",
                {"error": str(e), "role": role}
            ))
            
            # Complete the session if we created it
            if should_close_session:
                asyncio.run(active_session.__aexit__(None, None, None))
        
        # Basic error handling
        return f"Error calling OpenAI API: {str(e)}"

async def run_agent_async(
    role: str, 
    prompt: str, 
    db: Optional[Session] = None,
    project_id: Optional[int] = None,
    active_session: Optional[AsyncAIActivitySessionManager] = None,
    on_start: Optional[Callable[[str], Any]] = None,
    on_complete: Optional[Callable[[str, str], Any]] = None,
    on_error: Optional[Callable[[str, Exception], Any]] = None
) -> str:
    """
    Asynchronous version of run_agent with real-time event logging.
    
    Args:
        role: The role of the agent (e.g., "GenerateAgent", "ValidateAgent")
        prompt: The instruction prompt to send to the agent
        db: Optional database session for logging events
        project_id: Optional project ID for associating events with a project
        active_session: Optional existing activity session to use
        on_start: Optional callback when the agent starts
        on_complete: Optional callback when the agent completes successfully
        on_error: Optional callback when the agent encounters an error
        
    Returns:
        The complete text response from the agent
    """
    # Get API key from environment variable
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        error_msg = "Error: OPENAI_API_KEY environment variable not set"
        if active_session:
            await active_session.add_event(
                "System",
                AIEventTypeEnum.ERROR,
                error_msg,
                {"error": "Missing API key"}
            )
        if on_error:
            on_error(role, Exception(error_msg))
        return error_msg
    
    # Configure the OpenAI client
    client = openai.AsyncOpenAI(api_key=api_key)
    
    # Prepare the system message with the agent's role
    system_message = f"You are a {role} for requirements engineering. Follow the provided instructions."
    
    # Full system and user messages for logging
    system_prompt = {"role": "system", "content": system_message}
    user_prompt = {"role": "user", "content": prompt}
    full_prompt = [system_prompt, user_prompt]
    
    # Create a new activity session if needed
    should_close_session = False
    try:
        if db and not active_session:
            active_session = AsyncAIActivitySessionManager(
                db,
                f"Agent {role}",
                "agent_run",
                project_id,
                {"role": role}
            )
            active_session = await active_session.__aenter__()
            should_close_session = True
        
        # Notify that the agent is starting
        if on_start:
            on_start(role)
        
        # Log the start event
        if active_session:
            await active_session.add_event(
                role,
                AIEventTypeEnum.START,
                f"Starting {role}",
                {"role": role}
            )
            
            # Log the prompt
            await active_session.add_event(
                role,
                AIEventTypeEnum.PROMPT,
                prompt,
                {
                    "role": role,
                    "full_prompt": full_prompt,
                    "system_message": system_message
                }
            )
        
        # Make the API call to OpenAI
        request_params = {
            "model": "gpt-4o",
            "messages": full_prompt,
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        response = await client.chat.completions.create(**request_params)
        
        # Extract the text response
        result = response.choices[0].message.content
        
        # Log the response
        if active_session:
            await active_session.add_event(
                role,
                AIEventTypeEnum.RESPONSE,
                result,
                {
                    "role": role,
                    "request_params": request_params,
                    "response_metadata": {
                        "model": response.model,
                        "usage": {
                            "prompt_tokens": response.usage.prompt_tokens,
                            "completion_tokens": response.usage.completion_tokens,
                            "total_tokens": response.usage.total_tokens
                        }
                    }
                }
            )
            
            # Log completion
            await active_session.add_event(
                role,
                AIEventTypeEnum.COMPLETE,
                f"Completed {role}",
                {"role": role}
            )
        
        # Notify that the agent has completed
        if on_complete:
            on_complete(role, result)
        
        # Close the session if we created it
        if should_close_session and active_session:
            await active_session.__aexit__(None, None, None)
        
        return result
        
    except Exception as e:
        # Log the error
        if active_session:
            await active_session.add_event(
                role,
                AIEventTypeEnum.ERROR,
                f"Error calling OpenAI API: {str(e)}",
                {"error": str(e), "role": role}
            )
            
            # Close the session if we created it
            if should_close_session:
                await active_session.__aexit__(None, None, None)
        
        # Notify about the error
        if on_error:
            on_error(role, e)
        
        # Basic error handling
        return f"Error calling OpenAI API: {str(e)}"