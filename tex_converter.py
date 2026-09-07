"""Texture conversion helpers (PC <-> Nintendo Switch)."""
from pathlib import Path

from req.AJTTools.plugins.tex.src.Tex import Tex


class TexConverter:
    @staticmethod
    def PCtex_to_NSWtex(pc_tex_path: Path, switch_tex_path: Path, output_switch_tex_path: Path) -> None:
        """Convert a PC texture to Nintendo Switch format via a temporary DDS file."""
        pc_tex = Tex(pc_tex_path)
        temp_dds = pc_tex_path.with_suffix('.temp_export.dds')
        try:
            pc_tex.export_file(str(temp_dds))
            switch_tex = Tex(switch_tex_path)
            switch_tex.import_file(str(temp_dds))
            switch_tex.save(output_switch_tex_path)
        finally:
            if temp_dds.exists():
                temp_dds.unlink()

    @staticmethod
    def NSWtex_to_PCtex(switch_tex_path: Path, pc_tex_path: Path, output_pc_tex_path: Path) -> None:
        """Convert a Nintendo Switch texture to PC format via a temporary DDS file."""
        switch_tex = Tex(switch_tex_path)
        temp_dds = switch_tex_path.with_suffix('.temp_export.dds')
        try:
            switch_tex.export_file(str(temp_dds))
            pc_tex = Tex(pc_tex_path)
            pc_tex.import_file(str(temp_dds))
            pc_tex.save(output_pc_tex_path)
        finally:
            if temp_dds.exists():
                temp_dds.unlink()