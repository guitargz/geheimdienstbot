import typing

from aiogram.dispatcher.filters import BoundFilter # type: ignore
from aiogram.dispatcher.handler import ctx_data # type: ignore
from aiogram.types.base import TelegramObject # type: ignore

from tgbot.models.role import UserRole


class RoleFilter(BoundFilter):
    key = 'role' #this would be the name of the parameter for calling dp.register_message_handler

    def __init__(self, role: typing.Union[None, UserRole, typing.Collection[UserRole]] = None):
        if role is None:
            self.roles = None
        elif isinstance(role, UserRole):
            self.roles = {role}
        else:
            self.roles = set(role)

    async def check(self, obj: TelegramObject):
        if self.roles is None:
            return True
        data = ctx_data.get()
        return data.get("role") in self.roles


class AdminFilter(BoundFilter):
    key = 'is_admin'

    def __init__(self, is_admin: typing.Optional[bool] = None):
        self.is_admin = is_admin

    async def check(self, obj: TelegramObject):
        if self.is_admin is None:
            return True
        data = ctx_data.get()
        return (data.get("role") is UserRole.ADMIN) == self.is_admin
