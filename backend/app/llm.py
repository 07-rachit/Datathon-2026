import os
import requests

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


class LLMNotConfigured(Exception):
    pass


def generate_answer(question: str, context_blocks: list[str], language: str = "en") -> str:
    """Call the Anthropic Messages API with retrieved context and return the answer text."""
    if not ANTHROPIC_API_KEY:
        raise LLMNotConfigured(
            "ANTHROPIC_API_KEY is not set on the server. Set it as an environment "
            "variable to enable AI-generated answers."
        )

    context_text = "\n\n".join(f"[Source {i+1}] {block}" for i, block in enumerate(context_blocks))
    language_instruction = (
        "Respond entirely in Kannada (ಕನ್ನಡ script), even though the case context below is in English. "
        "Translate case facts naturally rather than leaving them in English."
        if language == "kn"
        else "Respond in English."
    )
    system_prompt = (
        "You are a senior crime intelligence analyst assistant supporting investigators. "
        "You have deep, direct access to the case records provided in the context below - "
        "treat them as your case file, not as generic search snippets.\n\n"
        "How to help:\n"
        "- Explain cases clearly: what happened, who is involved, current status, and why it matters.\n"
        "- Actively look for connections across cases - shared persons, phone numbers, districts, "
        "crime types, or timing patterns - and point them out even if the investigator didn't ask.\n"
        "- When relevant, suggest concrete next investigative steps (e.g. cross-check a phone number "
        "against other open cases, revisit a witness statement, compare MO across incidents).\n"
        "- Be direct and specific - reference case IDs, names, and dates from the context rather than "
        "speaking in generalities.\n"
        "- If the context only partially answers the question, say what you can confirm and what "
        "would need further lookup. Never invent details not present in the context.\n"
        "- Reference sources as [Source N] when you state a fact drawn from them.\n\n"
        f"LANGUAGE: {language_instruction}\n\n"
        f"CASE FILE CONTEXT:\n{context_text}"
    )

    response = requests.post(
        ANTHROPIC_URL,
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": ANTHROPIC_MODEL,
            "max_tokens": 1200,
            "system": system_prompt,
            "messages": [{"role": "user", "content": question}],
        },
        timeout=45,
    )
    response.raise_for_status()
    data = response.json()
    text_parts = [block["text"] for block in data.get("content", []) if block.get("type") == "text"]
    return "\n".join(text_parts).strip() or "The model did not return a text response."
