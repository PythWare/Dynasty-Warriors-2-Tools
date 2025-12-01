# DW2_Tools/DW2_Bodyguard_Progression.py

import os
import tkinter as tk
from tkinter import ttk

from .Utility import DW2_BIN, setup_lilac_styles, LILAC  # central bin path

class GuardTool:
    """
    Dynasty Warriors 2 Bodyguard Progression Editor

    It uses DW2_BIN from Utility, seeks the 15 byte guard progression block and edits it, and
    can also patch AI_GUARD_FOLLOW to make player guards follow in formation
    """

    # Static meta
    AI_GUARD_FOLLOW = 0x15F71028
    FOLLOW_VALUE = b"\x11"

    def __init__(self, root):
        self.root = root
        self.root.title("Dynasty Warriors 2 Bodyguard Progression Editor")
        self.root.geometry("1250x700")
        self.root.resizable(False, False)

        setup_lilac_styles()
        
        self.bin_path = DW2_BIN

        self.guard_prog_offset = 0x160CF338

        self.spin_widgets: list[ttk.Spinbox] = []
        self.hex_values: list[str] = [f"{i:02X}" for i in range(256)]

        self._build_gui()

        # locate and read the progression data immediately
        if os.path.exists(self.bin_path):
            self._read_data()
        else:
            self.status_label.config(
                text=f"DW2.bin not found at: {self.bin_path}", foreground="red"
            )

    def _build_gui(self):
        # Full window lilac background for labels
        self.bg = ttk.Frame(self.root, style="Lilac.TFrame")
        self.bg.place(x=0, y=0, relwidth=1, relheight=1)

        # Top info line
        ttk.Label(
            self.bg,
            text=f"Editing BIN: {os.path.basename(self.bin_path)}",
            style="Lilac.TLabel"
        ).place(x=20, y=20)

        # Buttons
        self.write_btn = ttk.Button(
            self.root,
            text="Submit Values",
            command=self.write_data,
            width=14
        )
        self.write_btn.place(x=220, y=56)

        self.guard_follow = ttk.Button(
            self.root,
            text="Make Guards follow in formation",
            command=self.update_follow,
            width=40
        )
        self.guard_follow.place(x=400, y=56)

        # Labels explaining behaviour
        self.explain_1 = ttk.Label(
            self.bg,
            text=(
                "The button below permanently makes Player bodyguards follow in "
                "formation like AI guards do."
            ),
            style="Lilac.TLabel",
            foreground="green"
        )
        self.explain_1.place(x=400, y=24)

        self.explain_2 = ttk.Label(
            self.bg,
            text=(
                "The 5th tier is an unused bodyguard slot by default that Koei didn't "
                "use in the base game. Tier 5 is usable though, set the values you want "
                "then click Submit Values. Each tier affects the set of guards you get "
                "at each rank."
            ),
            style="Lilac.TLabel",
            foreground="green",
            wraplength=1200,
            justify="left"
        )
        self.explain_2.place(x=20, y=600)

        # Status line
        self.status_label = ttk.Label(self.bg, text="", style="Lilac.TLabel")
        self.status_label.place(x=20, y=400)

        # Labels for each field across 5 tiers
        self.labels = [
            # Tier 1
            "Rank (name ID value)",  # 0
            "Guard Model",  # 1
            "Guard Motion/Moveset",  # 2
            # Tier 2
            "Rank (name ID value)",
            "Guard Model",
            "Guard Motion/Moveset",
            # Tier 3
            "Rank (name ID value)",
            "Guard Model",
            "Guard Motion/Moveset",
            # Tier 4
            "Rank (name ID value)",
            "Guard Model",
            "Guard Motion/Moveset",
            # Tier 5
            "Rank (name ID value)",
            "Guard Model",
            "Guard Motion/Moveset"
        ]

        num_tiers = 5
        fields_per_tier = 3  # Rank, Model, Motion

        # Layout settings
        top_y = 110  # y for the tier headers
        header_to_fields_gap = 30
        row_h = 26  # vertical spacing between fields

        # Horizontal spacing for columns
        start_x = 20  # left margin
        col_width = 250  # distance between each tier column
        label_to_box_dx = 150  # how far to the right the spinbox is from its label

        tier_headers = [
            "Tier 1 Bodyguards",
            "Tier 2 Bodyguards",
            "Tier 3 Bodyguards",
            "Tier 4 Bodyguards",
            "Tier 5 Bodyguards"
        ]

        vcmd_hex = (self.root.register(self._validate_hex_byte), "%P")

        for tier in range(num_tiers):
            base_x = start_x + tier * col_width

            # Tier header label
            ttk.Label(
                self.bg,
                text=tier_headers[tier],
                style="Lilac.TLabel",
            ).place(x=base_x, y=top_y)

            # Fields for this tier
            for f in range(fields_per_tier):
                idx = tier * fields_per_tier + f  # index into self.labels
                field_y = top_y + header_to_fields_gap + f * row_h

                # Field label
                ttk.Label(
                    self.bg,
                    text=self.labels[idx],
                    style="Lilac.TLabel",
                ).place(x=base_x, y=field_y + 2)

                # Spinbox that cycles through fixed hex values 00–FF
                sb = ttk.Spinbox(
                    self.root,
                    values=self.hex_values,
                    width=4,
                    wrap=True,
                    validate="key",
                    validatecommand=vcmd_hex,
                )
                # Normalize to uppercase hex when leaving the field or pressing Enter
                sb.bind("<FocusOut>", self._force_upper_hex)
                sb.bind("<Return>", self._force_upper_hex)

                sb.place(x=base_x + label_to_box_dx, y=field_y)
                self.spin_widgets.append(sb)

    # Spinbox helpers

    def _force_upper_hex(self, event):
        """Normalize spinbox text to 2 digit uppercase hex on focus out/Enter"""
        sb = event.widget
        text = sb.get().strip()
        if not text:
            return

        try:
            val = int(text, 16)
        except ValueError:
            return

        # Clamp to a byte and write as 2 digit UPPER hex
        if val < 0:
            val = 0
        elif val > 255:
            val = 255

        self._set_sb_hex(sb, val)

    def _set_sb_hex(self, sb, value: int) -> None:
        """Set spinbox display to a 2 digit hex string like 00–FF"""
        value = max(0, min(255, int(value)))
        sb.delete(0, tk.END)
        sb.insert(0, f"{value:02X}")

    def _byte_from_sb_hex(self, sb) -> int:
        """Read a hex string from spinbox and convert to 0–255 integer"""
        s = sb.get().strip()
        if not s:
            return 0
        try:
            v = int(s, 16)
        except ValueError:
            v = 0
        return 0 if v < 0 else 255 if v > 255 else v

    def _validate_hex_byte(self, proposed: str) -> bool:
        """
        Validation callback for spinboxes
        It allows empty while typing and up to 2 hex digits
        """
        if proposed == "":
            return True
        if len(proposed) > 2:
            return False
        for ch in proposed:
            if ch not in "0123456789abcdefABCDEF":
                return False
        return True

    # Core logic

    def _read_data(self):
        """Find guard progression data, then populate the spinboxes"""
        if not os.path.exists(self.bin_path):
            self.status_label.config(
                text=f"DW2.bin not found: {self.bin_path}", foreground="red"
            )
            return

        try:
            with open(self.bin_path, "rb") as f:
                # Read 15 bytes of guard data
                f.seek(self.guard_prog_offset)
                values = list(f.read(15))
                if len(values) != 15:
                    raise ValueError("Could not read 15 bytes of guard data.")

            # Populate spinboxes
            for sb, val in zip(self.spin_widgets, values):
                self._set_sb_hex(sb, val)

            self.status_label.config(
                text=f"Guard progression data loaded at 0x{self.guard_prog_offset:X}.",
                foreground="green",
            )

        except Exception as e:
            self.status_label.config(text=f"Error reading: {e}", foreground="red")

    def write_data(self):
        """Write current spinbox values back to DW2.bin (15 bytes at guard_prog_offset)"""
        if self.guard_prog_offset is None:
            self.status_label.config(
                text="Guard progression offset not found; cannot write.",
                foreground="red",
            )
            return

        if not os.path.exists(self.bin_path):
            self.status_label.config(
                text=f"DW2.bin not found: {self.bin_path}", foreground="red"
            )
            return

        try:
            values = [self._byte_from_sb_hex(sb) for sb in self.spin_widgets]
            if len(values) != 15:
                raise ValueError(f"Expected 15 values, got {len(values)}")

            with open(self.bin_path, "r+b") as f:
                f.seek(self.guard_prog_offset)
                f.write(bytes(values))

            self.status_label.config(
                text="Guard progression data written successfully.",
                foreground="green",
            )

        except Exception as e:
            self.status_label.config(text=f"Error writing: {e}", foreground="red")

    def update_follow(self):
        """
        Patch AI_GUARD_FOLLOW so player bodyguards follow in formation like AI bodyguards do
        """
        if not os.path.exists(self.bin_path):
            self.status_label.config(
                text=f"DW2.bin not found: {self.bin_path}", foreground="red"
            )
            return

        try:
            with open(self.bin_path, "r+b") as f:
                f.seek(self.AI_GUARD_FOLLOW)
                f.write(self.FOLLOW_VALUE)

            self.status_label.config(
                text="Player guards now set to follow like AI guards.",
                foreground="green",
            )

        except Exception as e:
            self.status_label.config(text=f"Error writing: {e}", foreground="red")
