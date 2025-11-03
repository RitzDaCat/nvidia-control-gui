#!/usr/bin/env python3

import sys
import subprocess
import json
import os
import logging
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QPushButton, QSpinBox, QGroupBox, QTabWidget,
    QTextEdit, QComboBox, QCheckBox, QMessageBox, QGridLayout,
    QSystemTrayIcon, QMenu, QButtonGroup, QRadioButton
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QSettings, QShortcut
from PyQt6.QtGui import QIcon, QAction, QFont, QPalette, QColor, QKeySequence

# Constants
MIN_CLOCK_MHZ = 210
MAX_CLOCK_MHZ = 3200
DEFAULT_MIN_CLOCK = 210
DEFAULT_MAX_CLOCK = 2850
CLOCK_STEP = 15

MIN_POWER_W = 100
MAX_POWER_W = 600
DEFAULT_POWER_W = 450
POWER_STEP = 50

MIN_MEM_OFFSET_MHZ = -2000
MAX_MEM_OFFSET_MHZ = 2000
MEM_OFFSET_STEP = 50

POLLING_INTERVAL_MS = 2000
MONITOR_REFRESH_INTERVAL_MS = 5000

CONFIG_DIR = os.path.expanduser("~/.config/nvidia-control")
LOCK_STATUS_FILE = os.path.join(CONFIG_DIR, "clock_lock_status.txt")  # Legacy, will be replaced with per-GPU files

# Security: Validate config directory path
_CONFIG_DIR_PATH = Path(CONFIG_DIR).resolve()
_HOME_PATH = Path.home().resolve()

def validate_config_path(file_path: str) -> bool:
    """Validate that a config file path is within the config directory."""
    try:
        full_path = Path(file_path).resolve()
        # Ensure path is within config directory
        return _CONFIG_DIR_PATH in full_path.parents or full_path.parent == _CONFIG_DIR_PATH
    except (ValueError, OSError):
        return False

def sanitize_gpu_id(gpu_id: Any) -> Optional[int]:
    """Validate and sanitize GPU ID."""
    try:
        gpu_id_int = int(gpu_id)
        # Reasonable range for GPU IDs (0-127 should be enough)
        if 0 <= gpu_id_int <= 127:
            return gpu_id_int
        logger.warning(f"GPU ID out of range: {gpu_id_int}")
        return None
    except (ValueError, TypeError):
        logger.warning(f"Invalid GPU ID type: {type(gpu_id)}")
        return None

def validate_json_structure(data: Dict[str, Any], required_keys: Optional[list] = None) -> Tuple[bool, str]:
    """Validate JSON structure for settings files."""
    if not isinstance(data, dict):
        return False, "Data must be a dictionary"
    
    if required_keys:
        for key in required_keys:
            if key not in data:
                return False, f"Missing required key: {key}"
    
    # Validate data types
    if "gpu_id" in data:
        if not isinstance(data["gpu_id"], int):
            return False, "gpu_id must be an integer"
        if not sanitize_gpu_id(data["gpu_id"]):
            return False, "gpu_id out of valid range"
    
    if "power_limit" in data and data["power_limit"] is not None:
        if not isinstance(data["power_limit"], (int, float)):
            return False, "power_limit must be a number"
        if data["power_limit"] < 0 or data["power_limit"] > 1000:
            return False, "power_limit out of valid range"
    
    if "clock_lock" in data and data["clock_lock"] is not None:
        if not isinstance(data["clock_lock"], dict):
            return False, "clock_lock must be a dictionary"
        if "min" in data["clock_lock"] and data["clock_lock"]["min"] is not None:
            if not isinstance(data["clock_lock"]["min"], int):
                return False, "clock_lock.min must be an integer"
        if "max" in data["clock_lock"] and data["clock_lock"]["max"] is not None:
            if not isinstance(data["clock_lock"]["max"], int):
                return False, "clock_lock.max must be an integer"
    
    return True, ""

# Profile constants
PROFILE_GAMING = {
    "min_clock": 2400,
    "max_clock": 2850,
    "power_limit": 450,
    "perf_mode": "Prefer Maximum Performance"
}

PROFILE_BALANCED = {
    "min_clock": None,  # Reset to default
    "max_clock": None,
    "power_limit": 350,
    "perf_mode": "Adaptive"
}

PROFILE_QUIET = {
    "min_clock": 210,
    "max_clock": 1500,
    "power_limit": 250,
    "perf_mode": "Adaptive"
}

PROFILE_MINING = {
    "min_clock": 1200,
    "max_clock": 1400,
    "mem_offset": 1000,
    "power_limit": 300,
    "perf_mode": "Adaptive"
}

# Setup logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class GPUInfo:
    """
    Data class representing GPU information and current state.
    
    Attributes:
        gpu_id: GPU identifier (0, 1, 2, etc.)
        name: GPU model name (e.g., "NVIDIA GeForce RTX 4090")
        uuid: GPU UUID for identification
        current_clock: Current graphics clock speed in MHz
        max_clock: Maximum supported graphics clock in MHz
        memory_clock: Current memory clock speed in MHz
        max_memory_clock: Maximum supported memory clock in MHz
        power_draw: Current power draw in watts
        power_limit: Current power limit setting in watts
        max_power_limit: Maximum allowed power limit in watts
        temperature: Current GPU temperature in Celsius
        temperature_threshold: GPU shutdown temperature threshold in Celsius
        fan_speed: Current fan speed as percentage (0-100)
        fan_control_mode: Fan control mode ("auto" or "manual")
        utilization_gpu: GPU utilization percentage (0-100)
        utilization_memory: Memory utilization percentage (0-100)
        performance_state: Current performance state (P0, P1, P2, etc.)
        persistence_mode: Whether persistence mode is enabled
        clock_lock_status: Clock lock status ("locked" or "default")
        min_clock_lock: Minimum locked clock speed in MHz (if locked)
        max_clock_lock: Maximum locked clock speed in MHz (if locked)
    """
    gpu_id: int
    name: str
    uuid: str
    current_clock: int
    max_clock: int
    memory_clock: int
    max_memory_clock: int
    power_draw: float
    power_limit: int
    max_power_limit: int
    temperature: int
    temperature_threshold: int = 0  # GPU shutdown threshold
    fan_speed: int
    fan_control_mode: str = "auto"  # auto, manual
    utilization_gpu: int = 0
    utilization_memory: int = 0
    performance_state: str
    persistence_mode: bool
    clock_lock_status: str = "default"
    min_clock_lock: int = 0
    max_clock_lock: int = 0

