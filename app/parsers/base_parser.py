from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseParser(ABC):

    @abstractmethod
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        pass
