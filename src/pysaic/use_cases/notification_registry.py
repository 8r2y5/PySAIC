import logging
import os
import sys
import winreg

logger = logging.getLogger(__name__)

PROTOCOL_NAME = "pysaic"
BASE_REGISTRY_STR = f"Software\\Classes\\{PROTOCOL_NAME}"
COMMAND_PATH = f"{BASE_REGISTRY_STR}\\shell\\open\\command"

interpreter = sys.executable
script_path = os.path.abspath(sys.argv[0])

LAUNCH_COMMAND = f'"{interpreter}" "{script_path}" "%1"'


class KeyContext:
    def __init__(self, key_path):
        self.key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return True

    def __del__(self):
        winreg.CloseKey(self.key)

    def set(self, name, value):
        winreg.SetValueEx(self.key, name, 0, winreg.REG_SZ, value)


def _set_registry_values():
    with KeyContext(BASE_REGISTRY_STR) as key:
        key.set("URI Protocol", "")
        key.set("", f"URI:{PROTOCOL_NAME} Protocol")

    with KeyContext(f"{BASE_REGISTRY_STR}\\DefaultIcon") as key:
        logger.debug("Setting icon to: %r", interpreter)
        key.set("", f'"{interpreter}"')

    KeyContext(f"{BASE_REGISTRY_STR}\\shell")
    KeyContext(f"{BASE_REGISTRY_STR}\\shell\\open")

    with KeyContext(COMMAND_PATH) as key:
        logger.debug("Setting %s to %r", COMMAND_PATH, LAUNCH_COMMAND)
        key.set("", LAUNCH_COMMAND)


def _check_and_register_uri_protocol():
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, COMMAND_PATH, 0, winreg.KEY_READ
        ) as key:
            value, _ = winreg.QueryValueEx(key, "")

        if value != LAUNCH_COMMAND:
            logger.info("Fixing registry values, current: %r", value)
            _set_registry_values()
    except FileNotFoundError:
        logger.info("Creating registry values")
        _set_registry_values()


def check_and_register_uri_protocol():
    try:
        _check_and_register_uri_protocol()
    except PermissionError:
        logger.exception("Permission denied to registry.")
        return False
    except Exception:
        logger.exception("Could not access or set keys")
        return False
    return True
