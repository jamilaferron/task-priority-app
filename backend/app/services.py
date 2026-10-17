"""The add/clarify logic shared by both Siri endpoints."""

from . import ai
from .config import DEFAULT_CONSEQUENCE, DEFAULT_MINUTES, MAX_FOLLOW_UPS
from .models import Task
from .schemas import SiriReply
from .timeutils import spoken, to_local, to_storage, utcnow

DEFAULT_DEADLINE_QUESTION = "Is there a deadline, or is this a whenever task?"


def process_task(task: Task) -> SiriReply:
    """Run the AI over the task (plus any answers so far) and update it in place.

    The caller commits the database session.
    """
    allow_question = len(task.clarifications) < MAX_FOLLOW_UPS
    result = ai.extract_task(
        raw_input=task.raw_input,
        clarifications=task.clarifications,
        now_local=to_local(utcnow()),
        allow_question=allow_question,
    )

    task.title = result.title
    task.estimated_minutes = result.estimated_minutes or DEFAULT_MINUTES
    task.consequence = result.consequence or DEFAULT_CONSEQUENCE
    task.deadline = None if result.is_whenever or result.deadline is None else to_storage(result.deadline)

    deadline_unclear = result.deadline is None and not result.is_whenever
    if allow_question and (result.question or deadline_unclear):
        task.status = "needs_info"
        task.pending_question = result.question or DEFAULT_DEADLINE_QUESTION
        return SiriReply(
            status="needs_info",
            task_id=task.id,
            message=task.pending_question,
            question=task.pending_question,
        )

    # Out of questions (or none needed): an unclear deadline means the whenever pile.
    task.status = "active"
    task.pending_question = None
    if task.deadline is None:
        message = f"Added {task.title} to the whenever pile."
    else:
        message = f"Added {task.title}, due {spoken(task.deadline)}."
    return SiriReply(status="added", task_id=task.id, message=message)
