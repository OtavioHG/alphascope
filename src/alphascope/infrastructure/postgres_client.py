from __future__ import annotations

from sqlalchemy import text

from alphascope.storage.database import StorageSessionLocal


class PostgresClient:
    def ping(self) -> bool:
        session = StorageSessionLocal()
        try:
            session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
        finally:
            session.close()
