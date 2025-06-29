import sys
import os
import traceback
import logging
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QMenuBar, QMenu, QFileDialog,
    QDialog, QVBoxLayout, QLabel, QComboBox, QPushButton, QMessageBox, QTextEdit, QHBoxLayout, QWidget, QListWidget, QStackedWidget
)
from PyQt6.QtGui import QIcon, QAction, QClipboard, QPixmap
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from pathlib import Path
from win11toast import toast
import inspect
import ctypes

# Настройка логирования
log_directory = Path("logs")
log_directory.mkdir(exist_ok=True)
log_filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S.log")
log_filepath = log_directory / log_filename

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filepath),
        logging.StreamHandler()
    ]
)

class WorkerSignals(QObject):
    result = pyqtSignal(object)
    finished = pyqtSignal()
    error = pyqtSignal(tuple)

class WorkerThread(QThread):
    def __init__(self, function, *args):
        super().__init__()
        self.function = function
        self.args = args
        self.signals = WorkerSignals()

    def run(self):
        try:
            logging.info("WorkerThread started")
            result = self.function(*self.args)
            self.signals.result.emit(result)
        except Exception as e:
            traceback_str = traceback.format_exc()
            logging.error(f"Error in WorkerThread: {e}\n{traceback_str}")
            self.signals.error.emit((e, traceback_str))
        finally:
            logging.info("WorkerThread finished")
            self.signals.finished.emit()

class PlatformDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Platform")
        self.selected_platform = None
        self.selected_list_file = None
        self.output_dir = None

        layout = QVBoxLayout()

        self.platform_label = QLabel("Select Platform:")
        layout.addWidget(self.platform_label)

        self.platform_combo = QComboBox()
        self.platform_combo.addItems(["Steam (PC)", "Nintendo Switch", "PlayStation 4"])
        layout.addWidget(self.platform_combo)

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        layout.addWidget(self.ok_button)

        self.setLayout(layout)

    def accept(self):
        self.selected_platform = self.platform_combo.currentText()
        super().accept()

class GameSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Game")
        self.selected_game = None

        layout = QVBoxLayout()

        self.game_label = QLabel("Select Game:")
        layout.addWidget(self.game_label)

        self.game_combo = QComboBox()
        self.game_combo.addItems([
            "1 - original phoenix wright",
            "2 - justice for all",
            "3 - trials and tribulations",
            "4 - apollo justice",
            "5 - Gyakuten Saiban 1 (GBA)"
        ])
        layout.addWidget(self.game_combo)

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        layout.addWidget(self.ok_button)

        self.setLayout(layout)

    def accept(self):
        self.selected_game = self.game_combo.currentIndex() + 1
        super().accept()

