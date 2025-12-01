import os
import tkinter as tk
from tkinter import ttk, filedialog

from .Utility import DW2_BIN, BACKUP_DIR, ICON_DIR, stage_data, unit_data, setup_lilac_styles, LILAC  # core offsets/paths :contentReference[oaicite:3]{index=3}
from .Stage_Editor import filenames as STAGE_NAMES, stage_extension as STAGE_EXTS  # stage ids + mod extensions :contentReference[oaicite:4]{index=4}

class DW2ModManager:
    """
    DW2 Mod Manager

    It uses DW2_BIN from Utility
    Stage mods:
          Enable: pick .DW2YTR/.DW2HLG/etc file, write 512 slots
          in 8 chunks across stage_data offsets (64 slots per offset)
          
          Disable: pick corresponding Original.stage backup from BACKUP_DIR
          and restore data the same way (sector by sector)
    Unit mods:
         Enable: pick .DW2UnitMod file, write 53 + 201 units (7 bytes each)
          to unit_data[0] / unit_data[1]
         Disable: restore from BACKUP_DIR/DW2_Original.unitdata.
    """

    def __init__(self, root):
        self.root = root
        self.root.title("DW2 Mod Manager")
        
        self.root.iconbitmap(os.path.join(ICON_DIR, "icon3.ico"))

        self.root.minsize(600, 300)
        self.root.resizable(False, False)

        setup_lilac_styles()

        self._build_gui()

    # GUI

    def _build_gui(self):
        """Handles GUI design"""
        self.bg = ttk.Frame(self.root, style="Lilac.TFrame")
        self.bg.place(x=0, y=0, relwidth=1, relheight=1)

        ttk.Label(
            self.bg,
            text=f"DW2 BIN: {os.path.basename(DW2_BIN)}",
            style="Lilac.TLabel",
        ).place(x=20, y=20)

        ttk.Label(
            self.bg,
            text=f"Backups dir: {BACKUP_DIR}",
            style="Lilac.TLabel",
        ).place(x=20, y=45)

        # Stage Mods section
        ttk.Label(
            self.bg,
            text="Stage Mods",
            style="Lilac.TLabel",
            font=("TkDefaultFont", 10, "bold"),
        ).place(x=20, y=90)

        ttk.Button(
            self.bg,
            text="Enable Stage Mod (from file)",
            command=self.enable_stage_mod,
            width=30,
        ).place(x=40, y=120)

        ttk.Button(
            self.bg,
            text="Disable Stage Mod",
            command=self.disable_stage_mod,
            width=30,
        ).place(x=40, y=160)

        # Unit Mods section
        ttk.Label(
            self.bg,
            text="Unit Mods",
            style="Lilac.TLabel",
            font=("TkDefaultFont", 10, "bold"),
        ).place(x=320, y=90)

        ttk.Button(
            self.bg,
            text="Enable Unit Mod (from file)",
            command=self.enable_unit_mod,
            width=30,
        ).place(x=340, y=120)

        ttk.Button(
            self.bg,
            text="Disable Unit Mods",
            command=self.disable_unit_mods,
            width=30,
        ).place(x=340, y=160)

        # Status line
        self.status_label = ttk.Label(self.bg, text="", style="Lilac.TLabel")
        self.status_label.place(x=20, y=230)

    # Helper functions

    def _set_status(self, msg: str, ok: bool = True):
        self.status_label.config(
            text=msg,
            foreground="green" if ok else "red",
        )

    # Stage Mods 

    def _detect_stage_index_from_mod(self, path: str) -> int | None:
        """
        Given a stage mod filename, use extension to find which stage this is for
        """
        lower = path.lower()
        for i, ext in enumerate(STAGE_EXTS):
            if lower.endswith(ext.lower()):
                return i
        return None

    def _detect_stage_index_from_backup(self, path: str) -> int | None:
        """
        Given a backup filename like YTR_Stage_Original.stage,
        recover the stage index by matching against STAGE_NAMES
        """
        fname = os.path.basename(path)
        base, _ext = os.path.splitext(fname)

        if base.endswith("_Original"):
            stage_name = base[: -len("_Original")]
        else:
            # fallback, try base directly
            stage_name = base

        try:
            return STAGE_NAMES.index(stage_name)
        except ValueError:
            return None

    def enable_stage_mod(self):
        """
        Enable a stage mod from a .DW2YTR/.DW2HLG/ etc file
        Writes 512 slots (32 bytes each) in 8 sector chunks based on stage_data.
        """
        filetypes = [
            (
                "DW2 Stage Mods",
                " ".join(f"*{ext}" for ext in STAGE_EXTS)
            )
        ]

        mod_path = filedialog.askopenfilename(
            parent=self.root,
            initialdir=os.getcwd(),
            title="Select stage mod file",
            filetypes=filetypes,
        )
        if not mod_path:
            return

        stage_index = self._detect_stage_index_from_mod(mod_path)
        if stage_index is None:
            self._set_status("Could not detect which stage this mod is for.", ok=False)
            return

        offsets = stage_data[stage_index]  # 8 offsets per stage
        if len(offsets) != 8:
            self._set_status(
                f"Stage data for index {stage_index} does not have 8 offsets.",
                ok=False,
            )
            return

        try:
            with open(DW2_BIN, "r+b") as f_dw2, open(mod_path, "rb") as f_mod:
                # For each sector offset, write 64 * 32 byte slots
                for base_off in offsets:
                    f_dw2.seek(base_off)
                    for _ in range(64):
                        data = f_mod.read(32)
                        if len(data) != 32:
                            raise ValueError(
                                f"Stage mod file is too short for all 512 slots "
                                f"(stopped at offset 0x{base_off:X})."
                            )
                        f_dw2.write(data)

            self._set_status(
                f"Stage mod '{os.path.basename(mod_path)}' "
                f"applied to {STAGE_NAMES[stage_index]}.",
                ok=True,
            )

        except Exception as e:
            self._set_status(f"Error enabling stage mod: {e}", ok=False)

    def disable_stage_mod(self):
        """
        Disable a stage mod by restoring from an Original.stage backup file
        The backup contains 512 slots (32 bytes each) plus trailing offsets,
        we only read the slot data and write it back across the 8 sector offsets
        """
        filetypes = [
            ("Stage backups (*.stage)", "*.stage")
        ]

        backup_path = filedialog.askopenfilename(
            parent=self.root,
            initialdir=BACKUP_DIR,
            title="Select stage backup file",
            filetypes=filetypes,
        )
        if not backup_path:
            return

        stage_index = self._detect_stage_index_from_backup(backup_path)
        if stage_index is None:
            self._set_status(
                "Could not determine which stage this backup belongs to.",
                ok=False,
            )
            return

        offsets = stage_data[stage_index]
        if len(offsets) != 8:
            self._set_status(
                f"Stage data for index {stage_index} does not have 8 offsets.",
                ok=False,
            )
            return

        try:
            with open(DW2_BIN, "r+b") as f_dw2, open(backup_path, "rb") as f_backup:
                # same pattern as enabling: 8 sectors * 64 slots * 32 bytes
                for base_off in offsets:
                    f_dw2.seek(base_off)
                    for _ in range(64):
                        data = f_backup.read(32)
                        if len(data) != 32:
                            raise ValueError(
                                "Stage backup file is too short; "
                                "expected full 512-slot data."
                            )
                        f_dw2.write(data)

            self._set_status(
                f"Stage restored from '{os.path.basename(backup_path)}' "
                f"({STAGE_NAMES[stage_index]}).",
                ok=True,
            )

        except Exception as e:
            self._set_status(f"Error disabling stage mod: {e}", ok=False)

    # Unit Mods

    def enable_unit_mod(self):
        """
        Enable a unit mod from a .DW2UnitMod file
        Reads 53 + 201 unit entries (7 bytes each) and writes them into DW2.bin
        at unit_data[0] and unit_data[1], Any trailing data in the mod file
        like appended offsets is ignored
        """
        filetypes = [
            ("DW2 Unit Mods (*.DW2UnitMod)", "*.DW2UnitMod")
        ]

        mod_path = filedialog.askopenfilename(
            parent=self.root,
            initialdir=os.getcwd(),
            title="Select unit mod file",
            filetypes=filetypes,
        )
        if not mod_path:
            return

        NUM_SLOTS_FIRST = 53
        NUM_SLOTS_SECOND = 201
        SLOT_SIZE = 7

        try:
            with open(DW2_BIN, "r+b") as f_dw2, open(mod_path, "rb") as f_mod:
                # First block, 53 entries at unit_data[0]
                f_dw2.seek(unit_data[0])
                for _ in range(NUM_SLOTS_FIRST):
                    chunk = f_mod.read(SLOT_SIZE)
                    if len(chunk) != SLOT_SIZE:
                        raise ValueError(
                            "Unit mod file ended before all 53 entries were read."
                        )
                    f_dw2.write(chunk)

                # Second block, 201 entries at unit_data[1]
                f_dw2.seek(unit_data[1])
                for _ in range(NUM_SLOTS_SECOND):
                    chunk = f_mod.read(SLOT_SIZE)
                    if len(chunk) != SLOT_SIZE:
                        raise ValueError(
                            "Unit mod file ended before all 201 entries were read."
                        )
                    f_dw2.write(chunk)

            self._set_status(
                f"Unit mod '{os.path.basename(mod_path)}' enabled successfully.",
                ok=True,
            )

        except Exception as e:
            self._set_status(f"Error enabling unit mod: {e}", ok=False)

    def disable_unit_mods(self):
        """
        Restore original unit data from the backup created by UnitEditor
        
        Backups_For_Mod_Disabling/DW2_Original.unitdata

        Layout of backup:
          53 * 7 bytes + 201 * 7 bytes + each unit_data offset as 4 bytes
        We only read the 53 + 201 entries and write them to DW2.bin
        """
        backup_name = "DW2_Original.unitdata"
        backup_path = os.path.join(BACKUP_DIR, backup_name)

        if not os.path.exists(backup_path):
            self._set_status(
                f"Unit backup not found: {backup_path}\n"
                "Open Unit Editor once to generate it.",
                ok=False,
            )
            return

        NUM_SLOTS_FIRST = 53
        NUM_SLOTS_SECOND = 201
        SLOT_SIZE = 7

        try:
            with open(DW2_BIN, "r+b") as f_dw2, open(backup_path, "rb") as f_backup:
                # First 53 entries
                f_dw2.seek(unit_data[0])
                for _ in range(NUM_SLOTS_FIRST):
                    chunk = f_backup.read(SLOT_SIZE)
                    if len(chunk) != SLOT_SIZE:
                        raise ValueError(
                            "Unit backup file ended before all 53 entries were read."
                        )
                    f_dw2.write(chunk)

                # Next 201 entries
                f_dw2.seek(unit_data[1])
                for _ in range(NUM_SLOTS_SECOND):
                    chunk = f_backup.read(SLOT_SIZE)
                    if len(chunk) != SLOT_SIZE:
                        raise ValueError(
                            "Unit backup file ended before all 201 entries were read."
                        )
                    f_dw2.write(chunk)

            self._set_status(
                f"Unit data restored from '{backup_name}'.", ok=True
            )

        except Exception as e:
            self._set_status(f"Error disabling unit mods: {e}", ok=False)
