"""Retrieval-augmented answers, tailored to who is asking."""

from __future__ import annotations

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

BASE_PROMPT = """You are the CTData Assistant for the Connecticut Data Collaborative (ctdata.org).
You currently answer questions about CTData's EDUCATION data page and the blog posts linked from it.

Rules:
- Answer ONLY from the CONTEXT below. If the answer isn't there, say so honestly and suggest where on ctdata.org or which linked source (e.g. EdSight) they could look, or suggest the CTData Data Helpline (https://www.ctdata.org/datahelpline).
- Never invent numbers. Quote figures exactly as they appear in the context.
- When you mention a dataset or article, include its link from the context.
- Keep answers under about 180 words unless the user asks for more. Use short paragraphs or bullet points.

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
    system = BASE_PROMPT.format(audience=audience_instructions(profile))
    messages = [{"role": "system", "content": system}]
    # Last few turns so follow-ups like "what about by gender?" make sense.
    for turn in (history or [])[-6:]:
        if turn.get("role") in {"user", "assistant"} and turn.get("content"):
            messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": f"CONTEXT:\n{context or '(no matching content)'}\n\nQUESTION: {question}"})
    return messages


def offline_answer(question: str, passages: list[dict]) -> str:
    """Used when LM Studio isn't running: show the best matching passages as-is."""
    if not passages:
        return ("I couldn't find that on CTData's education page. Try asking about graduation rates, "
                "chronic absenteeism, suspension rates, test scores or student loan debt.")
    # Prefer direct dataset links whose label matches the question.
    terms = set(tokenize(question))
    link_lines = [
        line for p in passages if "#links" in p.get("id", "")
        for line in p["text"].splitlines()[1:] if terms & set(tokenize(line.split(": http")[0]))
    ]
    if link_lines:
        return "Here are the matching datasets on CTData's education page:\n\n" + "\n".join(link_lines[:5])
    best = passages[0]
    snippet = best["text"][:500].rsplit("\n", 1)[0] if len(best["text"]) > 500 else best["text"]
    return f"Here's what I found on **{best['title']}**:\n\n{snippet}"


def answer(kb: KnowledgeBase, question: str, profile: dict, history: list[dict] | None = None) -> dict:
    # Include the previous user question so short follow-ups still retrieve the right pages.
    prev = next((t["content"] for t in reversed(history or []) if t.get("role") == "user"), "")
    passages = kb.search(f"{prev} {question}" if len(question.split()) < 5 else question)

    reply = lmstudio.chat(build_messages(question, profile, history or [], passages))
    sources = list({p["url"]: {"title": p["title"], "url": p["url"]} for p in passages}.values())[:3]
    if reply:
        return {"answer": reply, "sources": sources, "mode": "llm"}
    return {"answer": offline_answer(question, passages), "sources": sources, "mode": "offline"}