class MainWindow(QMainWindow):
    request_platform_and_unpack = pyqtSignal(Path)

    def __init__(self):
        super().__init__()
        logging.info(f"Executing: {inspect.currentframe().f_lineno}")

        self.setWindowTitle("Henshuusha")
        self.setGeometry(100, 100, 800, 600)
        self.setWindowIcon(QIcon('icon.png'))

        menubar = self.menuBar()

        file_menu = menubar.addMenu('File')

        open_menu = file_menu.addMenu('Open')
        ds_menu = open_menu.addMenu('DS')
        gs1234_menu = ds_menu.addMenu('GS1234')

        extract_mes_action = QAction('mes_all.bin', self)
        extract_mes_action.triggered.connect(self.extract_mes_all_bin)
        gs1234_menu.addAction(extract_mes_action)

        convert_text_action = QAction('Script Converter', self)
        convert_text_action.triggered.connect(self.convert_text_messages)
        gs1234_menu.addAction(convert_text_action)

        ajt_menu = open_menu.addMenu('AJT')
        font_menu = ajt_menu.addMenu('Font')

        # Действие для конвертации из oft.1 в otf
        oft_to_otf_action = QAction('oft.1 -> otf', self)
        oft_to_otf_action.triggered.connect(self.convert_oft_to_otf)
        font_menu.addAction(oft_to_otf_action)

        pak_menu = ajt_menu.addMenu('PAK')

        unpack_action = QAction('Unpack', self)
        unpack_action.triggered.connect(self.unpack_pak)
        pak_menu.addAction(unpack_action)

        tex_menu = ajt_menu.addMenu('TEX')
        convert_to_image_action = QAction('Convert to DDS/PNG', self)
        convert_to_image_action.triggered.connect(self.convert_tex_to_image)
        tex_menu.addAction(convert_to_image_action)

        script_menu = ajt_menu.addMenu('Script')
        gs56_decode_action = QAction('GS56 Decode', self)
        gs56_decode_action.triggered.connect(self.decode_gs56_script)
        script_menu.addAction(gs56_decode_action)

        gs4_decode_action = QAction('GS4 Decode', self)
        gs4_decode_action.triggered.connect(self.decode_gs4_script)
        script_menu.addAction(gs4_decode_action)

        save_menu = file_menu.addMenu('Save')
        save_ajt_menu = save_menu.addMenu('AJT')

        save_pak_menu = save_ajt_menu.addMenu('PAK')
        create_pak_action = QAction('Create PAK', self)
        create_pak_action.triggered.connect(self.create_pak)
        save_pak_menu.addAction(create_pak_action)

        save_tex_menu = save_ajt_menu.addMenu('TEX')
        convert_to_tex_action = QAction('Convert to TEX', self)
        convert_to_tex_action.triggered.connect(self.convert_image_to_tex)
        save_tex_menu.addAction(convert_to_tex_action)

        save_script_menu = save_ajt_menu.addMenu('Script')
        gs56_encode_action = QAction('GS56 Encode', self)
        gs56_encode_action.triggered.connect(self.encode_gs56_script)
        save_script_menu.addAction(gs56_encode_action)

        gs4_encode_action = QAction('GS4 Encode', self)
        gs4_encode_action.triggered.connect(self.encode_gs4_script)
        save_script_menu.addAction(gs4_encode_action)

        # Действие для конвертации из otf в oft.1
        save_ajt_menu = save_menu.addMenu('AJT')
        font_save_menu = save_ajt_menu.addMenu('Font')

        otf_to_oft_action = QAction('otf -> oft.1', self)
        otf_to_oft_action.triggered.connect(self.convert_otf_to_oft)
        font_save_menu.addAction(otf_to_oft_action)

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

        self.text_edit.setVisible(False)
        self.copy_path_button.setVisible(False)
        self.close_button.setVisible(False)
        self.file_list_widget.setVisible(False)

        self.request_platform_and_unpack.connect(self.select_platform_and_unpack)

        extract_mes_dll_path = os.path.join(os.path.dirname(__file__), 'req', 'DS', 'extract_mes_all_bin.dll')
        self.extract_mes_all_bin = ctypes.CDLL(extract_mes_dll_path)
        self.extract_mes_all_bin.main.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_char_p)]
        self.extract_mes_all_bin.main.restype = ctypes.c_int

        convert_text_dll_path = os.path.join(os.path.dirname(__file__), 'req', 'DS', 'convert_text_messages.dll')
        self.convert_text_messages = ctypes.CDLL(convert_text_dll_path)
        self.convert_text_messages.main.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_char_p)]
        self.convert_text_messages.main.restype = ctypes.c_int

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.scale_image_to_label()

    def scale_image_to_label(self):
        if self.image_label.pixmap():
            pixmap = self.image_label.pixmap()
            scaled_pixmap = pixmap.scaled(
                self.image_label.size() * 0.9,  # 90% от размера QLabel
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)

    def show_error_message(self, message):
        logging.error(f"Error message: {message}")
        QMessageBox.critical(self, "Error", message)

    def unpack_pak(self):
        try:
            logging.info(f"Executing: {inspect.currentframe().f_lineno}")
            logging.info("Unpacking PAK file")
            options = QFileDialog.Option.ReadOnly
            file_name, _ = QFileDialog.getOpenFileName(self, "Open File", "", "PAK Files (*.pak)", options=options)
            if file_name:
                logging.info(f"Selected file: {file_name}")

                self.worker_thread = WorkerThread(lambda: self.request_platform_and_unpack.emit(Path(file_name)))
                self.worker_thread.signals.finished.connect(self.handle_unpack_finished)
                self.worker_thread.signals.error.connect(self.handle_unpack_error)
                self.worker_thread.start()
        except Exception as e:
            logging.error(f"Error opening file: {e}")
            self.show_error_message(f"An error occurred: {e}")
            traceback.print_exc()

    def handle_unpack_result(self, result):
        logging.info(f"Executing: {inspect.currentframe().f_lineno}")
        logging.info(f"Unpack result: {result}")

    def handle_unpack_finished(self):
        logging.info(f"Executing: {inspect.currentframe().f_lineno}")
        logging.info("Unpack finished")
        toast("Unpacking Finished", "The unpacking process has been completed successfully.")

    def handle_unpack_error(self, error):
        logging.info(f"Executing: {inspect.currentframe().f_lineno}")
        e, traceback_str = error
        logging.error(f"Unpack error: {e}\n{traceback_str}")
        self.show_error_message(f"An error occurred: {e}")

    def select_platform_and_unpack(self, file_name):
        try:
            logging.info(f"Executing: {inspect.currentframe().f_lineno}")
            logging.info("Selecting platform and unpacking")
            dialog = PlatformDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                selected_platform = dialog.selected_platform
                logging.info(f"Selected platform: {selected_platform}")

                output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
                if output_dir:
                    logging.info(f"Selected output directory: {output_dir}")

                    list_path = Path(os.path.dirname(__file__)) / 'req' / 'list_path'
                    list_files = [f for f in list_path.iterdir() if f.suffix == '.list']

                    if selected_platform == "Steam (PC)":
                        selected_list_file = "steam.list"
                    elif selected_platform == "Nintendo Switch":
                        selected_list_file = "nsw.list"
                    elif selected_platform == "PlayStation 4":
                        selected_list_file = "ps4.list"

                    release_list_path = list_path / selected_list_file
                    from req.AJTTools.plugins.pak.src.Pak import REPak

                    pak = REPak(file_name)
                    self.worker_thread = WorkerThread(pak.unpack, Path(output_dir), release_list_path)
                    self.worker_thread.signals.finished.connect(self.handle_unpack_finished)
                    self.worker_thread.signals.error.connect(self.handle_unpack_error)
                    self.worker_thread.start()
        except Exception as e:
            logging.error(f"Error selecting platform and unpacking: {e}")
            raise

    def decode_gs56_script(self):
        try:
            logging.info(f"Executing: {inspect.currentframe().f_lineno}")
            logging.info("Decoding GS56 script")
            options = QFileDialog.Option.ReadOnly
            file_names, _ = QFileDialog.getOpenFileNames(self, "Open File", "", "Script Files (*.user.2.*)", options=options)
            if file_names:
                logging.info(f"Selected files: {file_names}")

                def decode():
                    from req.AJT56script import decode_script
                    results = []
                    for file_name in file_names:
                        output_file = Path(file_name).with_suffix('.json')
                        decode_script(file_name, output_file)
                        with open(output_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        results.append(content)
                    return results

                self.worker_thread = WorkerThread(decode)
                self.worker_thread.signals.result.connect(self.handle_decode_result)
                self.worker_thread.signals.finished.connect(self.handle_decode_finished)
                self.worker_thread.signals.error.connect(self.handle_decode_error)
                self.worker_thread.start()
        except Exception as e:
            logging.error(f"Error decoding script: {e}")
            self.show_error_message(f"An error occurred: {e}")
            traceback.print_exc()

    def handle_decode_result(self, result):
        logging.info(f"Executing: {inspect.currentframe().f_lineno}")
        if result:
            combined_content = "\n".join(result)
            self.text_edit.setPlainText(combined_content)
            self.text_edit.setVisible(True)
            self.copy_path_button.setVisible(True)
            self.close_button.setVisible(True)
            QMessageBox.information(self, "Success", "Script decoding completed successfully!")

    def handle_decode_finished(self):
        logging.info(f"Executing: {inspect.currentframe().f_lineno}")
        logging.info("Decode finished")
        toast("Decoding Finished", "The decoding process has been completed successfully.")

    def handle_decode_error(self, error):
        logging.info(f"Executing: {inspect.currentframe().f_lineno}")
        e, traceback_str = error
        logging.error(f"Decode error: {e}\n{traceback_str}")
        self.show_error_message(f"An error occurred: {e}")

    def encode_gs56_script(self):
        try:
            logging.info(f"Executing: {inspect.currentframe().f_lineno}")
            logging.info("Encoding GS56 script")
            options = QFileDialog.Option.ReadOnly
            file_names, _ = QFileDialog.getOpenFileNames(self, "Open File", "", "Script Files (*.json *.bin)", options=options)
            if file_names:
                logging.info(f"Selected files: {file_names}")

                def encode():
                    from req.AJT56script import encode_script
                    results = []
                    for file_name in file_names:
                        output_file = Path(file_name).with_suffix('.bin')
                        encode_script(file_name, output_file)
                        with open(output_file, 'rb') as f:
                            content = f.read().decode('utf-8', errors='ignore')
                        results.append(content)
                    return results

                self.worker_thread = WorkerThread(encode)
                self.worker_thread.signals.result.connect(self.handle_encode_result)
                self.worker_thread.signals.finished.connect(self.handle_encode_finished)
                self.worker_thread.signals.error.connect(self.handle_encode_error)
                self.worker_thread.start()
        except Exception as e:
            logging.error(f"Error encoding script: {e}")
            self.show_error_message(f"An error occurred: {e}")
            traceback.print_exc()

    def handle_encode_result(self, result):
        logging.info(f"Executing: {inspect.currentframe().f_lineno}")
        if result:
            combined_content = "\n".join(result)
            self.text_edit.setPlainText(combined_content)
            self.text_edit.setVisible(True)
            self.copy_path_button.setVisible(True)
            self.close_button.setVisible(True)
            QMessageBox.information(self, "Success", "Script encoding completed successfully!")

    def handle_encode_finished(self):
        logging.info(f"Executing: {inspect.currentframe().f_lineno}")
        logging.info("Encode finished")
        toast("Encoding Finished", "The encoding process has been completed successfully.")

    def handle_encode_error(self, error):
        logging.info(f"Executing: {inspect.currentframe().f_lineno}")
        e, traceback_str = error
        logging.error(f"Encode error: {e}\n{traceback_str}")
        self.show_error_message(f"An error occurred: {e}")

    def decode_gs4_script(self):
        try:
            logging.info(f"Executing: {inspect.currentframe().f_lineno}")
            logging.info("Decoding GS4 script")
            options = QFileDialog.Option.ReadOnly
            file_names, _ = QFileDialog.getOpenFileNames(self, "Open File", "", "Script Files (*.user.2.*)", options=options)
            if file_names:
                logging.info(f"Selected files: {file_names}")

                def decode():
                    from req.AJTTools.plugins.script import AA4Script
                    results = []
                    for file_name in file_names:
                        file_path = Path(file_name)
                        script = AA4Script(file_path)
                        output_file = file_path.with_suffix('.txt')
                        script.write_txt(output_file)
                        with open(output_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        results.append(content)
                    return results

                self.worker_thread = WorkerThread(decode)
                self.worker_thread.signals.result.connect(self.handle_decode_result)
                self.worker_thread.signals.finished.connect(self.handle_decode_finished)
                self.worker_thread.signals.error.connect(self.handle_decode_error)
                self.worker_thread.start()
        except Exception as e:
            logging.error(f"Error decoding script: {e}")
            self.show_error_message(f"An error occurred: {e}")
            traceback.print_exc()

    def encode_gs4_script(self):
        try:
            logging.info(f"Executing: {inspect.currentframe().f_lineno}")
            logging.info("Encoding GS4 script")
            options = QFileDialog.Option.ReadOnly
            file_names, _ = QFileDialog.getOpenFileNames(self, "Open File", "", "Script Files (*.txt)", options=options)
            if file_names:
                logging.info(f"Selected files: {file_names}")

                def encode():
                    from req.AJTTools.plugins.script import AA4Script
                    results = []
                    for file_name in file_names:
                        file_path = Path(file_name)
                        script = AA4Script(file_path)
                        output_file = file_path.with_suffix('.user.2')
                        script.write_user2(output_file)
                        with open(output_file, 'rb') as f:
                            content = f.read().decode('utf-8', errors='ignore')
                        results.append(content)
                    return results

                self.worker_thread = WorkerThread(encode)
                self.worker_thread.signals.result.connect(self.handle_encode_result)
                self.worker_thread.signals.finished.connect(self.handle_encode_finished)
                self.worker_thread.signals.error.connect(self.handle_encode_error)
                self.worker_thread.start()
        except Exception as e:
            logging.error(f"Error encoding script: {e}")
            self.show_error_message(f"An error occurred: {e}")
            traceback.print_exc()

    def create_pak(self):
        try:
            logging.info(f"Executing: {inspect.currentframe().f_lineno}")
            logging.info("Creating PAK file")
            options = QFileDialog.Option.ShowDirsOnly
            dir_name = QFileDialog.getExistingDirectory(self, "Select Directory to Create PAK", options=options)
            if dir_name:
                logging.info(f"Selected directory to create PAK: {dir_name}")
                output_file, _ = QFileDialog.getSaveFileName(self, "Save PAK File", "", "PAK Files (*.pak)")
                if output_file:
                    logging.info(f"Selected output PAK file: {output_file}")

                    def build_pak(dir_path, pak_path):
                        from req.AJTTools.plugins.pak.src.Pak import build_pak_from_dir
                        build_pak_from_dir(dir_path, pak_path)

                    self.worker_thread = WorkerThread(build_pak, Path(dir_name), Path(output_file))
                    self.worker_thread.signals.finished.connect(self.handle_create_pak_finished)
                    self.worker_thread.signals.error.connect(self.handle_create_pak_error)
                    self.worker_thread.start()
        except Exception as e:
            logging.error(f"Error creating PAK file: {e}")
            self.show_error_message(f"An error occurred: {e}")
            traceback.print_exc()

    def handle_create_pak_finished(self):
        logging.info(f"Executing: {inspect.currentframe().f_lineno}")
        logging.info("PAK creation finished")
        toast("PAK Creation Finished", "The PAK file has been created successfully.")

    def handle_create_pak_error(self, error):
        logging.info(f"Executing: {inspect.currentframe().f_lineno}")
        e, traceback_str = error
        logging.error(f"PAK creation error: {e}\n{traceback_str}")
        self.show_error_message(f"An error occurred: {e}")

    def copy_path(self):
        try:
            logging.info(f"Executing: {inspect.currentframe().f_lineno}")
            logging.info("Copying path to clipboard")
            clipboard = QApplication.clipboard()
            clipboard.setText(self.text_edit.toPlainText().split('\n')[0])
            QMessageBox.information(self, "Success", "Path copied to clipboard!")
        except Exception as e:
            logging.error(f"Error copying path to clipboard: {e}")
            self.show_error_message(f"An error occurred: {e}")
            traceback.print_exc()

    def close_text_edit(self):
        logging.info(f"Executing: {inspect.currentframe().f_lineno}")
        logging.info("Closing text edit")
        self.text_edit.setVisible(False)
        self.copy_path_button.setVisible(False)
        self.close_button.setVisible(False)
        self.file_list_widget.setVisible(False)
        self.stacked_widget.setCurrentIndex(0)

    def extract_mes_all_bin(self):
        try:
            logging.info(f"Executing: {inspect.currentframe().f_lineno}")
            logging.info("Extracting mes_all.bin")
            options = QFileDialog.Option.ReadOnly
            file_name, _ = QFileDialog.getOpenFileName(self, "Open File", "", "BIN Files (*.bin)", options=options)
            if file_name:
                logging.info(f"Selected file: {file_name}")

                file_dir = os.path.dirname(file_name)

                argc = 3
                argv = (ctypes.c_char_p * argc)()
                argv[0] = b"extract_mes_all_bin"
                argv[1] = file_name.encode('utf-8')
                argv[2] = file_dir.encode('utf-8')

                self.worker_thread = WorkerThread(lambda: self.extract_mes_all_bin.main(argc, argv))
                self.worker_thread.signals.finished.connect(self.handle_extract_finished)
                self.worker_thread.signals.error.connect(self.handle_extract_error)
                self.worker_thread.start()
        except Exception as e:
            logging.error(f"Error extracting mes_all.bin: {e}")
            self.show_error_message(f"An error occurred: {e}")
            traceback.print_exc()

    def handle_extract_finished(self):
        logging.info(f"Executing: {inspect.currentframe().f_lineno}")
        logging.info("Extract finished")
        toast("Extract Finished", "The extraction process has been completed successfully.")

    def handle_extract_error(self, error):
        logging.info(f"Executing: {inspect.currentframe().f_lineno}")
        e, traceback_str = error
        logging.error(f"Extract error: {e}\n{traceback_str}")
        self.show_error_message(f"An error occurred: {e}")

    def convert_text_messages(self):
        try:
            logging.info(f"Executing: {inspect.currentframe().f_lineno}")
            logging.info("Converting text messages")
            options = QFileDialog.Option.ShowDirsOnly
            dir_name = QFileDialog.getExistingDirectory(self, "Select Directory with Scripts", options=options)
            if dir_name:
                logging.info(f"Selected directory: {dir_name}")

                game_dialog = GameSelectionDialog(self)
                if game_dialog.exec() == QDialog.DialogCode.Accepted:
                    selected_game = game_dialog.selected_game
                    logging.info(f"Selected game: {selected_game}")

                    argc = 3
                    argv = (ctypes.c_char_p * argc)()
                    argv[0] = b"convert_text_messages"
                    argv[1] = dir_name.encode('utf-8')
                    argv[2] = str(selected_game).encode('utf-8')

                    self.worker_thread = WorkerThread(lambda: self.convert_text_messages.main(argc, argv))
                    self.worker_thread.signals.finished.connect(self.handle_convert_finished)
                    self.worker_thread.signals.error.connect(self.handle_convert_error)
                    self.worker_thread.start()
        except Exception as e:
            logging.error(f"Error converting text messages: {e}")
            self.show_error_message(f"An error occurred: {e}")
            traceback.print_exc()

    def handle_convert_finished(self):
        logging.info(f"Executing: {inspect.currentframe().f_lineno}")
        logging.info("Convert finished")
        toast("Convert Finished", "The conversion process has been completed successfully.")

    def handle_convert_error(self, error):
        logging.info(f"Executing: {inspect.currentframe().f_lineno}")
        e, traceback_str = error
        logging.error(f"Convert error: {e}\n{traceback_str}")
        self.show_error_message(f"An error occurred: {e}")

    def convert_tex_to_image(self):
        options = QFileDialog.Option.ReadOnly
        file_names, _ = QFileDialog.getOpenFileNames(self, "Open TEX Files", "", "TEX Files (*.tex.*)", options=options)
        if file_names:
            format_dialog = QDialog(self)
            format_dialog.setWindowTitle("Select Output Format")
            layout = QVBoxLayout()

            format_label = QLabel("Select Format:")
            layout.addWidget(format_label)

            format_combo = QComboBox()
            format_combo.addItems(["PNG", "DDS"])
            layout.addWidget(format_combo)

            ok_button = QPushButton("OK")
            ok_button.clicked.connect(format_dialog.accept)
            layout.addWidget(ok_button)

            format_dialog.setLayout(layout)

            if format_dialog.exec() == QDialog.DialogCode.Accepted:
                selected_format = format_combo.currentText().lower()
                output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
                if output_dir:
                    self.worker_thread = WorkerThread(self._convert_tex_to_image_worker, file_names, selected_format, output_dir)
                    self.worker_thread.signals.result.connect(self.handle_convert_tex_result)
                    self.worker_thread.signals.finished.connect(self.handle_convert_finished)
                    self.worker_thread.signals.error.connect(self.handle_convert_error)
                    self.worker_thread.start()

    def _convert_tex_to_image_worker(self, file_names, selected_format, output_dir):
        from req.AJTTools.plugins.tex import Tex
        results = []
        for file_name in file_names:
            tex = Tex(file_name)
            output_file = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(file_name))[0]}.{selected_format}")
            tex.export_file(output_file)
            results.append(output_file)
        return results

    def handle_convert_tex_result(self, result):
        if result:
            if len(result) == 1:
                self.display_single_file(result[0])
            else:
                self.display_multiple_files(result)

    def display_single_file(self, file_path):
        if file_path.endswith('.png') or file_path.endswith('.dds'):
            pixmap = QPixmap(file_path)
            self.image_label.setPixmap(pixmap)
            self.scale_image_to_label()
            self.stacked_widget.setCurrentWidget(self.image_label)
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.text_edit.setPlainText(content)
            self.stacked_widget.setCurrentWidget(self.text_edit)

        self.text_edit.setVisible(True)
        self.copy_path_button.setVisible(True)
        self.close_button.setVisible(True)

    def display_multiple_files(self, file_paths):
        self.file_list_widget.clear()
        self.file_list_widget.addItems(file_paths)
        self.file_list_widget.setVisible(True)
        self.file_list_widget.setCurrentRow(0)

    def display_file_content(self, item):
        file_path = item.text()
        if file_path.endswith('.png'):
            pixmap = QPixmap(file_path)
            self.image_label.setPixmap(pixmap)
            self.scale_image_to_label()
            self.stacked_widget.setCurrentWidget(self.image_label)
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.text_edit.setPlainText(content)
            self.stacked_widget.setCurrentWidget(self.text_edit)

    def convert_image_to_tex(self):
        options = QFileDialog.Option.ReadOnly
        file_names, _ = QFileDialog.getOpenFileNames(self, "Open Image Files", "", "Image Files (*.png *.dds)", options=options)
        if file_names:
            output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
            if output_dir:
                self.worker_thread = WorkerThread(self._convert_image_to_tex_worker, file_names, output_dir)
                self.worker_thread.signals.finished.connect(self.handle_convert_finished)
                self.worker_thread.signals.error.connect(self.handle_convert_error)
                self.worker_thread.start()

    def _convert_image_to_tex_worker(self, file_names, output_dir):
        from req.AJTTools.plugins.tex import Tex
        results = []
        for file_name in file_names:
            base_name = os.path.basename(file_name)
            tex_name = base_name.replace('.png', '.tex.35').replace('.dds', '.tex.35')
            output_file = os.path.join(output_dir, tex_name)
            tex = Tex(output_file)
            tex.import_file(file_name)
            tex.save(output_file)
            results.append(output_file)
        return results

    def convert_oft_to_otf(self):
        options = QFileDialog.Option.ReadOnly
        file_names, _ = QFileDialog.getOpenFileNames(self, "Select OFT.1 Font Files", "", "Font Files (*.oft.*)", options=options)
        if file_names:
            if len(file_names) == 1:
                output_file, _ = QFileDialog.getSaveFileName(self, "Save OTF Font File", "", "OpenType Fonts (*.otf)")
                if output_file:
                    self.convert_fonts(file_names, output_file)
            else:
                output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
                if output_dir:
                    self.convert_fonts(file_names, output_dir)

    def convert_otf_to_oft(self):
        options = QFileDialog.Option.ReadOnly
        file_names, _ = QFileDialog.getOpenFileNames(self, "Select OTF Font Files", "", "OpenType Fonts (*.otf)", options=options)
        if file_names:
            if len(file_names) == 1:
                output_file, _ = QFileDialog.getSaveFileName(self, "Save OFT.1 Font File", "", "Font Files (*.oft.1)")
                if output_file:
                    self.convert_fonts_back(file_names, output_file)
            else:
                output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
                if output_dir:
                    self.convert_fonts_back(file_names, output_dir)

    def convert_fonts(self, file_names, output):
        try:
            from req.AJTTools.plugins.font import REFont
            if isinstance(output, str):  # Один файл
                font = REFont(file_names[0])
                font.export_file(output)
                QMessageBox.information(self, "Success", "Font conversion completed successfully!")
            else:  # Несколько файлов
                for file_name in file_names:
                    font = REFont(file_name)
                    base_name = os.path.basename(file_name).replace('.oft.', '.otf')
                    output_file = os.path.join(output, base_name)
                    font.export_file(output_file)
                QMessageBox.information(self, "Success", "All font conversions completed successfully!")
        except Exception as e:
            self.show_error_message(f"An error occurred: {e}")

    def convert_fonts_back(self, file_names, output):
        try:
            from req.AJTTools.plugins.font import REFont # Импортируем обработчик шрифтов
            if isinstance(output, str):  # Один файл
                font = REFont(output)  # Создаем экземпляр REFont с пустым именем
                font.import_file(file_names[0])
                font.save(output)
                QMessageBox.information(self, "Success", "Font conversion completed successfully!")
            else:  # Несколько файлов
                for file_name in file_names:
                    base_name = os.path.basename(file_name).replace('.otf', '.oft.1')
                    output_file = os.path.join(output, base_name)
                    font = REFont(output_file)  # Создаем экземпляр REFont с именем выходного файла
                    font.import_file(file_name)
                    font.save(output_file)
                QMessageBox.information(self, "Success", "All font conversions completed successfully!")
        except Exception as e:
            self.show_error_message(f"An error occurred: {e}")

def set_taskbar_icon(icon_path):
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"mycompany.myproduct.subproduct.{icon_path}")

def main():
    logging.info(f"Executing: {inspect.currentframe().f_lineno}")
    logging.info("Starting application")
    app = QApplication(sys.argv)
    set_taskbar_icon('icon.png')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()