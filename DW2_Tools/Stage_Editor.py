# DW2_Tools/Stage_Editor.py

import os
from io import BytesIO
import tkinter as tk
from tkinter import ttk, PhotoImage

from .Utility import (
    TheCheck,
    unit_names,
    stage_data,
    DW2_BIN,
    ICON_DIR,
    BACKUP_DIR,
    BACKGROUNDS_DIR,
)

from .DW2CordGuide import ImageMarkerApp

filenames = [
    "YTR_Stage",
    "HLG_Stage",
    "GD_Stage",
    "CBan_Stage",
    "CBi_Stage",
    "HF_Stage",
    "YL_Stage",
    "WZP_Stage",
]

stage_extension = [
    ".DW2YTR",
    ".DW2HLG",
    ".DW2GD",
    ".DW2CBan",
    ".DW2CBi",
    ".DW2HF",
    ".DW2YL",
    ".DW2WZP",
]

# name on self, label text, row index (for Y position)
FIELD_DEFS = [
    ("xcord",    "Spawn Position X",                        0),
    ("ycord",    "Spawn Position Y",                        1),
    ("direct",   "Spawn Direction",                         2),
    ("AreaP",    "Pathing",                                 3),
    ("PullingB", "Gate Behavior (Respawn/Retreat)",         4),
    ("Lif",      "Life Stat",                               5),
    ("LeaderU",  "Leader Unit",                             6),
    ("GuardU",   "Guard Units",                             7),
    ("Att",      "Attack Stat",                             8),
    ("Def",      "Defense Stat",                            9),
    ("AmountG",  "Amount of guards (9 is max)",            10),
    ("UnitS",    "Unit slot that unit belongs to",         11),
    ("UnitG",    "Unit Type",                               12),
    ("AIT",      "AI Type/Kind (4=horse, 2=bowman)",       13),
    ("UnitC",    "Orders (1=Attack enemy target, 3=Follow ally target)", 14),
    ("Hid",      "Hide Unit",                              15),
    ("Advance",  "Order Target Slot",                      16),
    ("ItemD",    "Item Dropped",                           17),
    ("AIL",      "AI Level",                               18),
    ("DelayO",   "Delay Order",                            19),
    ("PointsK",  "Points For K.O.",                        20),
]

