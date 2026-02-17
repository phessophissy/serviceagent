from abc import ABC, abstractmethod
from typing import Any


class Agent(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def run(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError
