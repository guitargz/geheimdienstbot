from datetime import datetime, timezone
import logging
from typing import List, Tuple

from aiogram import Dispatcher # type: ignore
from aiogram.dispatcher import FSMContext # type: ignore
from aiogram.dispatcher.filters.state import State, StatesGroup # type: ignore
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery # type: ignore
from aiogram.utils.callback_data import CallbackData # type: ignore

from tgbot.models.link import LinkData
from tgbot.models.role import UserRole
from tgbot.services.repository import Repo
from tgbot.services.feed import Feed
from tgbot.services.link import Link

cb = CallbackData("post", "line", "action")

class UserAction(StatesGroup):
    adding_search = State()
    creating_rss = State()
    creating_html = State()


def _log(obj) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    logger = logging.getLogger(__name__)
    logger.error(obj)

def get_keyboard_home():
    # Generate keyboard
    buttons = [
        InlineKeyboardButton(text="Create RSS Feed", callback_data="rss_feed_create_button"),
        InlineKeyboardButton(text="Create Google Feed", callback_data="html_feed_create_button"),
        InlineKeyboardButton(text="Start subscription", callback_data="subscription_start"),
        InlineKeyboardButton(text="Stop subscription", callback_data="subscription_stop"),
        InlineKeyboardButton(
            text="List/edit Feeds", 
            callback_data=cb.new(
                line = 0,
                action = "feed_list",
            )
        ),
    ]
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(*buttons)
    return keyboard


def get_keyboard_feedlist(line:int):
    # Generate keyboard
    buttons = [
        InlineKeyboardButton(
            text="Previous", 
            callback_data=cb.new(
                line = int(line)-10,
                action = "feed_list",
            )
        ),
        InlineKeyboardButton(
            text="Next", 
            callback_data=cb.new(
                line = int(line)+10,
                action = "feed_list",
            )
        ),
        InlineKeyboardButton(
            text="Back", 
            callback_data="start_menu"),
    ]
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(*buttons)
    return keyboard

def get_keyboard_searchlist():
    # Generate keyboard
    buttons = [
        InlineKeyboardButton(
            text="Add", 
            callback_data="search_add_button"
            ),
        InlineKeyboardButton(
            text="Back", 
            callback_data="start_menu"
            ),
        ]
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(*buttons)
    return keyboard


async def user_start(m: Message, state: FSMContext, repo: Repo, feed: Feed, link: Link):
    await state.finish()
    await state.update_data(subscription_stopped=True)
    #await repo.add_user(m.from_user.id)
    await repo.add_user(m.chat.id)
    #await m.reply(f"Hello, user!")
    await m.answer(
        "Hello! Please choose an action below.",
        #await feed.new_rss_items(m.from_user.id, repo, link),
        #await feed.new_google_search(m.from_user.id, link),
        reply_markup=get_keyboard_home(),
    )


async def menu_start(call: CallbackQuery, state: FSMContext):
    await state.finish()
    await call.message.answer(
            "What should the bot do?",
            reply_markup=get_keyboard_home(),
        )
    await call.answer()


async def list_feed(call: CallbackQuery, state: FSMContext, callback_data: dict, feed: Feed):
    #feeds = await feed.list_feeds(call.from_user.id, int(callback_data["line"]), False, "ANY('{html, rss}')")
    feeds = await feed.list_feeds(call["message"]["chat"]["id"], int(callback_data["line"]), False, "ANY('{html, rss}')")
    if not feeds:
        await call.message.answer("End of feeds list")
    else:
        await state.update_data(feedlist=feeds)
        feeds_message = [
            f"{row.id}. {row.feed_link}: {row.search_string} ({row.feed_type})\n"
            f"Delete: /delfeed{row.id}, Edit: /edit{row.id} \n\n" 
            for row in feeds
            ]
        await call.message.answer(
            "".join(feeds_message),
            reply_markup=get_keyboard_feedlist(callback_data["line"]),
            )
    await call.answer()


async def delete_feed(m: Message, state: FSMContext, feed: Feed):
    data = await state.get_data()
    if "@" in m.text: #bot in a group
        feed_id = int(m.text[8:-17])
    else: #bot in a private chat
        feed_id = int(m.text[8:])
    deleted_feed = [feeds for feeds in data["feedlist"] if feeds.id == feed_id]
    link = deleted_feed[0].feed_link
    await feed.delete_feeds(
        #m.from_user.id,
        m.chat.id,
        link,
        )
    answer_message = f"The feed {link} has been deleted. \n What should the bot do next?"
    await m.answer(
        answer_message,
        reply_markup=get_keyboard_home(),
        )


