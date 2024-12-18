import asyncio
import json
import logging
import time
from fastapi import (
    BackgroundTasks,
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid
import random

logger = logging.getLogger(__name__)

app = FastAPI()


BOT_USER_ID = "bot_user"

# In-memory data structure:
# chats = {
#   chat_id: {
#     "participants": [user_ids],
#     "messages": [ { "id", "user_id", "type", "content", "timestamp" }, ... ],
#     "read_receipts": { user_id: last_read_msg_id },
#     "presence": { user_id: {"status": "online"/"offline"/"typing", "last_seen": optional_datetime} }
#   }
# }
chats = {}
chat_connections = {}  # { chat_id: [WebSocket, WebSocket, ...] }


class CreateChatRequest(BaseModel):
    participants: List[str]


class Message(BaseModel):
    id: str
    user_id: str
    type: str  # "text" | "image" | "audio"
    content: str
    timestamp: str


class SendMessageRequest(BaseModel):
    user_id: str
    type: str = Field(..., regex="^(text|image|audio)$")
    content: str


class PresenceUpdateRequest(BaseModel):
    user_id: str
    status: str = Field(..., regex="^(online|offline|typing)$")


class MarkReadRequest(BaseModel):
    user_id: str


@app.post("/chats")
def create_chat(req: CreateChatRequest):
    chat_id = str(uuid.uuid4())
    participants = req.participants + [BOT_USER_ID]
    chats[chat_id] = {
        "participants": participants,
        "messages": [],
        "read_receipts": {p: None for p in req.participants},
        "presence": {
            p: {"status": "offline", "last_seen": datetime.utcnow().isoformat()}
            for p in participants
        },
    }
    return {"chat_id": chat_id, "participants": req.participants}


@app.get("/chats")
def list_chats():
    return [
        {"chat_id": cid, "participants": c["participants"]} for cid, c in chats.items()
    ]


@app.get("/chats/{chat_id}/messages")
def get_messages(chat_id: str):
    if chat_id not in chats:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chats[chat_id]["messages"]


async def _handle_bot_response_and_presence(
    chat_id: str,
):
    # Predefined bot responses: some texts, images, audios
    predefined_responses = [
        {"type": "text", "content": "Interesting..."},
        {"type": "text", "content": "Tell me more!"},
        {"type": "text", "content": "Got it!"},
        {"type": "image", "content": "http://example.com/image.png"},
        {"type": "audio", "content": "http://example.com/audio.mp3"},
    ]

    await asyncio.sleep(random.randint(2, 4))
    await _update_presence(chat_id, BOT_USER_ID, "online")

    await asyncio.sleep(random.randint(2, 4))
    await _mark_chat_read(chat_id, BOT_USER_ID)

    await asyncio.sleep(random.randint(2, 4))
    await _update_presence(chat_id, BOT_USER_ID, "typing")

    num_responses = random.randint(1, 3)
    for _ in range(num_responses):
        logger.info(f"Bot is responding in chat {chat_id}")
        resp = random.choice(predefined_responses)
        await _send_message(chat_id, BOT_USER_ID, resp["type"], resp["content"])

        await asyncio.sleep(random.randint(2, 4))

    await _update_presence(chat_id, BOT_USER_ID, "offline")


async def _send_message(chat_id, user_id: str, type: str, content: str):
    msg_id = str(uuid.uuid4())
    message = {
        "id": msg_id,
        "user_id": user_id,
        "type": type,
        "content": content,
        "timestamp": datetime.utcnow().isoformat(),
    }
    chats[chat_id]["messages"].append(message)

    await broadcast_to_chat(
        chat_id,
        "message_received",
        message,
    )


@app.post("/chats/{chat_id}/messages")
async def send_message(
    chat_id: str, req: SendMessageRequest, background_tasks: BackgroundTasks
):
    if chat_id not in chats:
        raise HTTPException(status_code=404, detail="Chat not found")
    if req.user_id not in chats[chat_id]["participants"]:
        raise HTTPException(
            status_code=403, detail="User not a participant in this chat"
        )

    await _send_message(chat_id, req.user_id, req.type, req.content)

    background_tasks.add_task(_handle_bot_response_and_presence, chat_id)

    return {"status": "message_sent"}


@app.post("/chats/{chat_id}/presence")
async def update_presence(chat_id: str, req: PresenceUpdateRequest):
    if chat_id not in chats:
        raise HTTPException(status_code=404, detail="Chat not found")
    if req.user_id not in chats[chat_id]["participants"]:
        raise HTTPException(
            status_code=403, detail="User not a participant in this chat"
        )

    await _update_presence(chat_id, req.user_id, req.status)

    return {"chat_id": chat_id, "user_id": req.user_id, "status": req.status}


async def _update_presence(chat_id, user_id, status):
    logger.info(f"Updating presence for {user_id} in chat {chat_id} to {status}")
    presence = chats[chat_id]["presence"]
    if status == "offline":
        presence[user_id] = {
            "status": "offline",
            "last_seen": datetime.utcnow().isoformat(),
        }
    else:
        presence[user_id] = {
            "status": status,
            "last_seen": presence[user_id]["last_seen"],
        }

    await broadcast_to_chat(
        chat_id,
        "presence_updated",
        {
            "status": status,
            "user_id": user_id,
            "last_seen": presence[user_id]["last_seen"],
        },
    )


@app.get("/chats/{chat_id}/presence")
def get_chat_presence(chat_id: str):
    if chat_id not in chats:
        raise HTTPException(status_code=404, detail="Chat not found")

    participants = chats[chat_id]["participants"]
    presence_info = chats[chat_id]["presence"]
    data = []
    for p in participants:
        data.append(
            {
                "user_id": p,
                "status": presence_info[p]["status"],
                "last_seen": presence_info[p]["last_seen"],
            }
        )
    return data


@app.post("/chats/{chat_id}/read")
async def mark_chat_read(chat_id: str, req: MarkReadRequest):
    if chat_id not in chats:
        raise HTTPException(status_code=404, detail="Chat not found")
    if req.user_id not in chats[chat_id]["participants"]:
        raise HTTPException(
            status_code=403, detail="User not a participant in this chat"
        )

    return await _mark_chat_read(chat_id, req)


async def _mark_chat_read(chat_id, user_id):
    messages = chats[chat_id]["messages"]
    last_msg_id = messages[-1]["id"] if messages else None
    chats[chat_id]["read_receipts"][user_id] = last_msg_id

    resp = {
        "chat_id": chat_id,
        "user_id": user_id,
        "last_read_message_id": last_msg_id,
    }

    await broadcast_to_chat(
        chat_id,
        "chat_read",
        resp,
    )
    return resp


@app.get("/chats/{chat_id}/read")
def get_chat_read(chat_id: str):
    if chat_id not in chats:
        raise HTTPException(status_code=404, detail="Chat not found")

    return {
        "chat_id": chat_id,
        "read_receipts": chats[chat_id]["read_receipts"],
    }


@app.websocket("/ws/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: str):
    await websocket.accept()

    if chat_id not in chat_connections:
        chat_connections[chat_id] = []
    chat_connections[chat_id].append(websocket)

    try:
        while True:
            # Optionally read messages from client if needed
            # message = await websocket.receive_text()
            # Handle incoming messages if your scenario requires it
            await websocket.receive_text()  # If not needed, you can omit this line
    except WebSocketDisconnect:
        chat_connections[chat_id].remove(websocket)
        if not chat_connections[chat_id]:
            del chat_connections[chat_id]


async def broadcast_to_chat(chat_id: str, event_type: str, payload: dict):
    """Send a JSON-serialized event to all WebSocket connections for the chat."""
    if chat_id in chat_connections:
        message = json.dumps({"event": event_type, "data": payload})
        to_remove = []
        for ws in chat_connections[chat_id]:
            try:
                await ws.send_text(message)
            except Exception as e:
                # Log the error and mark the WebSocket for removal
                print(f"Error sending message to client: {e}")
                to_remove.append(ws)
        # Remove broken connections
        for ws in to_remove:
            chat_connections[chat_id].remove(ws)
        if not chat_connections[chat_id]:
            del chat_connections[chat_id]