class NvidiaWorker(QThread):
    """
    Worker thread for polling GPU information in the background.
    
    This thread runs continuously to update GPU statistics without blocking
    the GUI. It emits signals when new data is available or errors occur.
    
    Signals:
        data_updated: Emitted when new GPU info is available (GPUInfo)
        error_occurred: Emitted when an error occurs (str error message)
    """
    data_updated = pyqtSignal(GPUInfo)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, gpu_id: int = 0):
        """
        Initialize the worker thread.
        
        Args:
            gpu_id: The GPU ID to monitor (default: 0)
        """
        super().__init__()
        self.running = True
        self.gpu_id = gpu_id
    
    @staticmethod
    def detect_gpus() -> list:
        """
        Detect all available NVIDIA GPUs on the system.
        
        Returns:
            List of dictionaries containing GPU information:
            [{"id": 0, "name": "NVIDIA GeForce RTX 4090", "uuid": "GPU-..."}, ...]
            
        Returns empty list if no GPUs found or error occurs.
        """
        try:
            result = subprocess.run(
                ["nvidia-smi", "--list-gpus"],
                capture_output=True, text=True, check=True, timeout=5
            )
            gpus = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    # Format: "GPU 0: NVIDIA GeForce RTX 4090 (UUID: GPU-...)"
                    parts = line.split(':')
                    if len(parts) >= 2:
                        gpu_id = int(parts[0].split()[1])
                        name = parts[1].split('(')[0].strip()
                        uuid = parts[1].split('UUID:')[1].split(')')[0].strip() if 'UUID:' in parts[1] else ""
                        gpus.append({"id": gpu_id, "name": name, "uuid": uuid})
            return gpus
        except Exception as e:
            logger.error(f"Error detecting GPUs: {e}")
            return []
    
    def run(self):
        """
        Main worker thread loop.
        
        Continuously polls GPU information at the configured interval
        and emits data_updated signal when new info is available.
        """
        while self.running:
            try:
                gpu_info = self.get_gpu_info()
                if gpu_info:
                    self.data_updated.emit(gpu_info)
            except Exception as e:
                logger.error(f"Error in worker thread: {e}", exc_info=True)
                self.error_occurred.emit(str(e))
            self.msleep(POLLING_INTERVAL_MS)
    
    def get_gpu_info(self) -> Optional[GPUInfo]:
        """
        Query current GPU information using nvidia-smi.
        
        Returns:
            GPUInfo object with current GPU state, or None if query fails.
            
        This method makes multiple nvidia-smi calls to gather:
        - GPU name and UUID
        - Clock speeds (graphics and memory)
        - Power information (draw, limit, max limit)
        - Temperature and fan speed
        - Utilization (GPU and memory)
        - Performance state and persistence mode
        - Clock lock status from saved configuration
        """
        try:
            # Get GPU name and UUID for specific GPU
            result = subprocess.run(
                ["nvidia-smi", "-i", str(self.gpu_id), "--query-gpu=name,uuid", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, check=True, timeout=5
            )
            gpu_data = result.stdout.strip().split(", ")
            if len(gpu_data) != 2:
                logger.error(f"Unexpected GPU name/UUID format: {result.stdout}")
                return None
            name, uuid = gpu_data
            
            # Get clock speeds
            result = subprocess.run(
                ["nvidia-smi", "-i", str(self.gpu_id), "--query-gpu=clocks.current.graphics,clocks.max.graphics,clocks.current.memory,clocks.max.memory",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, check=True, timeout=5
            )
            clocks = result.stdout.strip().split(", ")
            if len(clocks) != 4:
                logger.error(f"Unexpected clock format: {result.stdout}")
                return None
            current_clock = int(clocks[0]) if clocks[0] != "N/A" else 0
            max_clock = int(clocks[1]) if clocks[1] != "N/A" else 0
            memory_clock = int(clocks[2]) if clocks[2] != "N/A" else 0
            max_memory_clock = int(clocks[3]) if clocks[3] != "N/A" else 0
            
            # Get power info
            result = subprocess.run(
                ["nvidia-smi", "-i", str(self.gpu_id), "--query-gpu=power.draw,power.limit,power.max_limit",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, check=True, timeout=5
            )
            power_info = result.stdout.strip().split(", ")
            if len(power_info) != 3:
                logger.error(f"Unexpected power format: {result.stdout}")
                return None
            power_draw = float(power_info[0]) if power_info[0] != "N/A" else 0.0
            power_limit = float(power_info[1]) if power_info[1] != "N/A" else 0
            max_power_limit = float(power_info[2]) if power_info[2] != "N/A" else 0
            
            # Get temperature, fan speed, utilization, and other info
            result = subprocess.run(
                ["nvidia-smi", "-i", str(self.gpu_id), "--query-gpu=temperature.gpu,temperature.threshold,fan.speed,utilization.gpu,utilization.memory,pstate,persistence_mode",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, check=True, timeout=5
            )
            temp_info = result.stdout.strip().split(", ")
            if len(temp_info) != 7:
                logger.error(f"Unexpected temp/fan format: {result.stdout}")
                return None
            temperature = int(temp_info[0]) if temp_info[0] != "N/A" else 0
            temperature_threshold = int(temp_info[1]) if temp_info[1] != "N/A" else 0
            fan_speed = int(temp_info[2]) if temp_info[2] != "N/A" else 0
            utilization_gpu = int(temp_info[3]) if temp_info[3] != "N/A" else 0
            utilization_memory = int(temp_info[4]) if temp_info[4] != "N/A" else 0
            performance_state = temp_info[5] if temp_info[5] != "N/A" else "Unknown"
            persistence_mode = temp_info[6] == "Enabled"
            
            # Check fan control mode (manual vs auto) - requires querying nvidia-settings
            fan_control_mode = "auto"  # Default, will be checked separately
            
            # Check for clock lock status (per-GPU)
            clock_lock_status = "default"
            min_clock_lock = 0
            max_clock_lock = 0
            
            try:
                os.makedirs(CONFIG_DIR, exist_ok=True)
                # Security: Validate GPU ID before constructing path
                sanitized_gpu_id = sanitize_gpu_id(self.gpu_id)
                if sanitized_gpu_id is None:
                    logger.warning(f"Invalid GPU ID for lock file: {self.gpu_id}")
                    sanitized_gpu_id = 0  # Fallback to GPU 0
                
                gpu_lock_file = os.path.join(CONFIG_DIR, f"clock_lock_status_gpu{sanitized_gpu_id}.txt")
                
                # Security: Validate path before accessing
                if not validate_config_path(gpu_lock_file):
                    logger.error(f"Invalid config file path: {gpu_lock_file}")
                    return None
                
                if os.path.exists(gpu_lock_file):
                    with open(gpu_lock_file, 'r') as f:
                        data = f.read().strip()
                        if data and data != "default":
                            parts = data.split(',')
                            if len(parts) == 2:
                                try:
                                    clock_lock_status = "locked"
                                    min_clock_lock = int(parts[0])
                                    max_clock_lock = int(parts[1])
                                    # Validate clock values
                                    if min_clock_lock < MIN_CLOCK_MHZ or max_clock_lock > MAX_CLOCK_MHZ:
                                        logger.warning(f"Clock lock values out of range: {min_clock_lock}-{max_clock_lock}")
                                        clock_lock_status = "default"
                                        min_clock_lock = 0
                                        max_clock_lock = 0
                                except ValueError:
                                    logger.warning(f"Invalid clock lock data: {data}")
            except (OSError, IOError, ValueError) as e:
                logger.warning(f"Error reading clock lock status: {e}")
            
            return GPUInfo(
                gpu_id=self.gpu_id,
                name=name,
                uuid=uuid,
                current_clock=current_clock,
                max_clock=max_clock,
                memory_clock=memory_clock,
                max_memory_clock=max_memory_clock,
                power_draw=power_draw,
                power_limit=int(power_limit),
                max_power_limit=int(max_power_limit),
                temperature=temperature,
                temperature_threshold=temperature_threshold,
                fan_speed=fan_speed,
                fan_control_mode=fan_control_mode,
                utilization_gpu=utilization_gpu,
                utilization_memory=utilization_memory,
                performance_state=performance_state,
                persistence_mode=persistence_mode,
                clock_lock_status=clock_lock_status,
                min_clock_lock=min_clock_lock,
                max_clock_lock=max_clock_lock
            )
        except subprocess.TimeoutExpired:
            logger.error("nvidia-smi command timed out")
            return None
        except subprocess.CalledProcessError as e:
            logger.error(f"nvidia-smi command failed: {e.stderr}")
            return None
        except (ValueError, IndexError) as e:
            logger.error(f"Error parsing GPU info: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting GPU info: {e}", exc_info=True)
            return None
    
    def get_supported_clocks(self) -> Optional[list]:
        """Query GPU supported clock frequencies."""
        try:
            result = subprocess.run(
                ["nvidia-smi", "-i", str(self.gpu_id), "-q", "-d", "SUPPORTED_CLOCKS"],
                capture_output=True, text=True, check=True, timeout=10
            )
            # Parse supported clocks from output
            # Format: Graphics clocks and Memory clocks are listed separately
            supported_graphics = []
            for line in result.stdout.split('\n'):
                if 'Graphics' in line and 'MHz' in line:
                    try:
                        clock = int(line.split()[2])
                        supported_graphics.append(clock)
                    except (ValueError, IndexError):
                        continue
            return sorted(set(supported_graphics)) if supported_graphics else None
        except Exception as e:
            logger.warning(f"Could not query supported clocks: {e}")
            return None
    
    def get_actual_clock_lock(self) -> Optional[Tuple[int, int]]:
        """Query actual clock lock status from GPU."""
        try:
            result = subprocess.run(
                ["nvidia-smi", "-i", str(self.gpu_id), "-q", "-d", "CLOCK"],
                capture_output=True, text=True, check=True, timeout=5
            )
            # Look for locked clocks in output
            # This is a simplified check - actual parsing depends on nvidia-smi output format
            for line in result.stdout.split('\n'):
                if 'Locked Clocks' in line or 'Graphics' in line and 'Lock' in line:
                    # Try to extract min,max if available
                    # Note: nvidia-smi may not always show locked clocks in query mode
                    pass
            return None
        except Exception as e:
            logger.warning(f"Could not query clock lock status: {e}")
            return None
    
    def stop(self):
        self.running = False

class NvidiaControlGUI(QMainWindow):
    """
    Main application window for NVIDIA GPU Control Panel.
    
    This class manages the GUI, user interactions, and coordinates
    between the worker thread and GPU settings management.
    
    Features:
    - Multi-GPU support with selection dropdown
    - Real-time GPU monitoring via worker thread
    - Clock control (lock/unlock, memory offset)
    - Power management (power limit, persistence mode)
    - Fan control (automatic/manual)
    - Performance mode selection
    - Profile management (gaming, balanced, quiet, mining, custom)
    - Settings persistence across reboots
    - System tray integration
    """
    
    def __init__(self):
        """
        Initialize the NVIDIA Control GUI application.
        
        Sets up UI, detects GPUs, starts worker thread, configures
        system tray, loads settings, and restores previous state.
        """
        super().__init__()
        self.settings = QSettings("NvidiaControl", "Settings")
        self.gpu_info = None
        self.supported_clocks = None
        self.previous_settings = {}  # For rollback
        self.available_gpus = []
        self.current_gpu_id = 0
        self.coolbits_enabled = None  # Cache Coolbits status
        self.init_ui()
        self.detect_available_gpus()
        self.setup_worker()
        self.setup_tray()
        self.load_settings()
        # Restore clock locks on startup if enabled
        QTimer.singleShot(2000, self.restore_clock_locks)
        # Restore all settings on startup if enabled
        QTimer.singleShot(3000, self.restore_all_settings)
        # Check Coolbits status
        QTimer.singleShot(1000, self.check_coolbits)
        
    def init_ui(self):
        """
        Initialize and build the user interface.
        
        Creates all tabs, widgets, and layouts for:
        - Clock Control
        - Power Management
        - Fan Control
        - Profiles
        - Monitoring
        
        Also sets up dark theme styling and menu bar.
        """
        self.setWindowTitle("NVIDIA GPU Control Panel")
        self.setGeometry(100, 100, 900, 700)
        
        # Set dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QGroupBox {
                border: 1px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #555;
                height: 8px;
                background: #404040;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #76b900;
                border: 1px solid #555;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QPushButton {
                background-color: #404040;
                border: 1px solid #555;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #505050;
            }
            QPushButton:pressed {
                background-color: #76b900;
            }
            QSpinBox, QComboBox {
                background-color: #404040;
                border: 1px solid #555;
                padding: 5px;
                border-radius: 3px;
            }
            QTabWidget::pane {
                border: 1px solid #555;
                background-color: #2b2b2b;
            }
            QTabBar::tab {
                background-color: #404040;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #76b900;
            }
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Header with GPU info
        header_group = QGroupBox("GPU Information")
        header_layout = QGridLayout()
        
        # GPU selector (if multiple GPUs)
        self.gpu_selector_label = QLabel("GPU:")
        self.gpu_selector_combo = QComboBox()
        self.gpu_selector_combo.setToolTip("Select which GPU to configure. Only visible when multiple GPUs are detected.")
        self.gpu_selector_combo.currentIndexChanged.connect(self.on_gpu_changed)
        header_layout.addWidget(self.gpu_selector_label, 0, 0)
        header_layout.addWidget(self.gpu_selector_combo, 0, 1)
        
        self.gpu_name_label = QLabel("GPU: Detecting...")
        self.gpu_name_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.temp_label = QLabel("Temperature: --°C")
        self.power_label = QLabel("Power Draw: -- W")
        self.pstate_label = QLabel("P-State: --")
        self.fan_label = QLabel("Fan Speed: --%")
        self.util_label = QLabel("GPU Util: --%")
        
        header_layout.addWidget(self.gpu_name_label, 1, 0, 1, 2)
        header_layout.addWidget(self.temp_label, 2, 0)
        header_layout.addWidget(self.power_label, 2, 1)
        header_layout.addWidget(self.pstate_label, 3, 0)
        header_layout.addWidget(self.fan_label, 3, 1)
        header_layout.addWidget(self.util_label, 4, 0)
        
        header_group.setLayout(header_layout)
        main_layout.addWidget(header_group)
        
        # Tab widget for different control sections
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Clock Control Tab
        clock_tab = QWidget()
        clock_layout = QVBoxLayout(clock_tab)
        
        # Real-time Monitoring Section
        monitor_group = QGroupBox("Real-time Monitoring")
        monitor_layout = QGridLayout()
        
        monitor_layout.addWidget(QLabel("Current Clock:"), 0, 0)
        self.current_clock_label = QLabel("-- MHz")
        monitor_layout.addWidget(self.current_clock_label, 0, 1)
        
        monitor_layout.addWidget(QLabel("Current P-State:"), 0, 2)
        self.current_pstate_label = QLabel("--")
        monitor_layout.addWidget(self.current_pstate_label, 0, 3)
        
        # Polling control
        self.polling_check = QCheckBox("Enable Auto-Refresh (2s)")
        self.polling_check.setChecked(True)
        self.polling_check.setToolTip(
            "Automatically refresh GPU information every 2 seconds.\n"
            "Disable to reduce CPU usage or if experiencing performance issues."
        )
        self.polling_check.stateChanged.connect(self.toggle_polling)
        monitor_layout.addWidget(self.polling_check, 1, 0, 1, 2)
        
        self.refresh_now_btn = QPushButton("Refresh Now")
        self.refresh_now_btn.setToolTip(
            "Manually refresh GPU information immediately.\n\n"
            "Keyboard shortcut: F5"
        )
        self.refresh_now_btn.clicked.connect(self.refresh_gpu_info)
        monitor_layout.addWidget(self.refresh_now_btn, 1, 2, 1, 2)
        
        monitor_group.setLayout(monitor_layout)
        clock_layout.addWidget(monitor_group)
        
        # Clock Lock Control
        lock_group = QGroupBox("Clock Control")
        lock_layout = QGridLayout()
        
        # Status indicator
        self.clock_status_label = QLabel("Status: Checking...")
        self.clock_status_label.setStyleSheet("font-weight: bold;")
        lock_layout.addWidget(self.clock_status_label, 0, 0, 1, 4)
        
        lock_layout.addWidget(QLabel("Minimum Clock:"), 1, 0)
        self.min_clock_spin = QSpinBox()
        self.min_clock_spin.setRange(MIN_CLOCK_MHZ, MAX_CLOCK_MHZ)
        self.min_clock_spin.setSuffix(" MHz")
        self.min_clock_spin.setSingleStep(CLOCK_STEP)
        self.min_clock_spin.setValue(DEFAULT_MIN_CLOCK)
        self.min_clock_spin.setToolTip(
            f"Set the minimum GPU core clock speed.\n"
            f"Range: {MIN_CLOCK_MHZ}-{MAX_CLOCK_MHZ} MHz\n"
            f"Step: {CLOCK_STEP} MHz\n\n"
            f"Locking clocks prevents the GPU from downclocking, providing consistent performance."
        )
        lock_layout.addWidget(self.min_clock_spin, 1, 1)
        
        lock_layout.addWidget(QLabel("Maximum Clock:"), 1, 2)
        self.max_clock_spin = QSpinBox()
        self.max_clock_spin.setRange(MIN_CLOCK_MHZ, MAX_CLOCK_MHZ)
        self.max_clock_spin.setSuffix(" MHz")
        self.max_clock_spin.setSingleStep(CLOCK_STEP)
        self.max_clock_spin.setValue(DEFAULT_MAX_CLOCK)
        self.max_clock_spin.setToolTip(
            f"Set the maximum GPU core clock speed.\n"
            f"Range: {MIN_CLOCK_MHZ}-{MAX_CLOCK_MHZ} MHz\n"
            f"Step: {CLOCK_STEP} MHz\n\n"
            f"The GPU will not exceed this clock speed when locked."
        )
        lock_layout.addWidget(self.max_clock_spin, 1, 3)
        
        self.lock_clocks_btn = QPushButton("Apply Clock Settings")
        self.lock_clocks_btn.setToolTip(
            "Apply the clock lock settings to the GPU.\n"
            "This will prevent the GPU from changing clock speeds.\n\n"
            "Keyboard shortcut: Ctrl+L"
        )
        self.lock_clocks_btn.clicked.connect(self.apply_clock_lock)
        lock_layout.addWidget(self.lock_clocks_btn, 2, 0, 1, 2)
        
        self.reset_clocks_btn = QPushButton("Reset to Default")
        self.reset_clocks_btn.setToolTip(
            "Reset clock locks and allow the GPU to manage clocks automatically.\n\n"
            "Keyboard shortcut: Ctrl+R"
        )
        self.reset_clocks_btn.clicked.connect(self.reset_clocks)
        lock_layout.addWidget(self.reset_clocks_btn, 2, 2, 1, 2)
        
        lock_group.setLayout(lock_layout)
        clock_layout.addWidget(lock_group)
        
        # Memory Clock Control
        mem_group = QGroupBox("Memory Clock Control")
        mem_layout = QGridLayout()
        
        mem_layout.addWidget(QLabel("Current Memory Clock:"), 0, 0)
        self.current_mem_label = QLabel("-- MHz")
        mem_layout.addWidget(self.current_mem_label, 0, 1)
        
        mem_layout.addWidget(QLabel("Memory Clock Offset:"), 1, 0)
        self.mem_offset_spin = QSpinBox()
        self.mem_offset_spin.setRange(MIN_MEM_OFFSET_MHZ, MAX_MEM_OFFSET_MHZ)
        self.mem_offset_spin.setSuffix(" MHz")
        self.mem_offset_spin.setSingleStep(MEM_OFFSET_STEP)
        self.mem_offset_spin.setToolTip(
            f"Adjust memory clock speed offset.\n"
            f"Range: {MIN_MEM_OFFSET_MHZ} to {MAX_MEM_OFFSET_MHZ} MHz\n"
            f"Step: {MEM_OFFSET_STEP} MHz\n\n"
            f"Positive values increase memory speed (may improve performance).\n"
            f"Negative values decrease memory speed (may reduce power/heat).\n\n"
            f"Note: Requires Coolbits to be enabled in X config."
        )
        mem_layout.addWidget(self.mem_offset_spin, 1, 1)
        
        self.apply_mem_btn = QPushButton("Apply Memory Offset")
        self.apply_mem_btn.setToolTip(
            "Apply the memory clock offset to the GPU.\n"
            "This adjusts the memory clock speed relative to the default.\n\n"
            "Note: Requires Coolbits and nvidia-settings."
        )
        self.apply_mem_btn.clicked.connect(self.apply_memory_offset)
        mem_layout.addWidget(self.apply_mem_btn, 2, 0, 1, 2)
        
        mem_group.setLayout(mem_layout)
        clock_layout.addWidget(mem_group)
        
        clock_layout.addStretch()
        self.tabs.addTab(clock_tab, "Clock Control")
        
        # Power Control Tab
        power_tab = QWidget()
        power_layout = QVBoxLayout(power_tab)
        
        power_group = QGroupBox("Power Management")
        power_grid = QGridLayout()
        
        power_grid.addWidget(QLabel("Current Power Limit:"), 0, 0)
        self.current_power_label = QLabel("-- W")
        power_grid.addWidget(self.current_power_label, 0, 1)
        
        power_grid.addWidget(QLabel("Power Limit:"), 1, 0)
        self.power_limit_slider = QSlider(Qt.Orientation.Horizontal)
        self.power_limit_slider.setRange(MIN_POWER_W, MAX_POWER_W)
        self.power_limit_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.power_limit_slider.setTickInterval(POWER_STEP)
        self.power_limit_slider.setToolTip(
            f"Set the maximum power consumption limit for the GPU.\n"
            f"Range: {MIN_POWER_W}-{MAX_POWER_W}W (varies by GPU model)\n"
            f"Step: {POWER_STEP}W\n\n"
            f"Lower values reduce power consumption and heat output.\n"
            f"Higher values allow better performance but increase power draw.\n\n"
            f"The slider range will adjust based on your GPU's capabilities."
        )
        power_grid.addWidget(self.power_limit_slider, 1, 1)
        
        self.power_limit_value = QLabel("-- W")
        power_grid.addWidget(self.power_limit_value, 1, 2)
        
        self.power_limit_slider.valueChanged.connect(
            lambda v: self.power_limit_value.setText(f"{v} W")
        )
        
        self.apply_power_btn = QPushButton("Apply Power Limit")
        self.apply_power_btn.setToolTip(
            "Apply the selected power limit to the GPU.\n"
            "This will cap the maximum power consumption.\n\n"
            "Note: The actual limit may be slightly different due to GPU hardware constraints."
        )
        self.apply_power_btn.clicked.connect(self.apply_power_limit)
        power_grid.addWidget(self.apply_power_btn, 2, 0, 1, 3)
        
        # Persistence Mode
        self.persistence_check = QCheckBox("Enable Persistence Mode")
        self.persistence_check.setToolTip(
            "Keep the GPU initialized even when no applications are using it.\n\n"
            "Benefits:\n"
            "- Faster response when starting GPU applications\n"
            "- Reduced latency for first GPU command\n\n"
            "Drawbacks:\n"
            "- Slightly higher idle power consumption\n"
            "- GPU remains in a ready state at all times"
        )
        self.persistence_check.stateChanged.connect(self.toggle_persistence_mode)
        power_grid.addWidget(self.persistence_check, 3, 0, 1, 3)
        
        power_group.setLayout(power_grid)
        power_layout.addWidget(power_group)
        
        # Performance Mode
        perf_group = QGroupBox("Performance Mode")
        perf_layout = QVBoxLayout()
        
        self.perf_mode_combo = QComboBox()
        self.perf_mode_combo.addItems(["Adaptive", "Prefer Maximum Performance", "Auto"])
        self.perf_mode_combo.setToolTip(
            "Select GPU performance management mode:\n\n"
            "Adaptive: GPU adjusts performance based on workload\n"
            "Prefer Maximum Performance: GPU stays at maximum performance\n"
            "Auto: Let the driver decide automatically"
        )
        perf_layout.addWidget(self.perf_mode_combo)
        
        self.apply_perf_btn = QPushButton("Apply Performance Mode")
        self.apply_perf_btn.setToolTip(
            "Apply the selected performance mode to the GPU.\n"
            "This affects how the GPU manages clock speeds dynamically."
        )
        self.apply_perf_btn.clicked.connect(self.apply_performance_mode)
        perf_layout.addWidget(self.apply_perf_btn)
        
        perf_group.setLayout(perf_layout)
        power_layout.addWidget(perf_group)
        
        # Temperature Control
        temp_group = QGroupBox("Temperature Control")
        temp_layout = QGridLayout()
        
        temp_layout.addWidget(QLabel("Current Temperature:"), 0, 0)
        self.current_temp_label = QLabel("--°C")
        temp_layout.addWidget(self.current_temp_label, 0, 1)
        
        temp_layout.addWidget(QLabel("Shutdown Threshold:"), 1, 0)
        self.temp_threshold_label = QLabel("--°C")
        temp_layout.addWidget(self.temp_threshold_label, 1, 1)
        
        temp_group.setLayout(temp_layout)
        power_layout.addWidget(temp_group)
        
        power_layout.addStretch()
        self.tabs.addTab(power_tab, "Power Management")
        
        # Fan Control Tab
        fan_tab = QWidget()
        fan_layout = QVBoxLayout(fan_tab)
        
        fan_info_group = QGroupBox("Fan Information")
        fan_info_layout = QGridLayout()
        
        fan_info_layout.addWidget(QLabel("Current Fan Speed:"), 0, 0)
        self.current_fan_label = QLabel("--%")
        fan_info_layout.addWidget(self.current_fan_label, 0, 1)
        
        fan_info_layout.addWidget(QLabel("Control Mode:"), 0, 2)
        self.fan_mode_label = QLabel("Auto")
        fan_info_layout.addWidget(self.fan_mode_label, 0, 3)
        
        fan_info_group.setLayout(fan_info_layout)
        fan_layout.addWidget(fan_info_group)
        
        fan_control_group = QGroupBox("Fan Control")
        fan_control_layout = QVBoxLayout()
        
        # Use button group for exclusive selection
        self.fan_mode_group = QButtonGroup()
        self.fan_auto_radio = QRadioButton("Automatic Fan Control")
        self.fan_auto_radio.setChecked(True)
        self.fan_auto_radio.setToolTip(
            "Let the GPU automatically control fan speed based on temperature.\n"
            "This is the default and recommended mode for most users."
        )
        self.fan_mode_group.addButton(self.fan_auto_radio, 0)
        self.fan_auto_radio.toggled.connect(self.toggle_fan_mode)
        fan_control_layout.addWidget(self.fan_auto_radio)
        
        self.fan_manual_radio = QRadioButton("Manual Fan Control")
        self.fan_manual_radio.setToolTip(
            "Manually set a fixed fan speed percentage.\n\n"
            "Warning: Requires Coolbits to be enabled.\n"
            "Very low fan speeds may cause overheating!\n\n"
            "Use with caution and monitor temperatures."
        )
        self.fan_mode_group.addButton(self.fan_manual_radio, 1)
        self.fan_manual_radio.toggled.connect(self.toggle_fan_mode)
        fan_control_layout.addWidget(self.fan_manual_radio)
        
        manual_layout = QHBoxLayout()
        manual_layout.addWidget(QLabel("Fan Speed:"))
        self.fan_speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.fan_speed_slider.setRange(0, 100)
        self.fan_speed_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.fan_speed_slider.setTickInterval(10)
        self.fan_speed_slider.setEnabled(False)
        self.fan_speed_slider.setToolTip(
            "Set fan speed as a percentage (0-100%).\n\n"
            "Warning: Very low speeds (<20%) may cause overheating!\n"
            "Recommended: 30-70% for balanced cooling and noise.\n\n"
            "Use arrow keys or mouse to adjust."
        )
        self.fan_speed_slider.valueChanged.connect(
            lambda v: self.fan_speed_value.setText(f"{v}%")
        )
        manual_layout.addWidget(self.fan_speed_slider)
        
        self.fan_speed_value = QLabel("0%")
        manual_layout.addWidget(self.fan_speed_value)
        
        self.apply_fan_btn = QPushButton("Apply Fan Speed")
        self.apply_fan_btn.setEnabled(False)
        self.apply_fan_btn.setToolTip(
            "Apply the selected fan speed to the GPU.\n\n"
            "Warning: Ensure adequate cooling before applying low speeds."
        )
        self.apply_fan_btn.clicked.connect(self.apply_fan_speed)
        manual_layout.addWidget(self.apply_fan_btn)
        
        fan_control_layout.addLayout(manual_layout)
        
        # Coolbits status
        self.coolbits_status_label = QLabel("Coolbits: Checking...")
        self.coolbits_status_label.setStyleSheet("font-weight: bold;")
        fan_control_layout.addWidget(self.coolbits_status_label)
        
        fan_control_group.setLayout(fan_control_layout)
        fan_layout.addWidget(fan_control_group)
        
        # Fan Curve (Temperature-based)
        fan_curve_group = QGroupBox("Fan Curve")
        fan_curve_layout = QVBoxLayout()
        
        fan_curve_layout.addWidget(QLabel("Note: Fan curve requires Coolbits and will be implemented in a future update."))
        
        fan_curve_group.setLayout(fan_curve_layout)
        fan_layout.addWidget(fan_curve_group)
        
        fan_layout.addStretch()
        self.tabs.addTab(fan_tab, "Fan Control")
        
        # Profiles Tab
        profiles_tab = QWidget()
        profiles_layout = QVBoxLayout(profiles_tab)
        
        profiles_group = QGroupBox("Quick Profiles")
        profiles_grid = QGridLayout()
        
        self.gaming_btn = QPushButton("Gaming Profile\n(Max Performance)")
        self.gaming_btn.setToolTip(
            "Apply maximum performance settings:\n"
            f"- Clock Lock: {PROFILE_GAMING['min_clock']}-{PROFILE_GAMING['max_clock']} MHz\n"
            f"- Power Limit: {PROFILE_GAMING['power_limit']}W\n"
            f"- Performance Mode: {PROFILE_GAMING['perf_mode']}\n\n"
            "Ideal for gaming and demanding applications."
        )
        self.gaming_btn.clicked.connect(self.apply_gaming_profile)
        profiles_grid.addWidget(self.gaming_btn, 0, 0)
        
        self.balanced_btn = QPushButton("Balanced Profile\n(Moderate)")
        self.balanced_btn.setToolTip(
            "Apply balanced settings:\n"
            "- Clock Lock: Disabled (GPU manages clocks)\n"
            "- Power Limit: Default\n"
            "- Performance Mode: Adaptive\n\n"
            "Good for general use and multitasking."
        )
        self.balanced_btn.clicked.connect(self.apply_balanced_profile)
        profiles_grid.addWidget(self.balanced_btn, 0, 1)
        
        self.quiet_btn = QPushButton("Quiet Profile\n(Low Power)")
        self.quiet_btn.setToolTip(
            "Apply quiet/low power settings:\n"
            f"- Clock Lock: {PROFILE_QUIET['min_clock']}-{PROFILE_QUIET['max_clock']} MHz\n"
            f"- Power Limit: {PROFILE_QUIET['power_limit']}W\n"
            f"- Performance Mode: {PROFILE_QUIET['perf_mode']}\n\n"
            "Reduces power consumption and heat output for quieter operation."
        )
        self.quiet_btn.clicked.connect(self.apply_quiet_profile)
        profiles_grid.addWidget(self.quiet_btn, 1, 0)
        
        self.mining_btn = QPushButton("Mining Profile\n(Optimized)")
        self.mining_btn.setToolTip(
            "Apply mining-optimized settings:\n"
            f"- Clock Lock: {PROFILE_MINING['min_clock']}-{PROFILE_MINING['max_clock']} MHz\n"
            f"- Power Limit: {PROFILE_MINING['power_limit']}W\n"
            f"- Performance Mode: {PROFILE_MINING['perf_mode']}\n\n"
            "Optimized for cryptocurrency mining workloads."
        )
        self.mining_btn.clicked.connect(self.apply_mining_profile)
        profiles_grid.addWidget(self.mining_btn, 1, 1)
        
        profiles_group.setLayout(profiles_grid)
        profiles_layout.addWidget(profiles_group)
        
        # Custom Profile Save/Load
        custom_group = QGroupBox("Custom Profiles")
        custom_layout = QVBoxLayout()
        
        save_layout = QHBoxLayout()
        self.save_profile_btn = QPushButton("Save Current Settings")
        self.save_profile_btn.setToolTip(
            "Save the current clock, power, and performance settings as a custom profile.\n"
            "You can load this profile later to quickly restore these settings.\n\n"
            "Keyboard shortcut: Ctrl+S"
        )
        self.save_profile_btn.clicked.connect(self.save_custom_profile)
        save_layout.addWidget(self.save_profile_btn)
        
        self.load_profile_btn = QPushButton("Load Saved Profile")
        self.load_profile_btn.setToolTip(
            "Load a previously saved custom profile.\n"
            "This will restore all saved settings (clocks, power limit, performance mode).\n\n"
            "Keyboard shortcut: Ctrl+O"
        )
        self.load_profile_btn.clicked.connect(self.load_custom_profile)
        save_layout.addWidget(self.load_profile_btn)
        
        custom_layout.addLayout(save_layout)
        custom_group.setLayout(custom_layout)
        profiles_layout.addWidget(custom_group)
        
        profiles_layout.addStretch()
        self.tabs.addTab(profiles_tab, "Profiles")
        
        # Monitoring Tab
        monitor_tab = QWidget()
        monitor_layout = QVBoxLayout(monitor_tab)
        
        self.monitor_text = QTextEdit()
        self.monitor_text.setReadOnly(True)
        self.monitor_text.setFont(QFont("Courier", 9))
        monitor_layout.addWidget(self.monitor_text)
        
        monitor_btn_layout = QHBoxLayout()
        self.refresh_monitor_btn = QPushButton("Refresh")
        self.refresh_monitor_btn.clicked.connect(self.refresh_monitoring)
        monitor_btn_layout.addWidget(self.refresh_monitor_btn)
        
        self.auto_refresh_check = QCheckBox("Auto Refresh (5s)")
        self.auto_refresh_check.setToolTip(
            "Automatically refresh the detailed monitoring information every 5 seconds.\n"
            "Disable to reduce CPU usage."
        )
        self.auto_refresh_check.stateChanged.connect(self.toggle_auto_refresh)
        monitor_btn_layout.addWidget(self.auto_refresh_check)
        
        monitor_layout.addLayout(monitor_btn_layout)
        self.tabs.addTab(monitor_tab, "Monitoring")
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
        # Menu bar
        menubar = self.menuBar()
        
        # Settings menu
        settings_menu = menubar.addMenu("Settings")
        
        restore_clocks_action = QAction("Restore Clock Locks on Startup", self)
        restore_clocks_action.setCheckable(True)
        restore_clocks_action.setChecked(self.settings.value("restore_clock_locks", True, type=bool))
        restore_clocks_action.triggered.connect(
            lambda checked: self.settings.setValue("restore_clock_locks", checked)
        )
        settings_menu.addAction(restore_clocks_action)
        
        restore_all_action = QAction("Restore All Settings on Startup", self)
        restore_all_action.setCheckable(True)
        restore_all_action.setChecked(self.settings.value("restore_all_settings", False, type=bool))
        restore_all_action.triggered.connect(
            lambda checked: self.settings.setValue("restore_all_settings", checked)
        )
        settings_menu.addAction(restore_all_action)
        
        settings_menu.addSeparator()
        
        save_settings_action = QAction("Save Current Settings", self)
        save_settings_action.triggered.connect(self.save_all_settings)
        settings_menu.addAction(save_settings_action)
        
        generate_service_action = QAction("Generate Systemd Service", self)
        generate_service_action.triggered.connect(self.generate_systemd_service)
        settings_menu.addAction(generate_service_action)
        
        # Auto-refresh timer for monitoring
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.refresh_monitoring)
        
        # Initialize power limit range from GPU (will be updated when GPU info is available)
        self.power_limit_min = MIN_POWER_W
        self.power_limit_max = MAX_POWER_W
        
        # Setup tooltips and keyboard shortcuts
        self.setup_tooltips()
        self.setup_shortcuts()
    
    def detect_available_gpus(self):
        """Detect all available NVIDIA GPUs."""
        self.available_gpus = NvidiaWorker.detect_gpus()
        if not self.available_gpus:
            # Fallback: assume at least one GPU
            self.available_gpus = [{"id": 0, "name": "NVIDIA GPU", "uuid": ""}]
        
        # Update GPU selector
        self.gpu_selector_combo.clear()
        for gpu in self.available_gpus:
            self.gpu_selector_combo.addItem(f"GPU {gpu['id']}: {gpu['name']}", gpu['id'])
        
        # Hide selector if only one GPU
        if len(self.available_gpus) <= 1:
            self.gpu_selector_label.hide()
            self.gpu_selector_combo.hide()
        else:
            self.gpu_selector_label.show()
            self.gpu_selector_combo.show()
        
        # Set current GPU ID
        if self.available_gpus:
            self.current_gpu_id = self.settings.value("current_gpu_id", 0, type=int)
            if self.current_gpu_id >= len(self.available_gpus):
                self.current_gpu_id = 0
            self.gpu_selector_combo.setCurrentIndex(self.current_gpu_id)
    
    def on_gpu_changed(self, index: int):
        """Handle GPU selection change."""
        if index >= 0 and index < len(self.available_gpus):
            self.current_gpu_id = self.available_gpus[index]['id']
            self.settings.setValue("current_gpu_id", self.current_gpu_id)
            
            # Restart worker with new GPU ID
            if hasattr(self, 'worker'):
                self.worker.stop()
                self.worker.wait()
            
            self.setup_worker()
            self.query_supported_clocks()
    
    def setup_worker(self):
        self.worker = NvidiaWorker(self.current_gpu_id)
        self.worker.data_updated.connect(self.update_gpu_info)
        self.worker.error_occurred.connect(self.handle_error)
        self.worker.start()
        
        # Query supported clocks after GPU info is available
        QTimer.singleShot(3000, self.query_supported_clocks)
    
    def query_supported_clocks(self):
        """Query and cache GPU supported clock frequencies."""
        if self.worker:
            self.supported_clocks = self.worker.get_supported_clocks()
            if self.supported_clocks:
                logger.info(f"Found {len(self.supported_clocks)} supported clock frequencies")
    
    def validate_clock_values(self, min_clock: int, max_clock: int) -> Tuple[bool, str]:
        """
        Validate clock values against constraints and GPU capabilities.
        
        Args:
            min_clock: Minimum clock speed in MHz
            max_clock: Maximum clock speed in MHz
            
        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if values are valid, False otherwise
            - error_message: Empty string if valid, error description if invalid
            
        Validation checks:
            - Range: MIN_CLOCK_MHZ <= clock <= MAX_CLOCK_MHZ
            - Min <= Max
            - Step size: Must be multiple of CLOCK_STEP (15 MHz)
            - GPU capabilities: If supported_clocks available, checks if values are supported
        """
        # Basic range validation
        if min_clock < MIN_CLOCK_MHZ or max_clock > MAX_CLOCK_MHZ:
            return False, f"Clock values must be between {MIN_CLOCK_MHZ} and {MAX_CLOCK_MHZ} MHz"
        
        if min_clock > max_clock:
            return False, "Minimum clock cannot be higher than maximum clock"
        
        # Validate step size (15 MHz typical for NVIDIA GPUs)
        if min_clock % CLOCK_STEP != 0:
            return False, f"Minimum clock must be a multiple of {CLOCK_STEP} MHz"
        if max_clock % CLOCK_STEP != 0:
            return False, f"Maximum clock must be a multiple of {CLOCK_STEP} MHz"
        
        # Validate against GPU capabilities if available
        if self.supported_clocks:
            if min_clock not in self.supported_clocks:
                nearest = min(self.supported_clocks, key=lambda x: abs(x - min_clock))
                return False, f"Minimum clock {min_clock} MHz not supported. Nearest: {nearest} MHz"
            if max_clock not in self.supported_clocks:
                nearest = min(self.supported_clocks, key=lambda x: abs(x - max_clock))
                return False, f"Maximum clock {max_clock} MHz not supported. Nearest: {nearest} MHz"
        
        return True, ""
    
    def restore_clock_locks(self):
        """Restore clock locks from saved settings on startup (for all GPUs)."""
        if not self.settings.value("restore_clock_locks", False, type=bool):
            return
        
        # Restore for all detected GPUs
        for gpu in self.available_gpus:
            try:
                # Security: Validate GPU ID
                gpu_id = gpu.get('id', 0)
                sanitized_gpu_id = sanitize_gpu_id(gpu_id)
                if sanitized_gpu_id is None:
                    logger.warning(f"Skipping invalid GPU ID: {gpu_id}")
                    continue
                
                gpu_lock_file = os.path.join(CONFIG_DIR, f"clock_lock_status_gpu{sanitized_gpu_id}.txt")
                
                # Security: Validate path before reading
                if not validate_config_path(gpu_lock_file):
                    logger.error(f"Invalid config file path: {gpu_lock_file}")
                    continue
                
                if os.path.exists(gpu_lock_file):
                    # Security: Validate file size
                    file_size = os.path.getsize(gpu_lock_file)
                    if file_size > 1024:  # 1KB limit for lock files
                        logger.error(f"Lock file too large: {file_size} bytes")
                        continue
                    
                    with open(gpu_lock_file, 'r') as f:
                        data = f.read().strip()
                        if data and data != "default":
                            parts = data.split(',')
                            if len(parts) == 2:
                                try:
                                    min_clock = int(parts[0])
                                    max_clock = int(parts[1])
                                    
                                    # Security: Validate clock values
                                    if (MIN_CLOCK_MHZ <= min_clock <= MAX_CLOCK_MHZ and
                                        MIN_CLOCK_MHZ <= max_clock <= MAX_CLOCK_MHZ):
                                        # Validate before applying
                                        if self.gpu_info:  # Validate against current GPU info
                                            valid, msg = self.validate_clock_values(min_clock, max_clock)
                                            if valid:
                                                logger.info(f"Restoring clock lock for GPU {sanitized_gpu_id}: {min_clock}-{max_clock} MHz")
                                                self.run_nvidia_command(["nvidia-smi", "-lgc", f"{min_clock},{max_clock}"], 
                                                                       needs_sudo=True, gpu_id=sanitized_gpu_id)
                                            else:
                                                logger.warning(f"Could not restore clock locks for GPU {sanitized_gpu_id}: {msg}")
                                    else:
                                        logger.warning(f"Clock values out of range for GPU {sanitized_gpu_id}: {min_clock}-{max_clock}")
                                except ValueError:
                                    logger.warning(f"Invalid clock lock data for GPU {sanitized_gpu_id}: {data}")
            except (OSError, IOError, ValueError) as e:
                logger.warning(f"Error restoring clock locks for GPU {gpu.get('id', 'unknown')}: {e}")
    
    def setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("System tray is not available")
            return
        
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setToolTip("NVIDIA GPU Control")
        
        # Try to set an icon (fallback to default if not found)
        try:
            # Try common icon paths
            icon_paths = [
                "/usr/share/pixmaps/nvidia-settings.png",
                "/usr/share/icons/hicolor/48x48/apps/nvidia-settings.png",
                "/usr/share/icons/gnome/48x48/apps/nvidia-settings.png"
            ]
            icon_set = False
            for path in icon_paths:
                if os.path.exists(path):
                    self.tray_icon.setIcon(QIcon(path))
                    icon_set = True
                    break
            
            if not icon_set:
                # Use default system icon
                self.tray_icon.setIcon(self.style().standardIcon(
                    self.style().StandardPixmap.SP_ComputerIcon
                ))
        except Exception as e:
            logger.warning(f"Could not set tray icon: {e}")
        
        tray_menu = QMenu()
        
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        hide_action = QAction("Hide", self)
        hide_action.triggered.connect(self.hide)
        tray_menu.addAction(hide_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()
    
    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()
    
    def check_coolbits(self):
        """Check if Coolbits is enabled in X config."""
        try:
            # Try to query a Coolbits-dependent setting
            result = subprocess.run(
                ["nvidia-settings", "-q", "GPUFanControlState"],
                capture_output=True, text=True, timeout=5
            )
            # If command succeeds, Coolbits is likely enabled
            self.coolbits_enabled = result.returncode == 0
            if self.coolbits_enabled:
                self.coolbits_status_label.setText("Coolbits: ✓ Enabled")
                self.coolbits_status_label.setStyleSheet("font-weight: bold; color: #76b900;")
            else:
                self.coolbits_enabled = False
                self.coolbits_status_label.setText("Coolbits: ✗ Not Enabled (Fan control requires Coolbits)")
                self.coolbits_status_label.setStyleSheet("font-weight: bold; color: #ff6b6b;")
        except Exception as e:
            logger.warning(f"Could not check Coolbits: {e}")
            self.coolbits_enabled = False
            self.coolbits_status_label.setText("Coolbits: ✗ Status Unknown")
            self.coolbits_status_label.setStyleSheet("font-weight: bold; color: #ff6b6b;")
    
    def update_gpu_info(self, gpu_info: GPUInfo):
        self.gpu_info = gpu_info
        
        # Update header info with color coding
        self.gpu_name_label.setText(f"GPU {gpu_info.gpu_id}: {gpu_info.name}")
        
        # Temperature color coding
        temp_text = f"Temperature: {gpu_info.temperature}°C"
        if gpu_info.temperature >= 80:
            self.temp_label.setText(temp_text)
            self.temp_label.setStyleSheet("color: #ff6b6b; font-weight: bold;")
        elif gpu_info.temperature >= 70:
            self.temp_label.setText(temp_text)
            self.temp_label.setStyleSheet("color: #ffaa00; font-weight: bold;")
        else:
            self.temp_label.setText(temp_text)
            self.temp_label.setStyleSheet("color: #76b900;")
        
        # Power draw
        self.power_label.setText(f"Power Draw: {gpu_info.power_draw:.1f} W")
        
        # P-State with color
        pstate_text = f"P-State: {gpu_info.performance_state}"
        if "P0" in gpu_info.performance_state or "P1" in gpu_info.performance_state:
            self.pstate_label.setText(pstate_text)
            self.pstate_label.setStyleSheet("color: #76b900; font-weight: bold;")
        elif "P2" in gpu_info.performance_state or "P3" in gpu_info.performance_state:
            self.pstate_label.setText(pstate_text)
            self.pstate_label.setStyleSheet("color: #ffaa00;")
        else:
            self.pstate_label.setText(pstate_text)
            self.pstate_label.setStyleSheet("color: #ffffff;")
        
        # Fan speed with color
        fan_text = f"Fan Speed: {gpu_info.fan_speed}%"
        if gpu_info.fan_speed < 30:
            self.fan_label.setText(fan_text)
            self.fan_label.setStyleSheet("color: #ffaa00;")
        elif gpu_info.fan_speed > 80:
            self.fan_label.setText(fan_text)
            self.fan_label.setStyleSheet("color: #ff6b6b; font-weight: bold;")
        else:
            self.fan_label.setText(fan_text)
            self.fan_label.setStyleSheet("color: #76b900;")
        
        # GPU utilization
        util_text = f"GPU Util: {gpu_info.utilization_gpu}%"
        if gpu_info.utilization_gpu > 80:
            self.util_label.setText(util_text)
            self.util_label.setStyleSheet("color: #76b900; font-weight: bold;")
        elif gpu_info.utilization_gpu > 50:
            self.util_label.setText(util_text)
            self.util_label.setStyleSheet("color: #ffaa00;")
        else:
            self.util_label.setText(util_text)
            self.util_label.setStyleSheet("color: #ffffff;")
        
        # Update temperature labels
        if hasattr(self, 'current_temp_label'):
            self.current_temp_label.setText(f"{gpu_info.temperature}°C")
        if hasattr(self, 'temp_threshold_label'):
            self.temp_threshold_label.setText(f"{gpu_info.temperature_threshold}°C")
        
        # Update fan labels with visual feedback
        if hasattr(self, 'current_fan_label'):
            self.current_fan_label.setText(f"{gpu_info.fan_speed}%")
            # Color code fan speed (green=normal, yellow=low, red=high)
            if gpu_info.fan_speed < 30:
                self.current_fan_label.setStyleSheet("color: #ffaa00; font-weight: bold;")
            elif gpu_info.fan_speed > 80:
                self.current_fan_label.setStyleSheet("color: #ff6b6b; font-weight: bold;")
            else:
                self.current_fan_label.setStyleSheet("color: #76b900;")
        if hasattr(self, 'fan_mode_label'):
            self.fan_mode_label.setText(gpu_info.fan_control_mode.title())
            if gpu_info.fan_control_mode == "manual":
                self.fan_mode_label.setStyleSheet("color: #ffaa00; font-weight: bold;")
            else:
                self.fan_mode_label.setStyleSheet("color: #76b900;")
        
        # Update clock info
        self.current_clock_label.setText(f"{gpu_info.current_clock} MHz")
        self.current_pstate_label.setText(gpu_info.performance_state)
        self.current_mem_label.setText(f"{gpu_info.memory_clock} MHz")
        self.current_power_label.setText(f"{gpu_info.power_limit} W")
        
        # Update power limit slider range if needed
        if gpu_info.max_power_limit > 0:
            self.power_limit_min = max(MIN_POWER_W, int(gpu_info.max_power_limit * 0.3))
            self.power_limit_max = min(MAX_POWER_W, int(gpu_info.max_power_limit * 1.1))
            if self.power_limit_slider.maximum() != self.power_limit_max:
                self.power_limit_slider.setRange(self.power_limit_min, self.power_limit_max)
        
        # Update clock lock status with visual feedback
        if gpu_info.clock_lock_status == "locked":
            self.clock_status_label.setText(f"Status: 🔒 Locked ({gpu_info.min_clock_lock}-{gpu_info.max_clock_lock} MHz)")
            self.clock_status_label.setStyleSheet("font-weight: bold; color: #76b900; background-color: #1a3d1a; padding: 4px; border-radius: 3px;")
        else:
            self.clock_status_label.setText("Status: 🔓 Default (GPU manages clocks automatically)")
            self.clock_status_label.setStyleSheet("font-weight: bold; color: #ffffff; background-color: #3d3d3d; padding: 4px; border-radius: 3px;")
        
        # Update controls with current values if not focused
        # Don't update min_clock_spin - keep it at user-set value
        if not self.max_clock_spin.hasFocus():
            self.max_clock_spin.setValue(gpu_info.max_clock)
        if not self.power_limit_slider.hasFocus():
            self.power_limit_slider.setValue(gpu_info.power_limit)
            self.power_limit_value.setText(f"{gpu_info.power_limit} W")
        
        self.persistence_check.setChecked(gpu_info.persistence_mode)
    
    def handle_error(self, error_msg: str):
        self.statusBar().showMessage(f"Error: {error_msg}", 5000)
    
    def run_nvidia_command(self, args: list, needs_sudo: bool = True, gpu_id: Optional[int] = None) -> bool:
        """
        Execute nvidia command with optional privilege escalation.
        
        This is the main method for executing nvidia-smi and nvidia-settings
        commands. It includes security checks, GPU ID injection, and error handling.
        
        Args:
            args: Command arguments list (e.g., ["nvidia-smi", "-pl", "450"])
            needs_sudo: Whether to use pkexec for privilege escalation (default: True)
            gpu_id: Optional GPU ID to target (uses current_gpu_id if None)
            
        Returns:
            True if command executed successfully, False otherwise.
            
        Security:
            - Only allows nvidia-smi and nvidia-settings commands
            - Validates GPU IDs before injection
            - Limits error message length in logs
            - Uses timeout to prevent hanging
            
        Note:
            Commands requiring root privileges will prompt for password via pkexec.
        """
        if not args:
            logger.error("Empty command arguments")
            return False
        
        # Whitelist allowed commands for security
        allowed_commands = ["nvidia-smi", "nvidia-settings"]
        if args[0] not in allowed_commands:
            logger.error(f"Command not in whitelist: {args[0]}")
            QMessageBox.warning(self, "Security Error", 
                              f"Command '{args[0]}' is not allowed.")
            return False
        
        # Add GPU ID to nvidia-smi commands if not present
        if args[0] == "nvidia-smi" and "-i" not in args:
            gpu_id_to_use = gpu_id if gpu_id is not None else self.current_gpu_id
            # Validate GPU ID before using
            sanitized_id = sanitize_gpu_id(gpu_id_to_use)
            if sanitized_id is None:
                logger.error(f"Invalid GPU ID: {gpu_id_to_use}")
                QMessageBox.warning(self, "Invalid GPU ID", f"GPU ID {gpu_id_to_use} is invalid")
                return False
            # Insert after nvidia-smi
            args = [args[0], "-i", str(sanitized_id)] + args[1:]
        
        # Add GPU ID to nvidia-settings commands if not present
        if args[0] == "nvidia-settings":
            gpu_id_to_use = gpu_id if gpu_id is not None else self.current_gpu_id
            # Validate GPU ID before using
            sanitized_id = sanitize_gpu_id(gpu_id_to_use)
            if sanitized_id is None:
                logger.error(f"Invalid GPU ID: {gpu_id_to_use}")
                QMessageBox.warning(self, "Invalid GPU ID", f"GPU ID {gpu_id_to_use} is invalid")
                return False
            # Update [gpu:0] references to [gpu:X]
            for i, arg in enumerate(args):
                if "[gpu:0]" in arg:
                    args[i] = arg.replace("[gpu:0]", f"[gpu:{sanitized_id}]")
                elif "[gpu:" not in arg and "-a" in args and i > args.index("-a"):
                    # Try to add GPU specifier if missing
                    pass
        
        try:
            cmd = (["pkexec"] + args) if needs_sudo else args
            # Visual feedback: Show "Applying..." in status bar
            self.statusBar().showMessage(f"Applying settings...", 0)
            QApplication.processEvents()  # Update UI immediately
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=10
            )
            self.statusBar().showMessage("✓ Settings applied successfully", 3000)
            return True
        except subprocess.TimeoutExpired:
            error_msg = f"Command timed out: {' '.join(args)}"
            logger.error(error_msg)
            QMessageBox.warning(self, "Command Failed", error_msg)
            return False
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            # Security: Don't log full command arguments if they contain sensitive data
            # Log only the command name, not full arguments
            safe_cmd = args[0] if args else "unknown"
            logger.error(f"Command failed: {safe_cmd} - {error_msg[:200]}")  # Limit error message length
            
            # Provide helpful error messages
            if "Permission" in error_msg or "denied" in error_msg.lower():
                error_msg = f"Permission denied. This operation requires root privileges.\n\n{error_msg}"
            elif "not found" in error_msg.lower() or "command not found" in error_msg.lower():
                error_msg = f"Command not found. Please ensure NVIDIA drivers are installed.\n\n{error_msg}"
            elif "Coolbits" in error_msg or "fan" in error_msg.lower():
                error_msg = f"This feature requires Coolbits to be enabled in X config.\n\n{error_msg}"
            
            QMessageBox.warning(self, "Command Failed", 
                              f"Failed to execute command:\n{error_msg}")
            return False
        except FileNotFoundError:
            error_msg = f"Command not found: {args[0]}"
            logger.error(error_msg)
            QMessageBox.warning(self, "Command Not Found", 
                              f"{error_msg}\n\nPlease install:\n"
                              f"- nvidia-utils (for nvidia-smi)\n"
                              f"- nvidia-settings (for advanced features)")
            return False
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            QMessageBox.critical(self, "Error", error_msg)
            return False
    
    def apply_clock_lock(self):
        """
        Apply clock lock settings to the GPU.
        
        Locks the GPU core clock to the specified min/max range,
        preventing automatic clock adjustments. This provides
        consistent performance for gaming and demanding workloads.
        
        Validates clock values before applying and saves the lock
        status for persistence across reboots.
        """
        if not self.gpu_info:
            QMessageBox.warning(self, "No GPU Info", "GPU information not available. Please wait...")
            return
        
        min_clock = self.min_clock_spin.value()
        max_clock = self.max_clock_spin.value()
        
        # Validate clock values
        valid, error_msg = self.validate_clock_values(min_clock, max_clock)
        if not valid:
            QMessageBox.warning(self, "Invalid Values", error_msg)
            return
        
        reply = QMessageBox.question(
            self, "Apply Clock Lock",
            f"Apply clock lock: {min_clock} - {max_clock} MHz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Save previous state for rollback
            self.previous_settings["clock_lock"] = (
                self.gpu_info.min_clock_lock if self.gpu_info.clock_lock_status == "locked" else None
            )
            
            # Lock GPU clocks
            if self.run_nvidia_command(["nvidia-smi", "-lgc", f"{min_clock},{max_clock}"], 
                                      gpu_id=self.current_gpu_id):
                # Verify the lock was applied
                QTimer.singleShot(500, lambda: self.verify_clock_lock(min_clock, max_clock))
                
                # Save the lock status (per-GPU)
                try:
                    # Security: Validate GPU ID and path
                    sanitized_gpu_id = sanitize_gpu_id(self.current_gpu_id)
                    if sanitized_gpu_id is None:
                        logger.error(f"Invalid GPU ID for lock file: {self.current_gpu_id}")
                        return
                    
                    os.makedirs(CONFIG_DIR, exist_ok=True)
                    gpu_lock_file = os.path.join(CONFIG_DIR, f"clock_lock_status_gpu{sanitized_gpu_id}.txt")
                    
                    # Security: Validate path before writing
                    if not validate_config_path(gpu_lock_file):
                        logger.error(f"Invalid config file path: {gpu_lock_file}")
                        return
                    
                    # Security: Atomic write
                    temp_file = f"{gpu_lock_file}.tmp"
                    with open(temp_file, 'w') as f:
                        f.write(f"{min_clock},{max_clock}")
                    os.replace(temp_file, gpu_lock_file)
                except (OSError, IOError) as e:
                    logger.error(f"Failed to save clock lock status: {e}")
                    # Clean up temp file if exists
                    temp_file = f"{gpu_lock_file}.tmp"
                    if os.path.exists(temp_file):
                        try:
                            os.remove(temp_file)
                        except OSError:
                            pass
                
                QMessageBox.information(self, "Success", "Clock lock applied successfully")
            else:
                QMessageBox.warning(self, "Failed", "Failed to apply clock lock. Check permissions and GPU support.")
    
    def verify_clock_lock(self, expected_min: int, expected_max: int):
        """Verify that clock lock was actually applied."""
        if not self.gpu_info:
            return
        
        # Refresh GPU info to check actual state
        if self.worker:
            gpu_info = self.worker.get_gpu_info()
            if gpu_info:
                # Check if current clock is within expected range
                if gpu_info.current_clock < expected_min or gpu_info.current_clock > expected_max:
                    logger.warning(f"Clock lock verification: expected {expected_min}-{expected_max}, "
                                 f"but current is {gpu_info.current_clock} MHz")
                    self.statusBar().showMessage(
                        f"Warning: Clock may not be locked as expected. Current: {gpu_info.current_clock} MHz",
                        5000
                    )
    
    def reset_clocks(self):
        if not self.gpu_info:
            QMessageBox.warning(self, "No GPU Info", "GPU information not available. Please wait...")
            return
        
        reply = QMessageBox.question(
            self, "Reset Clocks",
            "Reset clocks to default values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.run_nvidia_command(["nvidia-smi", "-rgc"], gpu_id=self.current_gpu_id):
                # Remove the lock status file (per-GPU)
                try:
                    # Security: Validate GPU ID and path
                    sanitized_gpu_id = sanitize_gpu_id(self.current_gpu_id)
                    if sanitized_gpu_id is not None:
                        gpu_lock_file = os.path.join(CONFIG_DIR, f"clock_lock_status_gpu{sanitized_gpu_id}.txt")
                        
                        # Security: Validate path before removing
                        if validate_config_path(gpu_lock_file) and os.path.exists(gpu_lock_file):
                            os.remove(gpu_lock_file)
                except (OSError, IOError) as e:
                    logger.warning(f"Failed to remove clock lock status file: {e}")
                QMessageBox.information(self, "Success", "Clocks reset to default")
    
    def toggle_polling(self, state):
        """Toggle automatic GPU info polling"""
        if state == Qt.CheckState.Checked:
            self.worker.running = True
            if not self.worker.isRunning():
                self.worker.start()
            self.statusBar().showMessage("Auto-refresh enabled", 2000)
        else:
            self.worker.running = False
            self.statusBar().showMessage("Auto-refresh disabled", 2000)
    
    def refresh_gpu_info(self):
        """Manually refresh GPU info once"""
        if not self.worker:
            QMessageBox.warning(self, "Error", "Worker thread not initialized")
            return
        
        try:
            gpu_info = self.worker.get_gpu_info()
            if gpu_info:
                self.update_gpu_info(gpu_info)
                self.statusBar().showMessage("Refreshed", 1000)
            else:
                self.statusBar().showMessage("Failed to refresh GPU info", 3000)
        except Exception as e:
            logger.error(f"Error refreshing GPU info: {e}", exc_info=True)
            QMessageBox.warning(self, "Refresh Error", f"Failed to refresh: {str(e)}")
    
    
    def apply_memory_offset(self):
        if not self.gpu_info:
            QMessageBox.warning(self, "No GPU Info", "GPU information not available. Please wait...")
            return
        
        offset = self.mem_offset_spin.value()
        
        if offset < MIN_MEM_OFFSET_MHZ or offset > MAX_MEM_OFFSET_MHZ:
            QMessageBox.warning(self, "Invalid Value", 
                              f"Memory offset must be between {MIN_MEM_OFFSET_MHZ} and {MAX_MEM_OFFSET_MHZ} MHz")
            return
        
        # Validate step size
        if offset % MEM_OFFSET_STEP != 0:
            QMessageBox.warning(self, "Invalid Value", 
                              f"Memory offset must be a multiple of {MEM_OFFSET_STEP} MHz")
            return
        
        reply = QMessageBox.question(
            self, "Apply Memory Offset",
            f"Apply memory offset: {offset:+d} MHz?\n\n"
            f"Current memory clock: {self.gpu_info.memory_clock} MHz\n"
            f"Target memory clock: {self.gpu_info.memory_clock + offset} MHz\n\n"
            f"Warning: Incorrect values may cause instability!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Save previous state
            self.previous_settings["memory_offset"] = offset
            
            # Try multiple methods for setting memory offset
            # Method 1: nvidia-settings with multiple possible attribute names
            success = False
            methods = [
                ["nvidia-settings", "-a", f"[gpu:0]/GPUMemoryTransferRateOffset[3]={offset}"],
                ["nvidia-settings", "-a", f"[gpu:0]/GPUMemoryTransferRateOffsetAllPerformanceLevels={offset}"],
                ["nvidia-settings", "-a", f"GPUMemoryTransferRateOffset[3]={offset}"],
            ]
            
            for method in methods:
                if self.run_nvidia_command(method, needs_sudo=False, gpu_id=self.current_gpu_id):
                    success = True
                    break
            
            if success:
                QMessageBox.information(self, "Success", "Memory offset applied")
            else:
                QMessageBox.warning(self, "Failed", 
                                  "Could not apply memory offset. This may require:\n"
                                  "- nvidia-settings package installed\n"
                                  "- Coolbits enabled in X config\n"
                                  "- Or may not be supported on your GPU")
    
    def apply_power_limit(self):
        if not self.gpu_info:
            QMessageBox.warning(self, "No GPU Info", "GPU information not available. Please wait...")
            return
        
        power_limit = self.power_limit_slider.value()
        
        # Validate against GPU's actual max power limit
        if self.gpu_info.max_power_limit > 0:
            if power_limit > self.gpu_info.max_power_limit:
                QMessageBox.warning(self, "Invalid Value", 
                                  f"Power limit ({power_limit} W) exceeds GPU maximum ({self.gpu_info.max_power_limit} W)")
                return
        
        # Validate against slider range (which should be GPU-specific)
        if hasattr(self, 'power_limit_min') and hasattr(self, 'power_limit_max'):
            if power_limit < self.power_limit_min or power_limit > self.power_limit_max:
                QMessageBox.warning(self, "Invalid Value", 
                                  f"Power limit must be between {self.power_limit_min} and {self.power_limit_max} W")
                return
        
        reply = QMessageBox.question(
            self, "Apply Power Limit",
            f"Apply power limit: {power_limit} W?\n\n"
            f"GPU maximum: {self.gpu_info.max_power_limit} W",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Save previous state
            self.previous_settings["power_limit"] = self.gpu_info.power_limit
            
            if self.run_nvidia_command(["nvidia-smi", "-pl", str(power_limit)], 
                                      gpu_id=self.current_gpu_id):
                # Verify the power limit was applied
                QTimer.singleShot(500, lambda: self.verify_power_limit(power_limit))
                # Save settings for persistence
                self.save_all_settings()
                QMessageBox.information(self, "Success", "Power limit applied")
    
    def verify_power_limit(self, expected_power: int):
        """Verify that power limit was actually applied."""
        if not self.gpu_info or not self.worker:
            return
        
        gpu_info = self.worker.get_gpu_info()
        if gpu_info and abs(gpu_info.power_limit - expected_power) > 5:  # Allow 5W tolerance
            logger.warning(f"Power limit verification: expected {expected_power}W, "
                         f"but actual is {gpu_info.power_limit}W")
            self.statusBar().showMessage(
                f"Warning: Power limit may differ. Expected: {expected_power}W, Actual: {gpu_info.power_limit}W",
                5000
            )
    
    def toggle_persistence_mode(self, state):
        if not self.gpu_info:
            QMessageBox.warning(self, "No GPU Info", "GPU information not available. Please wait...")
            return
        
        mode = "1" if state == Qt.CheckState.Checked else "0"
        
        if self.run_nvidia_command(["nvidia-smi", "-pm", mode], gpu_id=self.current_gpu_id):
            mode_text = "enabled" if mode == "1" else "disabled"
            self.save_all_settings()  # Save for persistence
            self.statusBar().showMessage(f"Persistence mode {mode_text}", 3000)
    
    def toggle_fan_mode(self, checked: bool):
        """Toggle between auto and manual fan control."""
        if not checked:
            return
        
        manual_mode = self.fan_manual_radio.isChecked()
        self.fan_speed_slider.setEnabled(manual_mode)
        self.apply_fan_btn.setEnabled(manual_mode)
        
        if manual_mode:
            if not self.coolbits_enabled:
                QMessageBox.warning(
                    self, "Coolbits Required",
                    "Manual fan control requires Coolbits.\n\n"
                    "Switching back to automatic mode."
                )
                self.fan_auto_radio.setChecked(True)
                return
            
            # Enable manual mode via nvidia-settings
            self.run_nvidia_command(
                ["nvidia-settings", "-a", f"[gpu:{self.current_gpu_id}]/GPUFanControlState=1"],
                needs_sudo=False, gpu_id=self.current_gpu_id
            )
        else:
            # Disable manual mode (return to auto)
            self.run_nvidia_command(
                ["nvidia-settings", "-a", f"[gpu:{self.current_gpu_id}]/GPUFanControlState=0"],
                needs_sudo=False, gpu_id=self.current_gpu_id
            )
    
    def apply_fan_speed(self):
        """Apply manual fan speed setting."""
        if not self.gpu_info:
            QMessageBox.warning(self, "No GPU Info", "GPU information not available. Please wait...")
            return
        
        if not self.coolbits_enabled:
            QMessageBox.warning(
                self, "Coolbits Required",
                "Fan control requires Coolbits to be enabled.\n\n"
                "To enable Coolbits:\n"
                "1. Create/edit /etc/X11/xorg.conf.d/20-nvidia.conf\n"
                "2. Add: Option \"Coolbits\" \"4\" (or higher)\n"
                "3. Restart X server or reboot"
            )
            return
        
        fan_speed = self.fan_speed_slider.value()
        
        reply = QMessageBox.question(
            self, "Apply Fan Speed",
            f"Set fan speed to {fan_speed}%?\n\n"
            f"Warning: Very low fan speeds may cause overheating!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Try multiple methods for setting fan speed
            methods = [
                ["nvidia-settings", "-a", f"[fan:{self.current_gpu_id}]/GPUTargetFanSpeed={fan_speed}"],
                ["nvidia-settings", "-a", f"[gpu:{self.current_gpu_id}]/GPUFanControlState=1", 
                 "-a", f"[fan:{self.current_gpu_id}]/GPUTargetFanSpeed={fan_speed}"],
            ]
            
            success = False
            for method in methods:
                if self.run_nvidia_command(method, needs_sudo=False, gpu_id=self.current_gpu_id):
                    success = True
                    break
            
            if success:
                self.save_all_settings()  # Save for persistence
                QMessageBox.information(self, "Success", f"Fan speed set to {fan_speed}%")
            else:
                QMessageBox.warning(self, "Failed", 
                                  "Could not set fan speed. This requires:\n"
                                  "- Coolbits enabled in X config\n"
                                  "- nvidia-settings package\n"
                                  "- GPU must support manual fan control")
    
    def apply_performance_mode(self):
        if not self.gpu_info:
            QMessageBox.warning(self, "No GPU Info", "GPU information not available. Please wait...")
            return
        
        mode_map = {
            "Adaptive": "0",
            "Prefer Maximum Performance": "1",
            "Auto": "2"
        }
        mode = mode_map.get(self.perf_mode_combo.currentText())
        if mode is None:
            QMessageBox.warning(self, "Invalid Mode", "Unknown performance mode")
            return
        
        # This requires nvidia-settings
        if self.run_nvidia_command(["nvidia-settings", "-a", f"[gpu:0]/GpuPowerMizerMode={mode}"], 
                                  needs_sudo=False, gpu_id=self.current_gpu_id):
            self.save_all_settings()  # Save for persistence
            QMessageBox.information(self, "Success", "Performance mode applied")
    
    def _apply_profile(self, profile: Dict[str, Any], profile_name: str) -> Tuple[bool, list]:
        """
        Apply a profile configuration with proper ordering and rollback support.
        
        This is the core method for applying GPU settings profiles. It handles:
        - Resetting existing clock locks before applying new ones
        - Applying settings in optimal order (Power → Performance → Clocks → Memory)
        - Tracking applied settings for rollback on failure
        - Validating all values before applying
        
        Args:
            profile: Dictionary containing profile settings:
                - min_clock: Minimum clock speed (int or None)
                - max_clock: Maximum clock speed (int or None)
                - power_limit: Power limit in watts (int or None)
                - perf_mode: Performance mode string (or None)
                - mem_offset: Memory offset in MHz (int or None)
            profile_name: Name of the profile (for error messages)
            
        Returns:
            Tuple of (success, errors):
            - success: True if all settings applied successfully
            - errors: List of error descriptions for failed settings
            
        Note:
            Settings are applied in this order for best results:
            1. Power limit (establishes constraints)
            2. Performance mode (affects clock management)
            3. Clock lock (requires power/perf to be set)
            4. Memory offset (most likely to fail, applied last)
        """
        if not self.gpu_info:
            QMessageBox.warning(self, "No GPU Info", "GPU information not available. Please wait...")
            return False, []
        
        # Save current state for rollback
        rollback_state = {
            "clock_lock": (self.gpu_info.min_clock_lock, self.gpu_info.max_clock_lock) 
                          if self.gpu_info.clock_lock_status == "locked" else None,
            "power_limit": self.gpu_info.power_limit,
            "perf_mode": self.perf_mode_combo.currentText(),
            "mem_offset": self.mem_offset_spin.value()
        }
        
        # Update UI controls
        if profile.get("min_clock") is not None:
            self.min_clock_spin.setValue(profile["min_clock"])
        if profile.get("max_clock") is not None:
            self.max_clock_spin.setValue(profile["max_clock"])
        if profile.get("mem_offset") is not None:
            self.mem_offset_spin.setValue(profile["mem_offset"])
        if profile.get("power_limit") is not None:
            self.power_limit_slider.setValue(profile["power_limit"])
        if profile.get("perf_mode"):
            self.perf_mode_combo.setCurrentText(profile["perf_mode"])
        
        success = True
        errors = []
        applied_settings = []
        
        # CRITICAL FIX: Always reset clocks first when switching profiles
        # This prevents conflicts when switching from one locked profile to another
        if (profile.get("min_clock") is not None or profile.get("max_clock") is not None) and \
           self.gpu_info.clock_lock_status == "locked":
            logger.info("Resetting existing clock lock before applying new profile")
            if not self.run_nvidia_command(["nvidia-smi", "-rgc"], gpu_id=self.current_gpu_id):
                errors.append("clock reset (pre-lock)")
                success = False
        
        # Apply settings in optimal order: Power → Performance → Clocks → Memory
        # 1. Apply power limit first (establishes power constraints)
        if profile.get("power_limit") is not None:
            if self.run_nvidia_command(["nvidia-smi", "-pl", str(profile["power_limit"])], 
                                      gpu_id=self.current_gpu_id):
                applied_settings.append("power_limit")
            else:
                success = False
                errors.append("power limit")
        
        # 2. Apply performance mode (affects how GPU manages clocks)
        if profile.get("perf_mode"):
            mode_map = {
                "Adaptive": "0",
                "Prefer Maximum Performance": "1",
                "Auto": "2"
            }
            mode = mode_map.get(profile["perf_mode"])
            if mode:
                if self.run_nvidia_command(["nvidia-settings", "-a", f"[gpu:0]/GpuPowerMizerMode={mode}"], 
                                          needs_sudo=False, gpu_id=self.current_gpu_id):
                    applied_settings.append("performance_mode")
                else:
                    success = False
                    errors.append("performance mode")
        
        # 3. Apply clock lock (requires power and performance mode to be set first)
        if profile.get("min_clock") is not None and profile.get("max_clock") is not None:
            min_clock = profile["min_clock"]
            max_clock = profile["max_clock"]
            
            # Validate clock values
            valid, error_msg = self.validate_clock_values(min_clock, max_clock)
            if valid:
                clock_cmd = f"{min_clock},{max_clock}"
                if self.run_nvidia_command(["nvidia-smi", "-lgc", clock_cmd], gpu_id=self.current_gpu_id):
                    applied_settings.append("clock_lock")
                    try:
                        # Security: Validate GPU ID and path
                        sanitized_gpu_id = sanitize_gpu_id(self.current_gpu_id)
                        if sanitized_gpu_id is not None:
                            os.makedirs(CONFIG_DIR, exist_ok=True)
                            gpu_lock_file = os.path.join(CONFIG_DIR, f"clock_lock_status_gpu{sanitized_gpu_id}.txt")
                            
                            # Security: Validate path before writing
                            if validate_config_path(gpu_lock_file):
                                # Security: Atomic write
                                temp_file = f"{gpu_lock_file}.tmp"
                                with open(temp_file, 'w') as f:
                                    f.write(clock_cmd)
                                os.replace(temp_file, gpu_lock_file)
                    except (OSError, IOError) as e:
                        logger.warning(f"Failed to save clock lock status: {e}")
                        # Clean up temp file
                        temp_file = f"{gpu_lock_file}.tmp"
                        if os.path.exists(temp_file):
                            try:
                                os.remove(temp_file)
                            except OSError:
                                pass
                else:
                    success = False
                    errors.append("clock lock")
            else:
                success = False
                errors.append(f"clock validation: {error_msg}")
        
        # 4. Reset clocks if profile specifies None (unlock)
        elif profile.get("min_clock") is None or profile.get("max_clock") is None:
            if self.run_nvidia_command(["nvidia-smi", "-rgc"], gpu_id=self.current_gpu_id):
                applied_settings.append("clock_reset")
                try:
                    # Security: Validate GPU ID and path
                    sanitized_gpu_id = sanitize_gpu_id(self.current_gpu_id)
                    if sanitized_gpu_id is not None:
                        gpu_lock_file = os.path.join(CONFIG_DIR, f"clock_lock_status_gpu{sanitized_gpu_id}.txt")
                        
                        # Security: Validate path before removing
                        if validate_config_path(gpu_lock_file) and os.path.exists(gpu_lock_file):
                            os.remove(gpu_lock_file)
                except (OSError, IOError) as e:
                    logger.warning(f"Failed to remove clock lock status: {e}")
            else:
                success = False
                errors.append("clock reset")
        
        # 5. Apply memory offset last (most likely to cause issues)
        if profile.get("mem_offset") is not None:
            offset = profile["mem_offset"]
            # Try multiple methods
            mem_success = False
            methods = [
                ["nvidia-settings", "-a", f"[gpu:0]/GPUMemoryTransferRateOffset[3]={offset}"],
                ["nvidia-settings", "-a", f"[gpu:0]/GPUMemoryTransferRateOffsetAllPerformanceLevels={offset}"],
            ]
            for method in methods:
                if self.run_nvidia_command(method, needs_sudo=False, gpu_id=self.current_gpu_id):
                    mem_success = True
                    applied_settings.append("memory_offset")
                    break
            
            if not mem_success:
                errors.append("memory offset (may not be supported)")
                # Don't mark as failure since memory offset is optional
        
        # Rollback on critical failure
        if not success and len(applied_settings) > 0:
            reply = QMessageBox.question(
                self, "Partial Failure",
                f"Some settings failed to apply. Errors: {', '.join(errors)}\n\n"
                f"Rollback applied settings?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self._rollback_settings(rollback_state, applied_settings)
        
        return success, errors
    
    def _rollback_settings(self, rollback_state: Dict[str, Any], applied_settings: list):
        """Rollback settings to previous state."""
        logger.info("Rolling back settings...")
        
        # Rollback in reverse order
        if "memory_offset" in applied_settings and rollback_state.get("mem_offset") is not None:
            # Reset memory offset (complex, may not work)
            pass
        
        if "clock_lock" in applied_settings or "clock_reset" in applied_settings:
            if rollback_state.get("clock_lock"):
                min_c, max_c = rollback_state["clock_lock"]
                self.run_nvidia_command(["nvidia-smi", "-lgc", f"{min_c},{max_c}"], 
                                       gpu_id=self.current_gpu_id)
            else:
                self.run_nvidia_command(["nvidia-smi", "-rgc"], gpu_id=self.current_gpu_id)
        
        if "performance_mode" in applied_settings:
            # Performance mode rollback is complex, skip for now
            pass
        
        if "power_limit" in applied_settings and rollback_state.get("power_limit"):
            self.run_nvidia_command(["nvidia-smi", "-pl", str(rollback_state["power_limit"])], 
                                   gpu_id=self.current_gpu_id)
        
        logger.info("Rollback completed")
    
    def apply_gaming_profile(self):
        """Apply gaming profile with maximum performance settings."""
        reply = QMessageBox.question(
            self, "Apply Gaming Profile",
            "Apply Gaming Profile?\n\n"
            f"This will set:\n"
            f"- Clock Lock: {PROFILE_GAMING['min_clock']}-{PROFILE_GAMING['max_clock']} MHz\n"
            f"- Power Limit: {PROFILE_GAMING['power_limit']}W\n"
            f"- Performance: {PROFILE_GAMING['perf_mode']}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        success, errors = self._apply_profile(PROFILE_GAMING, "Gaming")
        
        if success:
            QMessageBox.information(self, "Success", "Gaming profile applied successfully")
        else:
            QMessageBox.warning(self, "Partial Success", 
                              f"Profile applied with errors: {', '.join(errors)}")
    
    def apply_balanced_profile(self):
        """Apply balanced profile for general use."""
        reply = QMessageBox.question(
            self, "Apply Balanced Profile",
            "Apply Balanced Profile?\n\n"
            f"This will set:\n"
            f"- Clocks: Default (unlocked)\n"
            f"- Power Limit: {PROFILE_BALANCED['power_limit']}W\n"
            f"- Performance: {PROFILE_BALANCED['perf_mode']}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        success, errors = self._apply_profile(PROFILE_BALANCED, "Balanced")
        
        if success:
            QMessageBox.information(self, "Success", "Balanced profile applied successfully")
        else:
            QMessageBox.warning(self, "Partial Success", 
                              f"Profile applied with errors: {', '.join(errors)}")
    
    def apply_quiet_profile(self):
        """Apply quiet profile for low power operation."""
        reply = QMessageBox.question(
            self, "Apply Quiet Profile",
            "Apply Quiet Profile?\n\n"
            f"This will set:\n"
            f"- Clock Lock: {PROFILE_QUIET['min_clock']}-{PROFILE_QUIET['max_clock']} MHz\n"
            f"- Power Limit: {PROFILE_QUIET['power_limit']}W\n"
            f"- Performance: {PROFILE_QUIET['perf_mode']}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        success, errors = self._apply_profile(PROFILE_QUIET, "Quiet")
        
        if success:
            QMessageBox.information(self, "Success", "Quiet profile applied successfully")
        else:
            QMessageBox.warning(self, "Partial Success", 
                              f"Profile applied with errors: {', '.join(errors)}")
    
    def apply_mining_profile(self):
        """Apply mining profile optimized for cryptocurrency mining."""
        reply = QMessageBox.question(
            self, "Apply Mining Profile",
            "Apply Mining Profile?\n\n"
            f"This will set:\n"
            f"- Clock Lock: {PROFILE_MINING['min_clock']}-{PROFILE_MINING['max_clock']} MHz\n"
            f"- Memory Offset: +{PROFILE_MINING['mem_offset']} MHz\n"
            f"- Power Limit: {PROFILE_MINING['power_limit']}W",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        success, errors = self._apply_profile(PROFILE_MINING, "Mining")
        
        if success:
            QMessageBox.information(self, "Success", "Mining profile applied successfully")
        else:
            QMessageBox.warning(self, "Partial Success", 
                              f"Profile applied with errors: {', '.join(errors)}")
    
    def save_custom_profile(self):
        profile = {
            "min_clock": self.min_clock_spin.value(),
            "max_clock": self.max_clock_spin.value(),
            "mem_offset": self.mem_offset_spin.value(),
            "power_limit": self.power_limit_slider.value(),
            "perf_mode": self.perf_mode_combo.currentText()
        }
        
        # Security: Validate profile structure before saving
        try:
            profile_json = json.dumps(profile)
            # Validate it can be parsed back
            json.loads(profile_json)
            self.settings.setValue("custom_profile", profile_json)
            QMessageBox.information(self, "Profile Saved", "Custom profile saved successfully")
        except (TypeError, ValueError, json.JSONEncodeError) as e:
            logger.error(f"Invalid profile data: {e}")
            QMessageBox.warning(self, "Invalid Profile", "Profile data is invalid and cannot be saved.")
    
    def load_custom_profile(self):
        profile_json = self.settings.value("custom_profile", None)
        if not profile_json:
            QMessageBox.warning(self, "No Profile", "No custom profile found")
            return
        
        try:
            profile = json.loads(profile_json)
            # Security: Validate profile structure
            if not isinstance(profile, dict):
                raise ValueError("Profile must be a dictionary")
            
            # Security: Validate and sanitize values
            required_keys = ["min_clock", "max_clock", "mem_offset", "power_limit", "perf_mode"]
            for key in required_keys:
                if key not in profile:
                    raise ValueError(f"Missing required key: {key}")
            
            # Validate value ranges
            min_clock = int(profile["min_clock"])
            max_clock = int(profile["max_clock"])
            if not (MIN_CLOCK_MHZ <= min_clock <= MAX_CLOCK_MHZ):
                raise ValueError(f"min_clock out of range: {min_clock}")
            if not (MIN_CLOCK_MHZ <= max_clock <= MAX_CLOCK_MHZ):
                raise ValueError(f"max_clock out of range: {max_clock}")
            
            mem_offset = int(profile["mem_offset"])
            if not (MIN_MEM_OFFSET_MHZ <= mem_offset <= MAX_MEM_OFFSET_MHZ):
                raise ValueError(f"mem_offset out of range: {mem_offset}")
            
            power_limit = int(profile["power_limit"])
            if not (MIN_POWER_W <= power_limit <= MAX_POWER_W):
                raise ValueError(f"power_limit out of range: {power_limit}")
            
            # Apply validated values
            self.min_clock_spin.setValue(min_clock)
            self.max_clock_spin.setValue(max_clock)
            self.mem_offset_spin.setValue(mem_offset)
            self.power_limit_slider.setValue(power_limit)
            self.perf_mode_combo.setCurrentText(profile["perf_mode"])
            
            QMessageBox.information(self, "Profile Loaded", "Custom profile loaded successfully")
        except (json.JSONDecodeError, ValueError, TypeError, KeyError) as e:
            logger.error(f"Invalid profile JSON: {e}")
            QMessageBox.warning(self, "Load Failed", f"Failed to load profile: {str(e)}")
    
    def refresh_monitoring(self):
        try:
            result = subprocess.run(
                ["nvidia-smi", "-q", "-d", "CLOCK,PERFORMANCE,POWER,TEMPERATURE"],
                capture_output=True,
                text=True,
                check=True
            )
            self.monitor_text.setPlainText(result.stdout)
        except Exception as e:
            self.monitor_text.setPlainText(f"Error getting monitoring data:\n{str(e)}")
    
    def toggle_auto_refresh(self, state):
        if state == Qt.CheckState.Checked:
            self.monitor_timer.start(MONITOR_REFRESH_INTERVAL_MS)
        else:
            self.monitor_timer.stop()
    
    def load_settings(self):
        """Load saved settings from QSettings."""
        # Load window geometry
        geometry = self.settings.value("geometry", None)
        if geometry:
            self.restoreGeometry(geometry)
        
        # Load last used values
        self.min_clock_spin.setValue(self.settings.value("min_clock", DEFAULT_MIN_CLOCK, type=int))
        self.max_clock_spin.setValue(self.settings.value("max_clock", DEFAULT_MAX_CLOCK, type=int))
        self.mem_offset_spin.setValue(self.settings.value("mem_offset", 0, type=int))
        self.power_limit_slider.setValue(self.settings.value("power_limit", DEFAULT_POWER_W, type=int))
        
        # Load preference for restoring clock locks on startup
        # This will be checked in restore_clock_locks()
        if not self.settings.contains("restore_clock_locks"):
            self.settings.setValue("restore_clock_locks", True)  # Default to enabled
        
        # Load preference for restoring all settings on startup
        if not self.settings.contains("restore_all_settings"):
            self.settings.setValue("restore_all_settings", False)  # Default to disabled (safer)
    
    def save_all_settings(self):
        """Save all current settings for persistence across reboots."""
        if not self.gpu_info:
            return
        
        try:
            # Security: Validate GPU ID before constructing path
            sanitized_gpu_id = sanitize_gpu_id(self.current_gpu_id)
            if sanitized_gpu_id is None:
                logger.error(f"Invalid GPU ID for settings: {self.current_gpu_id}")
                return
            
            settings_file = os.path.join(CONFIG_DIR, f"settings_gpu{sanitized_gpu_id}.json")
            
            # Security: Validate path before writing
            if not validate_config_path(settings_file):
                logger.error(f"Invalid config file path: {settings_file}")
                return
            
            os.makedirs(CONFIG_DIR, exist_ok=True)
            
            settings_data = {
                "gpu_id": sanitized_gpu_id,
                "power_limit": self.gpu_info.power_limit,
                "persistence_mode": self.gpu_info.persistence_mode,
                "performance_mode": self.perf_mode_combo.currentText(),
                "fan_mode": "manual" if self.fan_manual_radio.isChecked() else "auto",
                "fan_speed": self.fan_speed_slider.value() if self.fan_manual_radio.isChecked() else None,
                "clock_lock": {
                    "min": self.gpu_info.min_clock_lock if self.gpu_info.clock_lock_status == "locked" else None,
                    "max": self.gpu_info.max_clock_lock if self.gpu_info.clock_lock_status == "locked" else None
                },
                "timestamp": str(os.path.getmtime(settings_file)) if os.path.exists(settings_file) else None
            }
            
            # Security: Write to temporary file first, then rename (atomic write)
            temp_file = f"{settings_file}.tmp"
            with open(temp_file, 'w') as f:
                json.dump(settings_data, f, indent=2)
            os.replace(temp_file, settings_file)  # Atomic rename
            
            logger.info(f"Settings saved for GPU {sanitized_gpu_id}")
        except (OSError, IOError, ValueError, json.JSONEncodeError) as e:
            logger.error(f"Failed to save settings: {e}")
            # Clean up temp file if it exists
            temp_file = f"{settings_file}.tmp"
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError:
                    pass
    
    def restore_all_settings(self):
        """Restore all saved settings on startup."""
        if not self.settings.value("restore_all_settings", False, type=bool):
            return
        
        try:
            # Security: Validate GPU ID
            sanitized_gpu_id = sanitize_gpu_id(self.current_gpu_id)
            if sanitized_gpu_id is None:
                logger.error(f"Invalid GPU ID for settings restore: {self.current_gpu_id}")
                return
            
            settings_file = os.path.join(CONFIG_DIR, f"settings_gpu{sanitized_gpu_id}.json")
            
            # Security: Validate path before reading
            if not validate_config_path(settings_file):
                logger.error(f"Invalid config file path: {settings_file}")
                return
            
            if not os.path.exists(settings_file):
                return
            
            # Security: Validate file size (prevent DoS with huge files)
            file_size = os.path.getsize(settings_file)
            if file_size > 1024 * 1024:  # 1MB limit
                logger.error(f"Settings file too large: {file_size} bytes")
                return
            
            with open(settings_file, 'r') as f:
                settings_data = json.load(f)
            
            # Security: Validate JSON structure
            valid, error_msg = validate_json_structure(settings_data, required_keys=["gpu_id"])
            if not valid:
                logger.error(f"Invalid settings file structure: {error_msg}")
                return
            
            # Security: Validate values before restoring
            # Restore power limit
            if settings_data.get("power_limit"):
                power_limit = settings_data["power_limit"]
                if isinstance(power_limit, (int, float)) and 0 <= power_limit <= 1000:
                    self.run_nvidia_command(["nvidia-smi", "-pl", str(int(power_limit))], 
                                           gpu_id=sanitized_gpu_id)
                else:
                    logger.warning(f"Invalid power limit value: {power_limit}")
            
            # Restore persistence mode
            if settings_data.get("persistence_mode"):
                if isinstance(settings_data["persistence_mode"], bool):
                    mode = "1" if settings_data["persistence_mode"] else "0"
                    self.run_nvidia_command(["nvidia-smi", "-pm", mode], gpu_id=sanitized_gpu_id)
            
            # Restore performance mode
            if settings_data.get("performance_mode"):
                mode_map = {"Adaptive": "0", "Prefer Maximum Performance": "1", "Auto": "2"}
                perf_mode = settings_data["performance_mode"]
                if isinstance(perf_mode, str) and perf_mode in mode_map:
                    mode = mode_map[perf_mode]
                    self.run_nvidia_command(["nvidia-settings", "-a", f"[gpu:0]/GpuPowerMizerMode={mode}"], 
                                          needs_sudo=False, gpu_id=sanitized_gpu_id)
            
            # Restore fan settings
            if settings_data.get("fan_mode") == "manual" and settings_data.get("fan_speed"):
                fan_speed = settings_data["fan_speed"]
                if isinstance(fan_speed, (int, float)) and 0 <= fan_speed <= 100:
                    if self.coolbits_enabled:
                        self.fan_manual_radio.setChecked(True)
                        self.fan_speed_slider.setValue(int(fan_speed))
                        self.run_nvidia_command(
                            ["nvidia-settings", "-a", f"[fan:{sanitized_gpu_id}]/GPUTargetFanSpeed={int(fan_speed)}"],
                            needs_sudo=False, gpu_id=sanitized_gpu_id
                        )
                else:
                    logger.warning(f"Invalid fan speed value: {fan_speed}")
            
            logger.info(f"Settings restored for GPU {self.current_gpu_id}")
        except Exception as e:
            logger.warning(f"Error restoring settings: {e}")
    
    def generate_systemd_service(self):
        """Generate a systemd service file to restore settings on boot."""
        if not self.gpu_info:
            QMessageBox.warning(self, "No GPU Info", "GPU information not available. Please wait...")
            return
        
        reply = QMessageBox.question(
            self, "Generate Systemd Service",
            "This will create a systemd service file to restore GPU settings on boot.\n\n"
            "The service will restore:\n"
            "- Clock locks\n"
            "- Power limits\n"
            "- Persistence mode\n"
            "- Performance mode\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            # Get current settings
            settings_file = os.path.join(CONFIG_DIR, f"settings_gpu{self.current_gpu_id}.json")
            if not os.path.exists(settings_file):
                QMessageBox.warning(self, "No Settings", 
                                  "No saved settings found. Please save settings first.")
                return
            
            with open(settings_file, 'r') as f:
                settings_data = json.load(f)
            
            # Generate service file content
            service_content = f"""[Unit]
Description=NVIDIA GPU Control - Restore Settings for GPU {self.current_gpu_id}
After=graphical-session.target nvidia-persistenced.service
Wants=nvidia-persistenced.service

[Service]
Type=oneshot
ExecStart=/usr/bin/nvidia-control-gui --restore-settings
RemainAfterExit=yes
User=%i

[Install]
WantedBy=default.target
"""
            
            # Save service file
            # Security: Validate GPU ID and path
            sanitized_gpu_id = sanitize_gpu_id(self.current_gpu_id)
            if sanitized_gpu_id is None:
                QMessageBox.warning(self, "Invalid GPU ID", f"GPU ID {self.current_gpu_id} is invalid")
                return
            
            service_file = os.path.join(CONFIG_DIR, f"nvidia-control-gpu{sanitized_gpu_id}.service")
            
            # Security: Validate path before writing
            if not validate_config_path(service_file):
                logger.error(f"Invalid service file path: {service_file}")
                QMessageBox.warning(self, "Error", "Invalid service file path")
                return
            
            with open(service_file, 'w') as f:
                f.write(service_content)
            
            QMessageBox.information(
                self, "Service Generated",
                f"Systemd service file created:\n{service_file}\n\n"
                f"To install:\n"
                f"1. Copy to: ~/.config/systemd/user/\n"
                f"2. Run: systemctl --user daemon-reload\n"
                f"3. Run: systemctl --user enable nvidia-control-gpu{self.current_gpu_id}.service\n\n"
                f"Note: This requires adding --restore-settings flag support to the application."
            )
        except Exception as e:
            logger.error(f"Error generating service file: {e}")
            QMessageBox.warning(self, "Error", f"Failed to generate service file:\n{str(e)}")
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Save settings
        try:
            self.settings.setValue("geometry", self.saveGeometry())
            self.settings.setValue("min_clock", self.min_clock_spin.value())
            self.settings.setValue("max_clock", self.max_clock_spin.value())
            self.settings.setValue("mem_offset", self.mem_offset_spin.value())
            self.settings.setValue("power_limit", self.power_limit_slider.value())
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
        
        # Stop worker thread safely
        try:
            if hasattr(self, 'worker') and self.worker:
                self.worker.stop()
                self.worker.wait(3000)  # Wait up to 3 seconds
                if self.worker.isRunning():
                    logger.warning("Worker thread did not stop in time")
                    self.worker.terminate()
        except Exception as e:
            logger.error(f"Error stopping worker thread: {e}")
        
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("NVIDIA GPU Control")
    
    # Check for command-line arguments
    if "--restore-settings" in sys.argv:
        # Restore settings mode (for systemd service)
        try:
            import json
            config_dir = os.path.expanduser("~/.config/nvidia-control")
            
            # Restore settings for all GPUs
            gpus = NvidiaWorker.detect_gpus()
            if not gpus:
                gpus = [{"id": 0}]
            
            for gpu in gpus:
                gpu_id = gpu['id']
                settings_file = os.path.join(config_dir, f"settings_gpu{gpu_id}.json")
                
                if os.path.exists(settings_file):
                    with open(settings_file, 'r') as f:
                        settings_data = json.load(f)
                    
                    # Restore power limit
                    if settings_data.get("power_limit"):
                        subprocess.run(["pkexec", "nvidia-smi", "-i", str(gpu_id), 
                                      "-pl", str(settings_data["power_limit"])], 
                                     check=False)
                    
                    # Restore persistence mode
                    if settings_data.get("persistence_mode"):
                        mode = "1" if settings_data["persistence_mode"] else "0"
                        subprocess.run(["pkexec", "nvidia-smi", "-i", str(gpu_id), "-pm", mode], 
                                     check=False)
                    
                    # Restore clock locks
                    clock_lock = settings_data.get("clock_lock", {})
                    if clock_lock.get("min") and clock_lock.get("max"):
                        subprocess.run(["pkexec", "nvidia-smi", "-i", str(gpu_id), 
                                      "-lgc", f"{clock_lock['min']},{clock_lock['max']}"], 
                                     check=False)
            
            sys.exit(0)
        except Exception as e:
            logger.error(f"Error restoring settings: {e}")
            sys.exit(1)
    
    # Check if running as root
    if os.geteuid() == 0:
        reply = QMessageBox.warning(
            None, "Running as Root",
            "This application should not be run as root. Continue anyway?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.No:
            sys.exit(1)
    
    window = NvidiaControlGUI()
    
    # Check for --minimized flag (even though we don't support it, handle gracefully)
    if "--minimized" in sys.argv or "--hide" in sys.argv:
        # Just start minimized
        pass
    else:
        window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()