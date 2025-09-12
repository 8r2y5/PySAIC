import winreg
from getpass import getuser
from hashlib import md5


def get_windows_key_or_username():
    arch_keys = [0, winreg.KEY_WOW64_32KEY, winreg.KEY_WOW64_64KEY]
    for arch in arch_keys:
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                "SOFTWARE\Microsoft\Windows NT\CurrentVersion",
                0,
                winreg.KEY_READ | arch,
            )
            value, _ = winreg.QueryValueEx(key, "DigitalProductId")
            return value.decode("utf-8", errors="ignore")
        except (FileNotFoundError, TypeError):
            pass

    return getuser()


def get_user_for_irc():
    return md5(get_windows_key_or_username().encode()).hexdigest()[:8]
