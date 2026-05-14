from dataclasses import dataclass, field
from typing import Any
@dataclass
class ParseModel:
    type:str
    text:str
    metadata: dict[str,Any] = field(default_factory=dict)
    raw: Any = field(default=None, repr=False)

