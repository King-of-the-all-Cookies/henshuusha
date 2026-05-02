"""Script converter using AJTTools for GS4 and GS56 script formats."""
from pathlib import Path
from req.AJTTools.plugins.script.src import AA4Script, AA56Script

DESCRIPTION = """Encode and decode GS456 (AJ:AA Trilogy) script files using AJTTools."""



def encode_script(input_file: str, output_file: str) -> None:
    """
    Encode script from text format to binary user2 format.
    
    Supports both GS4 (Apollo Justice) and GS56 (Trials and Tribulations, Dual Destinies) formats.
    Auto-detects format based on input file structure.
    
    Args:
        input_file: Path to .txt script file (text format)
        output_file: Path where to save the binary .user2 file
    
    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If input format is not supported
    """
    input_path = Path(input_file)
    output_path = Path(output_file)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    if not input_path.name.endswith('.txt'):
        raise ValueError("Input file must be a .txt file")
    
    # Auto-detect whether it's GS4 or GS56 format by trying to parse
    # GS56 has more complex structure with labels, GS4 is simpler
    try:
        # Try as GS56 first (more specific format)
        script = AA56Script(input_path)
        script.write_user2(output_path)
    except Exception:
        # Fall back to GS4
        try:
            script = AA4Script(input_path)
            script.write_user2(output_path)
        except Exception as e:
            raise ValueError(f"Failed to parse script file. Ensure format is valid GS4 or GS56: {e}") from e


def decode_script(input_file: str, output_file: str) -> None:
    """
    Decode script from binary user2 format to text format.
    
    Supports both GS4 (Apollo Justice) and GS56 (Trials and Tribulations, Dual Destinies) formats.
    Auto-detects format based on binary structure.
    
    Args:
        input_file: Path to binary .user2 script file
        output_file: Path where to save the .txt text file
    
    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If input format is not supported or file is corrupted
    """
    input_path = Path(input_file)
    output_path = Path(output_file)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    # Auto-detect format by trying to parse as each type
    try:
        # Try GS56 first
        script = AA56Script(input_path)
        script.write_txt(output_path)
    except Exception:
        # Fall back to GS4
        try:
            script = AA4Script(input_path)
            script.write_txt(output_path)
        except Exception as e:
            raise ValueError(f"Failed to parse binary script. Ensure it's a valid GS4 or GS56 file: {e}") from e
