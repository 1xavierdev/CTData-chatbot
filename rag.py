"""Retrieval-augmented answers, tailored to who is asking."""

from __future__ import annotations

import re

import charts
import lmstudio
from kb import KnowledgeBase, tokenize

# The onboarding answers the widget collects. Keys match the Angular ChatProfile.
AGE_STYLE = {
    "Under 13": "The reader is a child. Use very simple words, short sentences, and a friendly tone. Compare numbers to things like classrooms or school buses.",
    "13-17": "The reader is a teenager. Keep it clear and engaging; relate data to school and everyday life.",
    "18-24": "The reader is a young adult. Be direct and practical.",
    "25-44": "The reader is an adult. Be clear and concise.",
    "45-64": "The reader is an adult. Be clear and concise.",
    "65+": "The reader is an older adult. Be clear and patient; avoid slang and unexplained acronyms.",
}

EDUCATION_STYLE = {
    "Middle school or below": "Aim for about a 5th-grade reading level. Explain every term like 'rate' or 'percent'.",
    "High school": "Aim for about an 8th-grade reading level. Briefly explain terms like 'median' or 'dataset'.",
    "Some college / Associate": "Aim for a general-audience reading level; define technical terms once.",
    "Bachelor's degree": "Use a professional reading level; define specialized statistical terms.",
    "Master's / Doctorate": "You can use technical vocabulary (methodology, sampling, margins of error) without defining it.",
}

FAMILIARITY_STYLE = {
    "New to data": "They are new to working with data: explain what a dataset is and how to read it, step by step.",
    "Some experience": "They have some experience with data: skip the basics but explain how to find and filter the data.",
    "Data expert": "They are comfortable with data: focus on sources, breakdowns available, coverage years and caveats.",
}

PROFESSION_HINTS = {
    "Student": "Give examples useful for a school project or assignment.",
    "Teacher / Educator": "Relate the data to classrooms, schools and districts; suggest how it could be used in lessons.",
    "Parent": "Relate the data to what it means for their child and local schools.",
    "Researcher / Analyst": "Mention data sources, available breakdowns and limitations.",
    "Policymaker / Government": "Highlight policy implications and comparisons across towns or groups.",
    "Journalist": "Point out newsworthy angles and the original source to cite.",
    "Nonprofit / Community": "Focus on how the data can support grant writing, programs and community needs.",
}

# Shown whenever a question isn't covered by the knowledge base.
NOT_FOUND = (
    "Sorry, I don't have information about that in my knowledge base. I answer questions from CTData's "
    "**Data by Topic** pages: business & economy, children & families, civic engagement, criminal justice, "
    "demographics & population, education, Hartford, health, housing, migration and town data, plus the "
    "CTData articles they link to.\n\n"
    "For anything else, browse https://www.ctdata.org/data-by-topic or ask the CTData Data Helpline: "
    "https://www.ctdata.org/datahelpline"
)
NOT_FOUND_MARKER = "NOT_IN_KB"

# Retrieval scores below this are never about the knowledge base (greetings, recipes, sports...).
MIN_SCORE = 0.60
# Sources scoring more than this below the best match are left out of the answer's source list.
SOURCE_MARGIN = 0.06
# Without the LLM to double-check, only answer confident matches.
MIN_OFFLINE_SCORE = 0.65
# Question words that say nothing about the topic, so they don't count toward keyword coverage.
GENERIC_TERMS = set(
    "find get see show list give know look like many much did were was happened latest recent current "
    "information info statistics stats number percent percentage rate rates result results trend trends "
    "last year years "
    # Asking for a chart or a file says nothing about the topic either.
    "chart charts graph graphs plot visualize visualise visualization image picture diagram infographic draw "
    "create make generate export download file ppt pptx powerpoint slide slides deck presentation pdf "
    "compare comparison versus vs difference please this that above previous answer".split()
)
EXPORT_FORMATS = [("pptx", re.compile(r"\b(pptx?|power ?point|slides?|slide deck|deck|presentation)\b", re.I)),
                  ("pdf", re.compile(r"\bpdf\b", re.I))]
EXPORT_LABELS = {"pptx": "PowerPoint", "pdf": "PDF"}


