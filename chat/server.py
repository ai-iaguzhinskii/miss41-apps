import json
import asyncio
import subprocess
import threading
import queue as thread_queue
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

LLAMA_URL = "http://100.64.0.4:8080/v1/chat/completions"
API_KEY   = "447fb367-493b-4c49-a0dc-b2ad6b03f69b"
MODEL     = "gemma-4-31b-jang-crack-Q8_0-00001-of-00009.gguf"


@app.get("/")
async def index():
    return FileResponse("index.html")


def stream_llama_thread(payload_dict, q: thread_queue.Queue):
    """Синхронно стримим llama в отдельном треде, результаты кладём в queue."""
    payload = json.dumps(payload_dict)
    cmd = [
        "curl", "-sN", "--max-time", "300",
        LLAMA_URL,
        "-H", f"Authorization: Bearer {API_KEY}",
        "-H", "Content-Type: application/json",
        "-d", payload,
    ]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        for line_bytes in proc.stdout:
            line = line_bytes.decode("utf-8", errors="replace").strip()
            if not line.startswith("data:"):
                continue
            part = line[5:].strip()
            if not part or part == "[DONE]":
                continue
            try:
                d = json.loads(part)
                delta = d["choices"][0].get("delta", {})
                rc = delta.get("reasoning_content") or delta.get("thinking")
                if rc:
                    q.put(("thinking", rc))
                text = delta.get("content") or ""
                if text:
                    q.put(("token", text))
            except Exception:
                continue
        proc.wait()
    except Exception as e:
        q.put(("error", str(e)))
    finally:
        q.put(("done", ""))


@app.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = json.loads(await websocket.receive_text())
            messages    = data.get("messages", [])
            max_tokens  = data.get("max_tokens", 3000)
            temperature = float(data.get("temperature", 0.7))

            payload = {
                "model": MODEL,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": True,
            }

            q: thread_queue.Queue = thread_queue.Queue()

            # запускаем стрим в отдельном треде
            t = threading.Thread(target=stream_llama_thread, args=(payload, q), daemon=True)
            t.start()

            # дренируем очередь асинхронно
            loop = asyncio.get_event_loop()
            while True:
                try:
                    # неблокирующий get через executor
                    kind, text = await loop.run_in_executor(None, lambda: q.get(timeout=0.1))
                    if kind == "done":
                        await websocket.send_text(json.dumps({"type": "done"}))
                        break
                    elif kind == "error":
                        await websocket.send_text(json.dumps({"type": "error", "text": text}))
                        break
                    else:
                        await websocket.send_text(json.dumps({"type": kind, "text": text}))
                except thread_queue.Empty:
                    if not t.is_alive():
                        # тред завершился, дочитываем остаток
                        while True:
                            try:
                                kind, text = q.get_nowait()
                                if kind == "done":
                                    await websocket.send_text(json.dumps({"type": "done"}))
                                    break
                                await websocket.send_text(json.dumps({"type": kind, "text": text}))
                            except thread_queue.Empty:
                                await websocket.send_text(json.dumps({"type": "done"}))
                                break
                        break
                    continue

    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8766)
