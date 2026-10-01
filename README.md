# CTData-chatbot

An AI assistant for [ctdata.org](https://www.ctdata.org), built for a hackathon demo.

- An **Angular** mock of the CTData home page has a chat button in the bottom-right corner. It opens a dialog that covers 80% of the screen.
- Before the first question, the bot asks 4 quick questions: **profession, age group, education level and data experience**. Every answer is then tailored to that person (reading level, vocabulary, examples).
- Answers come from a **knowledge base scraped from [ctdata.org/data-by-topic](https://www.ctdata.org/data-by-topic)**: all 11 topic pages (business, children & families, civic engagement, criminal justice, demographics, education, Hartford, health, housing, migration, town data), the CTData articles they link to, and the statewide trend tables of the linked EdSight education datasets (about 130 pages). Pages are embedded and searched locally (RAG), and replies are written by a model running in **LM Studio**.
- **Charts:** comparisons, trends and explicit requests ("chart…", "graph…", "compare…", "how has X changed") get an interactive chart under the answer: hover for values, click the legend to hide a series, switch line/bar, view the numbers as a table, or download a PNG. The chart type follows the data: line for years, bar for categories, doughnut for shares of a whole. Box plots would need many values per group (e.g. every district), which the knowledge base doesn't have.
  - EdSight numbers are charted straight from the scraped tables (exact).
  - Other numbers are extracted by the model as JSON and only charted if every value is stated in the source text *next to its label*. Otherwise there is no chart, and the answer says so if a chart was asked for.
- **PDF / PowerPoint:** every answer has "Save as PDF / PowerPoint" buttons, and typing "make a ppt of this", "create a pdf about chronic absenteeism" etc. downloads one. The deck has a native, editable chart; the PDF has the chart as shown in the browser plus a table of the numbers.
- Questions the knowledge base can't answer (weather, housing, jobs, ...) get a clear "not in my knowledge base" reply that points to ctdata.org and the Data Helpline, instead of a made-up answer.
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

On an 8 GB Mac use `Qwen3 4B` (or smaller) with a context length of about 4096: an 8B model swaps and can take minutes per answer, so every reply times out into offline mode.

The chat model is auto-detected. To pick one explicitly, set `CHAT_MODEL=<model id>` (and `EMBED_MODEL`, `LMSTUDIO_URL` if needed).

> The LLM does not do the scraping. A normal crawler (`scraper.py`) is faster and more reliable. LM Studio is used for embeddings (search) and for writing answers.

## 2. Build the knowledge base

```bash
pip install -r requirements.txt
python scraper.py        # crawls ctdata.org/data-by-topic (2 link hops) + EdSight tables -> data/pages.json
python kb.py             # chunks + embeds with LM Studio -> data/kb.json
```

Re-run `python kb.py` after starting LM Studio to switch from keyword search to semantic search.

## 3. Run the app

**Demo mode (one server):**

```bash
cd frontend && npm install && npm run build && cd ..
python server.py         # http://localhost:5000
```

On macOS, port 5000 is often taken by AirPlay Receiver: use `PORT=5050 python server.py`.

**UI development (hot reload):** run `python server.py` in one terminal, and `cd frontend && npm start` in another. Then open http://localhost:4200 (`/api` is proxied to Flask).

## Tests

```bash
python -m unittest discover -s tests -v
cd frontend && npx ng test --watch=false
```

## Project layout

| Path | What it does |
| --- | --- |
| `scraper.py` | Crawls a ctdata.org section and linked blog posts, keeps dataset links, and fetches the statewide tables behind linked EdSight datasets |
| `kb.py` | Chunking, LM Studio embeddings, semantic + BM25 search |
| `rag.py` | Persona rules (age / education / profession / data experience), prompt building, and "not in the knowledge base" detection |
| `charts.py` | Decides when to chart, builds chart specs from EdSight tables or model-extracted (and validated) numbers |
| `export.py` | Builds the PowerPoint (python-pptx) and PDF (fpdf2) versions of an answer |
| `lmstudio.py` | Small client for LM Studio's OpenAI-compatible API |
| `server.py` | Flask API (`/api/chat`, `/api/export`, `/api/health`); also serves the built Angular app |
| `frontend/src/app/chatbot/` | Chat widget: launcher, 80% dialog, onboarding, chat, sources, charts (`chart-view.ts`, Chart.js), PDF/PowerPoint export |
| `frontend/src/app/home/`, `layout/` | Mock CTData home page |
| `app.py` | Original rule-based CLI prototype |
| `scrape_ctdata.py` | Alternate corpus builder. Layer 1 scrapes ctdata.org topic pages (education); Layer 2 pulls dataset metadata + CSVs from the data.ctdata.org CKAN API (portal temporarily down, so re-run when it's back) |
| `ctdata_corpus/ctdata_corpus.jsonl` | Output of `scrape_ctdata.py`: one JSON record per topic page (`source`, `topic`, `url`, `text`, `dataset_links`) |

## Key findings about CTData

- **CTData.org** is the brochure site; actual datasets live on **data.ctdata.org** (CKAN portal, currently down) and **EdSight** (https://public-edsight.ct.gov, the CT Dept. of Education portal; all education dataset links point there).
- Education datasets share consistent filter dimensions: race/ethnicity, gender, English Learner status, free/reduced meal eligibility, special education status, homelessness, foster care. That makes a clean schema for natural-language-to-query.
- CTData already runs a human data "helpline" (~200 requests/yr). The LLM essentially automates it, which is good pitch framing.
- Be polite when scraping: both scrapers use a delay between requests and a descriptive User-Agent.

## Changing what gets scraped

- Default: `python scraper.py` starts at `/data-by-topic` and follows ctdata.org links 2 hops deep (topic pages, then the articles they link to). PDFs and spreadsheets are kept as links, not crawled.
- One section only: `python scraper.py --start /education --depth 1`
- Refresh only the EdSight tables (and their chart data) in the saved pages: `python scraper.py --edsight-only`
- After scraping, rebuild with `python kb.py`. If you change the scope, update `BASE_PROMPT` and `NOT_FOUND` (`rag.py`) and the sidebar "Answering from" note.
