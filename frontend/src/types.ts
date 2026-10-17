// Mirrors the backend's TaskOut and BoardOut (backend/app/schemas.py).

export type TaskStatus = "needs_info" | "active" | "done";

export interface Task {
  id: number;
  title: string;
  raw_input: string;
  deadline: string | null; // ISO, UTC
  estimated_minutes: number | null;
  consequence: number | null; // 1-5
  status: TaskStatus;
  pending_question: string | null;
  created_at: string;
  completed_at: string | null;
  latest_start: string | null;
}

export interface Board {
  overdue: Task[];
  ranked: Task[];
  whenever: Task[];
  needs_info: Task[];
  generated_at: string;
}

export interface TaskPatch {
  title?: string;
  deadline?: string | null; // null = move to the whenever pile
  estimated_minutes?: number;
  consequence?: number;
}

export const CONSEQUENCE_LABELS: Record<number, string> = {
  1: "Trivial",
  2: "Minor",
  3: "Moderate",
  4: "Serious",
  5: "Critical",
};
