"""Flask API for the CTData chatbot, and host for the built Angular UI.

    python server.py        # http://localhost:5000

During UI development run `npm start` in frontend/ instead; its dev server
proxies /api to this server (see frontend/proxy.conf.json).
"""

from __future__ import annotations

import io
import os
import re
from pathlib import Path

from flask import Flask, jsonify, request, send_file, send_from_directory

import export
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


EXPORTS = {
    "pptx": (export.build_pptx, "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
    "pdf": (export.build_pdf, "application/pdf"),
}


@app.post("/api/export")
def export_answer():
    """Download a chat answer as a PowerPoint deck or PDF (body: format + the doc described in export.py)."""
    body = request.get_json(silent=True) or {}
    fmt = body.get("format")
    if fmt not in EXPORTS or not str(body.get("answer", "")).strip():
        return jsonify({"error": "format must be pptx or pdf, and answer is required"}), 400
    build, mimetype = EXPORTS[fmt]
    doc = {"title": str(body.get("title", ""))[:200], "answer": str(body["answer"])[:20000],
           "sources": [s for s in body.get("sources") or [] if isinstance(s, dict) and s.get("url")][:10],
           "chart": body.get("chart") if isinstance(body.get("chart"), dict) else None,
           "chart_png": body.get("chart_png") if isinstance(body.get("chart_png"), str) else None}
    name = re.sub(r"[^a-z0-9]+", "-", doc["title"].lower()).strip("-")[:60] or "ctdata-answer"
    return send_file(io.BytesIO(build(doc)), mimetype=mimetype, as_attachment=True, download_name=f"{name}.{fmt}")


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
