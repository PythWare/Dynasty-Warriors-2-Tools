# DW2_Tools/Item_Editor.py
import os
import tkinter as tk

from .Utility import TheCheck, itemsoffset, DW2_BIN, ICON_DIR

# Field layout: var_name, label_text, column_index, row_index
# Columns: 0 = HP, 1 = Arrows, 2 = Stat 1–4, 3 = Stat 5–8
FIELD_DEFS = [
    ("hp1",    "Health Item 1",         0, 0),
    ("hp2",    "Health Item 2",         0, 1),
    ("hp3",    "Health Item 3",         0, 2),
    ("hp4",    "Health Item 4",         0, 3),

    ("arrow1", "Arrows 1",              1, 0),
    ("arrow2", "Arrows 2",              1, 1),
    ("arrow3", "Arrows 3",              1, 2),
    ("arrow4", "Arrows 4",              1, 3),

    ("s1",     "Stat increase Item 1",  2, 0),
    ("s2",     "Stat increase Item 2",  2, 1),
    ("s3",     "Stat increase Item 3",  2, 2),
    ("s4",     "Stat increase Item 4",  2, 3),

    ("s5",     "Stat increase Item 5",  3, 0),
    ("s6",     "Stat increase Item 6",  3, 1),
    ("s7",     "Stat increase Item 7",  3, 2),
    ("s8",     "Stat increase Item 8",  3, 3),
]


class ItemEditor(TheCheck):
    """
    DW2 Item Editor

    It uses a provided root, Reads/writes item values directly in DW2.bin
    """

    def __init__(self, root):
        self.root = root
        self.root.title("Item Editor")
        
        self.root.iconbitmap(os.path.join(ICON_DIR, "icon5.ico"))

        self.root.minsize(800, 500)
        self.root.resizable(False, False)

        # Tk variables per item value
        self.field_vars = {}
        for name, _label, _col, _row in FIELD_DEFS:
            var = tk.IntVar()
            setattr(self, name, var)
            self.field_vars[name] = var

        self.itemlist = []  # list storing item values (16 ints)

        # Build GUI
        self._build_labels()
        self._build_entries_and_button()

        # Load values from DW2.bin
        self.item_reader()

    # GUI helpers

    def _build_labels(self):
        self.status_label = tk.Label(self.root, text="", fg="green")
        self.status_label.place(x=400, y=330)

        tk.Label(
            self.root,
            text=(
                "You can change the value the items have with the Item Editor. "
                "Stat increase items refer to the attack and defense items that "
                "\n are given when an officer or gate captain is defeated."
            ),
            justify="left",
        ).place(x=10, y=400)

        # Place the item labels using FIELD_DEFS
        base_x = 0
        base_y = 0
        col_spacing = 200
        row_spacing = 80

        for _name, label_text, col, row in FIELD_DEFS:
            x = base_x + col * col_spacing
            y = base_y + row * row_spacing
            tk.Label(self.root, text=label_text).place(x=x, y=y)

    def _build_entries_and_button(self):
        vcmd = (self.root.register(self.validate_numeric_input), "%P")

        base_x = 0
        base_y = 40
        col_spacing = 200
        row_spacing = 80

        for name, _label_text, col, row in FIELD_DEFS:
            x = base_x + col * col_spacing
            y = base_y + row * row_spacing
            var = self.field_vars[name]
            tk.Entry(
                self.root,
                textvariable=var,
                validate="key",
                validatecommand=vcmd,
            ).place(x=x, y=y)

        tk.Button(
            self.root,
            text="Submit item values to the DW2.bin file",
            command=self.item_writer,
            height=3,
        ).place(x=30, y=330)

    # Reading/writing

    def item_reader(self):
        """
        Read the 16 item value entries from DW2.bin and populate the IntVars,
        Each entry in DW2 is 12 bytes: 4 byte ID, 4 byte value, and 4 byte effect
        """
        self.itemlist.clear()

        try:
            with open(DW2_BIN, "rb") as f1:
                f1.seek(itemsoffset)
                for _ in range(16):
                    item_id = f1.read(4)   # essential to read, may add support for editing IDs later
                    if len(item_id) != 4:
                        raise IOError("Unexpected EOF while reading item IDs.")
                    itemvalue = int.from_bytes(f1.read(4), "little")
                    itemeffect = f1.read(4)  # may add support for effect altering later
                    if len(itemeffect) != 4:
                        raise IOError("Unexpected EOF while reading item effects.")
                    self.itemlist.append(itemvalue)

            if len(self.itemlist) != 16:
                raise ValueError(
                    f"Expected 16 item values, got {len(self.itemlist)}."
                )

            # Assign into IntVars in the same order as FIELD_DEFS
            for i, (name, _label, _col, _row) in enumerate(FIELD_DEFS):
                self.field_vars[name].set(self.itemlist[i])

            self.status_label.config(
                text="Item values loaded successfully.", fg="green"
            )

        except Exception as e:
            self.status_label.config(
                text=f"Error reading item values: {e}", fg="red"
            )

    def item_writer(self):
        """
        Write the current item values directly into DW2.bin,
        keeps original IDs and effects but only the 4 byte value for each item is changed for now
        """
        try:
            # Collect current values from TK vars in FIELD_DEFS order
            col = [
                self.field_vars[name].get().to_bytes(4, "little")
                for name, _label, _col, _row in FIELD_DEFS
            ]

            if len(col) != 16:
                raise ValueError(
                    f"Expected 16 values to write, got {len(col)}."
                )

            with open(DW2_BIN, "r+b") as w1:
                w1.seek(itemsoffset)
                for item_value_bytes in col:
                    item_id = w1.read(4)  # keep existing ID
                    if len(item_id) != 4:
                        raise IOError("Unexpected EOF while reading item ID.")
                    w1.write(item_value_bytes)  # overwrite the value
                    item_effect = w1.read(4)    # keep existing effect
                    if len(item_effect) != 4:
                        raise IOError("Unexpected EOF while reading item effect.")

            self.status_label.config(
                text="Values were written without issues.", fg="green"
            )

        except Exception as e:
            self.status_label.config(
                text=f"Error with entries: {e}", fg="red"
            )
