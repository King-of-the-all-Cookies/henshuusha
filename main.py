"""Henshuusha — GUI application for working with Ace Attorney (Gyakuten Saiban) game files.

Features:
  - GS56/GS4 script conversion via AJTTools (txt <-> user2) and AJT56script (json/bin)
  - TEX <-> image (PNG/DDS) conversion
  - Font (oft.1 <-> otf) and PAK packing/unpacking
"""
import ctypes
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QAction, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QMenu, QFileDialog, QDialog, QMessageBox,
    QTextEdit, QHBoxLayout, QWidget, QListWidget, QStackedWidget, QPushButton, QLabel,
)

from dialogs import (
    PlatformDialog, GameSelectionDialog, FormatSelectDialog,
    SingleTexConvertDialog, MultipleTexConvertDialog,
)
from workers import WorkerThread, notify

BASE_DIR = Path(__file__).parent


def setup_logging():
    log_directory = Path("logs")
    log_directory.mkdir(exist_ok=True)
    log_filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_directory / log_filename),
            logging.StreamHandler(),
        ],
    )


# ---------------------------------------------------------------------------
# Background worker functions (run off the UI thread)
# ---------------------------------------------------------------------------

def _decode_gs56_json(file_names):
    """Decode GS56 scripts to .json using the AJT56script wrapper."""
    from req.AJT56script import decode_script
    results = []
    for file_name in file_names:
        output_file = Path(file_name).with_suffix('.json')
        decode_script(file_name, output_file)
        results.append(output_file.read_text(encoding='utf-8'))
    return results


def _encode_gs56_json(file_names):
    """Encode GS56 scripts from .json back to binary using the AJT56script wrapper."""
    from req.AJT56script import encode_script
    results = []
    for file_name in file_names:
        output_file = Path(file_name).with_suffix('.bin')
        encode_script(file_name, output_file)
        results.append(output_file.read_bytes().decode('utf-8', errors='ignore'))
    return results


def _decode_gs56_ajt(file_names):
    """Decode GS56 scripts to .txt using AJTTools (AA56Script)."""
    from req.AJTTools.plugins.script import AA56Script
    results = []
    for file_name in file_names:
        file_path = Path(file_name)
        output_file = file_path.with_suffix('.txt')
        script = AA56Script(file_path)
        script.write_txt(output_file)
        results.append(output_file.read_text(encoding='utf-8'))
    return results


def _encode_gs56_ajt(file_names):
    """Encode GS56 scripts from .txt back to .user2 using AJTTools (AA56Script)."""
    from req.AJTTools.plugins.script import AA56Script
    results = []
    for file_name in file_names:
        file_path = Path(file_name)
        output_file = file_path.with_suffix('.user.2')
        script = AA56Script(file_path)
        script.write_user2(output_file)
        results.append(output_file.read_bytes().decode('utf-8', errors='ignore'))
    return results


def _decode_gs4_ajt(file_names):
    """Decode GS4 scripts to .txt using AJTTools (AA4Script)."""
    from req.AJTTools.plugins.script import AA4Script
    results = []
    for file_name in file_names:
        file_path = Path(file_name)
        output_file = file_path.with_suffix('.txt')
        script = AA4Script(file_path)
        script.write_txt(output_file)
        results.append(output_file.read_text(encoding='utf-8'))
    return results


def _encode_gs4_ajt(file_names):
    """Encode GS4 scripts from .txt back to .user2 using AJTTools (AA4Script)."""
    from req.AJTTools.plugins.script import AA4Script
    results = []
    for file_name in file_names:
        file_path = Path(file_name)
        output_file = file_path.with_suffix('.user.2')
        script = AA4Script(file_path)
        script.write_user2(output_file)
        results.append(output_file.read_bytes().decode('utf-8', errors='ignore'))
    return results


def _convert_tex_to_image(file_names, output_format, output_dir):
    from req.AJTTools.plugins.tex import Tex
    results = []
    for file_name in file_names:
        tex = Tex(file_name)
        # Keep the full texture name (including the language suffix) so files of
        # different languages don't overwrite each other:
        # foo.tex.719230324.en -> foo.tex.719230324.en.png
        base_name = os.path.basename(file_name)
        output_file = os.path.join(output_dir, f"{base_name}.{output_format}")
        tex.export_file(output_file)
        results.append(output_file)
    return results


