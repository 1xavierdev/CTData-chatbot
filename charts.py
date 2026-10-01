"""Charts for chat answers: when to draw one, and the data behind it.

A chart spec is plain JSON the Angular widget renders with Chart.js and export.py
turns into a PowerPoint chart or PDF table:

    {"type": "line" | "bar" | "doughnut", "title": str, "unit": str,
     "labels": [str], "series": [{"name": str, "values": [number | None]}], "source": url}

Numbers come from two places:
1. EdSight tables, which the scraper saves as structured "records". These are exact.
2. Any other page: the chat model extracts the numbers as JSON, and every value must
   appear in the retrieved text, so a chart can't show invented data.
Box plots need many values per group (e.g. every district), which the knowledge base
doesn't have, so the types are limited to line, bar and doughnut.
"""

from __future__ import annotations

import json
import re

import lmstudio
from kb import PAGES_FILE

EXPLICIT = re.compile(r"\b(chart|graph|plot|visuali[sz]e|visuali[sz]ation|image|picture|diagram|infographic|draw)\b", re.I)
COMPARE = re.compile(
    r"\b(compare|comparison|compared|versus|vs\.?|difference|trends?|over time|changed?|increase[ds]?|decrease[ds]?"
    r"|grow(th|n)?|decline[ds]?|by year|each year|per year|highest|lowest|rank(ing)?|var(y|ies|ied|iation)"
    r"|breakdown|broken down|distribution|share|by (race|ethnicity|age|gender|sex|income|town|county|region|group))\b", re.I)
# Only used with EdSight's structured tables: a question about a figure gets its trend chart.
FIGURE = re.compile(r"\b(rates?|percent(age)?|how many|numbers?|counts?|%)\b", re.I)
YEAR_LABEL = re.compile(r"^(19|20)\d\d(-\d\d)?$")
MAX_SERIES = 8

_tables: dict[str, dict] | None = None


def chart_intent(question: str) -> str | None:
    """"explicit" if the user asked for a chart/image, "compare" for comparisons and trends, else None."""
    if EXPLICIT.search(question):
        return "explicit"
    if COMPARE.search(question):
        return "compare"
    return None


def tables() -> dict[str, dict]:
    """EdSight pages with structured records, by URL: {"title": ..., "records": [...]}."""
    global _tables
    if _tables is None:
        pages = json.loads(PAGES_FILE.read_text()) if PAGES_FILE.exists() else []
        _tables = {p["url"]: {"title": p["title"], "records": p["records"]} for p in pages if p.get("records")}
    return _tables


def to_number(value) -> float | None:
    try:
        return float(str(value).replace(",", "").replace("%", "").strip())
    except ValueError:
        return None


def pick_type(labels: list[str], series: list[dict], unit: str) -> str:
    """Years -> line (trend), a single share-of-whole breakdown -> doughnut, otherwise bar."""
    if len(labels) >= 3 and all(YEAR_LABEL.match(label) for label in labels):
        return "line"
    values = [v for v in series[0]["values"] if v is not None] if len(series) == 1 else []
    if values and 2 <= len(values) <= 6 and "%" in unit and 95 <= sum(values) <= 105:
        return "doughnut"
    return "bar"


def records_chart(question: str, passages: list[dict], intent: str | None) -> dict | None:
    """Chart an EdSight table among the retrieved passages, if any."""
    retrieved = [p["url"] for p in passages if p["url"] in tables()]
    if not retrieved or not (intent or FIGURE.search(question)):
        return None
    # Pick the table whose title/rows/measures share the most words with the question
    # ("in-school vs out-of-school" -> Sanctions), preferring tables that were retrieved.
    words = {w.rstrip("s") for w in re.findall(r"[a-z]{3,}", question.lower())} - {"the", "and", "for", "how", "what"}

    def score(u: str) -> tuple[int, int]:
        # Row names are the most specific match, so they count double.
        t = tables()[u]
        rows = " ".join(f"{r['name']} {r['measure']}" for r in t["records"]).lower()
        matches = sum(2 * (w in rows) or (w in t["title"].lower()) for w in words)
        return matches + (u in retrieved), -(retrieved.index(u) if u in retrieved else 99)

    url = max(tables(), key=score)
    records = tables()[url]["records"]
    title = tables()[url]["title"].replace("EdSight: ", "")

    # One measure per chart: percentages/rates unless the question asks for counts.
    measures = list(dict.fromkeys(r["measure"] for r in records))
    wants_count = re.search(r"\b(how many|numbers? of|counts?)\b", question, re.I) and not re.search(r"percent|%|rate", question, re.I)
    percent = [m for m in measures if "%" in m or "rate" in m.lower()]
    counts = [m for m in measures if m not in percent]
    measure = (counts if wants_count and counts else percent or measures)[0]

    rows = [r for r in records if r["measure"] == measure and to_number(r["value"]) is not None]
    years = sorted({r["year"] for r in rows})
    names = list(dict.fromkeys(r["name"] for r in rows))
    # If the question names some rows (e.g. "math"), chart just those.
    asked = [n for n in names if words & {w.rstrip("s") for w in re.findall(r"[a-z]{3,}", n.lower().removeprefix("state of connecticut"))}]
    names = (asked or names)[:MAX_SERIES]
    series = []
    for name in names:
        by_year = {r["year"]: to_number(r["value"]) for r in rows if r["name"] == name}
        label = name.removeprefix("State of Connecticut, ").removeprefix("State of Connecticut") or "Connecticut"
        series.append({"name": label, "values": [by_year.get(y) for y in years]})
    if not years or not series:
        return None
    unit = "%" if "%" in measure or "rate" in measure.lower() else ""
    measure_label = measure.replace("%", "(%)").replace("¹", "").strip()
    return {"type": pick_type(years, series, unit), "title": f"{title}: {measure_label}" if measure_label else title,
            "unit": unit,
            "labels": years, "series": series, "source": url}


