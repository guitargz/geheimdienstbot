import logging

from aiogram import Dispatcher # type: ignore
from aiogram.dispatcher import FSMContext # type: ignore
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup # type: ignore

from tgbot.models.role import UserRole
from tgbot.services.repository import Repo
from tgbot.services.feed import Feed

async def admin_start(m: Message):
    ...
    #await m.reply("Hello, admin!")
    
def register_admin(dp: Dispatcher):
    dp.register_message_handler(admin_start, commands=["start"], state="*", role=UserRole.ADMIN)
    # # or you can pass multiple roles:
    # dp.register_message_handler(admin_start, commands=["start"], state="*", role=[UserRole.ADMIN])
    # # or use another filter:
    # dp.register_message_handler(admin_start, commands=["start"], state="*", is_admin=True)