def _convert_image_to_tex(file_names, output_dir):
    from req.AJTTools.plugins.tex import Tex
    results = []
    for file_name in file_names:
        base = os.path.basename(file_name).replace('.png', '.tex.35').replace('.dds', '.tex.35')
        output_file = os.path.join(output_dir, base)
        tex = Tex(output_file)
        tex.import_file(file_name)
        tex.save(output_file)
        results.append(output_file)
    return results


def _convert_fonts_to_otf(file_names, output):
    from req.AJTTools.plugins.font import REFont
    if isinstance(output, str):
        REFont(file_names[0]).export_file(output)
    else:
        for file_name in file_names:
            base = os.path.basename(file_name).replace('.oft.', '.otf')
            REFont(file_name).export_file(os.path.join(output, base))


def _convert_fonts_to_oft(file_names, output):
    from req.AJTTools.plugins.font import REFont
    if isinstance(output, str):
        font = REFont(output)
        font.import_file(file_names[0])
        font.save(output)
    else:
        for file_name in file_names:
            base = os.path.basename(file_name).replace('.otf', '.oft.1')
            output_file = os.path.join(output, base)
            font = REFont(output_file)
            font.import_file(file_name)
            font.save(output_file)


def _build_pak(dir_path, pak_path):
    from req.AJTTools.plugins.pak.src.Pak import build_pak_from_dir
    build_pak_from_dir(dir_path, pak_path)


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker_thread = None
        self._setup_window()
        self._setup_central_widget()
        self._build_menus()
        self._load_dlls()

    # -- UI setup ----------------------------------------------------------

    def _setup_window(self):
        self.setWindowTitle("Henshuusha")
        self.setGeometry(100, 100, 800, 600)
        self.setWindowIcon(QIcon('icon.png'))

    def _setup_central_widget(self):
        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)

        self.copy_path_button = QPushButton("Copy Path", self)
        self.copy_path_button.clicked.connect(self.copy_path)

        self.close_button = QPushButton("Close", self)
        self.close_button.clicked.connect(self.close_text_edit)

        self.file_list_widget = QListWidget(self)
        self.file_list_widget.itemClicked.connect(self.display_file_content)

        self.stacked_widget = QStackedWidget(self)
        self.stacked_widget.addWidget(self.text_edit)

        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stacked_widget.addWidget(self.image_label)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.copy_path_button)
        button_layout.addWidget(self.close_button)

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.file_list_widget, stretch=1)
        main_layout.addWidget(self.stacked_widget, stretch=3)

        button_container = QWidget()
        button_container.setLayout(button_layout)
        main_layout.addWidget(button_container)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self._hide_viewer()

    def _build_menus(self):
        file_menu = self.menuBar().addMenu('File')
        file_menu.addMenu(self._build_open_menu())
        file_menu.addMenu(self._build_save_menu())
        file_menu.addMenu(self._build_convert_menu())

    def _build_open_menu(self):
        open_menu = QMenu('Open', self)

        ds_menu = open_menu.addMenu('DS')
        gs1234_menu = ds_menu.addMenu('GS1234')
        gs1234_menu.addAction(self._make_action('mes_all.bin', self._extract_mes_all_bin))
        gs1234_menu.addAction(self._make_action('Script Converter', self._convert_text_messages))

        ajt_menu = open_menu.addMenu('AJT')
        font_menu = ajt_menu.addMenu('Font')
        font_menu.addAction(self._make_action('oft.1 -> otf', self.convert_oft_to_otf))

        pak_menu = ajt_menu.addMenu('PAK')
        pak_menu.addAction(self._make_action('Unpack', self.unpack_pak))

        tex_menu = ajt_menu.addMenu('TEX')
        tex_menu.addAction(self._make_action('Convert to DDS/PNG', self.convert_tex_to_image))

        script_menu = ajt_menu.addMenu('Script')
        script_menu.addAction(self._make_action('GS56 Decode (AJTTools, txt)', self.decode_gs56_ajt))
        script_menu.addAction(self._make_action('GS56 Decode (JSON)', self.decode_gs56_json))
        script_menu.addAction(self._make_action('GS4 Decode (txt)', self.decode_gs4))

        return open_menu

    def _build_save_menu(self):
        save_menu = QMenu('Save', self)
        save_ajt_menu = save_menu.addMenu('AJT')

        save_pak_menu = save_ajt_menu.addMenu('PAK')
        save_pak_menu.addAction(self._make_action('Create PAK', self.create_pak))

        save_tex_menu = save_ajt_menu.addMenu('TEX')
        save_tex_menu.addAction(self._make_action('Convert to TEX', self.convert_image_to_tex))

        save_font_menu = save_ajt_menu.addMenu('Font')
        save_font_menu.addAction(self._make_action('otf -> oft.1', self.convert_otf_to_oft))

        save_script_menu = save_ajt_menu.addMenu('Script')
        save_script_menu.addAction(self._make_action('GS56 Encode (AJTTools, txt)', self.encode_gs56_ajt))
        save_script_menu.addAction(self._make_action('GS56 Encode (JSON)', self.encode_gs56_json))
        save_script_menu.addAction(self._make_action('GS4 Encode (txt)', self.encode_gs4))

        return save_menu

    def _build_convert_menu(self):
        convert_menu = QMenu('Convert', self)
        convert_menu.addAction(self._make_action('Convert PC <-> NSW textures', self.convert_single_tex))
        convert_menu.addAction(self._make_action('Convert PC <-> NSW textures (multiple)', self.convert_multiple_tex))
        return convert_menu

    def _make_action(self, text, slot):
        action = QAction(text, self)
        action.triggered.connect(slot)
        return action

    def _load_dlls(self):
        self.extract_mes_dll = _load_dll('extract_mes_all_bin.dll')
        self.convert_text_dll = _load_dll('convert_text_messages.dll')

    # -- Generic helpers ---------------------------------------------------

    def _select_files(self, caption, file_filter):
        options = QFileDialog.Option.ReadOnly
        file_names, _ = QFileDialog.getOpenFileNames(self, caption, "", file_filter, options=options)
        return file_names

    def _start_worker(self, function, *args, on_result=None, on_done=None):
        """Run `function(*args)` in the background; notifications are fire-and-forget."""
        self.worker_thread = WorkerThread(function, *args)
        if on_result is not None:
            self.worker_thread.signals.result.connect(on_result)
        if on_done is not None:
            self.worker_thread.signals.finished.connect(lambda: notify(*on_done))
        self.worker_thread.signals.error.connect(self._handle_worker_error)
        self.worker_thread.start()

    def _handle_worker_error(self, error):
        e, traceback_str = error
        logging.error(f"Background task failed: {e}\n{traceback_str}")
        QMessageBox.critical(self, "Error", f"An error occurred: {e}")

    def _show_results(self, results):
        if results:
            self.text_edit.setPlainText("\n".join(results))
            self._show_viewer()

    def _show_viewer(self):
        self.text_edit.setVisible(True)
        self.copy_path_button.setVisible(True)
        self.close_button.setVisible(True)

    def _hide_viewer(self):
        self.text_edit.setVisible(False)
        self.copy_path_button.setVisible(False)
        self.close_button.setVisible(False)
        self.file_list_widget.setVisible(False)

    # -- Viewers -----------------------------------------------------------

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.scale_image_to_label()

    def scale_image_to_label(self):
        if self.image_label.pixmap():
            scaled_pixmap = self.image_label.pixmap().scaled(
                self.image_label.size() * 0.9,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.image_label.setPixmap(scaled_pixmap)

    def display_single_file(self, file_path):
        self._show_viewer()
        if file_path.endswith(('.png', '.dds')):
            self.image_label.setPixmap(QPixmap(file_path))
            self.scale_image_to_label()
            self.stacked_widget.setCurrentWidget(self.image_label)
        else:
            self.text_edit.setPlainText(Path(file_path).read_text(encoding='utf-8'))
            self.stacked_widget.setCurrentWidget(self.text_edit)

    def display_multiple_files(self, file_paths):
        self.file_list_widget.clear()
        self.file_list_widget.addItems(file_paths)
        self.file_list_widget.setVisible(True)
        self.file_list_widget.setCurrentRow(0)

    def display_file_content(self, item):
        file_path = item.text()
        if file_path.endswith('.png'):
            self.image_label.setPixmap(QPixmap(file_path))
            self.scale_image_to_label()
            self.stacked_widget.setCurrentWidget(self.image_label)
        else:
            self.text_edit.setPlainText(Path(file_path).read_text(encoding='utf-8'))
            self.stacked_widget.setCurrentWidget(self.text_edit)

    def copy_path(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.text_edit.toPlainText().split('\n')[0])
        notify("Copied", "Path copied to clipboard!")

    def close_text_edit(self):
        self._hide_viewer()
        self.stacked_widget.setCurrentIndex(0)

    # -- Script conversion (AJTTools: txt <-> user2) -----------------------

    def decode_gs56_ajt(self):
        file_names = self._select_files("Open File", "Script Files (*.user.2.*)")
        if not file_names:
            return
        logging.info(f"GS56 decode (AJTTools): {file_names}")
        self._start_worker(
            _decode_gs56_ajt, file_names,
            on_result=self._show_results,
            on_done=("Decoding Finished", "GS56 scripts have been decoded to txt via AJTTools."),
        )

    def encode_gs56_ajt(self):
        file_names = self._select_files("Open File", "Script Files (*.txt)")
        if not file_names:
            return
        logging.info(f"GS56 encode (AJTTools): {file_names}")
        self._start_worker(
            _encode_gs56_ajt, file_names,
            on_result=self._show_results,
            on_done=("Encoding Finished", "GS56 scripts have been encoded to user2 via AJTTools."),
        )

    # -- Script conversion (AJT56script: json <-> bin) ---------------------

    def decode_gs56_json(self):
        file_names = self._select_files("Open File", "Script Files (*.user.2.*)")
        if not file_names:
            return
        logging.info(f"GS56 decode (JSON): {file_names}")
        self._start_worker(
            _decode_gs56_json, file_names,
            on_result=self._show_results,
            on_done=("Decoding Finished", "The decoding process has been completed successfully."),
        )

    def encode_gs56_json(self):
        file_names = self._select_files("Open File", "Script Files (*.json *.bin)")
        if not file_names:
            return
        logging.info(f"GS56 encode (JSON): {file_names}")
        self._start_worker(
            _encode_gs56_json, file_names,
            on_result=self._show_results,
            on_done=("Encoding Finished", "The encoding process has been completed successfully."),
        )

    # -- Script conversion (GS4) -------------------------------------------

    def decode_gs4(self):
        file_names = self._select_files("Open File", "Script Files (*.user.2.*)")
        if not file_names:
            return
        logging.info(f"GS4 decode (AJTTools): {file_names}")
        self._start_worker(
            _decode_gs4_ajt, file_names,
            on_result=self._show_results,
            on_done=("Decoding Finished", "GS4 scripts have been decoded to txt via AJTTools."),
        )

    def encode_gs4(self):
        file_names = self._select_files("Open File", "Script Files (*.txt)")
        if not file_names:
            return
        logging.info(f"GS4 encode (AJTTools): {file_names}")
        self._start_worker(
            _encode_gs4_ajt, file_names,
            on_result=self._show_results,
            on_done=("Encoding Finished", "GS4 scripts have been encoded to user2 via AJTTools."),
        )

    # -- DS tools (DLL helpers) --------------------------------------------

    def _extract_mes_all_bin(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "BIN Files (*.bin)", options=QFileDialog.Option.ReadOnly)
        if not file_name:
            return
        logging.info(f"Extracting mes_all.bin: {file_name}")

        file_dir = os.path.dirname(file_name)
        argc = 3
        argv = (ctypes.c_char_p * argc)()
        argv[0] = b"extract_mes_all_bin"
        argv[1] = file_name.encode('utf-8')
        argv[2] = file_dir.encode('utf-8')

        self._start_worker(
            lambda: self.extract_mes_dll.main(argc, argv),
            on_done=("Extract Finished", "The extraction process has been completed successfully."),
        )

    def _convert_text_messages(self):
        options = QFileDialog.Option.ShowDirsOnly
        dir_name = QFileDialog.getExistingDirectory(self, "Select Directory with Scripts", options=options)
        if not dir_name:
            return

        game_dialog = GameSelectionDialog(self)
        if game_dialog.exec() != QDialog.DialogCode.Accepted:
            return
        logging.info(f"Converting text messages: {dir_name} (game {game_dialog.selected_game})")

        argc = 3
        argv = (ctypes.c_char_p * argc)()
        argv[0] = b"convert_text_messages"
        argv[1] = dir_name.encode('utf-8')
        argv[2] = str(game_dialog.selected_game).encode('utf-8')

        self._start_worker(
            lambda: self.convert_text_dll.main(argc, argv),
            on_done=("Convert Finished", "The conversion process has been completed successfully."),
        )

    # -- PAK ---------------------------------------------------------------

    def unpack_pak(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "PAK Files (*.pak)", options=QFileDialog.Option.ReadOnly)
        if not file_name:
            return
        logging.info(f"Unpacking PAK: {file_name}")
        self._unpack_with_platform(Path(file_name))

    def _unpack_with_platform(self, file_path):
        platform_dialog = PlatformDialog(self)
        if platform_dialog.exec() != QDialog.DialogCode.Accepted:
            return

        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if not output_dir:
            return

        list_mapping = {
            "Steam (PC)": "steam.list",
            "Nintendo Switch": "nsw.list",
            "PlayStation 4": "ps4.list",
        }
        list_path = BASE_DIR / 'req' / 'list_path' / list_mapping[platform_dialog.selected_platform]

        def worker():
            from req.AJTTools.plugins.pak.src.Pak import REPak
            pak = REPak(file_path)
            pak.unpack(Path(output_dir), list_path)

        self._start_worker(
            worker,
            on_done=("Unpacking Finished", "The unpacking process has been completed successfully."),
        )

    def create_pak(self):
        options = QFileDialog.Option.ShowDirsOnly
        dir_name = QFileDialog.getExistingDirectory(self, "Select Directory to Create PAK", options=options)
        if not dir_name:
            return

        output_file, _ = QFileDialog.getSaveFileName(self, "Save PAK File", "", "PAK Files (*.pak)")
        if not output_file:
            return
        logging.info(f"Creating PAK from {dir_name} -> {output_file}")

        self._start_worker(
            _build_pak, Path(dir_name), Path(output_file),
            on_done=("PAK Creation Finished", "The PAK file has been created successfully."),
        )

    # -- TEX ---------------------------------------------------------------

    def convert_single_tex(self):
        dialog = SingleTexConvertDialog(self)
        dialog.exec()

    def convert_multiple_tex(self):
        dialog = MultipleTexConvertDialog(self)
        dialog.exec()

    def convert_tex_to_image(self):
        file_names = self._select_files("Open TEX Files", "TEX Files (*.tex *.tex.*)")
        if not file_names:
            return

        format_dialog = FormatSelectDialog(self)
        if format_dialog.exec() != QDialog.DialogCode.Accepted:
            return

        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if not output_dir:
            return
        logging.info(f"Converting TEX to {format_dialog.selected_format}: {file_names}")

        self._start_worker(
            _convert_tex_to_image, file_names, format_dialog.selected_format, output_dir,
            on_result=self._handle_convert_tex_result,
            on_done=("Convert Finished", "The conversion process has been completed successfully."),
        )

    def _handle_convert_tex_result(self, result):
        if not result:
            return
        if len(result) == 1:
            self.display_single_file(result[0])
        else:
            self.display_multiple_files(result)

    def convert_image_to_tex(self):
        file_names = self._select_files("Open Image Files", "Image Files (*.png *.dds)")
        if not file_names:
            return

        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if not output_dir:
            return
        logging.info(f"Converting images to TEX: {file_names}")

        self._start_worker(
            _convert_image_to_tex, file_names, output_dir,
            on_done=("Convert Finished", "The conversion process has been completed successfully."),
        )

    # -- Fonts -------------------------------------------------------------

    def convert_oft_to_otf(self):
        file_names = self._select_files("Select OFT.1 Font Files", "Font Files (*.oft.*)")
        if not file_names:
            return

        if len(file_names) == 1:
            output, _ = QFileDialog.getSaveFileName(self, "Save OTF Font File", "", "OpenType Fonts (*.otf)")
            if not output:
                return
        else:
            output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
            if not output_dir:
                return
            output = output_dir

        self._start_worker(
            _convert_fonts_to_otf, file_names, output,
            on_done=("Font Conversion Finished", "Font conversion completed successfully."),
        )

    def convert_otf_to_oft(self):
        file_names = self._select_files("Select OTF Font Files", "OpenType Fonts (*.otf)")
        if not file_names:
            return

        if len(file_names) == 1:
            output, _ = QFileDialog.getSaveFileName(self, "Save OFT.1 Font File", "", "Font Files (*.oft.1)")
            if not output:
                return
        else:
            output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
            if not output_dir:
                return
            output = output_dir

        self._start_worker(
            _convert_fonts_to_oft, file_names, output,
            on_done=("Font Conversion Finished", "Font conversion completed successfully."),
        )


def _load_dll(dll_name):
    dll_path = BASE_DIR / 'req' / 'DS' / dll_name
    dll = ctypes.CDLL(str(dll_path))
    dll.main.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_char_p)]
    dll.main.restype = ctypes.c_int
    return dll


def set_taskbar_icon(icon_path):
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"mycompany.myproduct.subproduct.{icon_path}")


def main():
    setup_logging()
    logging.info("Starting application")
    app = QApplication(sys.argv)
    set_taskbar_icon('icon.png')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()