async def edit_feed(m: Message, state: FSMContext, feed: Feed):
    data = await state.get_data()
    if "@" in m.text: #bot in a group
        feed_id = int(m.text[5:-17])
    else: #bot in a private chat
        feed_id = int(m.text[5:])  
    edited_feed = [feeds for feeds in data["feedlist"] if feeds.id == feed_id]
    link = edited_feed[0].feed_link
    search_strings = edited_feed[0].search_string
    await state.update_data(edited_link=link, edited_search_string=search_strings)
    search_message = [
            f"{index}. {row}\n"
            f"Delete: /delsearch{index} \n\n" 
            for index, row in enumerate(search_strings)
            ]
    await m.answer(
            "".join(search_message),
            reply_markup=get_keyboard_searchlist(),
            )


async def create_rss_feed_button(call: CallbackQuery, state: FSMContext):
    await call.message.answer(
            "Please send a new RSS feed link",
        )
    await UserAction.creating_rss.set()
    data = await state.get_data() #
    await call.answer()


async def create_rss_feed(m: Message, state: FSMContext, feed: Feed):
    new_link = m.text.lower()
    #if await feed.feed_exists(m.from_user.id, new_link):
    if await feed.feed_exists(m.chat.id, new_link):
        await state.finish()
        message = f"You are already subscribed to this feed.\nWhat should the bot do next?"
        await m.answer(
        "".join(message),
        reply_markup=get_keyboard_home(),
        )
    else:
        await state.update_data(new_rss_feed=new_link)
        message = ( 
            f"Please enter the search string for the feed <code>{new_link}</code>\n"
            f"You can add several keywords separated by comma and space like <code>'apple, google'</code>"
        )
        data = await state.get_data() #
        await UserAction.adding_search.set()
        await m.answer(
        "".join(message),
        parse_mode = "HTML",
        )
        

async def create_html_feed_button(call: CallbackQuery, state: FSMContext):
    await call.message.answer(
            "Please send a new Google Search feed link (in which site the search should happen). Example: <code>'apple.com'</code>",
            parse_mode = "HTML",
        )
    await UserAction.creating_html.set()
    await call.answer()


async def create_html_feed(m: Message, state: FSMContext, feed: Feed):
    new_link = m.text.lower()
    #if await feed.feed_exists(m.from_user.id, new_link):
    if await feed.feed_exists(m.chat.id, new_link):
        await state.finish()
        message = f"You are already subscribed to this feed.\nWhat should the bot do next?"
        await m.answer(
        "".join(message),
        reply_markup=get_keyboard_home(),
        )
    else:
        await state.update_data(new_html_feed=new_link)
        message = ( 
            f"Please enter the search string for the feed {new_link}\n"
            f"You can add several keywords separated by comma and space like <code>'apple, google'</code>"
        )
        await UserAction.adding_search.set()
        await m.answer(
        "".join(message),
        parse_mode = "HTML",
        )


async def add_search_button(call: CallbackQuery, state: FSMContext):
    await call.message.answer(
            "Please send a new search string",
        )
    await UserAction.adding_search.set()
    await call.answer()


async def add_search(m: Message, state: FSMContext, feed: Feed):
    data = await state.get_data()
    if "edited_link" in data.keys(): #changing existing feed
        link = data["edited_link"]
        search_strings = data["edited_search_string"]
        search_strings.append(m.text.lower())
        await state.finish()
        await feed.update_search(
            search_strings,
            #m.from_user.id,
            m.chat.id,
            link,
            )
    else: #adding new feed
        if "new_rss_feed" in data.keys():
            data_key = "new_rss_feed"
            feed_type = "rss"
        else:
            data_key = "new_html_feed"
            feed_type = "html"
        link = data[data_key]
        search_strings = []
        search_strings.append(m.text.lower())
        await state.finish()
        await feed.create_feed(
            search_strings,
            #m.from_user.id,
            m.chat.id,
            link,
            feed_type,
        )
    answer_message = f"The search string <code>'{m.text.lower()}'</code> has been added for the feed <code>{link}</code>. \nWhat should the bot do next?"
    await m.answer(
        answer_message,
        reply_markup=get_keyboard_home(),
        parse_mode="HTML",
        )


async def delete_search(m: Message, state: FSMContext, feed: Feed):
    data = await state.get_data()    
    if "@" in m.text: #bot in a group
        search_id = int(m.text[10:-17])
    else: #bot in a private chat
        search_id = int(m.text[10:])
    link = data["edited_link"]
    search_strings = data["edited_search_string"]
    answer_message = (
        f"The search string <code>'{search_strings[search_id]}'</code> has been deleted for the feed <code>{link}</code>.\n"
        f"What should the bot do next?"
        )
    search_strings.pop(search_id)
    await feed.update_search(
        search_strings,
        #m.from_user.id,
        m.chat.id,
        link,
        )
    await state.finish()
    await m.answer(
        answer_message,
        reply_markup=get_keyboard_home(),
        parse_mode="HTML",
        )


