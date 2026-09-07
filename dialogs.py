"""Dialog windows used by the application."""
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QComboBox, QPushButton, QFileDialog,
    QMessageBox,
)


class PlatformDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Platform")
        self.selected_platform = None

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Select Platform:"))
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(["Steam (PC)", "Nintendo Switch", "PlayStation 4"])
        layout.addWidget(self.platform_combo)

        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        layout.addWidget(ok_button)
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
        layout.addWidget(QLabel("Select Game:"))
        self.game_combo = QComboBox()
        self.game_combo.addItems([
            "1 - original phoenix wright",
            "2 - justice for all",
            "3 - trials and tribulations",
            "4 - apollo justice",
            "5 - Gyakuten Saiban 1 (GBA)",
        ])
        layout.addWidget(self.game_combo)

        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        layout.addWidget(ok_button)
        self.setLayout(layout)

    def accept(self):
        self.selected_game = self.game_combo.currentIndex() + 1
        super().accept()


class FormatSelectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Output Format")
        self.selected_format = None

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Select Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["PNG", "DDS"])
        layout.addWidget(self.format_combo)

        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        layout.addWidget(ok_button)
        self.setLayout(layout)

    def accept(self):
        self.selected_format = self.format_combo.currentText().lower()
        super().accept()


class SingleTexConvertDialog(QDialog):
    """Converts a single texture between PC and Nintendo Switch formats."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Convert Single Texture")
        self.setLayout(QVBoxLayout())

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["PC -> NSW", "NSW -> PC"])

        self.pc_tex_label = QLabel()
        self.nsw_tex_label = QLabel()
        self.output_label = QLabel()

        pc_button = QPushButton("Select PC Texture")
        pc_button.clicked.connect(lambda: self._select_file("Select PC Texture", self.pc_tex_label))
        nsw_button = QPushButton("Select NSW Texture")
        nsw_button.clicked.connect(lambda: self._select_file("Select NSW Texture", self.nsw_tex_label))
        output_button = QPushButton("Select Output Directory")
        output_button.clicked.connect(lambda: self._select_dir(self.output_label))
        convert_button = QPushButton("Convert")
        convert_button.clicked.connect(self.convert)

        layout = self.layout()
        layout.addWidget(QLabel("Select Conversion Mode:"))
        layout.addWidget(self.mode_combo)
        layout.addWidget(pc_button)
        layout.addWidget(self.pc_tex_label)
        layout.addWidget(nsw_button)
        layout.addWidget(self.nsw_tex_label)
        layout.addWidget(output_button)
        layout.addWidget(self.output_label)
        layout.addWidget(convert_button)

    def _select_file(self, title, label):
        file_path, _ = QFileDialog.getOpenFileName(self, title, "", "TEX Files (*.tex *.tex.*)")
        if file_path:
            label.setText(file_path)

    def _select_dir(self, label):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dir_path:
            label.setText(dir_path)

    def convert(self):
        from .tex_converter import TexConverter

        mode = self.mode_combo.currentText()
        pc_path = self.pc_tex_label.text()
        nsw_path = self.nsw_tex_label.text()
        output_dir = self.output_label.text()

        if not pc_path or not nsw_path or not output_dir:
            QMessageBox.warning(self, "Warning", "Please select all required fields.")
            return

        source_file = Path(pc_path) if mode == "PC -> NSW" else Path(nsw_path)
        reference_file = Path(nsw_path) if mode == "PC -> NSW" else Path(pc_path)
        output_path = Path(output_dir) / source_file.name

        try:
            if mode == "PC -> NSW":
                TexConverter.PCtex_to_NSWtex(pc_path, nsw_path, output_path)
            else:
                TexConverter.NSWtex_to_PCtex(nsw_path, pc_path, output_path)
            QMessageBox.information(self, "Success", "Texture converted successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred during conversion: {e}")


class MultipleTexConvertDialog(QDialog):
    """Converts multiple textures between PC and Nintendo Switch formats."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Convert Multiple Textures")
        self.setLayout(QVBoxLayout())

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["PC -> NSW", "NSW -> PC"])

        self.pc_dir_label = QLabel()
        self.nsw_dir_label = QLabel()
        self.output_dir_label = QLabel()

        pc_button = QPushButton("Select PC Directory")
        pc_button.clicked.connect(lambda: self._select_dir("Select PC Directory", self.pc_dir_label))
        nsw_button = QPushButton("Select NSW Directory")
        nsw_button.clicked.connect(lambda: self._select_dir("Select NSW Directory", self.nsw_dir_label))
        output_button = QPushButton("Select Output Directory")
        output_button.clicked.connect(lambda: self._select_dir("Select Output Directory", self.output_dir_label))
        convert_button = QPushButton("Convert")
        convert_button.clicked.connect(self.convert)

        layout = self.layout()
        layout.addWidget(QLabel("Select Conversion Mode:"))
        layout.addWidget(self.mode_combo)
        layout.addWidget(pc_button)
        layout.addWidget(self.pc_dir_label)
        layout.addWidget(nsw_button)
        layout.addWidget(self.nsw_dir_label)
        layout.addWidget(output_button)
        layout.addWidget(self.output_dir_label)
        layout.addWidget(convert_button)

    def _select_dir(self, title, label):
        dir_path = QFileDialog.getExistingDirectory(self, title)
        if dir_path:
            label.setText(dir_path)

    def convert(self):
        from .tex_converter import (
            TexConverter, is_tex_file, index_tex_files, find_tex_template,
        )

        mode = self.mode_combo.currentText()
        pc_dir = Path(self.pc_dir_label.text())
        nsw_dir = Path(self.nsw_dir_label.text())
        output_dir = Path(self.output_dir_label.text())

        if not self.pc_dir_label.text() or not self.nsw_dir_label.text() or not self.output_dir_label.text():
            QMessageBox.warning(self, "Warning", "Please select all required directories.")
            return

        try:
            # Collect ALL textures regardless of language:
            # foo.tex, foo.tex.<id>, foo.tex.<id>.en, foo.tex.<id>.fr, etc.
            pc_files = [f for f in pc_dir.rglob("*") if is_tex_file(f)]
            nsw_files = [f for f in nsw_dir.rglob("*") if is_tex_file(f)]

            pc_by_name, pc_by_base = index_tex_files(pc_files)
            nsw_by_name, nsw_by_base = index_tex_files(nsw_files)

            if mode == "PC -> NSW":
                sources, template_root, t_by_name, t_by_base, convert_fn = (
                    pc_files, nsw_dir, nsw_by_name, nsw_by_base, TexConverter.PCtex_to_NSWtex,
                )
            else:  # "NSW -> PC"
                sources, template_root, t_by_name, t_by_base, convert_fn = (
                    nsw_files, pc_dir, pc_by_name, pc_by_base, TexConverter.NSWtex_to_PCtex,
                )

            converted = 0
            skipped = 0
            for src_file in sources:
                # Match by exact name first, then by base name (without the
                # language suffix) so conversion works for ANY language.
                template_file = find_tex_template(src_file, t_by_name, t_by_base)

                if template_file is None:
                    skipped += 1
                    continue

                rel_template = template_file.relative_to(template_root)

                # Output name comes from the source texture (keeps its language
                # suffix); folder structure comes from the target template.
                output_file = output_dir / rel_template.parent / src_file.name
                output_file.parent.mkdir(parents=True, exist_ok=True)
                convert_fn(src_file, template_file, output_file)
                converted += 1

            if converted == 0:
                QMessageBox.warning(self, "Warning", "No matching textures found between the selected directories.")
            else:
                msg = f"All textures converted successfully! ({converted} file(s))"
                if skipped:
                    msg += f"\n{skipped} file(s) skipped - no matching texture found in the target directory."
                QMessageBox.information(self, "Success", msg)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred during conversion: {e}")