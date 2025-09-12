import logging
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from tkinter import (
    Button,
    Frame,
    Label,
    OptionMenu,
    Radiobutton,
    Spinbox,
    StringVar,
    Toplevel,
)
from tkinter.ttk import Style

import inject
from PIL import Image, ImageTk

from pysaic.avatar.avatar_maker import save_avatar, textures_path
from pysaic.constants import FACTION_AVATARS, crcr_factions
from pysaic.entities import IncomingEvent, IncomingQueue
from pysaic.enums import AppEventEnum, AvatarEnum, FactionsEnum
from pysaic.settings import GAMEDATA_PATH
from pysaic.state import State
from pysaic.ui.player_avatar_editor import PlayerAvatarEditor
from pysaic.use_cases.avatar import (
    calculate_icon_based_on_faction_and_name,
    get_valid_icon_from_icon_id,
)

PATH = Path(os.path.abspath(os.path.dirname(__file__)))
if not GAMEDATA_PATH.exists():
    raise FileNotFoundError(
        f"gamedata files directory not found at {GAMEDATA_PATH}."
    )

crc_dss_path = textures_path / "crc_icons.dds"
faction_file = {
    FactionsEnum.Loner.value: textures_path / "pysaic_icons_stalker.dds",
    FactionsEnum.Freedom.value: textures_path / "pysaic_icons_freedom.dds",
    FactionsEnum.Duty.value: textures_path / "pysaic_icons_dolg.dds",
    FactionsEnum.Monolith.value: textures_path / "pysaic_icons_monolith.dds",
    FactionsEnum.Bandit.value: textures_path / "pysaic_icons_bandit.dds",
    FactionsEnum.Clear_Sky.value: textures_path / "pysaic_icons_csky.dds",
    FactionsEnum.Ecologist.value: textures_path / "pysaic_icons_ecolog.dds",
    FactionsEnum.Military.value: textures_path / "pysaic_icons_army.dds",
    FactionsEnum.Renegade.value: textures_path / "pysaic_icons_renegade.dds",
    FactionsEnum.Mercenary.value: textures_path / "pysaic_icons_killer.dds",
    FactionsEnum.UNISG.value: textures_path / "pysaic_icons_unisg.dds",
    FactionsEnum.SIN.value: textures_path / "pysaic_icons_greh.dds",
    FactionsEnum.Zombie.value: textures_path / "crc_icons.dds",
}


logger = logging.getLogger(__name__)


