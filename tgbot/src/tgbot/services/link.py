import logging

from datetime import datetime, timedelta
from tgbot.models.link import LinkData
from typing import List

def _log(obj) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    logger = logging.getLogger(__name__)
    logger.error(obj)


class Link:
    """News delivery abstraction layer"""

    def __init__(self, conn = None):
        self.conn = conn


    async def is_sent(self, user_id: int, link: str) -> bool:
        result: bool = False
        row = await self.conn.fetchrow(
            "SELECT * FROM links WHERE user_id = $1 and article_link = $2",
            user_id,
            link,
        )
        if row:
            result = True
        return result


    async def save_link(self, link: LinkData) -> None:
        await self.conn.execute('''
            insert into links (key, user_id, article_link, sent)
            values (DEFAULT, $1, $2, $3)
            ''',
            int(link.user_id),
            link.article_link,
            link.sent,
            )
        return


    async def clear_old_link(self) -> None:
        d = datetime.today() - timedelta(days=15) #to get the deletion horizon
        await self.conn.execute(
            "delete from links where sent < $1",
            d,
            )
        return