CHART_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "unit": {"type": "string"},
        "labels": {"type": "array", "items": {"type": "string"}},
        "series": {"type": "array", "items": {
            "type": "object",
            "properties": {"name": {"type": "string"}, "values": {"type": "array", "items": {"type": "number"}}},
            "required": ["name", "values"],
        }},
    },
    "required": ["title", "unit", "labels", "series"],
}

EXTRACT_PROMPT = """Extract numbers from the CONTEXT for a chart that answers the QUESTION.
- Copy numbers exactly as they appear in the CONTEXT. Never estimate, round or invent a number.
- labels are the categories or years; each series has one value per label.
- unit is "%" for percentages, otherwise a short unit such as "cases" or "people".
- If the CONTEXT has fewer than 2 comparable numbers for the question, return empty labels and series."""


NUMBER = re.compile(r"\d[\d,]*\.?\d*")


def stated_with(value: float, label: str, context: str) -> bool:
    """True if the context states this number together with its label, so "52% in 2021" can't be charted
    under 2019: a year label must be in the same sentence; a category label ("Hartford") within a few words."""
    is_year = bool(YEAR_LABEL.match(label))
    label_words = re.findall(r"[a-z]{4,}", label.lower()) or [label.lower()]
    for sentence in re.split(r"(?<=[.!?;])\s+|\n", context):
        for m in NUMBER.finditer(sentence):
            if to_number(m.group()) != value:
                continue
            if is_year and label in sentence:
                return True
            nearby = sentence[max(0, m.start() - 60):m.end() + 25].lower()
            if not is_year and any(w in nearby for w in label_words):
                return True
    return False


def validate(spec: dict, context: str) -> dict | None:
    """Keep a model-extracted chart only if it is well formed and every value appears in the context."""
    labels = [str(label).strip() for label in spec.get("labels", [])]
    series = [s for s in spec.get("series", []) if isinstance(s, dict) and s.get("values")]
    if len(labels) < 2 or not series:
        return None
    # Small models sometimes return one single-value series per label; that's really one series.
    if len(series) == len(labels) and all(len(s["values"]) == 1 for s in series):
        series = [{"name": str(spec.get("title") or "Value"), "values": [s["values"][0] for s in series]}]
    for s in series:
        values = [to_number(v) for v in s["values"]]
        if len(values) != len(labels) or any(v is None or not stated_with(v, label, context)
                                             for v, label in zip(values, labels)):
            return None
    all_values = [to_number(v) for s in series for v in s["values"]]
    if len(set(all_values)) < 2:  # a flat line of one repeated number is almost always a made-up fill
        return None
    series = [{"name": str(s.get("name") or "Value")[:60], "values": [to_number(v) for v in s["values"]]}
              for s in series[:MAX_SERIES]]
    unit = str(spec.get("unit") or "")[:20]
    if "%" in unit and any(v > 100 for s in series for v in s["values"]):
        unit = ""  # counts mislabeled as percentages
    return {"type": pick_type(labels, series, unit), "title": str(spec.get("title") or "")[:120],
            "unit": unit, "labels": labels, "series": series}


def model_chart(question: str, passages: list[dict]) -> dict | None:
    context = "\n\n".join(p["text"] for p in passages)
    reply = lmstudio.chat_json([
        {"role": "system", "content": EXTRACT_PROMPT},
        {"role": "user", "content": f"CONTEXT:\n{context}\n\nQUESTION: {question}"},
    ], CHART_SCHEMA)
    if not reply:
        return None
    spec = validate(reply, context)
    if spec:
        spec["source"] = passages[0]["url"]
    return spec


def build_chart(question: str, passages: list[dict], use_model: bool = True, wanted: bool = False) -> dict | None:
    """A chart for this question, or None. Charts are only attempted when the question asks for one,
    asks for a comparison or trend, asks for a figure that has a structured EdSight table, or `wanted`
    is set (the answer is going into a PDF or PowerPoint)."""
    intent = chart_intent(question) or ("explicit" if wanted else None)
    if chart := records_chart(question, passages, intent):
        return chart
    if intent and use_model:
        return model_chart(question, passages)
    return None
