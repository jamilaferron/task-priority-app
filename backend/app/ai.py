"""The AI step: turn what was said into structured fields.

The AI only extracts. It never ranks tasks; ranking.py does that in plain code.
Everything provider-specific lives in this file, so switching to another AI
provider means rewriting `_call_model` only.
"""

from datetime import datetime

import anthropic
from pydantic import BaseModel, Field, ValidationError

from .config import AI_MODEL, APP_TIMEZONE


class AIError(Exception):
    """The AI call failed or returned something unusable."""


class Extraction(BaseModel):
    """The shape every AI reply must match. Pydantic rejects anything else."""

    title: str = Field(min_length=1, max_length=120)
    deadline: datetime | None = None
    is_whenever: bool = False
    estimated_minutes: int | None = Field(default=None, ge=1, le=10080)
    consequence: int | None = Field(default=None, ge=1, le=5)
    question: str | None = None


SYSTEM_PROMPT = """You turn a spoken to-do item into structured fields for a personal task list.
Always reply by calling the record_task tool.

Fields:
- title: a short action title, at most 8 words, e.g. "Pay the tax bill".
- deadline: when it must be done by, as ISO 8601 with UTC offset, in the user's time zone.
  Work out relative dates ("Friday", "tomorrow", "next week") from the current date given.
  If only a day is given, use 17:00 on that day. If no deadline was given, use null.
- is_whenever: true only if the user said there is no deadline (e.g. "whenever", "no rush",
  "no deadline", "at some point"). Otherwise false.
- estimated_minutes: a realistic estimate of how long the task itself takes. Always give your
  best estimate; never ask about duration.
- consequence: how bad it is if the deadline is missed, from 1 to 5:
    1 Trivial - nothing really happens if missed (e.g. try the new coffee place)
    2 Minor - small inconvenience, easy to fix later (e.g. return library book)
    3 Moderate - costs time, money or stress to fix (e.g. book the car MOT)
    4 Serious - affects other people, work or finances; hard to undo (e.g. submit reports)
    5 Critical - major money, legal, health or job consequences (e.g. pay the tax bill)
  Always give your best rating.
- question: one short question Siri will read aloud, only when asking is allowed and an
  essential detail is missing. If no deadline was mentioned and the user has not said it is a
  whenever task, ask: "Is there a deadline, or is this a whenever task?"
  Otherwise null. Never ask about something the user has already answered."""


RECORD_TASK_TOOL = {
    "name": "record_task",
    "description": "Record the structured details of the user's task.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "deadline": {"type": ["string", "null"], "description": "ISO 8601 with UTC offset, or null"},
            "is_whenever": {"type": "boolean"},
            "estimated_minutes": {"type": ["integer", "null"]},
            "consequence": {"type": ["integer", "null"], "minimum": 1, "maximum": 5},
            "question": {"type": ["string", "null"]},
        },
        "required": ["title", "deadline", "is_whenever", "estimated_minutes", "consequence", "question"],
    },
}

_client: anthropic.Anthropic | None = None


def _build_prompt(raw_input: str, clarifications: list[dict], now_local: datetime, allow_question: bool) -> str:
    lines = [
        f"Current date and time: {now_local:%A} {now_local.day} {now_local:%B %Y, %H:%M} ({APP_TIMEZONE.key}).",
        "",
        f"Task as spoken: {raw_input}",
    ]
    for qa in clarifications:
        lines += ["", f"You asked: {qa['question']}", f"User answered: {qa['answer']}"]
    lines.append("")
    if allow_question:
        lines.append("You may ask one follow-up question if an essential detail is missing.")
    else:
        lines.append("Do not ask any more questions. Set question to null and give your best guess for everything.")
    return "\n".join(lines)


def _call_model(prompt: str) -> dict:
    """Send the prompt to Claude and return the tool input it produced."""
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    try:
        response = _client.messages.create(
            model=AI_MODEL,
            max_tokens=500,
            system=SYSTEM_PROMPT,
            tools=[RECORD_TASK_TOOL],
            tool_choice={"type": "tool", "name": "record_task"},  # force a structured reply
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError as exc:
        raise AIError(f"AI request failed: {exc}") from exc

    for block in response.content:
        if block.type == "tool_use":
            return block.input
    raise AIError("AI did not return task details")


def extract_task(raw_input: str, clarifications: list[dict], now_local: datetime, allow_question: bool) -> Extraction:
    """Main entry point: spoken text (+ any follow-up answers) -> validated fields."""
    prompt = _build_prompt(raw_input, clarifications, now_local, allow_question)
    data = _call_model(prompt)
    try:
        return Extraction.model_validate(data)
    except ValidationError as exc:
        raise AIError(f"AI reply did not match the expected shape: {exc}") from exc
