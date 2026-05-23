from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ProviderRole(str, Enum):
    FAST = "fast"
    PLANNER = "planner"
    FALLBACK = "fallback"


@dataclass
class ProviderConfig:
    api_key: str
    model: Optional[str] = None


@dataclass
class LLMResponse:
    content: str
    provider: str
    model: str


class BaseLLMProvider(ABC):
    name: str

    def __init__(self, config: ProviderConfig):
        self.config = config

    @abstractmethod
    async def complete(self, prompt: str, system: str = "") -> LLMResponse:
        pass

    @property
    def model(self) -> str:
        return self.config.model or self.default_model

    @property
    @abstractmethod
    def default_model(self) -> str:
        pass
