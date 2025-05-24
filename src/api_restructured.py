from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import os

from src.routers import projects, elements, diagrams, ai_activity, agents

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

# Include routers
app.include_router(projects.router)
app.include_router(elements.router)
app.include_router(elements.project_router)
app.include_router(diagrams.router)
app.include_router(ai_activity.router)
app.include_router(agents.router)

# Check if a database file exists in the current directory or create a new one if not
DB_ENABLED = True
try:
    from src.models import Base, engine
    # Crée les tables si elles n'existent pas
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Error setting up database: {e}")
    DB_ENABLED = False

# Run the API server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api_restructured:app", host="0.0.0.0", port=8000, reload=True)