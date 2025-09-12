import re
from tkinter import Menu


class HoverInfo(Menu):
    def __init__(self, parent, text, command=None):
        self._com = command
        Menu.__init__(self, parent, tearoff=0)
        if not isinstance(text, str):
            raise TypeError(
                "Trying to initialise a Hover Menu with a non string type: "
                + text.__class__.__name__
            )

        text_token = re.split("\n", text)
        for token in text_token:
            self.add_command(label=token)

        self._displayed = False
        self.master.bind("<Enter>", self.display)
        self.master.bind("<Leave>", self.remove)

    def __del__(self):
        self.master.unbind("<Enter>")
        self.master.unbind("<Leave>")

    def display(self, event):
        if not self._displayed:
            self._displayed = True
            self.post(event.x_root, event.y_root)
        if self._com is not None:
            print("HoverInfo.Display", repr(self._com))
            if not self.master.bind("<Return>"):
                print("Binding <Return> to command")
                self.click(event)
            else:
                print("Already bound <Return> to command")
                # If already bound, unbind and rebind to ensure the command is set
                self.master.unbind_all("<Return>")
                self.master.bind_all("<Return>", self.click)

    def remove(self, event):
        if self._displayed:
            self._displayed = False
            self.unpost()

        if self._com is not None:
            self.unbind_all("<Return>")

    def click(self, event):
        self._com(event)
