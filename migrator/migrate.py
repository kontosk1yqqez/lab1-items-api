"""Консольний застосунок міграцій.

Чекає, поки база даних стане доступною, і застосовує всі міграції Alembic
(`alembic upgrade head`) до бази, вказаної в DATABASE_URL.
Використання:  python migrate.py [upgrade|downgrade|current|history] [revision]
"""
import os
import sys
import time
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

HERE = Path(__file__).resolve().parent


def wait_for_db(url: str, attempts: int = 30, delay: float = 2.0) -> None:
    engine = create_engine(url)
    for attempt in range(1, attempts + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"[migrator] database is reachable (attempt {attempt})", flush=True)
            return
        except Exception as exc:  # noqa: BLE001
            print(f"[migrator] waiting for database ({attempt}/{attempts}): {exc.__class__.__name__}", flush=True)
            time.sleep(delay)
    raise SystemExit("[migrator] database is not reachable, giving up")


def main(argv: list[str]) -> int:
    url = os.getenv("DATABASE_URL")
    if not url:
        print("[migrator] DATABASE_URL is not set", file=sys.stderr)
        return 2
    action = argv[1] if len(argv) > 1 else "upgrade"
    revision = argv[2] if len(argv) > 2 else ("head" if action == "upgrade" else "-1")

    wait_for_db(url)
    cfg = Config(str(HERE / "alembic.ini"))
    cfg.set_main_option("script_location", str(HERE / "migrations"))

    if action == "upgrade":
        command.upgrade(cfg, revision)
    elif action == "downgrade":
        command.downgrade(cfg, revision)
    elif action == "current":
        command.current(cfg, verbose=True)
    elif action == "history":
        command.history(cfg, verbose=True)
    else:
        print(f"[migrator] unknown action: {action}", file=sys.stderr)
        return 2
    print(f"[migrator] '{action} {revision}' completed", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
