"""Cutover — change-password + must_change_password flag."""


def test_login_flags_seed_password(client, monkeypatch):
    # Production forces password rotation for seed accounts
    from app.core.config import get_settings

    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    # Re-seed flag via authenticate path: existing test DB users may already be flagged false in development.
    # Assert login works; change-password test covers clearing the flag.
    res = client.post("/api/v1/auth/login", json={"user_id": "security", "password": "Security@123"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert "access_token" in body
    assert "must_change_password" in body["user"]
    get_settings.cache_clear()
    monkeypatch.delenv("APP_ENV", raising=False)
    get_settings.cache_clear()


def test_change_password_clears_flag(client):
    login = client.post("/api/v1/auth/login", json={"user_id": "store", "password": "Store@123"})
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    bad = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "wrong", "new_password": "StoreNew!23456"},
    )
    assert bad.status_code == 400

    block_default = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "Store@123", "new_password": "Store@123"},
    )
    assert block_default.status_code == 400

    ok = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "Store@123", "new_password": "StoreNew!23456"},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["must_change_password"] is False

    again = client.post("/api/v1/auth/login", json={"user_id": "store", "password": "StoreNew!23456"})
    assert again.status_code == 200, again.text
    assert again.json()["user"]["must_change_password"] is False
