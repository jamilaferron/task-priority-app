import type {
  Board,
  BreakCalendar,
  BreakPeriodIn,
  OneOffEvent,
  OneOffEventIn,
  Routine,
  RoutineIn,
  Schedule,
  Task,
  TaskPatch,
  Tick,
} from "./types";

const KEY_STORAGE = "taskBoardApiKey";

export class AuthError extends Error {}

// The API key is typed in once on the screen and remembered in this browser.
export function loadKey(): string {
  try {
    return localStorage.getItem(KEY_STORAGE) ?? "";
  } catch {
    return "";
  }
}

export function saveKey(key: string): void {
  try {
    if (key) localStorage.setItem(KEY_STORAGE, key);
    else localStorage.removeItem(KEY_STORAGE);
  } catch {
    // Storage blocked: the key just won't be remembered after a reload.
  }
}

async function request<T>(key: string, path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", "X-API-Key": key, ...init.headers },
  });
  if (res.status === 401) throw new AuthError("Wrong API key");
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  if (res.status === 204) return undefined as T; // deletes return no body
  return res.json() as Promise<T>;
}

const send = (method: string, body?: unknown): RequestInit => ({
  method,
  body: body === undefined ? undefined : JSON.stringify(body),
});

// ---- Tasks ----
export const getBoard = (key: string) => request<Board>(key, "/tasks");

export const completeTask = (key: string, id: number) =>
  request<Task>(key, `/tasks/${id}/complete`, send("POST"));

export const updateTask = (key: string, id: number, patch: TaskPatch) =>
  request<Task>(key, `/tasks/${id}`, send("PATCH", patch));

// ---- Schedule and checklists ----
export const getSchedule = (key: string) => request<Schedule>(key, "/schedule");

export const tickItem = (key: string, tick: Tick) => request<Schedule>(key, "/checklist/tick", send("POST", tick));

// ---- Routines ----
export const getRoutines = (key: string) => request<Routine[]>(key, "/routines");
export const createRoutine = (key: string, r: RoutineIn) => request<Routine>(key, "/routines", send("POST", r));
export const updateRoutine = (key: string, id: number, r: RoutineIn) =>
  request<Routine>(key, `/routines/${id}`, send("PUT", r));
export const deleteRoutine = (key: string, id: number) => request<void>(key, `/routines/${id}`, send("DELETE"));

// ---- One-off events ----
export const getEvents = (key: string) => request<OneOffEvent[]>(key, "/events");
export const createEvent = (key: string, e: OneOffEventIn) => request<OneOffEvent>(key, "/events", send("POST", e));
export const updateEvent = (key: string, id: number, e: OneOffEventIn) =>
  request<OneOffEvent>(key, `/events/${id}`, send("PUT", e));
export const deleteEvent = (key: string, id: number) => request<void>(key, `/events/${id}`, send("DELETE"));

// ---- Break calendars ----
export const getCalendars = (key: string) => request<BreakCalendar[]>(key, "/calendars");
export const createCalendar = (key: string, name: string) =>
  request<BreakCalendar>(key, "/calendars", send("POST", { name }));
export const deleteCalendar = (key: string, id: number) => request<void>(key, `/calendars/${id}`, send("DELETE"));
export const addPeriod = (key: string, calendarId: number, p: BreakPeriodIn) =>
  request<BreakCalendar>(key, `/calendars/${calendarId}/periods`, send("POST", p));
export const deletePeriod = (key: string, id: number) => request<void>(key, `/periods/${id}`, send("DELETE"));
