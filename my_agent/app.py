# app.py - Cloud-agnostic FastAPI application

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import os
from pathlib import Path

from .agent import GnomeCodeAgent
from .incremental_pipeline import IncrementalPipeline
from .config import CONFIG, SOURCE_DIRECTORY, VECTORSTORE_PATH

# FastAPI app
app = FastAPI(
    title="GNOME Code Assistant",
    description="AI-powered code assistant for GNOME development",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for your deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
agent = None
pipeline = None

# Request/Response models
class QueryRequest(BaseModel):
    query: str
    source_dir: Optional[str] = None

class QueryResponse(BaseModel):
    query: str
    answer: str
    intent: str
    tools_used: list
    tokens_used: int
    confidence: float
    tool_results: Dict[str, Any]

class RebuildRequest(BaseModel):
    source_dir: Optional[str] = None
    force_full: bool = False

class RebuildResponse(BaseModel):
    status: str
    message: str
    files_processed: int
    chunks_created: int

class HealthResponse(BaseModel):
    status: str
    openai_configured: bool
    vectorstore_exists: bool
    agent_ready: bool
    source_directory: str

# Background task status
rebuild_status = {"running": False, "message": "idle", "progress": 0}

@app.on_event("startup")
async def startup_event():
    """Initialize the agent and pipeline on startup."""
    global agent, pipeline
    
    try:
        print("🚀 Starting GNOME Code Assistant...")
        
        # Initialize pipeline
        pipeline = IncrementalPipeline(SOURCE_DIRECTORY)
        
        # Initialize agent
        agent = GnomeCodeAgent(str(SOURCE_DIRECTORY))
        
        print("✅ Agent initialized successfully")
        
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        raise

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with basic info."""
    return {
        "message": "GNOME Code Assistant API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    openai_ok = bool(os.getenv("OPENAI_API_KEY"))
    vectorstore_exists = VECTORSTORE_PATH.exists() and (VECTORSTORE_PATH / "index.faiss").exists()
    agent_ready = agent is not None
    
    return HealthResponse(
        status="healthy" if all([openai_ok, agent_ready]) else "degraded",
        openai_configured=openai_ok,
        vectorstore_exists=vectorstore_exists,
        agent_ready=agent_ready,
        source_directory=str(SOURCE_DIRECTORY)
    )

@app.post("/query", response_model=QueryResponse)
async def query_agent(request: QueryRequest):
    """Query the agent with a question."""
    global agent
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        # Update source directory if provided
        if request.source_dir:
            agent = GnomeCodeAgent(request.source_dir)
        
        # Run the agent
        result = agent.run(request.query)
        
        return QueryResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

async def background_rebuild(source_dir: Path, force_full: bool):
    """Background task for rebuilding the vectorstore."""
    global rebuild_status
    
    try:
        rebuild_status["running"] = True
        rebuild_status["message"] = "Starting rebuild..."
        rebuild_status["progress"] = 0
        
        # Create new pipeline instance
        pipeline = IncrementalPipeline(source_dir)
        
        rebuild_status["message"] = "Checking for modified files..."
        rebuild_status["progress"] = 20
        
        # Run incremental rebuild
        result = pipeline.rebuild_incremental(force_full=force_full)
        
        rebuild_status["message"] = "Rebuild completed"
        rebuild_status["progress"] = 100
        
        # Update global agent with new source directory
        global agent
        agent = GnomeCodeAgent(str(source_dir))
        
    except Exception as e:
        rebuild_status["message"] = f"Rebuild failed: {str(e)}"
        rebuild_status["progress"] = 0
    finally:
        rebuild_status["running"] = False

@app.post("/rebuild", response_model=RebuildResponse)
async def trigger_rebuild(request: RebuildRequest, background_tasks: BackgroundTasks):
    """Trigger a vectorstore rebuild."""
    if rebuild_status["running"]:
        return RebuildResponse(
            status="already_running",
            message=rebuild_status["message"],
            files_processed=0,
            chunks_created=0
        )
    
    source_dir = Path(request.source_dir) if request.source_dir else SOURCE_DIRECTORY
    
    # Start background task
    background_tasks.add_task(background_rebuild, source_dir, request.force_full)
    
    return RebuildResponse(
        status="started",
        message="Rebuild started in background",
        files_processed=0,
        chunks_created=0
    )

@app.get("/rebuild/status")
async def get_rebuild_status():
    """Get the current rebuild status."""
    return rebuild_status

@app.get("/config")
async def get_config():
    """Get current configuration."""
    return {
        "debug_mode": CONFIG.verbose,
        "model_name": CONFIG.model_name,
        "chunk_size": CONFIG.chunk_size,
        "max_tokens": CONFIG.max_tokens,
        "top_k": CONFIG.top_k,
        "source_directory": str(SOURCE_DIRECTORY),
        "vectorstore_path": str(VECTORSTORE_PATH)
    }

if __name__ == "__main__":
    import uvicorn
    
    # Use PORT environment variable if available, otherwise default to 8000
    port = int(os.getenv("PORT", 8000))
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=CONFIG.verbose,  # Reload in debug mode
        workers=1
    )



