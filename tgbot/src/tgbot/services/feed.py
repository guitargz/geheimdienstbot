import feedparser # type: ignore
from googlesearch import search # type: ignore
import logging

from datetime import datetime, timezone, timedelta
from tgbot.models.feed import FeedData
from tgbot.services.link import Link
from tgbot.services.repository import Repo
from time import mktime
from typing import List

def _log(obj) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    logger = logging.getLogger(__name__)
    logger.error(obj)


class Feed:
    """News delivery abstraction layer"""

    def __init__(self, conn = None):
        self.conn = conn

    
    def _parse_search_string(self, search_string: str) -> List[str]:
        search_str = search_string.split(",")
        search_str = list(filter(None, map(str.strip, search_str)))
        return search_str


    def _search_list_to_string(self, search_list: List[str]) -> str:
        search_str = ", ".join(search_list)
        return search_str


    async def new_rss_items(self, user_id, repo: Repo, link: Link) -> List[str]:
        """List new RSS feed items for the user"""
        result: List = []
        feeds = await self.list_feeds(user_id, 0, True, "'rss'")
        #last_sent: datetime = await repo.get_last_sent(user_id) #the user.last_sent field is not used at the moment
        for feed in feeds:
            fp = feedparser.parse(feed.feed_link)
            for entry in fp.entries:
                if "published" in fp.entries[0]:
                    entry_published = datetime.fromtimestamp(mktime(entry.published_parsed), timezone.utc)
                else:
                    entry_published = datetime.fromtimestamp(mktime(entry.updated_parsed), timezone.utc)
                #check if the rss entry date is later then the feed last updated for this user
                if entry_published > feed.last_updated: 
                    #check that keywords are in the title or content
                    if (any(x in entry.title.lower() for x in feed.search_string)) or ("content" in fp.entries[0] and any(x in entry.content[0].value.lower() for x in feed.search_string)): 
                        #check that link has not been sent yet
                        if not await link.is_sent(user_id, entry.link):
                            await self.update_last_updated(int(user_id), feed.feed_link, datetime.now(timezone.utc))
                            result.append(entry.link)
        return result
            

    async def new_google_search(self, user_id, link: Link) -> List[str]:
        result: List = []
        feeds = await self.list_feeds(user_id, 0, True, "'html'")
        for feed in feeds:
            for search_string in feed.search_string:
                gs = search(f"{search_string} site:{feed.feed_link} after:{datetime.today().strftime('%Y-%m-%d')}", num_results=5) #returns a list of article links
                for search_result in gs:
                    #check that link has not been sent yet
                    if not await link.is_sent(user_id, search_result):
                        await self.update_last_updated(int(user_id), feed.feed_link, datetime.now(timezone.utc))
                        result.append(search_result)
        return result


    async def list_feeds(self, user_id, line:int, all: bool, type: str) -> List[FeedData]:
        """List the current user's feeds"""
        result = []
        rows = await self.conn.fetch(
            f"SELECT * FROM feeds WHERE user_id = $1 and feed_type = {type} order by key asc",
            user_id,
        )
        if rows and 0 <= line < len(rows): 
            if (line + 9) < len(rows) and not all: # paginated list
                end = line + 10
            else: # full list
                end = len(rows)
            for index, row in enumerate(rows[line:end], start=line):
                feed = FeedData(
                    index,
                    row["key"],
                    row["user_id"], 
                    row["feed_link"], 
                    row["feed_type"], 
                    self._parse_search_string(row["search_string"]), 
                    row["last_updated"],
                    ) 
                result.append(feed)
        return result

    
    async def feed_exists(self, user_id: int, link: str) -> bool:
        """Checks if a feed with the link already exists for the user"""
        rows = await self.conn.fetch(
            "SELECT feed_link FROM feeds WHERE user_id = $1 and feed_link = $2 order by key asc",
            user_id,
            link,
        )
        return bool(rows)


    async def create_feed(self, search_strings: List[str], user_id: int, link: str, type: str) -> None:
        feed_type = type
        await self.conn.execute('''
            insert into feeds (user_id, key, feed_link, feed_type, search_string, last_updated)
            values ($1, DEFAULT, $2, $3, $4, $5)
            ''',
            int(user_id),
            link,
            feed_type,
            self._search_list_to_string(search_strings),
            datetime.now(timezone.utc) - timedelta(days=30),
            )
        return


    async def delete_feeds(self, user_id: int, link: str) -> None:
        await self.conn.execute(
            "delete from feeds where user_id=$1 and feed_link=$2",
            int(user_id),
            link,
            )
        return


    async def update_search(self, search_strings: List[str], user_id: int, link: str) -> None:
        await self.conn.execute(
            "update feeds set search_string=$1 where user_id=$2 and feed_link=$3",
            self._search_list_to_string(search_strings),
            int(user_id),
            link,
            )
        await self.update_last_updated(user_id, link, datetime.now(timezone.utc) - timedelta(days=30))
        return


    async def update_last_updated(self, user_id: int, link: str, timestamp: datetime) -> None:
        await self.conn.execute(
            "update feeds set last_updated=$1 where user_id=$2 and feed_link=$3",
            timestamp,
            int(user_id),
            link
            )
        return