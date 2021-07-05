import logging

from aiogram.dispatcher.middlewares import LifetimeControllerMiddleware # type: ignore

from tgbot.models.role import UserRole

def _log(obj) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    logger = logging.getLogger(__name__)
    logger.error(obj)

class RoleMiddleware(LifetimeControllerMiddleware):
    skip_patterns = ["error", "update"]

    def __init__(self, admin_id: int):
        super().__init__()
        self.admin_id = admin_id


    async def pre_process(self, obj, data, *args):
        if not hasattr(obj, "chat"):
            data["role"] = None
        elif obj.chat.type == "channel":
            data["role"] = UserRole.USER
        elif obj.chat.type == "private" and obj.from_user.id == self.admin_id:
            data["role"] = UserRole.ADMIN
        else:
            data["role"] = UserRole.USER


    async def post_process(self, obj, data, *args):
        del data["role"]
