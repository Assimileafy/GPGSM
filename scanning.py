#scanning.py contains the scanning function that will scan a directory for Games and their save files
#it basically shows the scanning window for main.py
#and detect the console type of the save files and save the data in a JSON file
#the JSON file will be used to populate the table in the main window - main.py
#Scanning will be done in a separate thread to prevent the GUI from freezing
#Scanning will be done by reading the ignore.json file to ignore certain files and directories


import os
from pathlib import Path
from datetime import datetime
import re
import json
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLabel, QProgressBar, 
                            QPushButton, QFileDialog, QMessageBox)

def load_ignore_list():
    """Load ignore patterns from ignore.json"""
    try:
        ignore_file = Path(__file__).parent / 'ignore.json'
        if ignore_file.exists():
            with open(ignore_file, 'r', encoding='utf-8') as f:
                # Skip any lines starting with #
                json_str = '\n'.join(line for line in f if not line.strip().startswith('#'))
                ignore_data = json.loads(json_str)
                return (ignore_data.get('ignore_directories', []), 
                       ignore_data.get('ignore_files', []))
    except Exception as e:
        print(f"Error loading ignore.json: {e}")
    return [], []

def detect_console_type(file_path):
    """
    Detect console type based on file extension and path patterns
    Returns tuple of (console_type, emulator, hardware_type)
    """
    file_path = file_path.lower()
    path = Path(file_path)
    extension = path.suffix

    # Dictionary mapping extensions and patterns to console types
    console_patterns = {
        '.sav': {
            'gb': ('Game Boy', 'mGBA/VBA', 'Original'),
            'gbc': ('GBC', 'mGBA/VBA', 'Color'), 
            'gba': ('GBA', 'mGBA/VBA', 'Advance'),
            'nes': ('NES', 'FCEUX', 'Original'),
            'snes': ('SNES', 'SNES9x', 'Original')
        },
        '.srm': {
            'snes': ('SNES', 'SNES9x', 'Original'),
            'gba': ('GBA', 'mGBA', 'Advance'),
            'genesis': ('Sega Genesis', 'Fusion', 'Original')
        },
        '.mcr': ('PS1', 'ePSXe', 'Original'),
        '.mc': ('PS2', 'PCSX2', 'Original'), 
        '.mem': ('N64', 'Project64', 'Original'),
        '.gci': ('GameCube', 'Dolphin', 'Original'),
        '.sram': ('SNES', 'ZSNES', 'Original'),
        '.dsv': ('DS', 'DeSmuME', 'Original'),
        '.duc': ('DS', 'DraStic', 'Original'),
        '.nps': ('PSP', 'PPSSPP', 'Original'),
        '.vms': ('Dreamcast', 'NullDC', 'Original'),
        '.sav2': ('3DS', 'Citra', 'Original'),
        '.dat': ('PS3', 'RPCS3', 'Original'),
        '.bin': ('PS Vita', 'Vita3K', 'Original'),
        '.nv': ('Switch', 'Yuzu', 'Original')
    }

    # Load emulator path from config
    config_path = Path(__file__).parent / 'config.json'
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            emulator_paths = config.get('emulator_paths', {})
    except Exception:
        emulator_paths = {}

    # Check file extension matches
    for ext, console_info in console_patterns.items():
        if extension == ext:
            if isinstance(console_info, dict):
                # Check path for specific console indicators
                path_str = str(path).lower()
                for key, value in console_info.items():
                    if key in path_str:
                        # Use configured emulator path if available
                        emulator_name = value[1].split('/')[0]  # Get first emulator name
                        emulator_path = emulator_paths.get(emulator_name, '')
                        return (value[0], emulator_path or value[1], value[2])
                # Default to first entry if no specific match
                first_value = next(iter(console_info.values()))
                emulator_name = first_value[1].split('/')[0]
                emulator_path = emulator_paths.get(emulator_name, '')
                return (first_value[0], emulator_path or first_value[1], first_value[2])
            else:
                emulator_name = console_info[1].split('/')[0]
                emulator_path = emulator_paths.get(emulator_name, '')
                return (console_info[0], emulator_path or console_info[1], console_info[2])

    # Default fallback
    return ('PC', 'Unknown', 'Unknown')

def scan_directory(directory):
    """
    Scan directory for game save files
    Returns list of dictionaries containing save file information
    """
    save_files = []
    ignore_dirs, ignore_files = load_ignore_list()
    
    # Common save file extensions
    save_extensions = {'.sav', '.srm', '.mcr', '.mc', '.mem', '.gci', 
                      '.sram', '.dsv', '.duc', '.nps', '.vms', '.sav2',
                      '.dat', '.bin', '.nv'}

    for root, dirs, files in os.walk(directory):
        # Remove ignored directories
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        
        for file in files:
            # Skip ignored files
            if file in ignore_files:
                continue
                
            if Path(file).suffix.lower() in save_extensions:
                file_path = os.path.join(root, file)
                
                # Get file modification time
                mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                # Extract game name from file name
                game_name = Path(file).stem
                # Clean up game name - remove common suffixes and patterns
                game_name = re.sub(r'[\[(].*?[\])]', '', game_name)  # Remove bracketed content
                game_name = re.sub(r'[._-]', ' ', game_name).strip()  # Replace separators with spaces
                
                # Detect console type and emulator
                console_type, emulator, hardware_type = detect_console_type(file_path)
                
                save_info = {
                    'console_type': console_type,
                    'game_name': game_name,
                    'save_path': file_path,
                    'date_modified': mod_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'emulator': emulator,
                    'hardware_type': hardware_type
                }
                
                save_files.append(save_info)
    
    return save_files

class ScannerThread(QThread):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)
    
    def __init__(self, directory):
        super().__init__()
        self.directory = directory
    
    def run(self):
        try:
            self.progress_signal.emit("Starting scan...")
            results = scan_directory(self.directory)
            self.progress_signal.emit(f"Found {len(results)} save files")
            self.finished_signal.emit(results)
        except Exception as e:
            self.error_signal.emit(str(e))

class ScanningWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scanning Directory")
        self.setModal(True)
        
        # Create layout
        layout = QVBoxLayout()
        
        # Add directory selection button
        self.select_button = QPushButton("Select Directory")
        self.select_button.clicked.connect(self.select_directory)
        layout.addWidget(self.select_button)
        
        # Add status label
        self.status_label = QLabel("Select a directory to scan")
        layout.addWidget(self.status_label)
        
        # Add progress bar
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        self.setLayout(layout)
        
        self.scan_results = []
        
    def select_directory(self):
        try:
            directory = QFileDialog.getExistingDirectory(self, "Select Directory")
            if directory:
                self.select_button.setEnabled(False)
                self.progress_bar.setRange(0, 0)  # Indeterminate progress
                
                # Create and start scanner thread
                self.scanner = ScannerThread(directory)
                self.scanner.progress_signal.connect(self.update_status)
                self.scanner.finished_signal.connect(self.handle_results)
                self.scanner.error_signal.connect(self.handle_error)
                self.scanner.start()
        except Exception as e:
            self.handle_error(f"Error selecting directory: {str(e)}")
    
    def update_status(self, message):
        self.status_label.setText(message)
    
    def handle_error(self, error_message):
        self.select_button.setEnabled(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        QMessageBox.critical(self, "Error", error_message)
    
    def handle_results(self, results):
        try:
            self.scan_results = results
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)
            self.accept()
        except Exception as e:
            self.handle_error(f"Error processing results: {str(e)}")
            
    def get_results(self):
        return self.scan_results
