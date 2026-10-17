import { useCallback, useEffect, useState } from "react";
import { AuthError, completeTask, getBoard, getSchedule, loadKey, saveKey, tickItem, updateTask } from "./api";
import Checklists, { remaining } from "./Checklists";
import { formatClock } from "./format";
import KeyForm from "./KeyForm";
import TaskCard from "./TaskCard";
import type { Board, Schedule, Task, TaskPatch, Tick } from "./types";

const REFRESH_MS = 30_000;
const IDLE_RETURN_MS = 60_000; // a list view goes back to "Start now" after a minute untouched

type View = "home" | "next" | "whenever" | "needs" | "checklists";

export default function App() {
  const [key, setKey] = useState(loadKey);
  const [board, setBoard] = useState<Board | null>(null);
  const [schedule, setSchedule] = useState<Schedule | null>(null);
  const [error, setError] = useState("");
  const [now, setNow] = useState(() => new Date());
  const [view, setView] = useState<View>("home");

  const refresh = useCallback(async () => {
    if (!key) return;
    try {
      const [b, s] = await Promise.all([getBoard(key), getSchedule(key)]);
      setBoard(b);
      setSchedule(s);
      setError("");
    } catch (e) {
      if (e instanceof AuthError) {
        saveKey("");
        setKey("");
      } else {
        setError("Can't reach the server. Retrying…");
      }
    }
  }, [key]);

  // Load now, then refresh the tasks, schedule and clock every 30 seconds.
  useEffect(() => {
    refresh();
    const id = setInterval(() => {
      refresh();
      setNow(new Date());
    }, REFRESH_MS);
    return () => clearInterval(id);
  }, [refresh]);

  // When a list is open, go back to the main view after a minute with no taps or typing.
  useEffect(() => {
    if (view === "home") return;
    let timer = setTimeout(() => setView("home"), IDLE_RETURN_MS);
    const restart = () => {
      clearTimeout(timer);
      timer = setTimeout(() => setView("home"), IDLE_RETURN_MS);
    };
    window.addEventListener("pointerdown", restart);
    window.addEventListener("keydown", restart);
    return () => {
      clearTimeout(timer);
      window.removeEventListener("pointerdown", restart);
      window.removeEventListener("keydown", restart);
    };
  }, [view]);

  if (!key) {
    return (
      <KeyForm
        onSubmit={(k) => {
          saveKey(k);
          setKey(k);
        }}
      />
    );
  }

  async function done(id: number) {
    await completeTask(key, id);
    await refresh();
  }

  async function save(id: number, patch: TaskPatch) {
    await updateTask(key, id, patch);
    await refresh();
  }

  async function tick(t: Tick) {
    try {
      setSchedule(await tickItem(key, t));
    } catch {
      setError("Couldn't save that tick. Try again.");
    }
  }

  const cardProps = { now, onDone: done, onSave: save };

  // Overdue tasks come first, then tasks in latest-start order. The first one is "Start now".
  const queue: Task[] = board ? [...board.overdue, ...board.ranked] : [];
  const [startNow, ...upNext] = queue;
  const isOverdue = (t: Task) => board?.overdue.some((o) => o.id === t.id) ?? false;

  if (!board || !schedule) {
    return (
      <main className="board">
        <Header now={now} error={error} />
        <p className="muted">Loading…</p>
      </main>
    );
  }

  if (view === "checklists") {
    return (
      <main className="board">
        <ListHeader title="Get ready" onBack={() => setView("home")} />
        {error && <p className="error">{error}</p>}
        <Checklists schedule={schedule} onTick={tick} />
      </main>
    );
  }

  if (view !== "home") {
    const lists: Record<"next" | "whenever" | "needs", { title: string; tasks: Task[]; empty: string }> = {
      next: { title: "Up next", tasks: upNext, empty: "Nothing else with a deadline." },
      whenever: { title: "Whenever pile", tasks: board.whenever, empty: "The whenever pile is empty." },
      needs: { title: "Needs details", tasks: board.needs_info, empty: "Nothing waiting for details." },
    };
    const list = lists[view];

    return (
      <main className="board">
        <ListHeader title={list.title} onBack={() => setView("home")} />
        {error && <p className="error">{error}</p>}
        {list.tasks.length === 0 ? (
          <p className="muted">{list.empty}</p>
        ) : (
          list.tasks.map((t) => (
            <TaskCard
              key={t.id}
              task={t}
              variant={view === "needs" ? "needs" : view === "whenever" ? "whenever" : isOverdue(t) ? "overdue" : "normal"}
              {...cardProps}
            />
          ))
        )}
      </main>
    );
  }

  // Prompts for checklists that still need ticking.
  const prompts: string[] = [];
  const week = schedule.week_check;
  if (week && !week.complete) {
    prompts.push(`Week ahead check: ${week.items.filter((i) => !i.ticked).length} to sort`);
  }
  if (remaining(schedule.tomorrow) > 0) prompts.push(`Tomorrow: ${remaining(schedule.tomorrow)} to get ready`);
  if (remaining(schedule.today) > 0) prompts.push(`Today: ${remaining(schedule.today)} to get ready`);

  return (
    <main className="board home">
      <Header now={now} error={error} />

      {prompts.length > 0 && (
        <button className="prompt" onClick={() => setView("checklists")}>
          {prompts.map((p) => (
            <span key={p}>{p}</span>
          ))}
          <span className="prompt-action">Check now →</span>
        </button>
      )}

      <section>
        {startNow ? (
          <>
            <h2 className={isOverdue(startNow) ? "overdue-heading" : ""}>
              {isOverdue(startNow) ? "Overdue: do this now" : "Start now"}
            </h2>
            <TaskCard task={startNow} variant="hero" {...cardProps} />
          </>
        ) : (
          <>
            <h2>Start now</h2>
            <p className="muted hero-empty">Nothing with a deadline. Pick something from the whenever pile.</p>
          </>
        )}
      </section>

      {schedule.today.entries.length > 0 && (
        <section>
          <h2>Today</h2>
          <ul className="agenda">
            {schedule.today.entries.map((e) => (
              <li key={e.source}>
                <span className="agenda-time">{e.time ?? "All day"}</span>
                <span>
                  {e.title}
                  {e.person && <span className="muted"> · {e.person}</span>}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <nav className="nav-buttons">
        <button className="btn btn-nav" onClick={() => setView("next")}>
          Up next
        </button>
        <button className="btn btn-nav" onClick={() => setView("whenever")}>
          Whenever pile
        </button>
        {board.needs_info.length > 0 && (
          <button className="btn btn-nav btn-needs" onClick={() => setView("needs")}>
            Needs details
          </button>
        )}
        <a className="btn btn-nav" href="#/manage">
          Routines
        </a>
      </nav>
    </main>
  );
}

function Header({ now, error }: { now: Date; error: string }) {
  return (
    <header className="board-header">
      <h1>{formatClock(now)}</h1>
      {error && <p className="error">{error}</p>}
    </header>
  );
}

function ListHeader({ title, onBack }: { title: string; onBack: () => void }) {
  return (
    <header className="list-header">
      <button className="btn" onClick={onBack}>
        ← Back
      </button>
      <h1>{title}</h1>
    </header>
  );
}
