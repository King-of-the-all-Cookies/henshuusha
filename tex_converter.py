"""Texture conversion helpers (PC <-> Nintendo Switch)."""
from pathlib import Path

from req.AJTTools.plugins.tex.src.Tex import Tex

# Language suffixes found on Ace Attorney texture files
# (e.g. foo.tex.719230324.en). Mirrors lang_exts from req/AJTTools/utils/utils.py.
TEX_LANG_EXTS = {
    'ja', 'en', 'de', 'fr', 'ko', 'it', 'es', 'zhcn', 'zhtw', 'ru', 'pl', 'nl',
    'pt', 'ptbr', 'fi', 'sv', 'da', 'no', 'cs', 'hu', 'sk', 'ar', 'tr', 'bg',
    'el', 'ro', 'th', 'ua', 'vi', 'id', 'cc', 'hi', 'es419'
}


def is_tex_file(path: Path) -> bool:
    """True if the path points to a texture file (any language variant)."""
    return path.is_file() and (".tex." in path.name or path.name.endswith(".tex"))


def get_tex_base_name(filename: str) -> str:
    """Strip the language suffix from a texture name:
    'foo.tex.719230324.en' -> 'foo.tex.719230324'
    'foo.tex.719230324'    -> 'foo.tex.719230324' (unchanged)
    """
    if "." in filename:
        stem, last = filename.rsplit(".", 1)
        if last in TEX_LANG_EXTS:
            return stem
    return filename


def index_tex_files(files):
    """Index textures for lookup by exact name and by base name.
    Returns (by_name, by_base). A base texture (no language suffix) is
    preferred as the template when available.
    """
    by_name = {}
    by_base = {}
    for f in files:
        by_name[f.name] = f
        base = get_tex_base_name(f.name)
        if base not in by_base:
            by_base[base] = f
        elif f.name == base:
            by_base[base] = f
    return by_name, by_base


def find_tex_template(src_file: Path, by_name: dict, by_base: dict):
    """Find the template texture for conversion: first by exact name, then by
    base name (without the language suffix) so conversion works for any language.
    """
    return by_name.get(src_file.name) or by_base.get(get_tex_base_name(src_file.name))


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