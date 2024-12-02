# main.py
# This is a General Purpose Game Save File Manager for Various Game Emulators, Consoles, etc.
# It is designed to be used with the PyQt5 library for the GUI.
# The Menu Bar will have options for Loading and Saving Catalogs, About Section, and Exit
# Games will be grouped by Console Type and saved in a JSON files in the Program's Data directory
# The Catalogs will be displayed in a Table Widget
# It will be able to infer what the last emulator that used the save file was, and will display that in a column.
# different catalogs exist for different Consoles/Platforms

from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileDialog, QTableWidget, 
                            QTableWidgetItem, QVBoxLayout, QPushButton, QWidget, QComboBox,
                            QMenuBar, QMenu, QAction, QMessageBox, QDialog, QFormLayout, 
                            QLineEdit, QCheckBox, QDialogButtonBox, QGroupBox, QHBoxLayout,
                            QListWidget, QListWidgetItem, QSplitter)
from PyQt5.QtCore import Qt
import os
import json
from pathlib import Path
from scanning import scan_directory, detect_console_type, ScanningWindow

class SaveFileManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Save File Manager")
        self.setGeometry(100, 100, 1000, 600)
        
        # Initialize data directory
        self.data_dir = Path(__file__).parent / 'data'
        self.data_dir.mkdir(exist_ok=True)
        
        # Load config
        self.config = self.load_config()
        
        # Define supported console types based on active systems
        self.console_types = [console for console, active 
                            in self.config['active_systems'].items() 
                            if active]
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create main widget
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        
        # Create splitter for resizable sections
        splitter = QSplitter(Qt.Horizontal)
        
        # Create sidebar
        self.sidebar = QListWidget()
        self.sidebar.addItem("All")
        self.sidebar.currentItemChanged.connect(self.change_catalog)
        splitter.addWidget(self.sidebar)
        
        # Create table
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Console Type", "Game Name", "Save Path", 
                                            "Date Modified", "Last Emulator Used", "Hardware Type"])
        splitter.addWidget(self.table)
        
        # Set splitter sizes (sidebar:table ratio = 1:4)
        splitter.setSizes([200, 800])
        
        main_layout.addWidget(splitter)
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Set default catalog from config
        self.current_catalog = self.config['default_catalog']
        self.update_sidebar()
        
        # Auto-scan directories if configured
        for directory in self.config['auto_scan_directories']:
            if os.path.exists(directory):
                scan_results = scan_directory(directory)
                self.update_table_with_results(scan_results)

    def load_config(self):
        """Load configuration from config.json"""
        config_path = Path(__file__).parent / 'config.json'
        try:
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Create default config if doesn't exist
                default_config = {
                    "emulator_paths": {
                        "mGBA": "", "VBA": "", "FCEUX": "", "SNES9x": "",
                        "Fusion": "", "ePSXe": "", "PCSX2": "", "Project64": "",
                        "Dolphin": "", "ZSNES": "", "DeSmuME": "", "DraStic": "",
                        "PPSSPP": "", "NullDC": "", "Citra": "", "RPCS3": "",
                        "Vita3K": "", "Yuzu": ""
                    },
                    "active_systems": {
                        system: True for system in [
                            "NES", "SNES", "N64", "GameCube", "Wii", "Switch",
                            "PS1", "PS2", "PS3", "PSP", "PS Vita",
                            "Game Boy", "GBC", "GBA", "DS", "3DS",
                            "Sega Genesis", "Dreamcast", "Saturn",
                            "PC", "Arcade"
                        ]
                    },
                    "default_catalog": "All",
                    "auto_scan_directories": [],
                    "backup_settings": {
                        "enabled": False,
                        "backup_directory": "",
                        "backup_frequency_days": 7,
                        "keep_backups": 3
                    }
                }
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=4)
                return default_config
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}

    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        # Add actions to File menu
        scan_action = QAction("Scan Directory", self)
        scan_action.triggered.connect(self.show_scanning_window)
        file_menu.addAction(scan_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Catalog menu
        catalog_menu = menubar.addMenu("Catalog")
        
        load_action = QAction("Load Catalog", self)
        load_action.triggered.connect(self.load_saved_data)
        catalog_menu.addAction(load_action)
        
        save_action = QAction("Save Catalog", self)
        save_action.triggered.connect(self.save_data)
        catalog_menu.addAction(save_action)
        
        clear_action = QAction("Clear Catalog", self)
        clear_action.triggered.connect(lambda: self.table.setRowCount(0))
        catalog_menu.addAction(clear_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        # Add Settings menu
        settings_menu = menubar.addMenu("Settings")
        
        emulator_paths_action = QAction("Emulator Paths", self)
        emulator_paths_action.triggered.connect(self.show_emulator_paths_dialog)
        settings_menu.addAction(emulator_paths_action)
        
        active_systems_action = QAction("Active Systems", self)
        active_systems_action.triggered.connect(self.show_active_systems_dialog)
        settings_menu.addAction(active_systems_action)

    def show_about(self):
        about_text = """
        Game Save File Manager
        Version 1.0
        
        A tool for managing game save files across different platforms and emulators.
        
        Features:
        - Scan directories for save files
        - Detect emulator and console types
        - Organize saves by platform
        - Save and load catalogs
        """
        QMessageBox.about(self, "About Save File Manager", about_text)

    def create_console_combo_box(self, default_value):
        combo = QComboBox()
        combo.addItems(self.console_types)
        if default_value in self.console_types:
            combo.setCurrentText(default_value)
        combo.currentTextChanged.connect(self.save_data)
        return combo

    def show_scanning_window(self):
        scanning_window = ScanningWindow(self)
        if scanning_window.exec_():
            scan_results = scanning_window.get_results()
            self.update_table_with_results(scan_results)

    def update_table_with_results(self, scan_results):
        """Update table with scan results and refresh sidebar"""
        try:
            if not scan_results:
                return
            
            current_row = self.table.rowCount()
            for result in scan_results:
                if self.current_catalog == "All" or result['console_type'] == self.current_catalog:
                    self.table.insertRow(current_row)
                    
                    # Add console type dropdown
                    combo = self.create_console_combo_box(result['console_type'])
                    self.table.setCellWidget(current_row, 0, combo)
                    
                    # Add other columns
                    self.table.setItem(current_row, 1, QTableWidgetItem(result['game_name']))
                    self.table.setItem(current_row, 2, QTableWidgetItem(result['save_path']))
                    self.table.setItem(current_row, 3, QTableWidgetItem(result['date_modified']))
                    self.table.setItem(current_row, 4, QTableWidgetItem(result['emulator']))
                    self.table.setItem(current_row, 5, QTableWidgetItem(result['hardware_type']))
                    
                    current_row += 1
            
            self.save_data()
            self.update_sidebar()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error updating table: {str(e)}")

    def change_catalog(self, current, previous):
        """Handle catalog change from sidebar"""
        if current:
            self.current_catalog = current.data(Qt.UserRole)
            self.load_saved_data()

    def save_data(self):
        """Save current catalog data"""
        try:
            data = []
            for row in range(self.table.rowCount()):
                row_data = {
                    'console_type': self.table.cellWidget(row, 0).currentText(),
                    'game_name': self.table.item(row, 1).text(),
                    'save_path': self.table.item(row, 2).text(),
                    'date_modified': self.table.item(row, 3).text(),
                    'emulator': self.table.item(row, 4).text(),
                    'hardware_type': self.table.item(row, 5).text()
                }
                data.append(row_data)
            
            catalog_file = self.data_dir / f'{self.current_catalog}.json'
            with open(catalog_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving data: {str(e)}")

    def load_saved_data(self):
        """Load catalog data"""
        try:
            self.table.setRowCount(0)
            catalog_file = self.data_dir / f'{self.current_catalog}.json'
            
            if not catalog_file.exists():
                return
            
            with open(catalog_file, 'r') as f:
                data = json.load(f)
            
            for row_data in data:
                row = self.table.rowCount()
                self.table.insertRow(row)
                
                # Add console type dropdown
                self.table.setCellWidget(row, 0, self.create_console_combo_box(row_data['console_type']))
                
                # Add other columns
                self.table.setItem(row, 1, QTableWidgetItem(row_data['game_name']))
                self.table.setItem(row, 2, QTableWidgetItem(row_data['save_path']))
                self.table.setItem(row, 3, QTableWidgetItem(row_data['date_modified']))
                self.table.setItem(row, 4, QTableWidgetItem(row_data['emulator']))
                self.table.setItem(row, 5, QTableWidgetItem(row_data['hardware_type']))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading data: {str(e)}")

    def show_emulator_paths_dialog(self):
        dialog = EmulatorPathsDialog(self.config, self)
        if dialog.exec_():
            self.save_config()

    def show_active_systems_dialog(self):
        dialog = ActiveSystemsDialog(self.config, self)
        if dialog.exec_():
            # Update console types list
            self.console_types = [console for console, active 
                                in self.config['active_systems'].items() 
                                if active]
            # Update sidebar
            self.update_sidebar()
            self.save_config()

    def save_config(self):
        """Save current configuration to config.json"""
        config_path = Path(__file__).parent / 'config.json'
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def update_sidebar(self):
        """Update sidebar with console types and game counts"""
        self.sidebar.clear()
        
        # Add "All" item
        all_item = QListWidgetItem("All")
        all_count = sum(1 for _ in range(self.table.rowCount()))
        all_item.setData(Qt.UserRole, "All")
        all_item.setText(f"All ({all_count})")
        self.sidebar.addItem(all_item)
        
        # Add console types with counts
        for console in self.console_types:
            count = sum(1 for row in range(self.table.rowCount())
                       if self.table.cellWidget(row, 0).currentText() == console)
            if count > 0:  # Only show consoles with games
                item = QListWidgetItem(f"{console} ({count})")
                item.setData(Qt.UserRole, console)
                self.sidebar.addItem(item)
        
        # Select current catalog
        for i in range(self.sidebar.count()):
            item = self.sidebar.item(i)
            if item.data(Qt.UserRole) == self.current_catalog:
                self.sidebar.setCurrentItem(item)
                break

class EmulatorPathsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Emulator Paths")
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # Create form for emulator paths
        form = QFormLayout()
        self.path_inputs = {}
        
        for emulator in self.config['emulator_paths'].keys():
            line_edit = QLineEdit(self.config['emulator_paths'][emulator])
            self.path_inputs[emulator] = line_edit
            
            # Add browse button
            row_layout = QHBoxLayout()
            row_layout.addWidget(line_edit)
            browse_btn = QPushButton("Browse")
            browse_btn.clicked.connect(lambda checked, e=emulator: self.browse_emulator(e))
            row_layout.addWidget(browse_btn)
            
            form.addRow(f"{emulator}:", row_layout)
        
        layout.addLayout(form)
        
        # Add OK/Cancel buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def browse_emulator(self, emulator):
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"Select {emulator} Executable", 
            "",
            "Executable files (*.exe);;All files (*.*)"
        )
        if file_path:
            self.path_inputs[emulator].setText(file_path)
    
    def accept(self):
        # Update config with new paths
        for emulator, input_widget in self.path_inputs.items():
            self.config['emulator_paths'][emulator] = input_widget.text()
        super().accept()

class ActiveSystemsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Active Systems")
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # Create checkboxes for each system
        systems_group = QGroupBox("Enable/Disable Systems")
        systems_layout = QVBoxLayout()
        self.system_checkboxes = {}
        
        for system in sorted(self.config['active_systems'].keys()):
            checkbox = QCheckBox(system)
            checkbox.setChecked(self.config['active_systems'][system])
            self.system_checkboxes[system] = checkbox
            systems_layout.addWidget(checkbox)
        
        systems_group.setLayout(systems_layout)
        layout.addWidget(systems_group)
        
        # Add Select All/None buttons
        buttons_layout = QHBoxLayout()
        select_all = QPushButton("Select All")
        select_none = QPushButton("Select None")
        select_all.clicked.connect(self.select_all_systems)
        select_none.clicked.connect(self.select_no_systems)
        buttons_layout.addWidget(select_all)
        buttons_layout.addWidget(select_none)
        layout.addLayout(buttons_layout)
        
        # Add OK/Cancel buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def select_all_systems(self):
        for checkbox in self.system_checkboxes.values():
            checkbox.setChecked(True)
    
    def select_no_systems(self):
        for checkbox in self.system_checkboxes.values():
            checkbox.setChecked(False)
    
    def accept(self):
        # Update config with new active systems
        for system, checkbox in self.system_checkboxes.items():
            self.config['active_systems'][system] = checkbox.isChecked()
        super().accept()

app = QApplication([])
window = SaveFileManager()
window.show()
app.exec()