# DW2_Tools/Unit_Editor.py

import os
from io import BytesIO
import tkinter as tk
from tkinter import ttk

from .Utility import TheCheck, unit_data, DW2_BIN, ICON_DIR, BACKUP_DIR # unit_data: offsets in DW2.bin

# Mod file extension written by Create Unit Mod
DW2_UNIT_MOD_EXT = ".DW2UnitMod"

# Slot layout: 7 bytes per unit
SLOT_SIZE = 7
NUM_SLOTS_FIRST = 53
NUM_SLOTS_SECOND = 201
NUM_SLOTS_TOTAL = NUM_SLOTS_FIRST + NUM_SLOTS_SECOND  # 254

# GUI field definitions: name on self, label text, row index
FIELD_DEFS = [
    ("name",      "Name",                         0),
    ("unknown",   "Unknown",                      1),
    ("model",     "Model",                        2),
    ("color",     "Color",                        3),
    ("motion",    "Weapon + Motion",              4),
    ("horse",     "Horse",                        5),
    ("itemcount", "Amount of items and heals",    6),
]


class UnitEditor(TheCheck):
    """
    Dynasty Warriors 2 Unit Editor

    Reads unit blocks from DW2.bin into a single BytesIO
    
    Layout: 53 * 7 bytes from unit_data[0] + 201 * 7 bytes from unit_data[1],
      then the original unit_data offsets appended as 4 byte values

    Offset per slot equals slot_index * 7

    One backup file written to Backups_For_Mod_Disabling if none exists
    """

    def __init__(self, root):
        self.root = root
        self.root.title("Unit Editor")
        
        self.root.iconbitmap(os.path.join(ICON_DIR, "icon2.ico"))

        self.root.minsize(500, 400)
        self.root.resizable(False, False)

        # In-memory unit data
        self.unit_mem: BytesIO | None = None
        self._load_unit_data_in_memory()

        # TK variables for each field
        self.field_vars = {}
        for name, _label, _row in FIELD_DEFS:
            var = tk.IntVar()
            setattr(self, name, var)      # self.name, self.model, etc
            self.field_vars[name] = var

        # Other TK variables
        self.modname = tk.StringVar()

        # Hex slot selector (0x0 to 0xFD for 254 slots)
        hex_values = [hex(i) for i in range(NUM_SLOTS_TOTAL)]
        self.selected_slot_str = tk.StringVar(self.root)
        self.selected_slot_str.set(hex_values[0])

        slot_combobox = ttk.Combobox(
            self.root,
            textvariable=self.selected_slot_str,
            values=hex_values,
            width=8,
            state="readonly",
        )
        slot_combobox.bind("<<ComboboxSelected>>", self.slot_selected)
        slot_combobox.place(x=350, y=10)

        # Buttons/status/mod name
        tk.Button(
            self.root,
            text="Create Unit Mod",
            command=self.create_unit_mod,
            height=3,
        ).place(x=10, y=330)

        tk.Entry(self.root, textvariable=self.modname).place(x=120, y=300)
        tk.Label(self.root, text="Enter a mod name").place(x=10, y=300)

        tk.Button(
            self.root,
            text="Submit values to unit data",
            command=self.submit_unit,
            height=3,
        ).place(x=300, y=330)

        self.status_label = tk.Label(self.root, text="", fg="green")
        self.status_label.place(x=10, y=270)

        # Labels + entries built from FIELD_DEFS
        self._build_labels()
        self._build_entries()

        # Character slot label
        tk.Label(self.root, text="Character slot:").place(x=240, y=10)

        # Load initial slot (0)
        self.unit_display(0)

    # In-memory loading & backup

    def _load_unit_data_in_memory(self):
        """
        Build a single BytesIO:
        
        53 * 7 bytes at unit_data[0] + 201 * 7 bytes at unit_data[1] +
        each value in unit_data as 4 bytes and create a single backup
        file if it doesn't already exist
        """
        os.makedirs(BACKUP_DIR, exist_ok=True)

        mem = BytesIO()
        with open(DW2_BIN, "rb") as f:
            # First 53 units (7 bytes each) from first offset
            f.seek(unit_data[0])
            for _ in range(NUM_SLOTS_FIRST):
                chunk = f.read(SLOT_SIZE)
                if len(chunk) != SLOT_SIZE:
                    raise IOError(
                        f"Unexpected EOF reading unit data at 0x{unit_data[0]:X}"
                    )
                mem.write(chunk)

            # Next 201 units (7 bytes each) from second offset
            f.seek(unit_data[1])
            for _ in range(NUM_SLOTS_SECOND):
                chunk = f.read(SLOT_SIZE)
                if len(chunk) != SLOT_SIZE:
                    raise IOError(
                        f"Unexpected EOF reading unit data at 0x{unit_data[1]:X}"
                    )
                mem.write(chunk)

            # Append original offsets at the end
            for a in unit_data:
                mem.write(a.to_bytes(4, "little"))

        mem.seek(0)
        self.unit_mem = mem

        # Create backup once if not already present
        backup_path = os.path.join(BACKUP_DIR, "DW2_Original.unitdata")
        if not os.path.exists(backup_path):
            with open(backup_path, "wb") as bf:
                bf.write(mem.getbuffer())

    # GUI layout helpers

    def _build_labels(self):
        label_x = 160
        base_y = 0
        row_h = 40

        for _name, label_text, row in FIELD_DEFS:
            y = base_y + row * row_h
            tk.Label(self.root, text=label_text).place(x=label_x, y=y)

    def _build_entries(self):
        vcmd = (self.root.register(self.validate_numeric_input), "%P")

        entry_x = 0
        base_y = 0
        row_h = 40

        for name, _label_text, row in FIELD_DEFS:
            y = base_y + row * row_h
            var = getattr(self, name)
            tk.Entry(
                self.root,
                textvariable=var,
                validate="key",
                validatecommand=vcmd,
            ).place(x=entry_x, y=y)

    # Slot handling

    def _get_selected_slot_index(self) -> int:
        """
        Parse the selected slot hex string (e.g. 0x1A) into an integer index
        """
        slot_str = self.selected_slot_str.get()
        try:
            return int(slot_str, 16)
        except ValueError:
            return 0

    def slot_selected(self, event=None):
        """Update display when a new slot is selected from the combobox"""
        slot_index = self._get_selected_slot_index()
        self.unit_display(slot_index)

    # Display & submit

    def unit_display(self, slot_index: int):
        """
        Read one 7 byte unit entry from in-memory buffer and populate TK vars
        
        Layout per 7-byte record:
          0: Name ID
          1: Unknown
          2: Model ID
          3: Color
          4: Weapon+Motion
          5: Horse
          6: Item/Heal count
        """
        if self.unit_mem is None:
            self.status_label.config(text="Unit data not loaded.", fg="red")
            return

        if not (0 <= slot_index < NUM_SLOTS_TOTAL):
            self.status_label.config(
                text=f"Slot {slot_index} out of range (0–{NUM_SLOTS_TOTAL-1}).",
                fg="red",
            )
            return

        offset = slot_index * SLOT_SIZE
        self.unit_mem.seek(offset)
        data = self.unit_mem.read(SLOT_SIZE)
        if len(data) != SLOT_SIZE:
            self.status_label.config(
                text=f"Unexpected end of unit data at slot {slot_index}.",
                fg="red",
            )
            return

        unitname = data[0]
        unk = data[1]
        unitmodel = data[2]
        unitcolor = data[3]
        unitmotion = data[4]
        unithorse = data[5]
        unititemcount = data[6]

        self.name.set(unitname)
        self.unknown.set(unk)
        self.model.set(unitmodel)
        self.color.set(unitcolor)
        self.motion.set(unitmotion)
        self.horse.set(unithorse)
        self.itemcount.set(unititemcount)

        self.status_label.config(
            text=f"Loaded slot {slot_index} (offset 0x{offset:X}).", fg="green"
        )

    def submit_unit(self):
        """
        Write current TK var values into the in-memory buffer for the selected slot
        """
        if self.unit_mem is None:
            self.status_label.config(text="Unit data not loaded.", fg="red")
            return

        try:
            slot_index = self._get_selected_slot_index()
            if not (0 <= slot_index < NUM_SLOTS_TOTAL):
                raise ValueError(f"Slot {slot_index} out of range.")

            # Build 7 byte record from TK vars
            record = bytes(
                [
                    self.name.get() & 0xFF,
                    self.unknown.get() & 0xFF,
                    self.model.get() & 0xFF,
                    self.color.get() & 0xFF,
                    self.motion.get() & 0xFF,
                    self.horse.get() & 0xFF,
                    self.itemcount.get() & 0xFF,
                ]
            )

            if len(record) != SLOT_SIZE:
                raise ValueError(f"Record length {len(record)} != {SLOT_SIZE}")

            offset = slot_index * SLOT_SIZE
            self.unit_mem.seek(offset)
            self.unit_mem.write(record)

            self.status_label.config(
                text=f"Values written for slot {slot_index}.", fg="green"
            )

        except Exception as e:
            self.status_label.config(
                text=f"Error with entries: {e}, please use values less than 255.",
                fg="red",
            )

    # Mod creation

    def create_unit_mod(self):
        """
        Dump the current in-memory unit data to a .DW2UnitMod file in the cwd
        """
        if self.unit_mem is None:
            self.status_label.config(text="Unit data not loaded.", fg="red")
            return

        sep = "."
        base_name = self.modname.get().split(sep, 1)[0] or "DW2Unit"
        usermodname = base_name + DW2_UNIT_MOD_EXT

        try:
            data = self.unit_mem.getvalue()
            with open(usermodname, "wb") as w1:
                w1.write(data)

            self.status_label.config(
                text=f"Mod file '{usermodname}' created successfully.", fg="green"
            )
        except Exception as e:
            self.status_label.config(
                text=f"Error creating mod file '{usermodname}': {e}", fg="red"
            )
