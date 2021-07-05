import logging
from datetime import datetime, timezone
from typing import List


def _log(obj) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    logger = logging.getLogger(__name__)
    logger.error(obj)

class Repo:
    """Db abstraction layer"""

    def __init__(self, conn):
        self.conn = conn

    # users
    async def add_user(self, user_id) -> None:
        """Store user in DB, ignore duplicates"""
        await self.conn.execute(
            "INSERT INTO users(id, frequency, feed_active, last_sent) VALUES ($1, 21600, false, $2) ON CONFLICT DO NOTHING",
            user_id,
            datetime.now(timezone.utc)
        )
        return


    async def list_active_users(self) -> List:
        """List all bot users"""
        rows = await self.conn.fetch(
                "select id from users where feed_active = true",
            )
        return rows


    async def get_last_sent(self, user_id) -> datetime:
        row = await self.conn.fetchrow(
            "SELECT last_sent FROM users WHERE id = $1",
            user_id,
        )
        return row["last_sent"]


    async def set_last_sent(self, user_id, timestamp: datetime) -> None:
        await self.conn.execute(
            "update users set last_sent=$1 where id=$2",
            timestamp,
            int(user_id),
            )


    async def set_inactive(self, user_id) -> None:
        await self.conn.execute(
            "update users set feed_active=false where id=$1",
            int(user_id),
            )


    async def set_active(self, user_id) -> None:
        await self.conn.execute(
            "update users set feed_active=true where id=$1",
            int(user_id),
            )