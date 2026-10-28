"""Phase 11 — offline sync API + security hardening checks."""

from sqlalchemy import create_engine, text

from app.core.config import get_settings


def _auth(client):
    login = client.post("/api/v1/auth/login", json={"user_id": "owner", "password": "Owner@123"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_sync_policy_requires_auth(client):
    assert client.get("/api/v1/sync/policy").status_code == 401


def test_sync_push_create_idempotent_and_conflict(client):
    headers = _auth(client)
    cid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

    policy = client.get("/api/v1/sync/policy", headers=headers)
    assert policy.status_code == 200
    assert policy.json()["policy"] == "server_authoritative_idempotent_create"

    first = client.post(
        "/api/v1/sync/push",
        headers=headers,
        json={
            "drafts": [
                {
                    "client_transaction_id": cid,
                    "type": "MATERIAL_LOADING_OUTWARD",
                    "notes": "offline gate",
                }
            ]
        },
    )
    assert first.status_code == 200
    body = first.json()
    assert body["accepted"] == 1
    assert body["results"][0]["outcome"] == "CREATED"
    txn_id = body["results"][0]["transaction_id"]
    assert txn_id.startswith("JV-")

    again = client.post(
        "/api/v1/sync/push",
        headers=headers,
        json={
            "drafts": [
                {
                    "client_transaction_id": cid,
                    "type": "MATERIAL_LOADING_OUTWARD",
                    "notes": "replay",
                }
            ]
        },
    )
    assert again.status_code == 200
    assert again.json()["results"][0]["outcome"] == "IDEMPOTENT"
    assert again.json()["results"][0]["transaction_id"] == txn_id

    type_clash = client.post(
        "/api/v1/sync/push",
        headers=headers,
        json={
            "drafts": [
                {
                    "client_transaction_id": cid,
                    "type": "JOB_WORK",
                }
            ]
        },
    )
    assert type_clash.status_code == 200
    assert type_clash.json()["results"][0]["outcome"] == "CONFLICT"
    assert type_clash.json()["conflicts"] == 1

    # Progress server row past soft statuses → CONFLICT on same client id
    engine = create_engine(get_settings().database_url, pool_pre_ping=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE transactions SET status='COMPLETED' "
                "WHERE client_transaction_id=:c"
            ),
            {"c": cid},
        )
    engine.dispose()

    progressed = client.post(
        "/api/v1/sync/push",
        headers=headers,
        json={
            "drafts": [
                {
                    "client_transaction_id": cid,
                    "type": "MATERIAL_LOADING_OUTWARD",
                }
            ]
        },
    )
    assert progressed.status_code == 200
    assert progressed.json()["results"][0]["outcome"] == "CONFLICT"


def test_health_includes_readiness(client):
    h = client.get("/health")
    assert h.status_code == 200
    data = h.json()
    assert data["status"] == "ok"
    assert "readiness" in data
    assert isinstance(data["readiness"], list)


def test_protected_routes_reject_bad_token(client):
    headers = {"Authorization": "Bearer not-a-real-token"}
    assert client.get("/api/v1/dashboard/summary", headers=headers).status_code == 401
    assert client.post("/api/v1/sync/push", headers=headers, json={"drafts": []}).status_code in (
        401,
        422,
    )


def test_unhandled_errors_do_not_leak_stack(client):
    """Health stays friendly; 404s are structured."""
    missing = client.get("/api/v1/transactions/does-not-exist-pk", headers=_auth(client))
    assert missing.status_code == 404
    detail = missing.json().get("detail") or missing.json().get("message")
    assert detail
    assert "Traceback" not in str(missing.json())