def show_custom_info_dialog(parent, title, message, bg_color, text_color):
    dialog = Toplevel()
    dialog.title(title)
    dialog.config(bg=bg_color)
    dialog.iconbitmap(PATH / "crcr_icon_new.ico")

    label = Label(
        dialog, text=message, bg=bg_color, fg=text_color, wraplength=600
    )
    label.pack(expand=True, padx=20, pady=20)

    button = Button(
        dialog,
        text="OK",
        command=dialog.destroy,
        background=bg_color,
        fg=text_color,
    )
    button.pack(pady=10)

    dialog.update_idletasks()
    screen_width = dialog.winfo_screenwidth()
    screen_height = dialog.winfo_screenheight()
    dialog_width = dialog.winfo_width()
    dialog_height = dialog.winfo_height()
    x = (screen_width // 2) - (dialog_width // 2)
    y = (screen_height // 2) - (dialog_height // 2)
    dialog.geometry(f"+{x}+{y}")

    dialog.transient(parent)
    dialog.grab_set()


class AvatarOptions:
    def __init__(self, config, main_window):
        self.main_window = main_window
        self.this_window = Toplevel(self.main_window)
        self.this_window.title("Avatar Options")
        self.this_window.geometry("400x330")
        self.this_window.wm_minsize(400, 330)
        self.this_window.resizable(True, True)
        self.this_window.iconbitmap(PATH / "crcr_icon_new.ico")
        self.config = config
        self.avatar_data = {}
        self._parse_avatar_data()
        self.this_window.protocol(
            "WM_DELETE_WINDOW", self._destroy_this_window
        )

    def _reload_label_image(self):
        image_path = GAMEDATA_PATH / "textures" / "ui" / "pysaic_player.dds"
        image_path = image_path.resolve().absolute()
        if not image_path.exists():
            logger.error("Image file %s does not exist.", image_path)
            self.info_label.config(
                text=f"Image file does not exist. Path: {image_path}"
            )
            return

        self._load_image_using_xy_values(image_path, 0, 0)

    def main(self):
        style = Style()
        style.configure("white.TSeparator", background="white")
        background_color = self.main_window.cget("bg")
        text_color = "ghost white"
        default_style_kwargs = {
            "background": background_color,
            "foreground": text_color,
            "activebackground": background_color,
            "activeforeground": text_color,
            "selectcolor": background_color,
        }
        main_frame = Frame(
            self.this_window,
            background=background_color,
        )
        self.info_label = Label(
            main_frame,
            text="Avatar Creator",
            font=("Arial", 16),
            background=background_color,
            foreground=text_color,
            wraplength=380,
        )
        self.info_label.pack(pady=5)
        self.image_label = Label(
            main_frame,
            background=background_color,
            foreground=text_color,
        )
        self._reload_label_image()
        buttons_frame = Frame(
            main_frame,
            background=background_color,
        )
        self.button_select_file = Button(
            buttons_frame,
            text="Avatar Picker",
            command=self.select_file,
            background=background_color,
            foreground=text_color,
        )
        self._create_avatar_options(
            background_color, default_style_kwargs, text_color
        )
        self.image_label.pack()

        button_cancel = Button(
            buttons_frame,
            text="Cancel",
            command=self._destroy_this_window,
            background=background_color,
            foreground=text_color,
        )

        self.button_select_file.pack(side="left", pady=10)
        button_save = Button(
            buttons_frame,
            text="Save",
            command=self._save,
            background=background_color,
            foreground=text_color,
        )
        button_cancel.pack(side="right", padx=(10, 0))
        button_save.pack(side="right")
        buttons_frame.pack(side="bottom", fill="x", padx=10)
        main_frame.pack(fill="both", expand=True)

    def select_file(self):
        self.avatar_picker = PlayerAvatarEditor(self, self.this_window)
        self.button_select_file.config(state="disabled")

    @inject.autoparams()
    def update_avatar(self, image: Image.Image, state: State):
        save_avatar(image, False)
        message = "Avatar has been saved successfully.\n\n"
        if state.is_game_running:
            message += (
                "Note: Changes will be visible after restarting the game."
            )
        else:
            message += f"Copied file to {textures_path / 'pysaic_player.dds'}. Make sure this is is Anomaly/gamedata/textures/ui folder."
        show_custom_info_dialog(
            self.this_window,
            "Avatar Saved",
            message,
            self.main_window.cget("bg"),
            "ghost white",
        )
        self._reload_label_image()

    def close_avatar_picker(self):
        self.button_select_file.config(state="normal")

    def _create_avatar_options(
        self, background_color, default_style_kwargs, text_color
    ):
        def set_avatar(selection=None):
            if selection is None:
                selection = self.avatar_var.get()

            logger.debug("Setting avatar to %r", selection)
            if selection == AvatarEnum.faction_and_name_based.value:
                self.faction_and_name_based_radio_button.select()
                static_avatar_radio_button.deselect()
                self.static_avatar_number_spinbox["state"] = "disabled"
                player_avatar_radio_button.deselect()
                faction_options_menu["state"] = "disabled"
                self._set_faction_and_name_based_avatar()
                self.info_label.config(text="")
                self.button_select_file["state"] = "disabled"

            elif selection == AvatarEnum.static.value:
                static_avatar_radio_button.select()
                self.static_avatar_number_spinbox["state"] = "normal"
                self.faction_and_name_based_radio_button.deselect()
                player_avatar_radio_button.deselect()
                faction_options_menu["state"] = "normal"
                self.info_label.config(text="")
                self.button_select_file["state"] = "disabled"
                self._set_static_avatar()

            elif selection == AvatarEnum.player.value:
                static_avatar_radio_button.deselect()
                self.static_avatar_number_spinbox["state"] = "disabled"
                self.faction_and_name_based_radio_button.deselect()
                player_avatar_radio_button.select()
                faction_options_menu["state"] = "normal"
                self.info_label.config(text="")
                self.button_select_file["state"] = "normal"
                self._reload_label_image()

        self.avatar_var = StringVar(self.main_window, value=self.config.avatar)
        bigger_faction_frame = Frame(
            self.this_window, background=background_color
        )
        faction_settings = Frame(
            bigger_faction_frame, background=background_color
        )
        self._create_faction_based_radio_button(
            faction_settings,
            set_avatar,
            default_style_kwargs,
        )

        static_avatar_radio_button_frame = Frame(
            faction_settings, background=background_color
        )
        static_avatar_radio_button = Radiobutton(
            static_avatar_radio_button_frame,
            text="Static avatar",
            value=AvatarEnum.static,
            variable=self.avatar_var,
            command=set_avatar,
            **default_style_kwargs,
        )
        static_avatar_radio_button.pack(side="left")

        self.static_faction_var = StringVar(
            self.main_window,
        )
        icon_type, static_faction_value, avatar_number = (
            get_valid_icon_from_icon_id(self.config.current_avatar)
        )
        static_faction_actor = FactionsEnum(static_faction_value)
        logger.debug(
            "Setting static avatar faction to %r with icon type %r and icon id %s",
            static_faction_actor,
            icon_type,
            avatar_number,
        )
        self.static_faction_var.set(
            static_faction_actor.name.replace("_", " ")
        )
        options = list(
            sorted(
                [
                    faction.name.replace("_", " ")
                    for faction in FactionsEnum
                    if faction != FactionsEnum.Anonymous
                ]
            )
        )
        faction_options_menu = OptionMenu(
            static_avatar_radio_button_frame,
            self.static_faction_var,
            *options,
        )
        faction_options_menu.config(
            bg=background_color,
            fg=text_color,
            activebackground=background_color,
            activeforeground=text_color,
        )
        faction_options_menu["menu"].config(
            bg=background_color,
            fg=text_color,
            activebackground="dim gray",
            activeforeground="black",
        )
        faction_options_menu.pack(side="left")

        max_value = FACTION_AVATARS[static_faction_actor.name]
        logger.debug(
            "Max value for static avatar %s number is %d",
            static_faction_actor,
            max_value,
        )
        self.spinbox_var = StringVar(self.main_window)
        self.spinbox_var.set(str(avatar_number))
        self.static_avatar_number_spinbox = Spinbox(
            static_avatar_radio_button_frame,
            from_=1,
            to=max_value + 1,
            increment=1,
            width=10,
            background=background_color,
            foreground=text_color,
            command=self._load_avatar_based_on_number,
            textvariable=self.spinbox_var,
        )
        # self.static_avatar_number_spinbox.delete(0, "end")
        # self.static_avatar_number_spinbox.insert(0, str(avatar_number))
        self.static_avatar_number_spinbox.pack(side="left", padx=5)

        player_avatar_frame = Frame(
            faction_settings, background=background_color
        )
        player_avatar_radio_button = Radiobutton(
            player_avatar_frame,
            text="Player avatar",
            value=AvatarEnum.player,
            variable=self.avatar_var,
            command=set_avatar,
            **default_style_kwargs,
        )
        player_avatar_radio_button.pack(side="left")

        faction_settings.pack(fill="x", padx=50)
        static_avatar_radio_button_frame.pack(anchor="w")
        player_avatar_frame.pack(anchor="w")
        bigger_faction_frame.pack(fill="x")
        set_avatar()

    def _create_faction_based_radio_button(
        self, faction_settings, set_avatar, default_style_kwargs
    ):
        self.faction_and_name_based_radio_button = Radiobutton(
            faction_settings,
            text="Faction and name based",
            value=AvatarEnum.faction_and_name_based,
            command=set_avatar,
            variable=self.avatar_var,
            **default_style_kwargs,
        )
        self.faction_and_name_based_radio_button.pack(anchor="w")

    def _set_faction_and_name_based_avatar(self):
        faction = self.config.current_faction.value
        avatar_id = calculate_icon_based_on_faction_and_name(
            self.config.current_faction.value, self.config.nick
        )
        logger.debug(
            "Setting faction and name based avatar to %r for faction %r",
            avatar_id,
            faction,
        )
        x, y = self.avatar_data[avatar_id]
        if avatar_id.startswith("crc_icon_"):
            texture_file = crc_dss_path
        else:
            texture_file = faction_file[faction]
        if not texture_file.exists():
            logger.error("Texture file does not exist: %s", texture_file)
            return
        self._load_image_using_xy_values(texture_file, x, y)

    def _parse_avatar_data(self):
        texture_descriptions = (
            GAMEDATA_PATH / "configs" / "ui" / "textures_descr"
        )
        if not texture_descriptions.exists():
            logger.error(
                "Texture descriptions file does not exist: %s",
                texture_descriptions,
            )
            return
        self._parse_texture_description(texture_descriptions / "crc_icons.xml")
        for avatar_config in (
            "ui_pysaic_icons_army",
            "ui_pysaic_icons_bandit",
            "ui_pysaic_icons_csky",
            "ui_pysaic_icons_dolg",
            "ui_pysaic_icons_ecolog",
            "ui_pysaic_icons_freedom",
            "ui_pysaic_icons_greh",
            "ui_pysaic_icons_isg",
            "ui_pysaic_icons_killer",
            "ui_pysaic_icons_monolith",
            "ui_pysaic_icons_renegade",
            "ui_pysaic_icons_stalker",
        ):
            self._parse_texture_description(
                texture_descriptions / f"{avatar_config}.xml"
            )

    def _parse_texture_description(self, texture_file):
        logger.debug("Parsing texture file: %s", texture_file)
        tree = ET.parse(texture_file)
        for node in tree.getroot()[0]:
            if node.attrib["id"] in (
                "crc_icon_tkgp",
                "crc_icon_info",
                "crc_icon_error",
            ):
                continue

            self.avatar_data[node.attrib["id"]] = (
                int(node.attrib["x"]),
                int(node.attrib["y"]),
            )

    def _load_image_using_xy_values(self, texture_file, x, y):
        image = (
            Image.open(texture_file)
            .convert("RGBA")
            .crop((x, y, x + 126, y + 56))
            .resize((240, 81), Image.Resampling.LANCZOS)
        )
        resize_image = ImageTk.PhotoImage(image)
        self.image_label.config(image=resize_image)
        self.image_label.image = (
            resize_image  # Keep a reference to avoid garbage collection
        )

    def _set_static_avatar(self):
        self._load_avatar_based_on_number()

    def _load_avatar_based_on_number(self):
        faction = self.static_faction_var.get()
        try:
            avatar_number = int(self.static_avatar_number_spinbox.get())
        except ValueError:
            logger.error(
                "Invalid avatar number: %s",
                self.static_avatar_number_spinbox.get(),
            )
            return

        if faction not in FACTION_AVATARS:
            logger.error("Faction %r not found in FACTION_AVATARS", faction)
            return

        max_value = FACTION_AVATARS[faction]
        if avatar_number < 1 or avatar_number > max_value:
            self.spinbox_var.set(str(max_value))

        faction = FactionsEnum[faction.replace(" ", "_")].value
        if avatar_number <= crcr_factions[faction]:
            texture_file = crc_dss_path
            avatar_id = f"crc_icon_{faction}_{avatar_number}"
        else:
            texture_file = faction_file[faction]
            avatar_id = f"pysaic_icon_{faction}_{avatar_number - crcr_factions[faction]}"

        if avatar_id not in self.avatar_data:
            logger.error("Avatar ID %s not found in avatar data", avatar_id)
            return
        x, y = self.avatar_data[avatar_id]

        self._load_image_using_xy_values(texture_file, x, y)

    @inject.autoparams()
    def _save(self, incoming_queue: IncomingQueue):
        avatar_type = self.avatar_var.get()
        if avatar_type == AvatarEnum.faction_and_name_based.value:
            self.config.avatar = AvatarEnum.faction_and_name_based.value
            self.config.current_avatar = (
                calculate_icon_based_on_faction_and_name(
                    self.config.current_faction.value, self.config.nick
                )
            )
        elif avatar_type == AvatarEnum.static.value:
            faction = self.static_faction_var.get()
            try:
                avatar_number = int(self.static_avatar_number_spinbox.get())
            except ValueError:
                logger.error(
                    "Invalid avatar number: %s",
                    self.static_avatar_number_spinbox.get(),
                )
                return

            if faction not in FACTION_AVATARS:
                logger.error(
                    "Faction %r not found in FACTION_AVATARS", faction
                )
                return

            max_value = FACTION_AVATARS[faction]
            if avatar_number < 1 or avatar_number > max_value:
                self.static_avatar_number_spinbox.set(max_value)

            faction = FactionsEnum[faction.replace(" ", "_")].value
            if avatar_number <= crcr_factions[faction]:
                icon_type = "crc_icon"
                icon_id = f"{faction}_{avatar_number}"
            else:
                icon_type = "pysaic_icon"
                icon_id = f"{faction}_{avatar_number - crcr_factions[faction]}"

            self.config.avatar = AvatarEnum.static.value
            self.config.current_avatar = f"{icon_type}_{icon_id}"
        elif avatar_type == AvatarEnum.player.value:
            self.config.avatar = AvatarEnum.player.value
            self.config.current_avatar = "pysaic_icon_player"
        logger.debug(
            "Saving avatar type %s with current avatar %s",
            self.config.avatar,
            self.config.current_avatar,
        )
        self.config.save_config()
        incoming_queue.put_nowait(
            IncomingEvent.create_app_event(
                what=AppEventEnum.OPTIONS_UPDATED, payload=self.config.avatar
            )
        )
        self._destroy_this_window()

    def _destroy_this_window(self):
        logger.debug("Destroying avatar options window")
        self.this_window.destroy()
        self.main_window.focus()
