import asyncio
import asyncpg # type: ignore
import logging

from aiogram import Bot, Dispatcher # type: ignore
from aiogram.contrib.fsm_storage.memory import MemoryStorage # type: ignore
from aiogram.contrib.fsm_storage.redis import RedisStorage # type: ignore
#from aiogram.contrib.middlewares.logging import LoggingMiddleware  # type: ignore #comment to switch off bot logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler # type: ignore

from tgbot.config import load_config
from tgbot.filters.role import RoleFilter, AdminFilter
from tgbot.handlers.admin import register_admin
from tgbot.handlers.user import register_user, start_menu, feed_list, feed_delete, feed_edit, rss_feed_create_button, rss_feed_create, \
                                html_feed_create_button, html_feed_create, search_add_button, search_add, search_delete, subscription_start, \
                                subscription_stop, subscription_items
from tgbot.middlewares.db import DbMiddleware
from tgbot.middlewares.role import RoleMiddleware

def _log(obj) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    logger = logging.getLogger(__name__)
    logger.error(obj)


async def subscription_loop(dp: Dispatcher, pool) -> None:
    items = await subscription_items(pool)
    _log(items)
    for item in items:
        await dp.bot.send_message(int(item[0]), item[1])


def schedule_jobs(scheduler, dp, pool):
    scheduler.add_job(subscription_loop, "interval", seconds=300, args=(dp, pool))


async def main():
    _log("Starting bot")
    config = load_config("bot.ini")

    if config.tg_bot.use_redis:
        storage = RedisStorage()
    else:
        storage = MemoryStorage()
    
    pool = await asyncpg.create_pool(
        user=config.db.user,
        password=config.db.password,
        database=config.db.database,
        host=config.db.host,
        #echo=False,
    )
    

    bot = Bot(token=config.tg_bot.token)
    dp = Dispatcher(bot, storage=storage)
    dp.middleware.setup(DbMiddleware(pool))
    dp.middleware.setup(RoleMiddleware(config.tg_bot.admin_id))
    #dp.middleware.setup(LoggingMiddleware()) #comment to switch off bot logging
    dp.filters_factory.bind(RoleFilter)
    dp.filters_factory.bind(AdminFilter)

    scheduler = AsyncIOScheduler()
    #logging.getLogger('apscheduler').setLevel(logging.DEBUG) #comment to switch off the apscheduler logging
    schedule_jobs(scheduler, dp, pool)
    

    register_admin(dp)
    register_user(dp)
    start_menu(dp)
    feed_list(dp)
    feed_delete(dp)
    feed_edit(dp)
    rss_feed_create_button(dp)
    rss_feed_create(dp)
    html_feed_create_button(dp)
    html_feed_create(dp)
    search_add_button(dp)
    search_add(dp)
    search_delete(dp)
    subscription_start(dp)
    subscription_stop(dp)


    # start
    try:
        scheduler.start()
        await dp.start_polling()
    finally:
        await dp.storage.close()
        await dp.storage.wait_closed()
        await bot.session.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        _log("Bot stopped!")
