"""Quick Aiven MySQL connectivity check. Run from backend/: python ../scripts/test-aiven-mysql.py"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from dotenv import load_dotenv
import pymysql

load_dotenv(Path(__file__).resolve().parents[1] / "backend" / ".env")

url = os.environ.get("DATABASE_URL", "")
# mysql+pymysql://user:pass@host:port/db?...
try:
    rest = url.split("://", 1)[1]
    creds, hostpart = rest.split("@", 1)
    user, password = creds.split(":", 1)
    hostport, dbpart = hostpart.split("/", 1)
    host, port_s = hostport.rsplit(":", 1)
    database = dbpart.split("?", 1)[0]
    port = int(port_s)
except Exception as exc:  # noqa: BLE001
    print("Could not parse DATABASE_URL:", exc)
    sys.exit(1)

print(f"Connecting to {host}:{port}/{database} as {user} …")
try:
    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset="utf8mb4",
        connect_timeout=20,
        ssl={},  # TLS on (Aiven REQUIRED)
    )
except Exception as exc:  # noqa: BLE001
    print("FAILED:", type(exc).__name__, exc)
    print("\nIf getaddrinfo / Non-existent domain: copy Host again from Aiven Overview.")
    sys.exit(2)

with conn.cursor() as cur:
    cur.execute("SELECT VERSION(), DATABASE(), CURRENT_USER()")
    print("OK:", cur.fetchone())
conn.close()
