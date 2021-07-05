from datetime import datetime
from typing import List, NamedTuple

class FeedData(NamedTuple):
    id: int
    key: int
    user_id: int
    feed_link: str
    feed_type: str
    search_string: List[str]
    last_updated: datetime