async def start_subscription(call: CallbackQuery, state: FSMContext, repo: Repo):
    #await repo.set_active(call.from_user.id)
    await repo.set_active(call["message"]["chat"]["id"])
    await call.message.answer("Subscription has been started. You will receive messages automatically. Please execute /start and select 'Stop Subscription' to cancel.")
    await call.answer()         


async def stop_subscription(call: CallbackQuery, state: FSMContext, repo: Repo):
    #await repo.set_active(call.from_user.id)
    await repo.set_inactive(call["message"]["chat"]["id"])
    await call.message.answer("Subscription has been stopped. You will not receive messages anymore. Please execute /start and select 'Start Subscription' to continue.")
    await call.answer() 


async def subscription_items(pool) -> List[Tuple]:
    db = await pool.acquire()
    repo = Repo(db)
    feed = Feed(db)
    link = Link(db)
    users = await repo.list_active_users()
    result: List = []
    await link.clear_old_link() # delete old saved links
    for user in users:
        user = user["id"]
        new_items = await feed.new_rss_items(int(user), repo, link)
        new_items.extend(
            await feed.new_google_search(int(user), link)
            )
        #await repo.set_last_sent(int(user), datetime.now(timezone.utc)) #the user.last_sent field is not used at the moment
        for item in new_items:
            sent_link = LinkData(
                user,
                item,
                datetime.now(timezone.utc)
            )
            await link.save_link(sent_link)
            user_item = (user, item)
            result.append(user_item)
    await db.close()
    return result


def register_user(dp: Dispatcher):
    dp.register_message_handler(user_start, commands=["start"], state="*", role=UserRole.USER)
    #dp.register_channel_post_handler(user_start, lambda message: message.text.startswith('/start'), state="*", role=UserRole.USER)


def start_menu(dp: Dispatcher):
    dp.register_callback_query_handler(menu_start, state="*", text="start_menu")    


def feed_list(dp: Dispatcher):
    dp.register_callback_query_handler(list_feed, cb.filter(action=["feed_list"]))


def feed_delete(dp: Dispatcher):
    dp.register_message_handler(delete_feed, lambda message: message.text.startswith('/delfeed'), role=UserRole.USER)
    #dp.register_channel_post_handler(delete_feed, lambda message: message.text.startswith('/delfeed'), role=UserRole.USER)


def feed_edit(dp: Dispatcher):
    dp.register_message_handler(edit_feed, lambda message: message.text.startswith('/edit'), role=UserRole.USER)
    #dp.register_channel_post_handler(edit_feed, lambda message: message.text.startswith('/edit'), role=UserRole.USER)


def rss_feed_create_button(dp: Dispatcher):
    dp.register_callback_query_handler(create_rss_feed_button, text="rss_feed_create_button")


def rss_feed_create(dp: Dispatcher):
    dp.register_message_handler(create_rss_feed, state=UserAction.creating_rss, role=UserRole.USER)
    #dp.register_channel_post_handler(create_rss_feed, state=UserAction.creating_rss, role=UserRole.USER)


def html_feed_create_button(dp: Dispatcher):
    dp.register_callback_query_handler(create_html_feed_button, text="html_feed_create_button")


def html_feed_create(dp: Dispatcher):
    dp.register_message_handler(create_html_feed, state=UserAction.creating_html, role=UserRole.USER)
    #dp.register_channel_post_handler(create_html_feed, state=UserAction.creating_html, role=UserRole.USER)


def search_add_button(dp: Dispatcher):
    dp.register_callback_query_handler(add_search_button, text="search_add_button")
    

def search_add(dp: Dispatcher):
    dp.register_message_handler(add_search, state=UserAction.adding_search, role=UserRole.USER)
    #dp.register_channel_post_handler(add_search, state=UserAction.adding_search, role=UserRole.USER)


def search_delete(dp: Dispatcher):
    dp.register_message_handler(delete_search, lambda message: message.text.startswith('/delsearch'), role=UserRole.USER)
    #dp.register_channel_post_handler(delete_search, lambda message: message.text.startswith('/delsearch'), role=UserRole.USER)


def subscription_start(dp: Dispatcher):
    dp.register_callback_query_handler(start_subscription, state="*", text="subscription_start") 


def subscription_stop(dp: Dispatcher):
    dp.register_callback_query_handler(stop_subscription, state="*", text="subscription_stop") 