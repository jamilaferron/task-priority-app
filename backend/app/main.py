"""FastAPI app: task endpoints, routine/schedule endpoints, and the built wall screen if present.

Run locally:  uvicorn app.main:app --reload
Interactive docs: http://localhost:8000/docs
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from .ai import AIError
from .auth import require_api_key
from .database import Base, engine, get_db
from .models import Task
from .ranking import build_board
from .schedule_api import router as schedule_router
from .schemas import BoardOut, ClarifyIn, SiriReply, TaskIn, TaskOut, TaskPatch
from .services import process_task
from .timeutils import from_storage, to_storage, utcnow


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)  # creates any tables that don't exist yet
    yield


app = FastAPI(title="Task Priority API", lifespan=lifespan)


router = APIRouter(prefix="/tasks", dependencies=[Depends(require_api_key)])


def get_task_or_404(task_id: int, db: Session) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(404, "Task not found")
    return task


def run_ai(task: Task, db: Session) -> SiriReply:
    """Call the AI, save the result, and turn AI failures into a message Siri can say."""
    try:
        reply = process_task(task)
    except AIError as exc:
        db.rollback()
        raise HTTPException(502, "Sorry, I couldn't process that task. Please try again.") from exc
    db.commit()
    return reply


@router.post("", response_model=SiriReply)
def add_task(body: TaskIn, db: Session = Depends(get_db)):
    """Siri sends what you said. Reply: 'added' or 'needs_info' with a question."""
    task = Task(raw_input=body.text.strip(), clarifications=[])
    db.add(task)
    db.flush()  # gives the task an id before the AI runs
    return run_ai(task, db)


@router.post("/{task_id}/clarify", response_model=SiriReply)
def clarify_task(task_id: int, body: ClarifyIn, db: Session = Depends(get_db)):
    """Siri sends your answer to the follow-up question."""
    task = get_task_or_404(task_id, db)
    if task.status != "needs_info" or not task.pending_question:
        raise HTTPException(409, "This task isn't waiting for an answer")
    task.clarifications = task.clarifications + [
        {"question": task.pending_question, "answer": body.answer.strip()}
    ]
    return run_ai(task, db)


@router.get("", response_model=BoardOut)
def get_board(db: Session = Depends(get_db)):
    """Everything the wall screen shows, already sorted."""
    tasks = db.scalars(select(Task).where(Task.status != "done")).all()
    board = build_board(list(tasks), now=utcnow())
    return BoardOut(
        **{section: [TaskOut.from_task(t) for t in items] for section, items in board.items()},
        generated_at=from_storage(utcnow()),
    )


@router.post("/{task_id}/complete", response_model=TaskOut)
def complete_task(task_id: int, db: Session = Depends(get_db)):
    """Tapping 'Done' on the screen."""
    task = get_task_or_404(task_id, db)
    task.status = "done"
    task.completed_at = utcnow()
    task.pending_question = None
    db.commit()
    return TaskOut.from_task(task)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, body: TaskPatch, db: Session = Depends(get_db)):
    """Correct what the AI got wrong, or promote a whenever task by giving it a deadline."""
    task = get_task_or_404(task_id, db)
    changes = body.model_dump(exclude_unset=True)  # only fields actually sent
    if "deadline" in changes:
        task.deadline = to_storage(changes["deadline"]) if changes["deadline"] else None
    for field in ("title", "estimated_minutes", "consequence"):
        if changes.get(field) is not None:
            setattr(task, field, changes[field])
    if task.status == "needs_info":  # you've filled in the details yourself
        task.status = "active"
        task.pending_question = None
    db.commit()
    return TaskOut.from_task(task)


app.include_router(router)
app.include_router(schedule_router)


@app.get("/health")
def health():
    return {"ok": True}


# Serve the built wall screen (frontend/dist) from the same server, if it exists.
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="screen")
