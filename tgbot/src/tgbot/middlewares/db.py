from aiogram.dispatcher.middlewares import LifetimeControllerMiddleware # type: ignore

from tgbot.services.repository import Repo
from tgbot.services.feed import Feed
from tgbot.services.link import Link


class DbMiddleware(LifetimeControllerMiddleware):
    skip_patterns = ["error", "update"]

    def __init__(self, pool):
        super().__init__()
        self.pool = pool

    async def pre_process(self, obj, data, *args):
        db = await self.pool.acquire()
        data["db"] = db
        data["repo"] = Repo(db)
        data["feed"] = Feed(db)
        data["link"] = Link(db)

    async def post_process(self, obj, data, *args):
        del data["repo"]
        del data["feed"]
        del data["link"]
        db = data.get("db")
        if db:
            await db.close()
