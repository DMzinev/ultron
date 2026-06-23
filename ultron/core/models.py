import os
from dataclasses import dataclass, asdict

@dataclass
class AnalysisPacket:
    file_path: str
    impact_score: float
    coupling_score: float
    mk_r: float
    delta_cest: float
    confidence: float
    
    # Optional metadata fields for UI compatibility
    level: str = "LOW"
    complexity: int = 1
    mitigation: str = ""
    callers: list = None
    changes: list = None
    delta_score: float = 0.0

    def to_dict(self):
        d = asdict(self)
        # Add legacy/alias keys for UI compatibility
        d['file'] = self.file_path
        d['filepath'] = os.path.basename(self.file_path) if self.file_path else ""
        d['coupling'] = self.coupling_score
        d['mkr'] = self.mk_r
        if self.callers is None:
            d['callers'] = []
        if self.changes is None:
            d['changes'] = []
        return d

    def __getitem__(self, key):
        d = self.to_dict()
        if key in d:
            return d[key]
        raise KeyError(key)

    def get(self, key, default=None):
        return self.to_dict().get(key, default)
