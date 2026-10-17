// Phone-friendly page for managing routines, one-off events and break calendars.
// Open it at  #/manage  (add it to your phone's home screen).

import { useCallback, useEffect, useState, type FormEvent } from "react";
import {
  addPeriod,
  AuthError,
  createCalendar,
  createEvent,
  createRoutine,
  deleteCalendar,
  deleteEvent,
  deletePeriod,
  deleteRoutine,
  getCalendars,
  getEvents,
  getRoutines,
  loadKey,
  saveKey,
  updateEvent,
  updateRoutine,
} from "./api";
import KeyForm from "./KeyForm";
import type { BreakCalendar, Category, OneOffEvent, OneOffEventIn, Routine, RoutineIn } from "./types";
import { CATEGORY_LABELS, DAY_NAMES } from "./types";

type Tab = "routines" | "events" | "breaks";
type Act = (fn: () => Promise<unknown>) => Promise<boolean>;

const toggle = (list: number[], value: number) =>
  list.includes(value) ? list.filter((v) => v !== value) : [...list, value];

const itemsFromText = (text: string) => text.split("\n").map((s) => s.trim()).filter(Boolean);

const formatDate = (iso: string) =>
  new Date(`${iso}T12:00:00`).toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short", year: "numeric" });

export default function Manage() {
  const [key, setKey] = useState(loadKey);
  const [tab, setTab] = useState<Tab>("routines");
  const [routines, setRoutines] = useState<Routine[]>([]);
  const [events, setEvents] = useState<OneOffEvent[]>([]);
  const [calendars, setCalendars] = useState<BreakCalendar[]>([]);
  const [error, setError] = useState("");

  const handleError = useCallback((e: unknown, message: string) => {
    if (e instanceof AuthError) {
      saveKey("");
      setKey("");
    } else {
      setError(message);
    }
  }, []);

  const reload = useCallback(async () => {
    if (!key) return;
    try {
      const [r, e, c] = await Promise.all([getRoutines(key), getEvents(key), getCalendars(key)]);
      setRoutines(r);
      setEvents(e);
      setCalendars(c);
      setError("");
    } catch (e) {
      handleError(e, "Can't reach the server.");
    }
  }, [key, handleError]);

  useEffect(() => {
    reload();
  }, [reload]);

  // Run a change, then reload everything. Returns true if it worked.
  const act: Act = async (fn) => {
    try {
      await fn();
      await reload();
      return true;
    } catch (e) {
      handleError(e, "Couldn't save. Check the details and try again.");
      return false;
    }
  };

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

  return (
    <main className="board manage">
      <header className="list-header">
        <a className="btn" href="#/">
          ← Screen
        </a>
        <h1>Manage</h1>
      </header>

      <div className="tabs" role="tablist">
        {(["routines", "events", "breaks"] as Tab[]).map((t) => (
          <button key={t} role="tab" aria-selected={tab === t} className={`tab ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>
            {t === "routines" ? "Routines" : t === "events" ? "Events" : "Breaks"}
          </button>
        ))}
      </div>

      {error && <p className="error">{error}</p>}

      {tab === "routines" && <RoutinesTab apiKey={key} routines={routines} calendars={calendars} act={act} />}
      {tab === "events" && <EventsTab apiKey={key} events={events} act={act} />}
      {tab === "breaks" && <BreaksTab apiKey={key} calendars={calendars} act={act} />}
    </main>
  );
}

// ---------------------------------------------------------------- Routines

function RoutinesTab({ apiKey, routines, calendars, act }: { apiKey: string; routines: Routine[]; calendars: BreakCalendar[]; act: Act }) {
  const [editing, setEditing] = useState<Routine | "new" | null>(null);
  const calendarName = (id: number) => calendars.find((c) => c.id === id)?.name ?? "?";

  // Sort by first day of the week, then time.
  const sorted = [...routines].sort(
    (a, b) => (a.weekdays[0] ?? 7) - (b.weekdays[0] ?? 7) || (a.time ?? "").localeCompare(b.time ?? ""),
  );

  if (editing) {
    return (
      <RoutineForm
        initial={editing === "new" ? null : editing}
        calendars={calendars}
        onCancel={() => setEditing(null)}
        onSave={async (r) => {
          const ok = await act(() =>
            editing === "new" ? createRoutine(apiKey, r) : updateRoutine(apiKey, editing.id, r),
          );
          if (ok) setEditing(null);
        }}
      />
    );
  }

  return (
    <>
      <button className="btn btn-done add-btn" onClick={() => setEditing("new")}>
        + Add routine
      </button>
      {sorted.length === 0 && <p className="muted">No routines yet.</p>}
      {sorted.map((r) => (
        <article key={r.id} className={`card manage-card ${r.active ? "" : "inactive"}`}>
          <div className="card-main">
            <h3 className="card-title">{r.title}</h3>
            <p className="card-meta">
              <span>{r.weekdays.map((d) => DAY_NAMES[d]).join(", ")}</span>
              {r.time && <span>{r.time}</span>}
              {r.person && <span>{r.person}</span>}
              <span className="pill">{CATEGORY_LABELS[r.category]}</span>
              {!r.active && <span className="pill">Off</span>}
            </p>
            {r.items.length > 0 && <p className="muted small">Needs: {r.items.join(", ")}</p>}
            {r.paused_by.length > 0 && (
              <p className="muted small">Paused by: {r.paused_by.map(calendarName).join(", ")}</p>
            )}
          </div>
          <div className="card-actions">
            <button className="btn" onClick={() => setEditing(r)}>
              Edit
            </button>
            <button
              className="btn"
              onClick={() => {
                if (confirm(`Delete "${r.title}"?`)) act(() => deleteRoutine(apiKey, r.id));
              }}
            >
              Delete
            </button>
          </div>
        </article>
      ))}
    </>
  );
}

function RoutineForm({
  initial,
  calendars,
  onSave,
  onCancel,
}: {
  initial: Routine | null;
  calendars: BreakCalendar[];
  onSave: (r: RoutineIn) => Promise<void>;
  onCancel: () => void;
}) {
  const [title, setTitle] = useState(initial?.title ?? "");
  const [person, setPerson] = useState(initial?.person ?? "");
  const [category, setCategory] = useState<Category>(initial?.category ?? "school");
  const [weekdays, setWeekdays] = useState<number[]>(initial?.weekdays ?? []);
  const [time, setTime] = useState(initial?.time ?? "");
  const [itemsText, setItemsText] = useState((initial?.items ?? []).join("\n"));
  const [active, setActive] = useState(initial?.active ?? true);
  const [pausedBy, setPausedBy] = useState<number[]>(initial?.paused_by ?? []);
  const [problem, setProblem] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) return setProblem("Give it a title.");
    if (weekdays.length === 0) return setProblem("Pick at least one day.");
    await onSave({
      title: title.trim(),
      person: person.trim(),
      category,
      weekdays: [...weekdays].sort(),
      time: time || null,
      items: itemsFromText(itemsText),
      active,
      paused_by: pausedBy,
    });
  }

  return (
    <form className="manage-form" onSubmit={submit}>
      <h2>{initial ? "Edit routine" : "New routine"}</h2>
      <label>
        Title
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Packed lunch" />
      </label>
      <label>
        Who
        <input value={person} onChange={(e) => setPerson(e.target.value)} placeholder="e.g. Kenzo or Me" />
      </label>
      <label>
        Type
        <select value={category} onChange={(e) => setCategory(e.target.value as Category)}>
          {(Object.keys(CATEGORY_LABELS) as Category[]).map((c) => (
            <option key={c} value={c}>
              {CATEGORY_LABELS[c]}
            </option>
          ))}
        </select>
        <small className="muted">School and work items appear in the Sunday week-ahead check.</small>
      </label>
      <fieldset>
        <legend>Days</legend>
        <div className="chips">
          {DAY_NAMES.map((name, i) => (
            <button
              key={name}
              type="button"
              className={`chip ${weekdays.includes(i) ? "on" : ""}`}
              aria-pressed={weekdays.includes(i)}
              onClick={() => setWeekdays(toggle(weekdays, i))}
            >
              {name}
            </button>
          ))}
        </div>
      </fieldset>
      <label>
        Time (optional)
        <input type="time" value={time} onChange={(e) => setTime(e.target.value)} />
      </label>
      <label>
        Checklist (one item per line)
        <textarea rows={4} value={itemsText} onChange={(e) => setItemsText(e.target.value)} placeholder={"Sandwich\nFruit\nDrink"} />
      </label>
      <fieldset>
        <legend>Paused during</legend>
        {calendars.length === 0 && <p className="muted small">No break calendars yet. Add them in the Breaks tab.</p>}
        {calendars.map((c) => (
          <label key={c.id} className="check">
            <input type="checkbox" checked={pausedBy.includes(c.id)} onChange={() => setPausedBy(toggle(pausedBy, c.id))} />
            {c.name}
          </label>
        ))}
      </fieldset>
      <label className="check">
        <input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} />
        Active
      </label>
      {problem && <p className="error">{problem}</p>}
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

// ---------------------------------------------------------------- One-off events

function EventsTab({ apiKey, events, act }: { apiKey: string; events: OneOffEvent[]; act: Act }) {
  const [editing, setEditing] = useState<OneOffEvent | "new" | null>(null);

  if (editing) {
    return (
      <EventForm
        initial={editing === "new" ? null : editing}
        onCancel={() => setEditing(null)}
        onSave={async (e) => {
          const ok = await act(() => (editing === "new" ? createEvent(apiKey, e) : updateEvent(apiKey, editing.id, e)));
          if (ok) setEditing(null);
        }}
      />
    );
  }

  return (
    <>
      <button className="btn btn-done add-btn" onClick={() => setEditing("new")}>
        + Add event
      </button>
      {events.length === 0 && <p className="muted">No upcoming events.</p>}
      {events.map((ev) => (
        <article key={ev.id} className="card manage-card">
          <div className="card-main">
            <h3 className="card-title">{ev.title}</h3>
            <p className="card-meta">
              <span>{formatDate(ev.on_date)}</span>
              {ev.time && <span>{ev.time}</span>}
              {ev.person && <span>{ev.person}</span>}
            </p>
            {ev.items.length > 0 && <p className="muted small">Needs: {ev.items.join(", ")}</p>}
          </div>
          <div className="card-actions">
            <button className="btn" onClick={() => setEditing(ev)}>
              Edit
            </button>
            <button
              className="btn"
              onClick={() => {
                if (confirm(`Delete "${ev.title}"?`)) act(() => deleteEvent(apiKey, ev.id));
              }}
            >
              Delete
            </button>
          </div>
        </article>
      ))}
    </>
  );
}

function EventForm({
  initial,
  onSave,
  onCancel,
}: {
  initial: OneOffEvent | null;
  onSave: (e: OneOffEventIn) => Promise<void>;
  onCancel: () => void;
}) {
  const [title, setTitle] = useState(initial?.title ?? "");
  const [person, setPerson] = useState(initial?.person ?? "");
  const [onDate, setOnDate] = useState(initial?.on_date ?? "");
  const [time, setTime] = useState(initial?.time ?? "");
  const [itemsText, setItemsText] = useState((initial?.items ?? []).join("\n"));
  const [problem, setProblem] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) return setProblem("Give it a title.");
    if (!onDate) return setProblem("Pick a date.");
    await onSave({ title: title.trim(), person: person.trim(), on_date: onDate, time: time || null, items: itemsFromText(itemsText) });
  }

  return (
    <form className="manage-form" onSubmit={submit}>
      <h2>{initial ? "Edit event" : "New event"}</h2>
      <label>
        Title
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Dentist" />
      </label>
      <label>
        Who
        <input value={person} onChange={(e) => setPerson(e.target.value)} />
      </label>
      <label>
        Date
        <input type="date" value={onDate} onChange={(e) => setOnDate(e.target.value)} />
      </label>
      <label>
        Time (optional)
        <input type="time" value={time} onChange={(e) => setTime(e.target.value)} />
      </label>
      <label>
        Checklist (one item per line)
        <textarea rows={3} value={itemsText} onChange={(e) => setItemsText(e.target.value)} />
      </label>
      {problem && <p className="error">{problem}</p>}
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

// ---------------------------------------------------------------- Break calendars

function BreaksTab({ apiKey, calendars, act }: { apiKey: string; calendars: BreakCalendar[]; act: Act }) {
  const [name, setName] = useState("");

  return (
    <>
      <p className="muted small">
        A break calendar pauses the routines linked to it. For example, link school and work routines to “School
        holidays”, and give each club its own calendar.
      </p>
      <form
        className="inline-form"
        onSubmit={async (e) => {
          e.preventDefault();
          if (name.trim() && (await act(() => createCalendar(apiKey, name.trim())))) setName("");
        }}
      >
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="New calendar, e.g. School holidays" />
        <button className="btn btn-done" type="submit">
          Add
        </button>
      </form>

      {calendars.map((c) => (
        <article key={c.id} className="card manage-card calendar-card">
          <div className="calendar-head">
            <h3 className="card-title">{c.name}</h3>
            <button
              className="btn"
              onClick={() => {
                if (confirm(`Delete "${c.name}" and all its breaks?`)) act(() => deleteCalendar(apiKey, c.id));
              }}
            >
              Delete
            </button>
          </div>
          {c.periods.length === 0 && <p className="muted small">No breaks yet.</p>}
          <ul className="periods">
            {c.periods.map((p) => (
              <li key={p.id}>
                <span>
                  {p.name && <strong>{p.name}: </strong>}
                  {formatDate(p.start_date)} to {formatDate(p.end_date)}
                </span>
                <button className="btn btn-small" onClick={() => act(() => deletePeriod(apiKey, p.id))} aria-label="Remove break">
                  ✕
                </button>
              </li>
            ))}
          </ul>
          <PeriodForm onAdd={(p) => act(() => addPeriod(apiKey, c.id, p))} />
        </article>
      ))}
    </>
  );
}

function PeriodForm({ onAdd }: { onAdd: (p: { name: string; start_date: string; end_date: string }) => Promise<boolean> }) {
  const [name, setName] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [problem, setProblem] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!start || !end) return setProblem("Pick both dates.");
    if (end < start) return setProblem("The end date is before the start date.");
    setProblem("");
    if (await onAdd({ name: name.trim(), start_date: start, end_date: end })) {
      setName("");
      setStart("");
      setEnd("");
    }
  }

  return (
    <form className="period-form" onSubmit={submit}>
      <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Name (optional), e.g. Half term" />
      <label>
        From
        <input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
      </label>
      <label>
        To
        <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
      </label>
      {problem && <p className="error">{problem}</p>}
      <button className="btn" type="submit">
        Add break
      </button>
    </form>
  );
}
