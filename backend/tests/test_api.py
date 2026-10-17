from datetime import datetime, timedelta, timezone

from app.ai import Extraction
from conftest import HEADERS

SOON = datetime.now(timezone.utc) + timedelta(days=3)


def test_requests_without_the_key_are_rejected(client):
    assert client.get("/tasks").status_code == 401
    assert client.get("/tasks", headers={"X-API-Key": "wrong"}).status_code == 401


def test_add_task_with_everything_needed(client, fake_ai):
    fake_ai.replies.append(Extraction(title="Pay the tax bill", deadline=SOON, estimated_minutes=20, consequence=5))
    r = client.post("/tasks", json={"text": "pay the tax bill by friday"}, headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["status"] == "added"
    assert r.json()["message"].startswith("Added Pay the tax bill, due")

    board = client.get("/tasks", headers=HEADERS).json()
    assert [t["title"] for t in board["ranked"]] == ["Pay the tax bill"]


def test_missing_deadline_triggers_follow_up_then_clarify(client, fake_ai):
    fake_ai.replies.append(Extraction(title="Book the MOT", estimated_minutes=10, consequence=3))
    r = client.post("/tasks", json={"text": "book the MOT"}, headers=HEADERS).json()
    assert r["status"] == "needs_info"
    assert r["question"] == "Is there a deadline, or is this a whenever task?"

    fake_ai.replies.append(Extraction(title="Book the MOT", deadline=SOON, estimated_minutes=10, consequence=3))
    r2 = client.post(f"/tasks/{r['task_id']}/clarify", json={"answer": "end of the month"}, headers=HEADERS).json()
    assert r2["status"] == "added"
    assert fake_ai.calls[1]["clarifications"] == [
        {"question": "Is there a deadline, or is this a whenever task?", "answer": "end of the month"}
    ]


def test_whenever_task_goes_to_the_pile(client, fake_ai):
    fake_ai.replies.append(Extraction(title="Sort the guest bedroom", is_whenever=True, estimated_minutes=120, consequence=2))
    r = client.post("/tasks", json={"text": "sort the guest bedroom, no rush"}, headers=HEADERS).json()
    assert r["status"] == "added"
    assert "whenever pile" in r["message"]
    board = client.get("/tasks", headers=HEADERS).json()
    assert [t["title"] for t in board["whenever"]] == ["Sort the guest bedroom"]


def test_after_two_follow_ups_the_ai_must_guess(client, fake_ai):
    vague = Extraction(title="Do the thing", estimated_minutes=30, consequence=3)
    fake_ai.replies += [vague, vague, vague]
    r = client.post("/tasks", json={"text": "do the thing"}, headers=HEADERS).json()
    client.post(f"/tasks/{r['task_id']}/clarify", json={"answer": "not sure"}, headers=HEADERS)
    final = client.post(f"/tasks/{r['task_id']}/clarify", json={"answer": "dunno"}, headers=HEADERS).json()

    assert [c["allow_question"] for c in fake_ai.calls] == [True, True, False]
    assert final["status"] == "added"  # no deadline after two tries -> whenever pile
    assert "whenever pile" in final["message"]


def test_promote_whenever_task_and_complete_it(client, fake_ai):
    fake_ai.replies.append(Extraction(title="Sort the guest bedroom", is_whenever=True, estimated_minutes=120, consequence=2))
    task_id = client.post("/tasks", json={"text": "sort guest bedroom whenever"}, headers=HEADERS).json()["task_id"]

    r = client.patch(f"/tasks/{task_id}", json={"deadline": SOON.isoformat(), "consequence": 4}, headers=HEADERS)
    assert r.status_code == 200
    board = client.get("/tasks", headers=HEADERS).json()
    assert [t["id"] for t in board["ranked"]] == [task_id]
    assert board["whenever"] == []

    client.post(f"/tasks/{task_id}/complete", headers=HEADERS)
    board = client.get("/tasks", headers=HEADERS).json()
    assert board["ranked"] == []


def test_editing_a_needs_info_task_makes_it_active(client, fake_ai):
    fake_ai.replies.append(Extraction(title="Call the plumber", estimated_minutes=10, consequence=3))
    task_id = client.post("/tasks", json={"text": "call the plumber"}, headers=HEADERS).json()["task_id"]
    client.patch(f"/tasks/{task_id}", json={"deadline": SOON.isoformat()}, headers=HEADERS)
    board = client.get("/tasks", headers=HEADERS).json()
    assert board["needs_info"] == []
    assert [t["id"] for t in board["ranked"]] == [task_id]