class StageEditor(TheCheck):  # for modding stage/battles
    def __init__(self, root):
        self.filenames = filenames  # stage ids for combobox
        self.stage_files: dict[str, BytesIO] = {}  # in-memory data per stage
        # track a single Coordinate Guide window
        self.coord_guide_window = None
        self.coord_guide_app = None
        
        self.root = root
        self.root.title("Stage Editor")
        self.root.iconbitmap(os.path.join(ICON_DIR, "icon1.ico"))
        self.root.minsize(1600, 900)
        self.root.resizable(False, False)

        # in-memory extraction from DW2.bin
        self.stage_data_create()

        # Load the default image based on the initial combobox selection
        initial_map_index = 0
        initial_image_path = self.get_image_filename(initial_map_index)
        self.img = PhotoImage(file=initial_image_path)
        self.img_label = tk.Label(self.root, image=self.img)
        self.img_label.place(x=0, y=0)

        # GUI: stage selection
        self.selected_file = tk.StringVar(self.root)
        self.selected_file.set(self.filenames[0])  # Default value
        file_combobox = ttk.Combobox(
            self.root, textvariable=self.selected_file, values=self.filenames
        )
        file_combobox.bind("<<ComboboxSelected>>", self.stage_search_on_map_change)
        file_combobox.place(x=1160, y=10)
        tk.Label(self.root, text="Stage to modify").place(x=1060, y=10)

        # GUI: slot selection (0–511)
        # GUI: side selection (Side 1 / Side 2)
        self.side_var = tk.StringVar(self.root)
        self.side_var.set("Side 1 (0–255)")
        side_combobox = ttk.Combobox(
            self.root,
            textvariable=self.side_var,
            state="readonly",
            values=["Side 1 (0–255)", "Side 2 (256–511)"],
            width=18,
        )
        side_combobox.bind("<<ComboboxSelected>>", self.slot_side_changed)
        side_combobox.place(x=920, y=10)
        tk.Label(self.root, text="Side").place(x=710, y=10)

        # GUI: slot selection within side (0–255)
        self.side_slot = tk.IntVar(self.root)
        self.side_slot.set(0)
        slot_combobox = ttk.Combobox(
            self.root,
            textvariable=self.side_slot,
            values=list(range(256)),
            width=10,
        )
        slot_combobox.bind("<<ComboboxSelected>>", self.slot_side_changed)
        slot_combobox.place(x=820, y=10)
        tk.Label(self.root, text="Unit Slot (per side)").place(x=700, y=10)

        # internal: global slot index 0–511, used by logic
        self.selected_slot = tk.IntVar(self.root)
        self.selected_slot.set(0)

        self.status_label = tk.Label(self.root, text="", fg="green")
        self.status_label.place(x=480, y=200)

        # unit name combo
        self.combo = ttk.Combobox(
            self.root, values=unit_names, width=30, state="readonly"
        )
        self.combo.place(x=1200, y=600)
        self.combo.set(unit_names[0])
        self.combo.bind("<<ComboboxSelected>>", self.on_select)

        # Tk variables for slot fields
        # Tk variables for slot fields, created from FIELD_DEFS
        self.field_vars = {}
        for name, _label, _row in FIELD_DEFS:
            var = tk.IntVar()
            setattr(self, name, var)          # keep self.xcord, self.ycord, etc. working
            self.field_vars[name] = var

        # raw bytes that should round trip unchanged
        self.unused1 = b"\x00"      # byte 8
        self.unused2 = b"\x00"      # byte 21
        self.unused3 = b"\x00" * 4  # bytes 29–32

        self.modname = tk.StringVar()
        tk.Button(
            self.root,
            text="Submit values to DATA file",
            command=self.submit_stage_values,
            height=5,
            width=20,
        ).place(x=1375, y=15)
        
        tk.Button(
            self.root,
            text="Open Coordinate Guide",
            command=self.open_coord_guide,
            height=5,
            width=20,
        ).place(x=1375, y=140)
        
        tk.Button(
            self.root,
            text="Create Stage Mod",
            command=self.create_stage_mod,
            width=15,
        ).place(x=550, y=10)
        tk.Entry(self.root, textvariable=self.modname).place(x=395, y=10)
        tk.Label(self.root, text="Enter a mod name").place(x=280, y=10)

        self.stage_labels()
        self.stage_entries()

        # load initial slot 0 of first stage
        self.stage_search(self.filenames[0], 0)

    # GUI helpers

    def stage_labels(self):
        """ Extra explanatory labels """
        tk.Label(
            self.root,
            text="Integer values to use for Leader unit and guard unit:",
        ).place(x=1200, y=570)
        tk.Label(
            self.root,
            text="""Unit Groups:
            0-Player
            1-Commander
            2-General (Doesn't advance with Group 3)
            3-Playable Officers
            4-NPC Officers
            5-Gate Captains/Bodyguards/Troops that don't respawn
            6-Troops""",
        ).place(x=700, y=570)

        # Field labels (left side), stacked vertically
        label_x = 160
        base_y = 0
        row_height = 40

        for name, label_text, row in FIELD_DEFS:
            y = base_y + row * row_height
            tk.Label(self.root, text=label_text).place(x=label_x, y=y)


    def stage_entries(self):
        vcmd = (self.root.register(self.validate_numeric_input), "%P")

        entry_x = 0
        base_y = 0
        row_height = 40

        for name, _label_text, row in FIELD_DEFS:
            y = base_y + row * row_height
            var = getattr(self, name)  # we set these in __init__
            tk.Entry(
                self.root,
                textvariable=var,
                validate="key",
                validatecommand=vcmd,
            ).place(x=entry_x, y=y)

    def on_select(self, event):
        # currently just holds selection, hook any extra logic here if needed
        selected_unit = self.combo.get()

    # In-memory stage init

    def stage_data_create(self):
        """
        Build one BytesIO per stage
        
        512 * 32 bytes of slot data + 8 * 4 byte original stage offsets

        Also on first run, create one backup file per stage in
        Backups_For_Mod_Disabling so mods can be disabled/restored later
        """
        self.stage_files.clear()
        # expect stage_data to have one list per stage name
        if len(stage_data) != len(self.filenames):
            raise ValueError("stage_data and filenames length mismatch")

        # make sure backup folder exists
        os.makedirs(BACKUP_DIR, exist_ok=True)

        with open(DW2_BIN, "rb") as f1:
            for i, stage_name in enumerate(self.filenames):
                mem = BytesIO()
                offsets_for_stage = stage_data[i]

                # slot region: 8 blocks * 64 slots * 32 bytes
                for base_off in offsets_for_stage:
                    f1.seek(base_off)
                    for _ in range(64):
                        chunk = f1.read(32)
                        if len(chunk) != 32:
                            raise IOError(
                                f"Unexpected EOF reading stage '{stage_name}' at 0x{base_off:X}"
                            )
                        mem.write(chunk)

                # append the original 8 offsets
                for base_off in offsets_for_stage:
                    mem.write(base_off.to_bytes(4, "little"))

                # rewind and store in-memory
                mem.seek(0)
                self.stage_files[stage_name] = mem

                # backup creation only if not already present
                backup_name = f"{stage_name}_Original.stage"
                backup_path = os.path.join(BACKUP_DIR, backup_name)

                if not os.path.exists(backup_path):
                    # write the entire in-memory buffer (512 slots + 8 offsets)
                    with open(backup_path, "wb") as bf:
                        bf.write(mem.getbuffer())

    # Map images

    def get_image_filename(self, map_index):
        map_filenames = [
            "YTR.png",
            "HLG.png",
            "GuanDu.png",
            "ChangBan.png",
            "ChiBi.png",
            "HeFei.png",
            "YiLing.png",
            "WuZhangPlains.png",
        ]
        return os.path.join(BACKGROUNDS_DIR, map_filenames[map_index])

    def stage_search_on_map_change(self, event=None):
        selected_file_value = self.selected_file.get()
        selected_slot_value = self.selected_slot.get()
        self.stage_search(selected_file_value, selected_slot_value)

        # Update map image
        selected_map_index = self.filenames.index(selected_file_value)
        image_filename = self.get_image_filename(selected_map_index)
        self.img = PhotoImage(file=image_filename)
        self.img_label.configure(image=self.img)

    def get_global_slot(self) -> int:
        """
        Convert side/side_slot to global slot index 0–511,
        Side 1: 0–255, Side 2: 256–511
        """
        side_label = self.side_var.get()
        # very simple mapping, check which side string we have
        side_index = 0 if "Side 1" in side_label else 1
        return side_index * 256 + self.side_slot.get()

    def slot_side_changed(self, event=None):
        """
        Called whenever either the side combobox or the per-side slot combobox changes
        Updates global selected_slot and refreshes the view
        """
        global_slot = self.get_global_slot()
        self.selected_slot.set(global_slot)
        selected_file_value = self.selected_file.get()
        self.stage_search(selected_file_value, global_slot)

    # Core: read/edit slots in memory

    def stage_search(self, selected_file, selected_slot):
        """
        Read one 32 byte slot from the in-memory stage file
        Offsets are computed as slot * 32

        Layout (0-based byte indices):
          0-1  Spawn X (2)
          2-3  Spawn Y (2)
          4    Spawn Direction
          5    Pathing
          6    Gate Behavior (Respawn/Retreat)
          7    Unused1
          8-9  Life (2)
          10   Leader Unit
          11   Guard Units
          12   Attack
          13   Defense
          14   Amount of Guards
          15   Slot that unit belongs to
          16   Unit Type
          17   AI Type
          18   Orders
          19   Hidden flag
          20   Unused2
          21   Order Target Slot
          22   Item Dropped
          23   AI Level
          24-25 Delay Order (2)
          26-27 Points For K.O. (2)
          28-31 Unused3 (4)
        """
        if selected_slot < 0 or selected_slot >= 512:
            self.status_label.config(text="Invalid slot index.", fg="red")
            return

        stage_file = self.stage_files[selected_file]
        getoffset = selected_slot * 32
        stage_file.seek(getoffset)

        x = int.from_bytes(stage_file.read(2), "little")
        y = int.from_bytes(stage_file.read(2), "little")
        direction = int.from_bytes(stage_file.read(1), "little")
        pathing = int.from_bytes(stage_file.read(1), "little")
        gate_behavior = int.from_bytes(stage_file.read(1), "little")
        self.unused1 = stage_file.read(1)
        Life = int.from_bytes(stage_file.read(2), "little")
        LeaderUnit = int.from_bytes(stage_file.read(1), "little")
        GuardUnits = int.from_bytes(stage_file.read(1), "little")
        Attack = int.from_bytes(stage_file.read(1), "little")
        Defense = int.from_bytes(stage_file.read(1), "little")
        AmountGuards = int.from_bytes(stage_file.read(1), "little")
        UnitSlot = int.from_bytes(stage_file.read(1), "little")
        UnitType = int.from_bytes(stage_file.read(1), "little")
        AIType = int.from_bytes(stage_file.read(1), "little")
        UnitCommand = int.from_bytes(stage_file.read(1), "little")
        Hide = int.from_bytes(stage_file.read(1), "little")
        self.unused2 = stage_file.read(1)
        AdvancingTarget = int.from_bytes(stage_file.read(1), "little")
        ItemDrop = int.from_bytes(stage_file.read(1), "little")
        AILevel = int.from_bytes(stage_file.read(1), "little")
        DelayOrder = int.from_bytes(stage_file.read(2), "little")
        PointsKO = int.from_bytes(stage_file.read(2), "little")
        self.unused3 = stage_file.read(4)

        # push values into TK vars
        self.xcord.set(x)
        self.ycord.set(y)
        self.direct.set(direction)
        self.AreaP.set(pathing)
        self.PullingB.set(gate_behavior)
        self.Lif.set(Life)
        self.LeaderU.set(LeaderUnit)
        self.GuardU.set(GuardUnits)
        self.Att.set(Attack)
        self.Def.set(Defense)
        self.AmountG.set(AmountGuards)
        self.UnitS.set(UnitSlot)
        self.UnitG.set(UnitType)
        self.AIT.set(AIType)
        self.UnitC.set(UnitCommand)
        self.Hid.set(Hide)
        self.Advance.set(AdvancingTarget)
        self.ItemD.set(ItemDrop)
        self.AIL.set(AILevel)
        self.DelayO.set(DelayOrder)
        self.PointsK.set(PointsKO)

    def submit_stage_values(self):
        """
        Write current TK variables back into the in-memory 32 byte slot
        """
        try:
            stage_name = self.selected_file.get()
            stage_file = self.stage_files[stage_name]
            selected_slot = self.selected_slot.get()

            if selected_slot < 0 or selected_slot >= 512:
                raise ValueError("Slot index out of range (0–511).")

            record = [
                self.xcord.get().to_bytes(2, "little"),   # 0-1
                self.ycord.get().to_bytes(2, "little"),   # 2-3
                self.direct.get().to_bytes(1, "little"),  # 4
                self.AreaP.get().to_bytes(1, "little"),   # 5
                self.PullingB.get().to_bytes(1, "little"),# 6
                self.unused1,                             # 7
                self.Lif.get().to_bytes(2, "little"),     # 8-9
                self.LeaderU.get().to_bytes(1, "little"), # 10
                self.GuardU.get().to_bytes(1, "little"),  # 11
                self.Att.get().to_bytes(1, "little"),     # 12
                self.Def.get().to_bytes(1, "little"),     # 13
                self.AmountG.get().to_bytes(1, "little"), # 14
                self.UnitS.get().to_bytes(1, "little"),   # 15
                self.UnitG.get().to_bytes(1, "little"),   # 16 (Unit Type)
                self.AIT.get().to_bytes(1, "little"),     # 17
                self.UnitC.get().to_bytes(1, "little"),   # 18
                self.Hid.get().to_bytes(1, "little"),     # 19
                self.unused2,                             # 20
                self.Advance.get().to_bytes(1, "little"), # 21
                self.ItemD.get().to_bytes(1, "little"),   # 22
                self.AIL.get().to_bytes(1, "little"),     # 23
                self.DelayO.get().to_bytes(2, "little"),  # 24-25
                self.PointsK.get().to_bytes(2, "little"), # 26-27
                self.unused3                              # 28-31
            ]

            total_len = sum(len(b) for b in record)
            if total_len != 32:
                raise ValueError(f"Record size is {total_len}, expected 32 bytes.")

            getoffset = selected_slot * 32
            stage_file.seek(getoffset)
            for b in record:
                stage_file.write(b)

            self.status_label.config(text="Values submitted without issues.", fg="green")
        except Exception as e:
            self.status_label.config(text=f"Error with entries: {e}", fg="red")

    # Mod creation

    def create_stage_mod(self):
        """
        Dump the current stage's in-memory data to a .DW2 mod file
        """
        try:
            sep = "."
            stage_name = self.selected_file.get()
            file_index = self.filenames.index(stage_name)
            stage_file = self.stage_files[stage_name]

            base_name = self.modname.get().split(sep, 1)[0] or stage_name
            usermodname = base_name + stage_extension[file_index]

            data = stage_file.getvalue()
            with open(usermodname, "wb") as w1:
                w1.write(data)

            self.status_label.config(
                text=f"Mod file '{usermodname}' created successfully.", fg="green"
            )
        except Exception as e:
            self.status_label.config(
                text=f"Error creating mod file: {e}", fg="red"
            )
    # collect valid slots for coordinate guider
    def open_coord_guide(self):
        """
        Collect all used unit slots for the current stage,
        then open or refresh a single DW2CordGuide window and auto mark all coords
        Side 1 gets blue markers, Side 2 gets red markers
        """
        try:
            stage_name = self.selected_file.get()
            stage_file = self.stage_files[stage_name]

            coords_side1 = []  # slots 0–255
            coords_side2 = []  # slots 256–511

            # Each slot is 32 bytes, LeaderUnit is the 11th byte (offset 10)
            # Layout per 32-byte record:
            #  0-1: X (2 bytes)
            #  2-3: Y (2 bytes)
            #  4:   Direction
            #  5:   AreaPrior
            #  6:   PullingBack
            #  7:   Unused1
            #  8-9: Life
            # 10:  LeaderUnit
            #  rest is unused for this filter
            for slot in range(512):
                offset = slot * 32

                # Read X/Y
                stage_file.seek(offset)
                x = int.from_bytes(stage_file.read(2), "little")
                y = int.from_bytes(stage_file.read(2), "little")

                # Read LeaderUnit
                stage_file.seek(offset + 10)
                leader_byte = stage_file.read(1)
                if not leader_byte:
                    continue
                leader = leader_byte[0]

                # Only consider slots where LeaderUnit != 255
                if leader != 255:
                    if slot < 256:
                        coords_side1.append((x, y))
                    else:
                        coords_side2.append((x, y))

            total = len(coords_side1) + len(coords_side2)
            if total == 0:
                self.status_label.config(
                    text="No valid units found (Leader != 255) for this stage.",
                    fg="red",
                )
                return

            # If a guide window already exists, reuse it
            if (
                self.coord_guide_window is not None
                and self.coord_guide_window.winfo_exists()
                and self.coord_guide_app is not None
            ):
                guide_app = self.coord_guide_app
                # set map for this stage
                guide_app.set_map_by_stage(stage_name)
                # clear old markers, then mark new coords
                guide_app.clear_markers()
                if coords_side1:
                    guide_app.auto_mark_coords(coords_side1, color="blue")  # Side 1
                if coords_side2:
                    guide_app.auto_mark_coords(coords_side2, color="red")   # Side 2
                # bring to front
                self.coord_guide_window.lift()
                self.coord_guide_window.focus_force()
            else:
                # Create coordinate guide window
                guide_win = tk.Toplevel(self.root)
                guide_win.title("DW2 Coordinate Guide")

                guide_app = ImageMarkerApp(guide_win)

                # Keep references so they aren't garbage collected
                self.coord_guide_window = guide_win
                self.coord_guide_app = guide_app

                # When closed, clear our references
                def on_close():
                    self.coord_guide_window = None
                    self.coord_guide_app = None
                    guide_win.destroy()

                guide_win.protocol("WM_DELETE_WINDOW", on_close)

                # Select matching map for this stage
                guide_app.set_map_by_stage(stage_name)

                # Auto mark all coordinates
                if coords_side1:
                    guide_app.auto_mark_coords(coords_side1, color="blue")  # Side 1
                if coords_side2:
                    guide_app.auto_mark_coords(coords_side2, color="red")   # Side 2

        except Exception as e:
            self.status_label.config(
                text=f"Coord guide error: {e}",
                fg="red",
            )
