import type { Board, Task, TaskPatch } from "./types";

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
  return res.json() as Promise<T>;
}

export const getBoard = (key: string) => request<Board>(key, "/tasks");

export const completeTask = (key: string, id: number) =>
  request<Task>(key, `/tasks/${id}/complete`, { method: "POST" });

export const updateTask = (key: string, id: number, patch: TaskPatch) =>
  request<Task>(key, `/tasks/${id}`, { method: "PATCH", body: JSON.stringify(patch) });
