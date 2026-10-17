import { useState, type FormEvent } from "react";
import type { Task, TaskPatch } from "./types";
import { CONSEQUENCE_LABELS } from "./types";
import { formatDateTime, formatDuration, fromLocalInput, toLocalInput } from "./format";

type Variant = "hero" | "normal" | "overdue" | "whenever" | "needs";

interface Props {
  task: Task;
  variant: Variant;
  now: Date;
  onDone: (id: number) => void;
  onSave: (id: number, patch: TaskPatch) => Promise<void>;
}

export default function TaskCard({ task, variant, now, onDone, onSave }: Props) {
  const [editing, setEditing] = useState(false);
  const lateToStart = task.latest_start !== null && new Date(task.latest_start) <= now;

  return (
    <article className={`card card-${variant}`}>
      <div className="card-main">
        <h3 className="card-title">{task.title || task.raw_input}</h3>

        {variant === "needs" ? (
          <p className="card-meta">
            Waiting on: <em>{task.pending_question}</em>
            <br />
            You said: “{task.raw_input}”
          </p>
        ) : (
          <p className="card-meta">
            <span className="pill">{formatDuration(task.estimated_minutes)}</span>
            {task.consequence !== null && (
              <span className={`pill pill-c${task.consequence}`}>{CONSEQUENCE_LABELS[task.consequence]}</span>
            )}
            {task.deadline && <span>Due {formatDateTime(task.deadline)}</span>}
            {task.latest_start && variant !== "overdue" && (
              <span className={lateToStart ? "late" : ""}>
                {lateToStart ? "Should have started " : "Start by "}
                {formatDateTime(task.latest_start)}
              </span>
            )}
          </p>
        )}
      </div>

      <div className="card-actions">
        <button className="btn btn-done" onClick={() => onDone(task.id)}>
          Done
        </button>
        <button className="btn" onClick={() => setEditing((e) => !e)}>
          {editing ? "Close" : "Edit"}
        </button>
      </div>

      {editing && (
        <EditForm
          task={task}
          onCancel={() => setEditing(false)}
          onSave={async (patch) => {
            await onSave(task.id, patch);
            setEditing(false);
          }}
        />
      )}
    </article>
  );
}

function EditForm({
  task,
  onCancel,
  onSave,
}: {
  task: Task;
  onCancel: () => void;
  onSave: (patch: TaskPatch) => Promise<void>;
}) {
  const [title, setTitle] = useState(task.title || task.raw_input);
  const [whenever, setWhenever] = useState(task.deadline === null);
  const [deadline, setDeadline] = useState(toLocalInput(task.deadline));
  const [minutes, setMinutes] = useState(task.estimated_minutes ?? 30);
  const [consequence, setConsequence] = useState(task.consequence ?? 3);
  const [error, setError] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!whenever && !deadline) {
      setError("Pick a deadline, or tick “Whenever”.");
      return;
    }
    try {
      await onSave({
        title: title.trim(),
        deadline: whenever ? null : fromLocalInput(deadline),
        estimated_minutes: minutes,
        consequence,
      });
    } catch {
      setError("Couldn't save. Try again.");
    }
  }

  return (
    <form className="edit-form" onSubmit={submit}>
      <label>
        Title
        <input value={title} onChange={(e) => setTitle(e.target.value)} required />
      </label>
      <label className="check">
        <input type="checkbox" checked={whenever} onChange={(e) => setWhenever(e.target.checked)} />
        Whenever (no deadline)
      </label>
      {!whenever && (
        <label>
          Deadline
          <input type="datetime-local" value={deadline} onChange={(e) => setDeadline(e.target.value)} />
        </label>
      )}
      <label>
        Minutes
        <input
          type="number"
          min={1}
          value={minutes}
          onChange={(e) => setMinutes(Math.max(1, Number(e.target.value) || 1))}
        />
      </label>
      <label>
        Consequence
        <select value={consequence} onChange={(e) => setConsequence(Number(e.target.value))}>
          {[1, 2, 3, 4, 5].map((level) => (
            <option key={level} value={level}>
              {level} {CONSEQUENCE_LABELS[level]}
            </option>
          ))}
        </select>
      </label>
      {error && <p className="error">{error}</p>}
      <div className="card-actions">
        <button className="btn btn-done" type="submit">
          Save
        </button>
        <button className="btn" type="button" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
