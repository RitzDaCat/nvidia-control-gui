# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-11-03

### Added
- Initial release of NVIDIA GPU Control Panel
- **Clock Control**:
  - Set minimum and maximum GPU core clock speeds
  - Memory clock offset adjustment
  - Clock lock/unlock functionality
  - Real-time clock monitoring
- **Power Management**:
  - Power limit control (100-600W)
  - Persistence mode toggle
  - Performance mode selection (Adaptive, Maximum Performance, Auto)
  - Real-time power draw monitoring
- **Fan Control**:
  - Manual fan speed control (0-100%)
  - Automatic fan control mode
  - Coolbits detection and status display
  - Real-time fan speed monitoring
- **Multi-GPU Support**:
  - Automatic GPU detection
  - GPU selector dropdown
  - Per-GPU settings management
  - Per-GPU configuration files
- **Profiles**:
  - Gaming profile (max performance)
  - Balanced profile (adaptive)
  - Quiet profile (low power)
  - Mining profile (optimized)
  - Custom profile save/load
- **Monitoring**:
  - Real-time GPU statistics
  - Temperature, fan speed, power draw display
  - GPU and memory utilization tracking
  - Performance state monitoring
  - Detailed monitoring tab with nvidia-smi output
- **User Experience**:
  - Comprehensive tooltips on all controls
  - Keyboard shortcuts (F5, Ctrl+L, Ctrl+R, Ctrl+S, Ctrl+O, F1, Ctrl+1-5)
  - Color-coded visual feedback (temperature, fan speed, performance)
  - Help dialog (F1) with shortcuts and tips
  - Status bar messages with visual indicators
- **Security**:
  - Input validation for all user inputs
  - Path validation to prevent directory traversal
  - JSON structure validation
  - File size limits
  - Atomic file operations
  - Command whitelist
  - GPU ID validation
- **Installation**:
  - PKGBUILD for Arch Linux
  - install.sh script for easy installation
  - uninstall.sh script for clean removal
  - Systemd service for autostart
  - Desktop entry for application menus
- **Documentation**:
  - Comprehensive README
  - Installation guide (INSTALL.md)
  - Packaging guide (PACKAGING.md)
  - AUR submission guide (AUR-SUBMISSION.md)
  - Code docstrings and API documentation

### Security
- Added `sanitize_gpu_id()` function for GPU ID validation
- Added `validate_config_path()` for path security
- Added `validate_json_structure()` for JSON validation
- Implemented file size limits (1MB settings, 1KB lock files)
- Added atomic file writes (temp file + rename)
- Enhanced error logging (limited sensitive data)

### Changed
- Improved error messages with context-aware descriptions
- Enhanced visual feedback with color coding
- Better status indicators for clock lock status

### Fixed
- Multi-GPU command execution (proper GPU ID injection)
- Settings persistence per-GPU
- Clock lock file management per-GPU
- Desktop entry for KDE Plasma compatibility

### Documentation
- Added comprehensive README with features and usage
- Created installation guide
- Created packaging guide
- Created AUR submission guide
- Added code docstrings
- Created review documentation

## [Unreleased]

### Planned
- Fan curve editor (temperature-based)
- Historical performance graphs
- Application-specific profiles
- Scheduled profiles
- CLI interface
- Web interface (optional)
- Better error recovery
- GPU disconnection handling
- Unit tests and integration tests

