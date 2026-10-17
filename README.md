# Task Priority App

Say a task to Siri. An AI pulls out the deadline, how long it takes and how bad it is to miss.
The code ranks everything by **latest start time**, and a wall screen shows what to start now.

```
backend/    Python + FastAPI + SQLite (the API, the AI step, the ranking)
frontend/   React + TypeScript (the wall screen)
```

## Where things live

| File | What it does |
| --- | --- |
| `backend/app/main.py` | The task endpoints |
| `backend/app/auth.py` | The API key check |
| `backend/app/ai.py` | The AI prompt, the consequence scale, and response validation |
| `backend/app/ranking.py` | Buffers and sorting — no AI, just rules |
| `backend/app/services.py` | Add/clarify logic, including the two-follow-up limit |
| `backend/app/models.py` | All database tables |
| `backend/app/schedule.py` | Routine rules: which days, holiday pauses, when checklists appear |
| `backend/app/schedule_api.py` | Endpoints for routines, events, break calendars and ticks |
| `frontend/src/App.tsx` | Wall screen: checklist prompt, start now, today's agenda, lists |
| `frontend/src/Checklists.tsx` | Week-ahead, tomorrow and today checklists |
| `frontend/src/Manage.tsx` | Phone page for routines, events and break calendars |
| `frontend/src/TaskCard.tsx` | One task, with Done and Edit |

## 1. Run the backend

Needs Python 3.10 or newer.

```bash
cd backend
python3 -m venv .venv               # on a Mac, use python3 here
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then edit .env
```

In `.env`, set `API_KEY` to a long random string and `ANTHROPIC_API_KEY` to your key from console.anthropic.com. To make a random key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Run the tests (they use a fake AI, so no API key or cost needed):

```bash
pytest
```

Start the server:

```bash
uvicorn app.main:app --reload
```

Open **http://localhost:8000/docs**. Click **Authorize**, paste your `API_KEY`, then try `POST /tasks` with:

```json
{ "text": "pay the council tax by Friday" }
```

Try a vague one too ("book the MOT") to see the follow-up question.

## 2. Run the wall screen

Needs Node 18 or newer. In a second terminal, with the backend still running:

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** and enter your `API_KEY`. The screen refreshes every 30 seconds.

To serve the screen from the backend itself (one server, one address), run `npm run build`. FastAPI then serves it at http://localhost:8000.

## 3. Build the Siri Shortcut

To test from your iPhone before deploying, start the backend so other devices on your Wi-Fi can reach it:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Find your laptop's local IP address (e.g. `192.168.1.20`). Below, `SERVER` means `http://192.168.1.20:8000` for now, and your HTTPS address once deployed.

In the **Shortcuts** app, create a new shortcut called **Add task** (you'll say "Hey Siri, add task"), then add these actions in order:

1. **Dictate Text**.
2. **Get Contents of URL**
   - URL: `SERVER/tasks`
   - Method: **POST**
   - Headers: `X-API-Key` = your API key
   - Request Body: **JSON**, add a Text field `text` = *Dictated Text*
3. **Set Variable** `Reply` to *Contents of URL*.
4. **Repeat** 2 times, containing:
   1. **Get Dictionary Value** `status` from `Reply`.
   2. **If** *Dictionary Value* **is** `needs_info`:
      1. **Get Dictionary Value** `question` from `Reply`.
      2. **Ask for Input** (Text), prompt = *Dictionary Value*.
      3. **Get Dictionary Value** `task_id` from `Reply`.
      4. **Get Contents of URL**
         - URL: `SERVER/tasks/` followed by *Dictionary Value* (the task id), then `/clarify`
         - Method **POST**, the same `X-API-Key` header
         - Request Body **JSON**: Text field `answer` = *Provided Input*
      5. **Set Variable** `Reply` to *Contents of URL*.
   3. **End If**.
5. **End Repeat**.
6. **Get Dictionary Value** `message` from `Reply`.
7. **Speak Text** *Dictionary Value*.

If Siri says nothing at the end, the server probably returned an error. Check the terminal running uvicorn.

## 4. Routines and checklists

Restart the backend after updating; it creates the new tables by itself (your tasks are kept).

**Open the manage page:** http://localhost:5173/#/manage, or tap **Routines** on the screen.

**On your phone:** start the screen with `npm run dev -- --host`, then open `http://<laptop IP>:5173/#/manage` in Safari. Tap **Share → Add to Home Screen** to open it like an app.

**Set up in this order:**

1. **Breaks tab:** add "School holidays" with this year's holiday dates, then a calendar for each club, e.g. "Performing arts breaks".
2. **Routines tab:** add each routine with its days, time and checklist. Tick the calendars that pause it: school and work routines → School holidays; each club → its own calendar; weekend activities → none.
3. **Events tab:** one-off things like appointments.

**When checklists appear on the screen:**

| When | What |
| --- | --- |
| Sunday | Week-ahead check: every school and work item for the coming week |
| Monday | The same check again, if not finished on Sunday |
| From 18:00 | Tomorrow's checklist |
| Each day | Today's checklist until everything is ticked |

A prompt appears above "Start now"; tap it to tick things off. Times and rules are at the top of `backend/app/schedule.py`.

## How ranking works

```
latest start = deadline − estimated duration − buffer
```

| Consequence | Buffer |
| --- | --- |
| 1 Trivial, 2 Minor | none |
| 3 Moderate | 2 hours |
| 4 Serious | 1 day |
| 5 Critical | 2 days |

Overdue tasks are pinned to the top. Tasks without a deadline go to the whenever pile. Tap **Edit** on any task and give it a deadline to promote it.

## Small additions to the spec

- **`clarifications` field:** stores each follow-up question and answer so the AI sees the whole conversation.
- **Date without a time:** if you only give a day ("by Friday"), the AI assumes 17:00. Change this in `SYSTEM_PROMPT` in `ai.py`.
- **"Needs details" section:** if you abandon a Siri follow-up, the task appears there so you can finish it with Edit.
- **Running out of questions:** after two follow-ups, a task with no clear deadline goes to the whenever pile.

## Deploying (later)

Any platform that runs Python (Render, Railway, Fly.io) will work:

- Build the frontend (`npm run build`) so FastAPI serves it.
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT` from `backend/`.
- Set `API_KEY`, `ANTHROPIC_API_KEY` and `APP_TIMEZONE` as environment variables.
- Point `DATABASE_URL` at a persistent disk (e.g. `sqlite:////data/tasks.db`), or tasks vanish on redeploy.
