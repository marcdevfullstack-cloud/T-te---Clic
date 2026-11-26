"""Réglages de Tête-à-Clic, enregistrés automatiquement (settings.json)."""
import json
import os
import sys
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

APP_NAME = "Tête-à-Clic"
APP_ID = "TeteAClic"  # forme sans accents : dossiers, identifiants techniques
VERSION = "1.1.0"
AUTHOR = "MarcDev@"
CONTACT_EMAIL = "marcdevfullstack@gmail.com"

PROJECT_DIR = Path(__file__).resolve().parent.parent
FROZEN = getattr(sys, "frozen", False)
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", PROJECT_DIR))


def default_data_dir() -> Path:
    if FROZEN:
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_ID
    return PROJECT_DIR / "data"


@dataclass
class Config:
    camera_index: int = 0
    sensitivity_x: float = 1.0  # 0,5 = grands mouvements de tête ; 2 = petits mouvements
    sensitivity_y: float = 1.0
    smoothing: float = 0.5  # 0 = réactif, 1 = très stable
    dwell_click: bool = True  # clic en restant immobile
    dwell_seconds: float = 1.2
    blink_click: bool = True  # clignement long = clic gauche
    brow_right_click: bool = True  # sourcils levés = clic droit
    mouth_scroll: bool = True  # bouche ouverte + tête haut/bas = défilement
    click_sound: bool = True
    voice: bool = True
    data_dir: Path = field(default_factory=default_data_dir, metadata={"internal": True})

    @property
    def settings_path(self) -> Path:
        return self.data_dir / "settings.json"

    @property
    def model_path(self) -> Path:
        return RESOURCE_DIR / "models" / "face_landmarker.task"

    def user_fields(self) -> list[str]:
        return [f.name for f in fields(self) if not f.metadata.get("internal")]

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if k in self.user_fields()}

    def update(self, data: dict) -> list[str]:
        """Applique les valeurs valides ; renvoie les clés modifiées."""
        changed = []
        for key in self.user_fields():
            if key not in data:
                continue
            current = getattr(self, key)
            try:
                value = type(current)(data[key])
            except (TypeError, ValueError):
                continue
            if value != current:
                setattr(self, key, value)
                changed.append(key)
        return changed

    def save(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        tmp = self.settings_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        tmp.replace(self.settings_path)

    @classmethod
    def load(cls) -> "Config":
        cfg = cls()
        try:
            cfg.update(json.loads(cfg.settings_path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
        return cfg
