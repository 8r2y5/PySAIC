from dataclasses import asdict
from pathlib import Path

import yaml

from pysaic.settings import THEMES_PATH

# A dictionary holding the definitions for all built-in themes.
# This structure makes it easier to add or modify themes in the future.
_THEMES = {
    "pysaic_gray": {
        "background": {
            "active_background": "#37373D",
            "active_foreground": "#FFFFFF",
            "app": "#252526",
            "content": "#1E1E1E",
            "in_between": "#333333",
        },
        "content": {
            "afk": "#DCDCAA",
            "direct_message": "#FF79C6",
            "error": "#F48771",
            "highlight": "#264F78",
            "hyper_link": "#3794FF",
            "information": "#9CDCFE",
            "offline": "#F44747",
            "online": "#6A9955",
            "surge": "#569CD6",
            "text": "#CCCCCC",
            "time": "#858585",
            "underground": "#569CD6",
        },
        "factions": {
            "anonymous": "#573613",
            "bandit": "#cd6839",
            "clear_sky": "#00bfff",
            "duty": "#ff3030",
            "ecologist": "#ff8c00",
            "freedom": "#00ff7f",
            "loner": "#eedd82",
            "mercenary": "#1e90ff",
            "military": "#7ccd7c",
            "monolith": "#9a32cd",
            "renegade": "#adff2f",
            "sin": "#8b1c62",
            "unisg": "#fa8072",
            "zombie": "#573613",
        },
        "pressed": "#404040",
        "slider_arrow": "#CCCCCC",
        "slider_arrow_disabled": "#424242",
    },
    "pysaic_light_90": {
        "background": {
            "active_background": "#000080",
            "active_foreground": "#FFFFFF",
            "app": "#C0C0C0",
            "content": "#FFFFFF",
            "in_between": "#808080",
        },
        "content": {
            "afk": "#808000",
            "direct_message": "#800080",
            "error": "#FF0000",
            "highlight": "#B0B0B0",
            "hyper_link": "#0000FF",
            "information": "#008080",
            "offline": "#404040",
            "online": "#008000",
            "surge": "#0000A0",
            "text": "#000000",
            "time": "#404040",
            "underground": "#0000A0",
        },
        "factions": {
            "anonymous": "#573613",
            "bandit": "#A0522D",
            "clear_sky": "#0080FF",
            "duty": "#FF0000",
            "ecologist": "#FF8000",
            "freedom": "#00FF00",
            "loner": "#D4AF37",
            "mercenary": "#0000FF",
            "military": "#006400",
            "monolith": "#800080",
            "renegade": "#808000",
            "sin": "#800000",
            "unisg": "#CD5C5C",
            "zombie": "#573613",
        },
        "pressed": "#808080",
        "slider_arrow": "#000000",
        "slider_arrow_disabled": "#808080",
    },
    "pysaic_matrix": {
        "background": {
            "active_background": "#003B00",
            "active_foreground": "#00FF41",
            "app": "#040904",
            "content": "#000b00",
            "in_between": "#002200",
        },
        "content": {
            "afk": "#4D5D00",
            "direct_message": "#00FF41",
            "error": "#661100",
            "highlight": "#004B00",
            "hyper_link": "#008F8F",
            "information": "#00FF41",
            "offline": "#7a8400",
            "online": "#00FF41",
            "surge": "#00ffac",
            "text": "#00FF41",
            "time": "#008F11",
            "underground": "#00ffdf",
        },
        "factions": {
            "anonymous": "#2E2D00",
            "bandit": "#6B5B00",
            "clear_sky": "#00A86B",
            "duty": "#7A1F00",
            "ecologist": "#ADFF2F",
            "freedom": "#00FF41",
            "loner": "#C5B358",
            "mercenary": "#204040",
            "military": "#4B5320",
            "monolith": "#4B0082",
            "renegade": "#556B2F",
            "sin": "#910000",
            "unisg": "#5F9EA0",
            "zombie": "#2E2D00",
        },
        "pressed": "#001100",
        "slider_arrow": "#00FF41",
        "slider_arrow_disabled": "#002200",
    },
    "pysaic_tactical_alert": {
        "background": {
            "active_background": "#2A0000",
            "active_foreground": "#FFA0A0",
            "app": "#060202",
            "content": "#000000",
            "in_between": "#3B0000",
        },
        "content": {
            "afk": "#B0B000",
            "direct_message": "#c742ff",
            "error": "#FF1111",
            "highlight": "#FFFF00",
            "hyper_link": "#00FFFF",
            "information": "#80FFFF",
            "offline": "#601010",
            "online": "#FF4141",
            "surge": "#00ffb9",
            "text": "#FF4141",
            "time": "#b32424",
            "underground": "#00ffb3",
        },
        "factions": {
            "anonymous": "#808080",
            "bandit": "#ffd900",
            "clear_sky": "#00BFFF",
            "duty": "#FF0000",
            "ecologist": "#A0FF40",
            "freedom": "#00FF00",
            "loner": "#C0C000",
            "mercenary": "#00A0FF",
            "military": "#40FF80",
            "monolith": "#C000FF",
            "renegade": "#80FF00",
            "sin": "#C00000",
            "unisg": "#FF8080",
            "zombie": "#608020",
        },
        "pressed": "#220000",
        "slider_arrow": "#FF4141",
        "slider_arrow_disabled": "#3B0000",
    },
    "crcr": {
        "background": {
            "active_background": "#E0E0E0",
            "active_foreground": "#000000",
            "app": "#F5F5F5",
            "content": "#FFFFFF",
            "in_between": "#D1D1D1",
        },
        "content": {
            "afk": "#757575",
            "direct_message": "#005FB8",
            "error": "#D32F2F",
            "highlight": "#FFFF00",
            "hyper_link": "#0066CC",
            "information": "#00009C",
            "offline": "#FF0000",
            "online": "#008000",
            "surge": "#5b5bff",
            "text": "#000000",
            "time": "#000000",
            "underground": "#5b5bff",
        },
        "factions": {
            "anonymous": "#000000",
            "bandit": "#000000",
            "clear_sky": "#000000",
            "duty": "#000000",
            "ecologist": "#000000",
            "freedom": "#000000",
            "loner": "#000000",
            "mercenary": "#000000",
            "military": "#000000",
            "monolith": "#000000",
            "renegade": "#000000",
            "sin": "#000000",
            "unisg": "#000000",
            "zombie": "#000000",
        },
        "pressed": "#737373",
        "slider_arrow": "#fffaf0",
        "slider_arrow_disabled": "#696969",
    },
}


def _create_theme_file(theme_data: dict, theme_path: Path):
    """Helper function to write a theme dictionary to a YAML file."""
    with open(theme_path, "w") as f:
        yaml.dump(theme_data, f)


def create_default_themes(config: dict):
    """
    Creates default theme files and sets the initial theme in the config.

    This function ensures the themes directory exists, generates the default 'pysaic'
    theme from the color configuration, and then creates additional predefined
    themes from the _THEMES dictionary.
    """
    theme_name = "pysaic"
    theme_path = THEMES_PATH / f"{theme_name}.yml"
    config["theme_name"] = theme_name

    THEMES_PATH.mkdir(parents=True, exist_ok=True)

    # Create the default 'pysaic' theme from the current color config
    from pysaic.config import ColorsConfig

    default_colors = asdict(ColorsConfig.load_from_config({}))
    _create_theme_file(default_colors, theme_path)
    config["colors"] = default_colors

    # Create all other predefined themes
    for name, data in _THEMES.items():
        path = THEMES_PATH / f"{name}.yml"
        _create_theme_file(data, path)
