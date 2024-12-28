from ....io import LittleEndianBinaryFileReader, LittleEndianBinaryFileWriter
from ....utils import try_create_dir

from pathlib import Path
import zlib
import zstd
import os
import logging
import inspect

class PakEntry:
    def __init__(self, f: LittleEndianBinaryFileReader):
        logging.info(f"Executing: {inspect.currentframe().f_lineno}")
        if f is not None:
            self.lowercase_path_hash = f.readuint32()
            self.uppercase_path_hash = f.readuint32()
            self.offset = f.readint64()
            self.compressed_size = f.readint64()
            self.decompressed_size = f.readint64()
            self.compression_flag = f.readint64()
            self.checksum = f.readint64()

    def export(self, f: LittleEndianBinaryFileReader, root_output_dir: str, hashmap: dict):
        logging.info(f"Executing: {inspect.currentframe().f_lineno}")
        logging.info(f"Exporting PakEntry")
        if self.lowercase_path_hash in hashmap:
            output_path = hashmap[self.lowercase_path_hash]
        else:
            output_path = os.path.join('unknown', f'{self.lowercase_path_hash}-{self.uppercase_path_hash}.bin')

        f.seek(self.offset)
        compressed_data = f.read(self.compressed_size)
        if self.compression_flag & 1:  # deflate
            data = zlib.decompress(compressed_data, -15)
            compression = 'deflate'
        elif self.compression_flag & 2:
            data = zstd.decompress(compressed_data)
            compression = 'zstd'
        else:
            data = compressed_data
            compression = 'none'

        assert len(data) == self.decompressed_size, "Decompression error: decompressed data size doesn't match the expected value"
        logging.info(f"Unpacking {str(output_path)}... (compression:{compression})")
        filepath = os.path.join(root_output_dir, output_path)
        try_create_dir(filepath)
        with open(filepath, mode='wb') as file:
            file.write(data)

    def write(self, f: LittleEndianBinaryFileWriter):
        logging.info(f"Executing: {inspect.currentframe().f_lineno}")
        f.writeuint32(self.lowercase_path_hash)
        f.writeuint32(self.uppercase_path_hash)
        f.writeint64(self.offset)
        f.writeint64(self.compressed_size)
        f.writeint64(self.decompressed_size)
        f.writeint64(self.compression_flag)
        f.writeint64(self.checksum)
