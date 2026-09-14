"""Backend FastAPI de Jarvis - expose la conversation via WebSocket pour l'interface desktop."""
import asyncio
import queue
import threading

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq

from jarvis.config import GROQ_API_KEY, MODEL, TEMPERATURE
from jarvis.conversation import Conversation
from jarvis.personality import SYSTEM_PROMPT
from jarvis.tools import registry  # noqa: F401 - declenche le chargement des outils
import jarvis.tools  # noqa: F401 - charge tous les modules d'outils

app = FastAPI(title="Jarvis")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_client = Groq(api_key=GROQ_API_KEY)
_conversation = Conversation(_client, SYSTEM_PROMPT, MODEL, TEMPERATURE)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/tools")
def tools():
    return {"tools": registry.list_tools()}


@app.get("/api/stats")
def stats():
    return {
        "messages": _conversation.message_count,
        "turns": _conversation.turn_count,
        "compactions": _conversation.compaction_count,
    }


@app.post("/api/reset")
def reset():
    _conversation.reset()
    return {"status": "ok"}


def _stream_worker(user_message: str, q: "queue.Queue"):
    try:
        for event in _conversation.send_stream(user_message):
            q.put(event)
        if _conversation.should_compact():
            _conversation.compact()
            q.put({"type": "compacted"})
    except Exception as e:
        q.put({"type": "error", "message": str(e)})
    finally:
        q.put(None)


@app.websocket("/ws/chat")
async def chat(websocket: WebSocket):
    await websocket.accept()
    loop = asyncio.get_event_loop()

    try:
        while True:
            data = await websocket.receive_json()
            user_message = (data.get("message") or "").strip()
            if not user_message:
                continue

            q: "queue.Queue" = queue.Queue()
            threading.Thread(target=_stream_worker, args=(user_message, q), daemon=True).start()

            while True:
                event = await loop.run_in_executor(None, q.get)
                if event is None:
                    break
                await websocket.send_json(event)

    except WebSocketDisconnect:
        pass


def main():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8756, log_level="info")


if __name__ == "__main__":
    main()
