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

// ---- Phase 2: routines and checklists (mirrors backend/app/schedule_schemas.py) ----

export type Category = "school" | "work" | "activity" | "other";

export interface Routine {
  id: number;
  title: string;
  person: string;
  category: Category;
  weekdays: number[]; // 0 = Monday ... 6 = Sunday
  time: string | null; // "HH:MM"
  items: string[];
  active: boolean;
  paused_by: number[]; // break calendar ids
}
export type RoutineIn = Omit<Routine, "id">;

export interface OneOffEvent {
  id: number;
  title: string;
  person: string;
  on_date: string; // "YYYY-MM-DD"
  time: string | null;
  items: string[];
}
export type OneOffEventIn = Omit<OneOffEvent, "id">;

export interface BreakPeriod {
  id: number;
  name: string;
  start_date: string;
  end_date: string;
}
export type BreakPeriodIn = Omit<BreakPeriod, "id">;

export interface BreakCalendar {
  id: number;
  name: string;
  periods: BreakPeriod[];
}

export interface ChecklistItem {
  name: string;
  ticked: boolean;
}

export interface DayEntry {
  source: string;
  title: string;
  person: string;
  time: string | null;
  items: ChecklistItem[];
}

export interface Day {
  day: string;
  entries: DayEntry[];
  complete: boolean;
}

export interface WeekItem {
  name: string;
  ticked: boolean;
  needed_for: string[];
}

export interface WeekCheck {
  week_start: string;
  items: WeekItem[];
  complete: boolean;
}

export interface Schedule {
  today: Day;
  tomorrow: Day | null;
  week_check: WeekCheck | null;
}

export interface Tick {
  scope: "day" | "week";
  period: string;
  source: string;
  item: string;
  ticked: boolean;
}

export const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export const CATEGORY_LABELS: Record<Category, string> = {
  school: "School",
  work: "Work",
  activity: "Activity",
  other: "Other",
};

export const CONSEQUENCE_LABELS: Record<number, string> = {
  1: "Trivial",
  2: "Minor",
  3: "Moderate",
  4: "Serious",
  5: "Critical",
};
