"""FastAPI entrypoint for the Quiz Taker backend."""

from __future__ import annotations

import logging
import uuid

from chatkit.server import StreamingResult
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from starlette.responses import JSONResponse

from .file_store import file_store, StoredFile
from .server import QuizServer, create_quiz_server

logger = logging.getLogger(__name__)

app = FastAPI(title="Quiz Taker API")

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5180", "http://127.0.0.1:5180","https://quiz.theologi.ca"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_quiz_server: QuizServer | None = create_quiz_server()


def get_quiz_server() -> QuizServer:
    if _quiz_server is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Quiz server not initialized",
        )
    return _quiz_server


@app.post("/chatkit")
async def chatkit_endpoint(
    request: Request,
    server: QuizServer = Depends(get_quiz_server),
) -> Response:
    """Main ChatKit endpoint - handles all chat interactions and actions."""
    payload = await request.body()
    result = await server.process(payload, {"request": request})
    
    if isinstance(result, StreamingResult):
        return StreamingResponse(result, media_type="text/event-stream")
    if hasattr(result, "json"):
        return Response(content=result.json, media_type="application/json")
    return JSONResponse(result)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


# Two-phase upload endpoints for file attachments

@app.post("/chatkit/uploads")
async def initiate_upload(request: Request):
    """Phase 1: Initiate an upload and return the upload URL."""
    body = await request.json()
    filename = body.get("filename", "unknown")
    content_type = body.get("content_type", "application/octet-stream")
    
    # Generate a temporary upload ID
    upload_id = str(uuid.uuid4())
    
    # Return the URL where the file should be uploaded
    return {
        "upload_id": upload_id,
        "upload_url": f"http://127.0.0.1:8087/chatkit/uploads/{upload_id}",
        "filename": filename,
        "content_type": content_type,
    }


async def _handle_file_upload(upload_id: str, request: Request):
    """Handle the actual file upload."""
    content_type = request.headers.get("content-type", "application/octet-stream")
    
    # Read the file data
    data = await request.body()
    
    # Store the file using the upload_id as the key
    file_store._files[upload_id] = StoredFile(
        id=upload_id,
        filename=f"upload_{upload_id}",
        content_type=content_type,
        data=data,
        size=len(data),
    )
    
    logger.info(f"[upload_file] Stored file {upload_id}: {len(data)} bytes, type: {content_type}")
    
    return {
        "id": upload_id,
        "size": len(data),
        "content_type": content_type,
    }


@app.put("/chatkit/uploads/{upload_id}")
async def upload_file_put(upload_id: str, request: Request):
    """Phase 2: Handle file upload via PUT."""
    return await _handle_file_upload(upload_id, request)


@app.post("/chatkit/uploads/{upload_id}")
async def upload_file_post(upload_id: str, request: Request):
    """Phase 2: Handle file upload via POST."""
    return await _handle_file_upload(upload_id, request)


@app.get("/chatkit/files/{file_id}")
async def get_file(file_id: str):
    """Get a file by ID."""
    stored = file_store.load(file_id)
    if not stored:
        raise HTTPException(status_code=404, detail="File not found")
    
    return Response(
        content=stored.data,
        media_type=stored.content_type,
        headers={"Content-Disposition": f'inline; filename="{stored.filename}"'},
    )

