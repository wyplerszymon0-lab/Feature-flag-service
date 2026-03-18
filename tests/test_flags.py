import pytest
from fastapi.testclient import TestClient
from main import app, flags


@pytest.fixture(autouse=True)
def clear_flags():
    flags.clear()
    yield


client = TestClient(app)


def make_flag(key="test-flag", strategy="all", enabled=True, **kwargs):
    rule = {"strategy": strategy}
    rule.update(kwargs)
    return client.post("/flags", json={"key": key, "enabled": enabled, "rule": rule})


def test_create_flag():
    resp = make_flag()
    assert resp.status_code == 201
    assert resp.json()["key"] == "test-flag"


def test_create_duplicate_flag():
    make_flag()
    resp = make_flag()
    assert resp.status_code == 409


def test_get_flag():
    make_flag(key="my-flag")
    resp = client.get("/flags/my-flag")
    assert resp.status_code == 200
    assert resp.json()["key"] == "my-flag"


def test_get_flag_not_found():
    resp = client.get("/flags/nonexistent")
    assert resp.status_code == 404


def test_list_flags():
    make_flag(key="flag-a")
    make_flag(key="flag-b")
    resp = client.get("/flags")
    assert resp.json()["total"] == 2


def test_update_flag():
    make_flag(key="toggle-flag", enabled=False)
    resp = client.patch("/flags/toggle-flag", json={"enabled": True})
    assert resp.json()["enabled"] is True


def test_delete_flag():
    make_flag(key="to-delete")
    resp = client.delete("/flags/to-delete")
    assert resp.status_code == 204
    assert client.get("/flags/to-delete").status_code == 404


def test_evaluate_all_strategy():
    make_flag(key="open-flag", strategy="all", enabled=True)
    resp = client.post("/flags/open-flag/evaluate", json={"user_id": "user-123"})
    assert resp.json()["enabled"] is True
    assert resp.json()["reason"] == "strategy_all"


def test_evaluate_disabled_flag():
    make_flag(key="off-flag", enabled=False)
    resp = client.post("/flags/off-flag/evaluate", json={"user_id": "user-123"})
    assert resp.json()["enabled"] is False
    assert resp.json()["reason"] == "flag_disabled"


def test_evaluate_user_strategy_match():
    make_flag(key="user-flag", strategy="users", user_ids=["alice", "bob"])
    resp = client.post("/flags/user-flag/evaluate", json={"user_id": "alice"})
    assert resp.json()["enabled"] is True


def test_evaluate_user_strategy_no_match():
    make_flag(key="user-flag", strategy="users", user_ids=["alice"])
    resp = client.post("/flags/user-flag/evaluate", json={"user_id": "charlie"})
    assert resp.json()["enabled"] is False


def test_evaluate_group_strategy_match():
    make_flag(key="beta-flag", strategy="groups", groups=["beta-testers"])
    resp = client.post("/flags/beta-flag/evaluate", json={"user_id": "u1", "groups": ["beta-testers"]})
    assert resp.json()["enabled"] is True


def test_evaluate_percentage_deterministic():
    make_flag(key="pct-flag", strategy="percentage", percentage=50.0)
    r1 = client.post("/flags/pct-flag/evaluate", json={"user_id": "stable-user"})
    r2 = client.post("/flags/pct-flag/evaluate", json={"user_id": "stable-user"})
    assert r1.json()["enabled"] == r2.json()["enabled"]


def test_evaluate_batch():
    make_flag(key="flag-x", strategy="all", enabled=True)
    make_flag(key="flag-y", enabled=False)
    resp = client.post("/evaluate/batch?keys=flag-x&keys=flag-y", json={"user_id": "u1"})
    results = {r["flag_key"]: r["enabled"] for r in resp.json()["results"]}
    assert results["flag-x"] is True
    assert results["flag-y"] is False


def test_health():
    resp = client.get("/health")
    assert resp.json()["status"] == "ok"
```

---

**`requirements.txt`**
```
fastapi==0.115.0
uvicorn==0.30.0
pydantic==2.7.0
pytest==8.2.0
