import logging
from dataclasses import asdict, dataclass
from enum import StrEnum

import yaml

logger = logging.getLogger(__name__)


class ColorsEnum(StrEnum):
    Time = "Time"
    Text = "Text"
    Highlight = "Highlight"
    Information = "Information"
    Error = "Error"
    Clear_Sky = "Clear_Sky"
    Loner = "Loner"
    Duty = "Duty"
    Freedom = "Freedom"
    Military = "Military"
    Mercenary = "Mercenary"
    Bandit = "Bandit"
    Monolith = "Monolith"
    Ecologist = "Ecologist"
    Renegade = "Renegade"
    Zombie = "Zombie"
    Anonymous = "Anonymous"
    UNISG = "UNISG"
    SIN = "SIN"

    DM = "DM"
    online = "online"
    offline = "offline"
    app_background = "app_background"
    element_background = "element_background"


@dataclass
class Colors:
    Time: str
    Text: str
    Highlight: str
    Information: str
    Error: str
    Clear_Sky: str
    Loner: str
    Duty: str
    Freedom: str
    Military: str
    Mercenary: str
    Bandit: str
    Monolith: str
    Ecologist: str
    Renegade: str
    Zombie: str
    Anonymous: str
    UNISG: str
    SIN: str
    DM: str
    online: str
    offline: str
    app_background: str
    element_background: str

    @classmethod
    def load_colors(cls, path: str = "colors.yml"):
        try:
            with open(path) as f:
                colors = yaml.safe_load(f)
        except Exception:
            logger.exception("Could not load colors from %s", path)
            colors = cls._default_colors()
            instance = cls(**colors)
            instance.save_colors(path)
        else:
            instance = cls(**colors)

        return instance

    def save_colors(self, path: str = "colors.yml"):
        with open(path, "w") as f:
            yaml.dump(asdict(self), f)

    @classmethod
    def _default_colors(cls):
        return {
            "Time": "floral white",
            "Text": "ghost white",
            "Highlight": "lemon chiffon",
            "Information": "lightblue",
            "Error": "red3",
            "Clear_Sky": "deep sky blue",
            "Loner": "light goldenrod",
            "Duty": "firebrick1",
            "Freedom": "spring green",
            "Military": "PaleGreen3",
            "Mercenary": "dodgerblue",
            "Bandit": "sienna3",
            "Monolith": "DarkOrchid3",
            "Ecologist": "darkorange",
            "Renegade": "green yellow",
            "Zombie": "black",
            "Anonymous": "black",
            "UNISG": "salmon",
            "SIN": "maroon4",
            "DM": "hot pink",
            "online": "green",
            "offline": "red",
            "app_background": "gray30",
            "element_background": "gray40",
        }


if __name__ == "__main__":
    print(ColorsEnum.Time)
