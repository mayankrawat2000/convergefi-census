import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import json

from app.agent import CensusAgent
from app.config import ARTIFACTS_DIR, WORKSPACE_DIR, DATA_DIR
from app.database import list_sessions, get_session_messages, delete_session

app = FastAPI(title="Document Q&A Chatbot API", version="1.0.0")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LoginRequest(BaseModel):
    user_id: str
    password: str

@app.post("/api/login")
async def login_endpoint(req: LoginRequest):
    """
    Validates credentials against USER_ID and PASSWORD env vars.
    Returns 200 on success, 401 on failure.
    """
    expected_user = os.environ.get("USER_ID", "")
    expected_pass = os.environ.get("PASSWORD", "")
    if req.user_id == expected_user and req.password == expected_pass:
        return {"status": "ok"}
    raise HTTPException(status_code=401, detail="Invalid credentials")


class ChatRequest(BaseModel):
    message: str = Field(..., description="The user query")
    session_id: str = Field(..., description="The unique session identifier for tracking memory")
    model: Optional[str] = Field(None, description="Optional override for model ID")
    reasoning_effort: Optional[str] = Field("medium", description="Optional reasoning effort (low/medium/high)")

class CitationModel(BaseModel):
    source_document: str
    page_number: int
    snippet: str

class ArtifactModel(BaseModel):
    name: str
    type: str
    description: str

class ChatResponse(BaseModel):
    answer: str
    citations: List[CitationModel]
    artifacts: List[ArtifactModel]
    logs: List[str]

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    """
    Core chat endpoint that handles messages and executes the agent loop.
    """
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
        
    try:
        agent = CensusAgent(session_id=req.session_id)
        if req.model:
            agent.model = req.model
        if req.reasoning_effort:
            agent.reasoning_effort = req.reasoning_effort
            
        response_dict = agent.chat(req.message)
        
        return ChatResponse(
            answer=response_dict.get("answer", "No answer was returned."),
            citations=response_dict.get("citations", []),
            artifacts=response_dict.get("artifacts", []),
            logs=response_dict.get("logs", [])
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@app.post("/api/chat/stream")
async def chat_stream_endpoint(req: ChatRequest):
    """
    Streaming variant of /api/chat.
    Returns a text/event-stream response with SSE events emitted token by token.
    """
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    def generate():
        agent = CensusAgent(session_id=req.session_id)
        if req.model:
            agent.model = req.model
        if req.reasoning_effort:
            agent.reasoning_effort = req.reasoning_effort
        try:
            for event in agent.stream_chat(req.message):
                yield event
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ─── Session Management Endpoints ─────────────────────────────────────────────

@app.get("/api/sessions")
async def list_sessions_endpoint():
    """
    Returns all sessions sorted newest first.
    Each item: { session_id, title, updated_at, created_at }
    """
    return list_sessions()


@app.get("/api/sessions/{session_id}")
async def get_session_endpoint(session_id: str):
    """
    Returns the full message list for a session (for UI replay).
    """
    messages = get_session_messages(session_id)
    if messages is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "messages": messages}


@app.delete("/api/sessions/{session_id}")
async def delete_session_endpoint(session_id: str):
    """
    Deletes a session and all its history.
    """
    deleted = delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "success", "message": "Session deleted"}


@app.delete("/api/history/{session_id}")
async def clear_history_endpoint(session_id: str):
    """
    Clears conversation history for a session (delegates to MongoDB).
    """
    delete_session(session_id)
    return {"status": "success", "message": "History cleared"}


# ─── Static File Endpoints ─────────────────────────────────────────────────────

@app.get("/api/artifacts/{filename}")
async def serve_artifact_endpoint(filename: str):
    """
    Serves images, plots, or data sheets generated by the agent.
    """
    safe_filename = os.path.basename(filename)
    filepath = os.path.join(ARTIFACTS_DIR, safe_filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Artifact not found")
        
    return FileResponse(filepath)

@app.get("/api/pdf/{filename}")
async def serve_pdf_endpoint(filename: str):
    """
    Serves source PDF files from the data directory for inline preview.
    """
    safe_filename = os.path.basename(filename)
    filepath = os.path.join(DATA_DIR, safe_filename)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="PDF not found")

    return FileResponse(filepath, media_type="application/pdf")

@app.get("/api/health")
async def health_check():
    """
    Simple health check.
    """
    master_csv_path = os.path.join(WORKSPACE_DIR, "data", "census_master.csv")
    master_exists = os.path.exists(master_csv_path)
    
    return {
        "status": "healthy",
        "database_connected": os.path.exists(os.path.join(WORKSPACE_DIR, "census_data.db")),
        "master_dataset_ready": master_exists
    }
