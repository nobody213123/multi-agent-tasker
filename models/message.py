from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class DataRequest:
    names: list[str]
    reason: str = ""


@dataclass
class ExtraData:
    items: dict[str, dict] = field(default_factory=dict)
