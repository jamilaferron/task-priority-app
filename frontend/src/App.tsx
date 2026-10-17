import { useCallback, useEffect, useState } from "react";
import {
  AuthError,
  completeTask,
  getBoard,
  loadKey,
  saveKey,
  updateTask,
} from "./api";
import { formatClock } from "./format";
import TaskCard from "./TaskCard";
import type { Board, Task, TaskPatch } from "./types";

const REFRESH_MS = 30_000;
const IDLE_RETURN_MS = 60_000; // a list view goes back to "Start now" after a minute untouched

type View = "home" | "next" | "whenever" | "needs";

export default function App() {
  const [key, setKey] = useState(loadKey);
  const [board, setBoard] = useState<Board | null>(null);
  const [error, setError] = useState("");
  const [now, setNow] = useState(() => new Date());
  const [view, setView] = useState<View>("home");

  const refresh = useCallback(async () => {
    if (!key) return;
    try {
      setBoard(await getBoard(key));
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

  // Load now, then refresh the tasks and the clock every 30 seconds.
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

  const cardProps = { now, onDone: done, onSave: save };

  // Overdue tasks come first, then tasks in latest-start order. The first one is "Start now".
  const queue: Task[] = board ? [...board.overdue, ...board.ranked] : [];
  const [startNow, ...upNext] = queue;
  const isOverdue = (t: Task) =>
    board?.overdue.some((o) => o.id === t.id) ?? false;

  if (!board) {
    return (
      <main className="board">
        <Header now={now} error={error} />
        <p className="muted">Loading…</p>
      </main>
    );
  }

  if (view !== "home") {
    const lists: Record<
      Exclude<View, "home">,
      { title: string; tasks: Task[]; empty: string }
    > = {
      next: {
        title: "Up next",
        tasks: upNext,
        empty: "Nothing else with a deadline.",
      },
      whenever: {
        title: "Whenever pile",
        tasks: board.whenever,
        empty: "The whenever pile is empty.",
      },
      needs: {
        title: "Needs details",
        tasks: board.needs_info,
        empty: "Nothing waiting for details.",
      },
    };
    const list = lists[view];

    return (
      <main className="board">
        <header className="list-header">
          <button className="btn" onClick={() => setView("home")}>
            ← Back
          </button>
          <h1>{list.title}</h1>
        </header>
        {error && <p className="error">{error}</p>}
        {list.tasks.length === 0 ? (
          <p className="muted">{list.empty}</p>
        ) : (
          list.tasks.map((t) => (
            <TaskCard
              key={t.id}
              task={t}
              variant={
                view === "needs"
                  ? "needs"
                  : view === "whenever"
                    ? "whenever"
                    : isOverdue(t)
                      ? "overdue"
                      : "normal"
              }
              {...cardProps}
            />
          ))
        )}
      </main>
    );
  }

  return (
    <main className="board home">
      <Header now={now} error={error} />

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
            <p className="muted hero-empty">
              Nothing with a deadline. Pick something from the whenever pile.
            </p>
          </>
        )}
      </section>

      <nav className="nav-buttons">
        <button className="btn btn-nav" onClick={() => setView("next")}>
          Up next
        </button>
        <button className="btn btn-nav" onClick={() => setView("whenever")}>
          Whenever pile
        </button>
        {board.needs_info.length > 0 && (
          <button
            className="btn btn-nav btn-needs"
            onClick={() => setView("needs")}
          >
            Needs details
          </button>
        )}
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

function KeyForm({ onSubmit }: { onSubmit: (key: string) => void }) {
  const [value, setValue] = useState("");
  return (
    <main className="board key-form">
      <h1>Task board</h1>
      <p className="muted">
        Enter the API key from your server's .env file. This screen will
        remember it.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (value.trim()) onSubmit(value.trim());
        }}
      >
        <input
          type="password"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="API key"
          autoFocus
        />
        <button className="btn btn-done" type="submit">
          Connect
        </button>
      </form>
    </main>
  );
}
