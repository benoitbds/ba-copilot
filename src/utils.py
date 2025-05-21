import os
import openai
import asyncio
from typing import Optional, Dict, Any, Union, Callable
from dotenv import load_dotenv
from sqlalchemy.orm import Session
import models
from websocket import AsyncAIActivitySessionManager
from models import AIEventTypeEnum

# Load environment variables from .env file if present
load_dotenv()

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
                {"role": role}
            )
        
        # Make the API call to OpenAI
        response = await client.chat.completions.create(
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
        
        # Log the response
        if active_session:
            await active_session.add_event(
                role,
                AIEventTypeEnum.RESPONSE,
                result,
                {"role": role}
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