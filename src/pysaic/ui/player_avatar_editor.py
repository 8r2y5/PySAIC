from tkinter import (
    BooleanVar,
    Button,
    Canvas,
    Checkbutton,
    Frame,
    Scale,
    Tk,
    Toplevel,
    filedialog,
)
from tkinter.ttk import Style

from PIL import Image, ImageDraw, ImageTk
from PIL.Image import LANCZOS

from pysaic.avatar.avatar_maker import generate_avatar
from pysaic.config import Config
from pysaic.ui.constants import WM_DELETE_WINDOW

RECT_W, RECT_H = 126, 56


class PlayerAvatarEditor:
    def __init__(self, parent, master_window: Tk):
        self.parent = parent
        self.config: Config = parent.config
        self.master_window = master_window
        self.window = Toplevel()
        self.window.protocol(WM_DELETE_WINDOW, self.close_window)
        self.window.title("Player Avatar Editor")
        self.window.configure(background=self.config.colors.background.app)
        self.window.wm_minsize(400, 300)
        self.window.resizable(True, True)
        if master_window:
            self.window.grab_set()
        self.original_rect_coords = (0, 0, 0, 0)
        self.visual_zoom_factor = 1.0
        self.image_pan_x = 0
        self.image_pan_y = 0
        self.create_widgets()
        self.window.transient(master_window)

    def create_widgets(self):
        style = Style()
        style.theme_use("clam")
        background_color = self.config.colors.background.app
        text_color = self.config.colors.content.text

        # Configure columns for proper button alignment
        self.window.grid_rowconfigure(0, weight=1)
        self.window.grid_columnconfigure(0, weight=0)  # Select button column
        self.window.grid_columnconfigure(1, weight=1)  # Spacer column
        self.window.grid_columnconfigure(
            2, weight=0
        )  # Save/Close button column

        self.avatar_canvas = Canvas(
            self.window,
            bg="gray",
            background=background_color,
            highlightthickness=0,
            bd=0,
        )
        self.avatar_canvas.grid(row=0, column=0, columnspan=3, sticky="nsew")
        self.canvas_width = self.avatar_canvas.winfo_reqwidth()
        self.canvas_height = self.avatar_canvas.winfo_reqheight()

        self.scale_adjust = Scale(
            self.window,
            orient="horizontal",
            background=background_color,
            foreground=text_color,
            highlightthickness=1,
            # bd=0,
        )
        self.scale_adjust.grid(
            row=1, column=0, columnspan=2, sticky="ew", padx=10
        )
        self.visual_zoom_var = BooleanVar()
        self.visual_zoom_checkbox = Checkbutton(
            self.window,
            text="Visual Zoom (2x)",
            variable=self.visual_zoom_var,
            command=self.toggle_visual_zoom,
            background=background_color,
            foreground=text_color,
            selectcolor=background_color,
        )
        self.visual_zoom_checkbox.grid(row=1, column=2, padx=10, pady=10)

        # Place the Select button on the left
        self.select_button = Button(
            self.window,
            text="Select file",
            command=self.select_avatar,
            background=background_color,
            foreground=text_color,
        )
        self.select_button.grid(row=2, column=0, padx=10, pady=10, sticky="w")

        # Create a Frame to hold Save and Close buttons
        button_frame = Frame(self.window, bg=background_color)
        button_frame.grid(row=2, column=2, padx=10, pady=10, sticky="e")

        # Place Save and Close buttons inside the frame
        self.save_button = Button(
            button_frame,
            text="Save Avatar",
            command=self.save_avatar,
            background=background_color,
            foreground=text_color,
        )
        self.save_button.pack(side="left", padx=(0, 5))

        self.close_button = Button(
            button_frame,
            text="Cancel",
            command=self.close_window,
            background=background_color,
            foreground=text_color,
        )
        self.close_button.pack(side="left", padx=(5, 0))

        self._reset_values()
        self.window.protocol("WM_DELETE_WINDOW", self.close_window)

    def toggle_visual_zoom(self):
        if self.visual_zoom_var.get():
            self.visual_zoom_factor = 2.0
        else:
            self.visual_zoom_factor = 1.0

        if not self.original_image:
            return

        self.show_processed_avatar()

    def select_avatar(self):
        file_path = filedialog.askopenfilename(
            title="Select Avatar Image",
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")],
            parent=self.window,
        )
        if file_path:
            self._reset_values()
            self.original_image = Image.open(file_path)
            self.avatar_canvas.delete("all")
            self.scale_adjust.config(from_=0.1, to=2, resolution=0.1)
            self.scale_adjust.set(1)
            self.scale_adjust.config(command=self.zoom_image)
            self.visual_zoom_var.set(False)
            self.visual_zoom_checkbox.deselect()
            self.visual_zoom_factor = 1.0
            self.avatar_canvas.bind("<ButtonPress-1>", self.on_canvas_press)
            self.avatar_canvas.bind("<B1-Motion>", self.on_canvas_drag)
            self.avatar_canvas.bind(
                "<ButtonRelease-1>", self.on_canvas_release
            )
            self.scale_adjust.bind("<ButtonRelease-1>", self.on_canvas_release)
            self.avatar_path = file_path
            self.drag_data = {
                "x": 0,
                "y": 0,
                "image_x": 0,
                "image_y": 0,
            }

            canvas_w = self.avatar_canvas.winfo_width()
            canvas_h = self.avatar_canvas.winfo_height()
            rect_x1 = (canvas_w - RECT_W) // 2
            rect_y1 = (canvas_h - RECT_H) // 2
            rect_x2 = rect_x1 + RECT_W
            rect_y2 = rect_y1 + RECT_H

            self.original_rect_coords = (rect_x1, rect_y1, rect_x2, rect_y2)
            self.zoom_image(1.0)
            self.show_processed_avatar()

    def save_avatar(self):
        self.parent.update_avatar(self.processed_image)
        self.close_window()

    def close_window(self):
        self.master_window.focus()
        self.parent.close_avatar_picker()
        self.window.destroy()

    def zoom_image(self, scale_value):
        if not self.original_image:
            return

        scale = float(scale_value)

        new_size = (
            int(self.original_image.width * scale),
            int(self.original_image.height * scale),
        )

        scaled_image = self.original_image.resize(new_size, LANCZOS)
        self.avatar_image = ImageTk.PhotoImage(scaled_image)

        if self.image_item_id:
            # Get current position to maintain pan
            current_x, current_y = self.avatar_canvas.coords(
                self.image_item_id
            )
            # Adjust pan based on new scale
            self.image_pan_x = (
                current_x
                - (
                    self.original_image.width * self.scale_adjust.get()
                    - scaled_image.width
                )
                / 2
            )
            self.image_pan_y = (
                current_y
                - (
                    self.original_image.height * self.scale_adjust.get()
                    - scaled_image.height
                )
                / 2
            )
        else:
            # Initial centering
            canvas_w = self.avatar_canvas.winfo_width()
            canvas_h = self.avatar_canvas.winfo_height()
            self.image_pan_x = (canvas_w - scaled_image.width) // 2
            self.image_pan_y = (canvas_h - scaled_image.height) // 2

        if self.image_item_id:
            self.avatar_canvas.delete(self.image_item_id)

        self.image_item_id = self.avatar_canvas.create_image(
            self.image_pan_x,
            self.image_pan_y,
            anchor="nw",
            image=self.avatar_image,
        )

        self.draw_overlay()

    def on_canvas_press(self, event):
        if not self.original_image:
            return
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        if self.processed_avatar_item_id:
            self.avatar_canvas.delete(self.processed_avatar_item_id)
            self.processed_avatar_item_id = None

    def on_canvas_drag(self, event):
        if not self.original_image:
            return

        dx = event.x - self.drag_data["x"]
        dy = event.y - self.drag_data["y"]
        self.image_pan_x += dx
        self.image_pan_y += dy

        img_w = self.avatar_image.width()
        img_h = self.avatar_image.height()

        rect_x1, rect_y1, rect_x2, rect_y2 = self.original_rect_coords

        if img_w > RECT_W:
            if self.image_pan_x > rect_x1:
                self.image_pan_x = rect_x1
            if self.image_pan_x + img_w < rect_x2:
                self.image_pan_x = rect_x2 - img_w
        else:
            self.image_pan_x = rect_x1 + (RECT_W - img_w) / 2

        if img_h > RECT_H:
            if self.image_pan_y > rect_y1:
                self.image_pan_y = rect_y1
            if self.image_pan_y + img_h < rect_y2:
                self.image_pan_y = rect_y2 - img_h
        else:
            self.image_pan_y = rect_y1 + (RECT_H - img_h) / 2

        self.avatar_canvas.coords(
            self.image_item_id, self.image_pan_x, self.image_pan_y
        )
        self.draw_overlay()
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def on_canvas_release(self, event):
        if not self.original_image:
            return
        self.show_processed_avatar()

    def draw_overlay(self):
        if not self.original_image:
            return

        image_coords = self.avatar_canvas.coords(self.image_item_id)
        x_offset = image_coords[0]
        y_offset = image_coords[1]

        rect_x1, rect_y1, rect_x2, rect_y2 = self.original_rect_coords

        scale = self.scale_adjust.get()
        scaled_rect_coords = (
            (rect_x1 - x_offset) / scale,
            (rect_y1 - y_offset) / scale,
            (rect_x2 - x_offset) / scale,
            (rect_y2 - y_offset) / scale,
        )
        image = self.original_image.copy().convert("RGBA")
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 128))
        draw = ImageDraw.Draw(overlay)
        draw.rectangle(scaled_rect_coords, fill=(0, 0, 0, 0))
        image_with_overlay = Image.alpha_composite(image, overlay)
        new_size = (
            int(self.original_image.width * scale),
            int(self.original_image.height * scale),
        )
        final_image = image_with_overlay.resize(new_size, LANCZOS)
        self.overlay_image_tk = ImageTk.PhotoImage(final_image)

        if self.image_item_id:
            self.avatar_canvas.itemconfig(
                self.image_item_id, image=self.overlay_image_tk
            )

        if self.rectangle_item_id:
            self.avatar_canvas.delete(self.rectangle_item_id)
        self.rectangle_item_id = self.avatar_canvas.create_rectangle(
            rect_x1, rect_y1, rect_x2, rect_y2, outline="white", width=2
        )
        self.avatar_canvas.tag_raise(self.rectangle_item_id)

    def show_processed_avatar(self):
        if not self.original_image:
            return

        image_x, image_y = self.avatar_canvas.coords(self.image_item_id)
        current_scale = self.scale_adjust.get()
        rect_x1, rect_y1, rect_x2, rect_y2 = self.original_rect_coords

        original_coords = (
            (rect_x1 - image_x) / current_scale,
            (rect_y1 - image_y) / current_scale,
            (rect_x2 - image_x) / current_scale,
            (rect_y2 - image_y) / current_scale,
        )

        self.processed_image = generate_avatar(
            self.original_image.copy(), coordinates=original_coords
        )

        zoomed_size = (
            int(self.processed_image.width * self.visual_zoom_factor),
            int(self.processed_image.height * self.visual_zoom_factor),
        )
        processed_image = self.processed_image.resize(zoomed_size, LANCZOS)

        self.processed_avatar_tk = ImageTk.PhotoImage(processed_image)

        if self.processed_avatar_item_id:
            self.avatar_canvas.delete(self.processed_avatar_item_id)

        rect_center_x = (rect_x1 + rect_x2) / 2
        rect_center_y = (rect_y1 + rect_y2) / 2
        new_x = rect_center_x - (processed_image.width / 2)
        new_y = rect_center_y - (processed_image.height / 2)

        self.processed_avatar_item_id = self.avatar_canvas.create_image(
            new_x, new_y, anchor="nw", image=self.processed_avatar_tk
        )

        self.avatar_canvas.tag_raise(self.processed_avatar_item_id)

    def _reset_values(self):
        self.avatar_image = None
        self.original_image = None
        self.avatar_path = None
        self.image_item_id = None
        self.rectangle_item_id = None
        self.processed_avatar_item_id = None
        self.processed_image = None


if __name__ == "__main__":
    app = PlayerAvatarEditor()
    app.window.mainloop()
