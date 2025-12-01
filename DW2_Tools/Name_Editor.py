import os
import tkinter as tk
from tkinter import ttk
from .Utility import DW2_BIN, ICON_DIR

class NameEditor:
    """DW2 name editor"""

    def __init__(self, root):
        self.root = root
        self.root.title("Name Editor")
        self.root.iconbitmap(os.path.join(ICON_DIR, "icon4.ico"))

        self.root.minsize(700, 400)
        self.root.resizable(False, False)

        # base offset, slot count, byte length per name
        self.name_offsets1 = [0x16141F78, 64, 15]
        self.name_offsets2 = [0x161424A8, 27, 15]
        self.name_offsets3 = [0x1615A410, 41, 7]
        self.name_offsets4 = [0x1615A688, 14, 7]

        # Which offset group is currently being used for the active slot
        self.current_offset_group = None

        # TK variables
        self.noffset1 = tk.StringVar()
        self.selected_slot = tk.IntVar(self.root)
        self.selected_slot.set(0)  # Default value

        # GUI setup

        tk.Label(self.root, text="Unit Names:").place(x=10, y=0)

        tk.Label(self.root, text="Unit Name Slots:").place(x=200, y=0)
        slot_combobox = ttk.Combobox(
            self.root,
            textvariable=self.selected_slot,
            values=list(range(146)),
            width=10,
        )
        slot_combobox.bind("<<ComboboxSelected>>", self.slot_selected)
        slot_combobox.place(x=300, y=0)

        tk.Entry(self.root, textvariable=self.noffset1, width=40).place(x=10, y=30)
        update_button = ttk.Button(
            self.root, text="Update Name", command=self.update_name
        )
        update_button.place(x=10, y=60)

        self.status_label = tk.Label(self.root, text="", fg="green")
        self.status_label.place(x=10, y=100)

        # load initial slot 0
        self.slot_selected()

    # Slot selection & display

    def slot_selected(self, event=None):
        """Update display data when a new slot is selected"""
        selected_slot_value = self.selected_slot.get()
        self.name_display(selected_slot_value)

    def _resolve_slot_offset(self, selected_slot_value):
        """
        Determine which offset group & offset/length apply for the given slot
        Returns offset, byte_length, group_ref or None, None, None
        """

        # name_offsets1: slots 0-63 (64 slots), 16 byte spacing, 15 byte name
        if selected_slot_value < self.name_offsets1[1]:
            base, count, byte_len = self.name_offsets1
            offset = base + selected_slot_value * 16
            return offset, byte_len, self.name_offsets1

        # name_offsets2: next 27 slots
        if self.name_offsets1[1] <= selected_slot_value < (self.name_offsets1[1] + self.name_offsets2[1]):
            base, count, byte_len = self.name_offsets2
            rel = selected_slot_value - self.name_offsets1[1]
            offset = base + rel * 16
            return offset, byte_len, self.name_offsets2

        # name_offsets3: next 41 slots
        if (self.name_offsets1[1] + self.name_offsets2[1]) <= selected_slot_value < (
            self.name_offsets1[1] + self.name_offsets2[1] + self.name_offsets3[1]
        ):
            base, count, byte_len = self.name_offsets3
            rel = selected_slot_value - (self.name_offsets1[1] + self.name_offsets2[1])
            offset = base + rel * 8
            return offset, byte_len, self.name_offsets3

        # name_offsets4: remaining up to slot 145
        if (
            self.name_offsets1[1] + self.name_offsets2[1] + self.name_offsets3[1]
            <= selected_slot_value
            < 146
        ):
            base, count, byte_len = self.name_offsets4
            rel = selected_slot_value - (
                self.name_offsets1[1] + self.name_offsets2[1] + self.name_offsets3[1]
            )
            offset = base + rel * 8
            return offset, byte_len, self.name_offsets4

        return None, None, None

    def name_display(self, selected_slot_value: int):
        """Read the name for the selected slot from DW2.bin and show it"""
        offset, byte_length, group = self._resolve_slot_offset(selected_slot_value)
        if offset is None:
            self.status_label.config(
                text=f"Slot {selected_slot_value} is out of known ranges.", fg="red"
            )
            return

        self.current_offset_group = group

        try:
            with open(DW2_BIN, "r+b") as f:
                pos = f.seek(offset)
                name_bytes = f.read(byte_length)

            # Basic status info
            self.status_label.config(
                text=(
                    f"Slot {selected_slot_value}: "
                    f"offset 0x{offset:X} ({pos}), Max Length Supported: {byte_length}"
                ),
                fg="green",
            )

            # Decode for display: strip trailing nulls, assume ASCII-ish
            clean_bytes = name_bytes.split(b"\x00", 1)[0]
            try:
                name_str = clean_bytes.decode("ascii", errors="ignore")
            except Exception:
                # fallback: show raw repr, user can overwrite
                name_str = repr(name_bytes)

            self.noffset1.set(name_str)

        except Exception as e:
            self.status_label.config(text=f"Error reading name: {e}", fg="red")

    # Write back

    def update_name(self):
        """Write the edited name back into DW2.bin for the current slot"""
        if self.current_offset_group is None:
            self.status_label.config(text="No valid name slot selected.", fg="red")
            return

        new_name = self.noffset1.get()
        byte_limit = self.current_offset_group[2]  # max bytes for this name

        # Encode as single-byte ASCII
        # Truncate to byte_limit, then pad with nulls.
        try:
            raw_bytes = new_name.encode("ascii", errors="ignore")
        except Exception:
            raw_bytes = new_name.encode("utf-8", errors="ignore")

        new_name_truncated = raw_bytes[:byte_limit]
        new_name_padded = new_name_truncated.ljust(byte_limit, b"\x00")

        # Determine correct offset again based on current group & slot
        slot = self.selected_slot.get()
        offset, _byte_length, group = self._resolve_slot_offset(slot)
        if offset is None or group is not self.current_offset_group:
            self.status_label.config(
                text="Internal mismatch in name slot/group.", fg="red"
            )
            return

        try:
            with open(DW2_BIN, "r+b") as f:
                f.seek(offset)
                f.write(new_name_padded)

            self.status_label.config(
                text=f"Updated name for slot {slot}.", fg="green"
            )
        except Exception as e:
            self.status_label.config(text=f"Error writing name: {e}", fg="red")
