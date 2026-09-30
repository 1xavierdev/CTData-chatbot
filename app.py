"""Simple Connecticut data chatbot."""

from __future__ import annotations


def get_answer(question: str) -> str:
    """Return a helpful answer to simple Connecticut data questions."""
    text = (question or "").strip().lower()

    if not text:
        return "I can help with Connecticut data. Ask about the capital, population, nickname, or largest city."

    if "capital" in text:
        return "Connecticut's capital is Hartford."

    if "population" in text:
        return "Connecticut's population is about 3.6 million residents."

    if "largest city" in text or "biggest city" in text:
        return "Connecticut's largest city is Bridgeport."

    if "nickname" in text:
        return "Connecticut's nickname is the Constitution State."

    if "state bird" in text or "bird" in text:
        return "Connecticut's state bird is the American robin."

    if "connecticut" in text:
        return "I can help with Connecticut data such as capital, population, largest city, nickname, and state bird."

    return "I can help with Connecticut data. Ask me about the capital, population, nickname, or largest city."


if __name__ == "__main__":
    while True:
        user_input = input("Ask about Connecticut: ")
        if user_input.strip().lower() in {"quit", "exit", "q"}:
            break
        print(get_answer(user_input))