# "show me a chart of X", "create a pdf about X", "X as a chart" -> "X": the request wording confuses
# retrieval and the model (which then apologizes that it can't draw), so only the topic is sent on.
_OUTPUTS = r"(?:chart|graph|plot|image|picture|diagram|infographic|visuali[sz]ation|pdf|pptx?|power ?point|slides?|deck|presentation)s?"
_LEADING_REQUEST = re.compile(
    r"^\s*(?:(?:please|can you|could you|would you)\s+)*"
    r"(?:(?:(?:show|draw|make|create|generate|give|build|export|download|turn|put|plot|graph|chart|visuali[sz]e)\s+(?:me\s+|us\s+)?)?"
    r"(?:(?:an?|the|this|that|some)\s+)?" + _OUTPUTS + r"\s+(?:(?:of|about|on|for|showing|comparing|with)\s+)?"
    r"|(?:plot|graph|chart|visuali[sz]e|draw)\s+)", re.I)
_TRAILING_REQUEST = re.compile(r"\s+(?:as|in|into|on|with)\s+(?:an?\s+|the\s+)?" + _OUTPUTS + r"\s*[?.!]*$", re.I)


def topic_question(question: str) -> str:
    """The question without "make a chart / pdf" wording; unchanged if nothing would be left."""
    topic = _TRAILING_REQUEST.sub("", _LEADING_REQUEST.sub("", question, count=1)).strip()
    has_topic = any(t not in GENERIC_TERMS for t in tokenize(topic))
    return topic[:1].upper() + topic[1:] if topic != question.strip() and has_topic else question


def export_format(question: str) -> str | None:
    """"pptx" or "pdf" when the user asks for the answer as a file."""
    return next((fmt for fmt, pattern in EXPORT_FORMATS if pattern.search(question)), None)

BASE_PROMPT = """You are the CTData Assistant for the Connecticut Data Collaborative (ctdata.org).
You answer questions about Connecticut using CTData's Data by Topic pages (business, children & families, civic
engagement, criminal justice, demographics, education, Hartford, health, housing, migration, town data) and the
CTData articles linked from them.

Rules:
- Answer ONLY from the CONTEXT below.
- If the CONTEXT has nothing on the question's topic (e.g. weather, sports, recipes, or any subject the CONTEXT doesn't mention), reply with exactly {marker} and nothing else. Don't stretch loosely related figures to fit: school discipline incidents are not crime rates, national figures are not Connecticut figures.
- If the CONTEXT covers the topic but not the exact detail asked (e.g. one district or one school), say which figures you do have, and link the dataset page where they can look it up.
- Never invent numbers. Quote figures exactly as they appear in the context.
- If no year is asked for, give the most recent year in the context first, then the trend.
- When you mention a dataset or article, include its link from the context.
- Keep answers under about 180 words unless the user asks for more. Use short paragraphs or bullet points.
- The app draws charts and creates PDF and PowerPoint files from your answer by itself. Never say you can't make charts, images or files, and don't draw text charts or tables of your own: just answer in words.

About the person you are talking to:
{audience}
"""


def audience_instructions(profile: dict) -> str:
    profile = profile or {}
    lines = []
    if profession := profile.get("profession"):
        lines.append(f"- Profession: {profession}. {PROFESSION_HINTS.get(profession, 'Use examples relevant to their work.')}")
    if age := profile.get("age"):
        lines.append(f"- Age group: {age}. {AGE_STYLE.get(age, '')}")
    if education := profile.get("education"):
        lines.append(f"- Education: {education}. {EDUCATION_STYLE.get(education, '')}")
    if familiarity := profile.get("familiarity"):
        lines.append(f"- Data experience: {familiarity}. {FAMILIARITY_STYLE.get(familiarity, '')}")
    return "\n".join(lines) or "- Unknown. Write for a general audience."


def build_messages(question: str, profile: dict, history: list[dict], passages: list[dict]) -> list[dict]:
    context = "\n\n".join(f"[{i + 1}] {p['title']} ({p['url']})\n{p['text']}" for i, p in enumerate(passages))
    system = BASE_PROMPT.format(audience=audience_instructions(profile), marker=NOT_FOUND_MARKER)
    messages = [{"role": "system", "content": system}]
    # Last few turns so follow-ups like "what about by gender?" make sense.
    for turn in (history or [])[-6:]:
        if turn.get("role") in {"user", "assistant"} and turn.get("content"):
            messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": (
        f"CONTEXT:\n{context or '(no matching content)'}\n\nQUESTION: {question}\n\n"
        f"(If the CONTEXT doesn't cover this question, reply only {NOT_FOUND_MARKER}.)"
    )})
    return messages


