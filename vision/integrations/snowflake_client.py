from __future__ import annotations

from typing import Optional

import snowflake.connector


class SnowflakeLLM:
    """Thin wrapper over Snowflake Cortex COMPLETE API."""

    def __init__(
        self,
        *,
        account: str,
        user: str,
        password: str,
        role: Optional[str] = None,
        warehouse: Optional[str] = None,
        database: Optional[str] = None,
        schema: Optional[str] = None,
        model: str = "mistral-7b",
    ) -> None:
        self.account = account
        self.user = user
        self.password = password
        self.role = role
        self.warehouse = warehouse
        self.database = database
        self.schema = schema
        self.model = model

    def complete(self, prompt: str, *, model: Optional[str] = None) -> str:
        active_model = model or self.model
        conn = snowflake.connector.connect(
            account=self.account,
            user=self.user,
            password=self.password,
            role=self.role,
            warehouse=self.warehouse,
            database=self.database,
            schema=self.schema,
        )
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT SNOWFLAKE.CORTEX.COMPLETE(%s, %s) AS response",
                    (active_model, prompt),
                )
                row = cur.fetchone()
                if not row or not row[0]:
                    raise RuntimeError("Snowflake Cortex did not return a response.")
                return row[0]
        finally:
            conn.close()
