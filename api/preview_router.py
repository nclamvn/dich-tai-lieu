#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Real-time Preview Router

Provides WebSocket endpoint for live translation preview.
Streams translated chunks as they are completed.
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/preview", tags=["Real-time Preview"])


class PreviewSession:
    """Manages a preview session for streaming translation."""

    def __init__(self, session_id: str, websocket: WebSocket):
        self.session_id = session_id
        self.websocket = websocket
        self.is_active = True
        self.current_chunk = 0
        self.total_chunks = 0
        self.content = []  # Accumulated translated content

    async def send_chunk(self, chunk_index: int, content: str, metadata: Dict = None):
        """Send a translated chunk to the client."""
        if not self.is_active:
            return

        try:
            await self.websocket.send_json({
                "event": "chunk_translated",
                "session_id": self.session_id,
                "chunk_index": chunk_index,
                "content": content,
                "metadata": metadata or {},
            })
            self.current_chunk = chunk_index
            self.content.append(content)
        except Exception as e:
            logger.error(f"Failed to send chunk: {e}")
            self.is_active = False

    async def send_progress(self, progress: float, stage: str = "translating"):
        """Send progress update."""
        if not self.is_active:
            return

        try:
            await self.websocket.send_json({
                "event": "progress",
                "session_id": self.session_id,
                "progress": progress,
                "stage": stage,
                "chunks_completed": self.current_chunk,
                "total_chunks": self.total_chunks,
            })
        except Exception as e:
            logger.error(f"Failed to send progress: {e}")

    async def send_complete(self, outputs: Dict = None):
        """Send completion message."""
        try:
            await self.websocket.send_json({
                "event": "completed",
                "session_id": self.session_id,
                "total_chunks": len(self.content),
                "outputs": outputs or {},
            })
        except Exception as e:
            logger.error(f"Failed to send completion: {e}")
        finally:
            self.is_active = False

    async def send_error(self, error: str):
        """Send error message."""
        try:
            await self.websocket.send_json({
                "event": "error",
                "session_id": self.session_id,
                "error": error,
            })
        except Exception as e:
            logger.error(f"Failed to send error: {e}")
        finally:
            self.is_active = False


# Active preview sessions
_sessions: Dict[str, PreviewSession] = {}


class PreviewManager:
    """Manages preview sessions and integrates with translation pipeline."""

    @staticmethod
    def create_session(session_id: str, websocket: WebSocket) -> PreviewSession:
        """Create a new preview session."""
        session = PreviewSession(session_id, websocket)
        _sessions[session_id] = session
        return session

    @staticmethod
    def get_session(session_id: str) -> Optional[PreviewSession]:
        """Get an existing session."""
        return _sessions.get(session_id)

    @staticmethod
    def remove_session(session_id: str):
        """Remove a session."""
        if session_id in _sessions:
            del _sessions[session_id]

    @staticmethod
    async def broadcast_chunk(job_id: str, chunk_index: int, content: str, metadata: Dict = None):
        """Broadcast a chunk to all sessions watching this job."""
        for session_id, session in list(_sessions.items()):
            if session.session_id.startswith(job_id) and session.is_active:
                await session.send_chunk(chunk_index, content, metadata)


@router.websocket("/stream/{job_id}")
async def preview_stream(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for streaming translation preview.

    Connect to receive real-time translated chunks as they are completed.

    Messages:
    - `chunk_translated`: New chunk is available
    - `progress`: Translation progress update
    - `completed`: Translation finished
    - `error`: An error occurred
    """
    await websocket.accept()

    session_id = f"{job_id}_{id(websocket)}"
    session = PreviewManager.create_session(session_id, websocket)

    logger.info(f"Preview session started: {session_id}")

    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "event": "connected",
            "session_id": session_id,
            "job_id": job_id,
        })

        # Keep connection alive and handle client messages
        while session.is_active:
            try:
                # Wait for client messages (ping, commands, etc.)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0  # 30 second timeout
                )

                message = json.loads(data)

                if message.get("action") == "ping":
                    await websocket.send_json({"event": "pong"})

                elif message.get("action") == "get_content":
                    # Send accumulated content
                    await websocket.send_json({
                        "event": "content",
                        "content": "\n\n".join(session.content),
                        "chunks": len(session.content),
                    })

            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({"event": "heartbeat"})

    except WebSocketDisconnect:
        logger.info(f"Preview session disconnected: {session_id}")

    except Exception as e:
        logger.error(f"Preview session error: {e}")
        try:
            await session.send_error(str(e))
        except Exception:
            pass

    finally:
        PreviewManager.remove_session(session_id)
        logger.info(f"Preview session ended: {session_id}")


@router.get("/sessions")
async def list_active_sessions():
    """List active preview sessions (for debugging)."""
    return {
        "count": len(_sessions),
        "sessions": [
            {
                "session_id": s.session_id,
                "is_active": s.is_active,
                "chunks_received": len(s.content),
            }
            for s in _sessions.values()
        ]
    }


# Integration hook for translation pipeline
async def notify_chunk_translated(
    job_id: str,
    chunk_index: int,
    original: str,
    translated: str,
    metadata: Dict = None
):
    """
    Called by translation pipeline when a chunk is translated.

    This broadcasts the chunk to all connected preview clients.
    """
    session = PreviewManager.get_session(job_id)
    if session:
        await session.send_chunk(chunk_index, translated, {
            "original": original[:100] + "..." if len(original) > 100 else original,
            **(metadata or {})
        })

    # Also broadcast to any session watching this job
    await PreviewManager.broadcast_chunk(job_id, chunk_index, translated, metadata)


async def notify_progress(job_id: str, progress: float, stage: str = "translating"):
    """Called by translation pipeline to update progress."""
    for session in _sessions.values():
        if session.session_id.startswith(job_id) and session.is_active:
            await session.send_progress(progress, stage)


async def notify_completed(job_id: str, outputs: Dict = None):
    """Called when translation is complete."""
    for session in _sessions.values():
        if session.session_id.startswith(job_id) and session.is_active:
            await session.send_complete(outputs)