def topic_coverage(query: str, passages: list[dict]) -> float:
    """Share of the question's topic words (by stem) that appear in the retrieved passages."""
    terms = {t for t in tokenize(query) if t not in GENERIC_TERMS}
    if not terms:
        return 0.0
    words = set(tokenize(" ".join(p["title"] + " " + p["text"] for p in passages)))
    # Match on a 5-letter stem ("suspended" ~ "suspension"); short words like "hi" must match exactly.
    return sum(any(w.startswith(t[:5]) for w in words) if len(t) >= 5 else t in words for t in terms) / len(terms)


def offline_answer(question: str, passages: list[dict]) -> str:
    """Used when LM Studio isn't running: show the best matching passages as-is."""
    if not passages:
        return NOT_FOUND
    # Prefer direct dataset links whose label matches the question.
    terms = set(tokenize(question))
    link_lines = [
        line for p in passages if "#links" in p.get("id", "")
        for line in p["text"].splitlines()[1:] if terms & set(tokenize(line.split(": http")[0]))
    ]
    if link_lines:
        return "Here are the matching datasets on CTData:\n\n" + "\n".join(link_lines[:5])
    best = passages[0]
    snippet = best["text"][:500].rsplit("\n", 1)[0] if len(best["text"]) > 500 else best["text"]
    return f"Here's what I found on **{best['title']}**:\n\n{snippet}"


def answer(kb: KnowledgeBase, question: str, profile: dict, history: list[dict] | None = None) -> dict:
    export = export_format(question)
    if export and not {t for t in tokenize(question) if t not in GENERIC_TERMS}:
        # "make a ppt of this": the widget exports the previous answer it already has on screen.
        return {"answer": f"Here's your {EXPORT_LABELS[export]} of the previous answer.", "sources": [],
                "mode": "export", "export": export, "export_previous": True}

    result = search_and_answer(kb, question, profile, history, for_export=bool(export))
    if export and result["mode"] != "not_found":
        result["export"] = export
    return result


def search_and_answer(kb: KnowledgeBase, question: str, profile: dict, history: list[dict] | None = None,
                      for_export: bool = False) -> dict:
    asked = question  # keep the original wording to tell whether a chart was requested
    question = topic_question(question)
    # Include the previous user question so short follow-ups ("show that as a chart") still retrieve the right pages.
    prev = next((t["content"] for t in reversed(history or []) if t.get("role") == "user"), "")
    query = f"{prev} {question}" if len(question.split()) < 5 else question
    passages = kb.search(query)
    # Similarity cutoffs only apply to embedding scores, not BM25 keyword scores.
    semantic = bool(passages) and passages[0].get("match") == "semantic"
    top = passages[0]["score"] if semantic else 1.0
    coverage = topic_coverage(query, passages)
    not_found = {"answer": NOT_FOUND, "sources": [], "mode": "not_found"}
    if not passages or top < MIN_SCORE or coverage == 0:
        return not_found

    reply = lmstudio.chat(build_messages(question, profile, history or [], passages))
    # Only list sources about as relevant as the best match (retrieval always returns 4 passages).
    relevant = [p for p in passages if not semantic or p["score"] >= top - SOURCE_MARGIN]
    sources = list({p["url"]: {"title": p["title"], "url": p["url"]} for p in relevant}.values())[:3]
    if reply and NOT_FOUND_MARKER in reply:
        return not_found
    if reply:
        result = {"answer": reply, "sources": sources, "mode": "llm"}
    elif coverage < 1 or top < MIN_OFFLINE_SCORE:
        return not_found
    else:
        result = {"answer": offline_answer(question, passages), "sources": sources, "mode": "offline"}

    if chart := charts.build_chart(f"{query} {asked}", passages, use_model=reply is not None, wanted=for_export):
        result["chart"] = chart
    elif charts.chart_intent(asked) == "explicit":
        result["answer"] += ("\n\nI couldn't find numbers in my knowledge base that can be charted for this "
                             "question, so there's no chart this time.")
    return result
