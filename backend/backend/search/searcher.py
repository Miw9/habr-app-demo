import abc
from dataclasses import dataclass
from typing import Iterable, Optional, Any


@dataclass
class CardSearchResult:
    total_count: int
    card_ids: Iterable[str]
    next_card_offset: Optional[int]


ElasticsearchQuery = Any


class Searcher(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def search_cards(self, query: str = "", count: int = 20, offset: int = 0) -> CardSearchResult:
        pass
