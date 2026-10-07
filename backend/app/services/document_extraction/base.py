from abc import ABC, abstractmethod
from pathlib import Path

from app.schemas.extraction import ExtractedDocument


class DocumentExtractor(ABC):
    @abstractmethod
    def extract(self, file_path: Path) -> ExtractedDocument:
        raise NotImplementedError
