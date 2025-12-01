# DW2_Tools/gui.py

import tkinter as tk
from tkinter import ttk

from .Stage_Editor import StageEditor
from .Name_Editor import NameEditor
from .Unit_Editor import UnitEditor
from .Item_Editor import ItemEditor
from .DW2_Bodyguard_Progression import GuardTool
from .Mod_Manager import DW2ModManager
from .Utility import setup_lilac_styles, LILAC

class Core_Tools():
    def __init__(self, root):
        self.root = root
        self.root.title("Dynasty Warriors 2 Modding Tools Version 2.0")
        self.root.geometry("1020x800")
        self.root.resizable(False, False)

        setup_lilac_styles()

        self.tool_buttons = []

        self.stage_editor_window = None
        self.name_editor_window = None
        self.unit_editor_window = None
        self.item_editor_window = None
        self.guard_editor_window = None
        self.mod_manager_window = None

        self.gui_setup()

    def open_stage_editor(self):
        """Function for calling Stage Editor"""
        # If window exists and hasn't been destroyed, focus it
        if (self.stage_editor_window is not None and
                self.stage_editor_window.winfo_exists()):
            self.stage_editor_window.lift()
            self.stage_editor_window.focus_force()
            return

        # Otherwise, create a new Toplevel for the Stage Editor
        win = tk.Toplevel(self.root)
        win.title("Stage Editor")
        self.stage_editor_window = win

        # create the editor in this window
        StageEditor(win)

        # when this window is closed, clear the reference
        def on_close():
            self.stage_editor_window = None
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", on_close)

    def open_name_editor(self):
        """Function for calling Name Editor"""
        # If window exists and hasn't been destroyed, focus it
        if (
            self.name_editor_window is not None
            and self.name_editor_window.winfo_exists()
        ):
            self.name_editor_window.lift()
            self.name_editor_window.focus_force()
            return

        # Otherwise, create a new Toplevel for the Name Editor
        win = tk.Toplevel(self.root)
        win.title("Name Editor")
        self.name_editor_window = win

        # create the editor in this window
        NameEditor(win)

        # when this window is closed, clear the reference
        def on_close():
            self.name_editor_window = None
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", on_close)

    def open_unit_editor(self):
        """Function for calling Unit Editor"""
        # If window exists and hasn't been destroyed, focus it
        if (
            self.unit_editor_window is not None
            and self.unit_editor_window.winfo_exists()
        ):
            self.unit_editor_window.lift()
            self.unit_editor_window.focus_force()
            return

        # Otherwise, create a new Toplevel for the Name Editor
        win = tk.Toplevel(self.root)
        win.title("Unit Editor")
        self.unit_editor_window = win

        # create the editor in this window
        UnitEditor(win)

        # when this window is closed, clear the reference
        def on_close():
            self.unit_editor_window = None
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", on_close)

    def open_item_editor(self):
        """Function for calling Item Editor"""
        # If window exists and hasn't been destroyed, focus it
        if (
            self.item_editor_window is not None
            and self.item_editor_window.winfo_exists()
        ):
            self.item_editor_window.lift()
            self.item_editor_window.focus_force()
            return

        # Otherwise, create a new Toplevel for the Item Editor
        win = tk.Toplevel(self.root)
        win.title("Item Editor")
        self.item_editor_window = win

        # create the editor in this window
        ItemEditor(win)

        # when this window is closed, clear the reference
        def on_close():
            self.item_editor_window = None
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", on_close)

    def open_guard_editor(self):
        """Function for calling Guard Editor"""
        # If window exists and hasn't been destroyed, focus it
        if (
            self.guard_editor_window is not None
            and self.guard_editor_window.winfo_exists()
        ):
            self.guard_editor_window.lift()
            self.guard_editor_window.focus_force()
            return

        # Otherwise, create a new Toplevel for the Item Editor
        win = tk.Toplevel(self.root)
        win.title("Bodyguard Editor")
        self.guard_editor_window = win

        # create the editor in this window
        GuardTool(win)

        # when this window is closed, clear the reference
        def on_close():
            self.guard_editor_window = None
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", on_close)

    def open_mod_manager(self):
        """Function for calling Mod Manager"""
        # If window exists and hasn't been destroyed, focus it
        if (
            self.mod_manager_window is not None
            and self.mod_manager_window.winfo_exists()
        ):
            self.mod_manager_window.lift()
            self.mod_manager_window.focus_force()
            return

        # Otherwise, create a new Toplevel for the Mod Manager
        win = tk.Toplevel(self.root)
        win.title("Mod Manager")
        self.mod_manager_window = win

        # create the editor in this window
        DW2ModManager(win)

        # when this window is closed, clear the reference
        def on_close():
            self.mod_manager_window = None
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", on_close)
        
    def gui_setup(self):
        """Handles GUI designing"""
        self.bg = ttk.Frame(self.root, style="Lilac.TFrame")
        self.bg.place(x=0, y=0, relwidth=1, relheight=1)

        self.explainer_1 = ttk.Label(
                self.bg,
                text="Select the tool you want to use.",
                style="Lilac.TLabel"
            )
        self.explainer_1.place(x=50, y=20)

        # Status line (text messages)
        self.status_label = ttk.Label(
            self.bg,
            text="",
            style="Lilac.TLabel",
            foreground="green"
        )
        self.status_label.place(x=400, y=24)

        self.tools = [
                "Stage Editor",
                "Unit Editor",
                "Item Editor",
                "Name Editor",
                "Bodyguard Editor",
                "Mod Manager"
            ]

        top_y = 150
        row_spacing = 60
        col_spacing = 420
        left_margin = 180
        max_cols = 2

        for i, tool in enumerate(self.tools):
            row = i // max_cols
            col = i % max_cols

            x = left_margin + col * col_spacing
            y = top_y + row * row_spacing

            btn = ttk.Button(
                self.bg,
                text=tool,
                width=35,
            )
            btn.place(x=x, y=y)

            # attach commands per tool
            if tool == "Stage Editor":
                btn.config(command=self.open_stage_editor)
            elif tool == "Name Editor":
                btn.config(command=self.open_name_editor)
            elif tool == "Unit Editor":
                btn.config(command=self.open_unit_editor)
            elif tool == "Item Editor":
                btn.config(command=self.open_item_editor)
            elif tool == "Bodyguard Editor":
                btn.config(command=self.open_guard_editor)
            elif tool == "Mod Manager":
                btn.config(command=self.open_mod_manager)
            self.tool_buttons.append(btn)
