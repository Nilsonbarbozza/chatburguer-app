from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

class ExtractionMethod(str, Enum):
    JSON_LD    = "json_ld"
    NEXT_DATA  = "next_data"
    DOM        = "dom"
    FAILED     = "failed"

@dataclass
class ExtractionResult:
    text:             str
    method:           ExtractionMethod
    confidence:       float        # 0.0 → 1.0
    extraction_ms:    int          # tempo em ms
    char_count:       int = field(init=False)
    fallback_count:   int = 0      # quantas táticas foram tentadas

    def __post_init__(self):
        self.char_count = len(self.text) if self.text else 0

    @property
    def is_valid(self) -> bool:
        return self.confidence >= 0.5 and self.char_count >= 200

@dataclass
class DataClearResult:
    dataset_entries:    list
    extraction_method:  ExtractionMethod
    quality_score:      float
    extraction_time_ms: int
    waf_detected:       bool        = False
    fallback_count:     int         = 0
    error:              Optional[str] = None
    hub_items:          list        = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return len(self.dataset_entries) == 0 and len(self.hub_items) == 0
