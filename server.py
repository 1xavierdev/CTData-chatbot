"""Flask API for the CTData chatbot, and host for the built Angular UI.

    python server.py        # http://localhost:5000

During UI development run `npm start` in frontend/ instead; its dev server
proxies /api to this server (see frontend/proxy.conf.json).
"""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

import lmstudio
import rag
from kb import KnowledgeBase

UI_DIR = Path(__file__).parent / "frontend" / "dist" / "frontend" / "browser"

app = Flask(__name__)
kb = KnowledgeBase.load()


@app.get("/api/health")
def health():
    return jsonify({
        "chunks": len(kb.chunks),
        "search": "semantic" if kb.has_vectors else "keyword",
        "chat_model": lmstudio.chat_model(),
    })


@app.post("/api/chat")
def chat():
    body = request.get_json(silent=True) or {}
    question = str(body.get("message", "")).strip()
    if not question:
        return jsonify({"error": "message is required"}), 400
    return jsonify(rag.answer(kb, question[:1000], body.get("profile") or {}, body.get("history") or []))


@app.get("/", defaults={"path": ""})
@app.get("/<path:path>")
def ui(path: str):
    if not UI_DIR.exists():
        return "UI not built yet: run `npm run build` in frontend/ (or use `npm start` for dev).", 404
    if path and (UI_DIR / path).is_file():
        return send_from_directory(UI_DIR, path)
    return send_from_directory(UI_DIR, "index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
