# CTData.org Conversational AI — AI Hackathon

Making [CTData.org](https://www.ctdata.org) conversational: an LLM layer that lets users
ask plain-language questions and pull up Connecticut public data (starting with **education**).

## What's in this repo

| File / folder | What it is |
|---|---|
| `scrape_ctdata.py` | Scraper that builds the LLM corpus. Layer 1: scrapes www.ctdata.org topic pages (currently scoped to education). Layer 2: pulls full dataset metadata + CSVs from the data.ctdata.org CKAN API (portal temporarily down — re-run when it's back). |
| `ctdata_corpus/ctdata_corpus.jsonl` | Scraped corpus — one JSON record per topic page (text + dataset links). RAG-ready. |

## Key findings so far

- **CTData.org** is the brochure site; actual datasets live on **data.ctdata.org** (CKAN portal, currently down) and **EdSight** (public-edsight.ct.gov, the CT Dept. of Education portal — all education dataset links point there).
- Education datasets share consistent filter dimensions: race/ethnicity, gender, English Learner status, free/reduced meal eligibility, special education status, homelessness, foster care — a clean schema for natural-language-to-query.
- CTData already runs a human data "helpline" (~200 requests/yr) — the LLM essentially automates it. Good pitch framing.

## Usage

```bash
python scrape_ctdata.py   # rebuild the corpus (Layer 1 works now; Layer 2 needs the CKAN portal up)
```

Output: `ctdata_corpus/ctdata_corpus.jsonl` — each line is a JSON record
(`source`, `topic`, `url`, `text`, `dataset_links`), ready for embedding / RAG.

## Roadmap

- [x] Scan CTData.org site structure
- [x] Scraper for education topic page → JSONL corpus
- [ ] Pull one real education dataset (e.g., chronic absenteeism) from EdSight
- [ ] Minimal RAG chatbot: answer questions from the corpus
- [ ] Natural-language-to-query over the dataset (function calling / text-to-SQL)
- [ ] Demo UI for the hackathon

## Notes

- Be polite when scraping: the script includes a 1s delay between requests and a descriptive User-Agent.
- EdSight portal: https://public-edsight.ct.gov
