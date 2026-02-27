from abc import ABC, abstractmethod
from typing import Dict, Any

class BasePusher(ABC):
    @abstractmethod
    def send_message(self, contact_id: str, message: str) -> Dict[str, Any]:
        pass
