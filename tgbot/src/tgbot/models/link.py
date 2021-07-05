from datetime import datetime
from typing import NamedTuple

class LinkData(NamedTuple):
    user_id: int
    article_link: str
    sent: datetime