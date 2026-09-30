# CTData-chatbot

An AI assistant for [ctdata.org](https://www.ctdata.org), built for a hackathon demo.

- An **Angular** mock of the CTData home page has a chat button in the bottom-right corner. It opens a dialog that covers 80% of the screen.
- Before the first question, the bot asks 4 quick questions: **profession, age group, education level and data experience**. Every answer is then tailored to that person (reading level, vocabulary, examples).
- Answers come from a **knowledge base scraped from [ctdata.org/education](https://www.ctdata.org/education)** and the blog posts it links to. Pages are embedded and searched locally (RAG), and replies are written by a model running in **LM Studio**.
- If LM Studio isn't running, the bot falls back to keyword search and shows matching datasets and links, so the demo never breaks.

```
Browser (Angular)  ──/api/chat──▶  Flask (server.py)
                                      │  kb.py: search chunks (embeddings or BM25)
                                      │  rag.py: build persona-aware prompt
                                      ▼
                                 LM Studio (localhost:1234, OpenAI-compatible)
```

## 1. Set up LM Studio

1. Install [LM Studio](https://lmstudio.ai) and download two models:
   - **Chat model**: `Qwen3 8B` (recommended; good instruction following, runs on ~8 GB RAM/VRAM at Q4_K_M).
     Alternatives: `Llama 3.1 8B Instruct`, `Gemma 3 12B` (better answers, needs more memory) or `Qwen3 4B` / `Gemma 3 4B` for small laptops.
   - **Embedding model**: `nomic-embed-text-v1.5` (bundled with LM Studio).
2. In the **Developer** tab, load both models and click **Start Server** (port 1234).

The chat model is auto-detected. To pick one explicitly, set `CHAT_MODEL=<model id>` (and `EMBED_MODEL`, `LMSTUDIO_URL` if needed).

> The LLM does not do the scraping. A normal crawler (`scraper.py`) is faster and more reliable. LM Studio is used for embeddings (search) and for writing answers.

## 2. Build the knowledge base

```bash
pip install -r requirements.txt
python scraper.py        # crawls ctdata.org/education -> data/pages.json
python kb.py             # chunks + embeds with LM Studio -> data/kb.json
```

Re-run `python kb.py` after starting LM Studio to switch from keyword search to semantic search.

## 3. Run the app

**Demo mode (one server):**

```bash
cd frontend && npm install && npm run build && cd ..
python server.py         # http://localhost:5000
```

**UI development (hot reload):** run `python server.py` in one terminal, and `cd frontend && npm start` in another. Then open http://localhost:4200 (`/api` is proxied to Flask).

## Tests

```bash
python -m unittest discover -s tests -v
cd frontend && npx ng test --watch=false
```

## Project layout

| Path | What it does |
| --- | --- |
| `scraper.py` | Crawls a ctdata.org section and linked blog posts, and keeps dataset links |
| `kb.py` | Chunking, LM Studio embeddings, semantic + BM25 search |
| `rag.py` | Persona rules (age / education / profession / data experience) and prompt building |
| `lmstudio.py` | Small client for LM Studio's OpenAI-compatible API |
| `server.py` | Flask API (`/api/chat`, `/api/health`); also serves the built Angular app |
| `frontend/src/app/chatbot/` | Chat widget: launcher, 80% dialog, onboarding, chat, sources |
| `frontend/src/app/home/`, `layout/` | Mock CTData home page |
| `app.py` | Original rule-based CLI prototype |

## Expanding beyond Education

1. Crawl more sections: `python scraper.py --start /education --start /census --start /data-by-topic --max-pages 150`
2. Rebuild: `python kb.py`
3. Update the scope line in `BASE_PROMPT` (`rag.py`), `SUGGESTED_QUESTIONS` (`chat.models.ts`) and the sidebar "Currently answering from" note.
