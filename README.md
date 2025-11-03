# NVIDIA GPU Control Panel

A comprehensive GUI tool for managing NVIDIA GPU settings on Linux, specifically designed for Arch-based systems like CachyOS.

## Badges

[![License](https://img.shields.io/badge/license-GPL3-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/ritzdacat/nvidia-control-gui/releases)
[![Python](https://img.shields.io/badge/python-3.6+-green.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Linux-lightgrey.svg)](https://www.linux.org/)
[![Arch Linux](https://img.shields.io/badge/arch%20linux-supported-blue.svg)](https://archlinux.org/)
[![Maintenance](https://img.shields.io/badge/maintenance-actively--developed-brightgreen.svg)](https://github.com/ritzdacat/nvidia-control-gui)

### Dependencies

[![PyQt6](https://img.shields.io/badge/PyQt6-6.0%2B-41cd52.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![NVIDIA Drivers](https://img.shields.io/badge/NVIDIA-Drivers%20Required-red.svg)](https://www.nvidia.com/Download/index.aspx)
[![Polkit](https://img.shields.io/badge/polkit-required-orange.svg)](https://www.freedesktop.org/wiki/Software/polkit/)
[![nvidia-settings](https://img.shields.io/badge/nvidia--settings-required-orange.svg)](https://github.com/NVIDIA/nvidia-settings)

---

**Note**: Replace `ritzdacat` in badge URLs with your actual GitHub username after creating the repository.

## Overview

The NVIDIA GPU Control Panel provides a user-friendly interface for managing GPU settings that are typically configured via command-line tools. It addresses common needs such as preventing GPU downclocking during gaming, managing power consumption, controlling fan speeds, and creating performance profiles for different use cases.

### What This Tool Does

This application solves the problem of manually configuring NVIDIA GPU settings through command-line tools. It provides:

- **Clock Management**: Lock GPU core clock speeds to prevent downclocking during gaming or demanding workloads
- **Power Control**: Adjust power limits to balance performance and power consumption
- **Fan Control**: Manually control fan speeds for optimal cooling (requires Coolbits)
- **Profile Management**: Save and quickly switch between different GPU configurations
- **Multi-GPU Support**: Manage multiple NVIDIA GPUs independently
- **Settings Persistence**: Automatically restore your preferred settings after reboot

### When to Use This Tool

Use this tool when you need to:

- Prevent GPU clock drops during gaming
- Optimize power consumption for your workload
- Control fan speeds manually for quieter or cooler operation
- Quickly switch between performance profiles (gaming, quiet, mining, etc.)
- Manage multiple NVIDIA GPUs with different settings

## Features

### Clock Control

Set minimum and maximum GPU core clock speeds (210-3200 MHz) to lock the GPU to a specific performance range. This prevents the GPU from downclocking, providing consistent performance during gaming or other demanding applications.

- Core clock management with validation against GPU capabilities
- Memory clock offset adjustment (-2000 to +2000 MHz)
- Clock lock/unlock functionality
- Real-time clock speed monitoring
- Per-GPU clock settings

### Power Management

Control GPU power consumption to balance performance and power draw. Useful for reducing heat output, power bills, or optimizing for specific workloads.

- Power limit control (100-600W, automatically adjusted to GPU capabilities)
- Persistence mode toggle (keeps GPU initialized for faster response)
- Performance mode selection (Adaptive, Maximum Performance, Auto)
- Real-time power draw monitoring
- Temperature monitoring with visual warnings

### Fan Control

Manually control GPU fan speeds for optimal cooling or quieter operation. Requires Coolbits to be enabled in your X configuration.

- Manual fan speed control (0-100%)
- Automatic fan control mode (GPU default)
- Coolbits detection and status display
- Real-time fan speed monitoring
- Safety warnings for low fan speeds

### Monitoring

Real-time monitoring of GPU statistics to help you understand current GPU state and make informed decisions about settings.

- Current clock speeds (graphics and memory)
- Temperature display with color-coded warnings
- Power draw and power limit
- GPU and memory utilization (0-100%)
- Performance state information (P0-P12)
- Detailed monitoring tab with full nvidia-smi output
- Auto-refresh capability (2-second intervals)

### Profile Management

Quick profiles for common use cases, plus the ability to save and load custom profiles.

**Quick Profiles**:
- **Gaming**: Maximum performance (2400-2850 MHz, 450W)
- **Balanced**: Default adaptive clocking for general use
- **Quiet**: Low power for silent operation (210-1500 MHz, 250W)
- **Mining**: Optimized for cryptocurrency mining workloads

**Custom Profiles**: Save your own configurations and load them with a single click or keyboard shortcut.

### Additional Features

- **Keyboard Shortcuts**: Quick access to common functions
- **Comprehensive Tooltips**: Detailed help text on all controls
- **Visual Feedback**: Color-coded indicators for temperature, fan speed, and performance
- **System Tray Integration**: Minimize to tray, quick access from system tray
- **Settings Persistence**: Automatic saving of settings per-GPU across reboots
- **Multi-GPU Support**: Switch between GPUs with a dropdown selector
- **Systemd Service**: Optional autostart service for settings restoration
- **Desktop Entry**: Integration with application menus (KDE Plasma, GNOME, etc.)
- **Help System**: Built-in help dialog with shortcuts and tips

## Requirements

### System Requirements

- **Operating System**: Linux (Arch-based recommended, but works on any Linux with NVIDIA drivers)
- **GPU**: NVIDIA GPU with proprietary drivers installed
- **Python**: Version 3.6 or higher

### Dependencies

The following packages are required:

| Package | Purpose | Arch Package |
|---------|---------|--------------|
| [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) | GUI framework | `python-pyqt6` |
| [Polkit](https://www.freedesktop.org/wiki/Software/polkit/) | Privilege escalation | `polkit` |
| [nvidia-utils](https://archlinux.org/packages/extra/x86_64/nvidia-utils/) | Provides nvidia-smi command | `nvidia-utils` |
| [nvidia-settings](https://github.com/NVIDIA/nvidia-settings) | Advanced GPU control features | `nvidia-settings` |

**Optional Dependencies**:
- `nvidia-dkms` - For kernel module support (DKMS variant)

### Verifying Requirements

Before installation, verify your system meets the requirements:

```bash
# Check NVIDIA drivers
nvidia-smi

# Check Python version
python3 --version  # Should be 3.6 or higher

# Check PyQt6 availability
python3 -c "import PyQt6"  # Should not error
```

## Installation

### Method 1: PKGBUILD (Recommended for Arch Linux)

This method creates a proper Arch Linux package that can be managed with pacman.

```bash
# Clone the repository
git clone https://github.com/ritzdacat/nvidia-control-gui.git
cd nvidia-control-gui

# Build and install
makepkg -si

# Or using Makefile
make install
```

**Benefits**: Package is tracked by pacman, easy to update or remove, dependencies handled automatically.

### Method 2: install.sh Script

Quick installation script for manual setup.

```bash
chmod +x install.sh
./install.sh
```

The script will:
- Check system requirements
- Install dependencies via pacman
- Set up application files
- Create desktop entry
- Optionally configure autostart

**Benefits**: Simple, interactive, creates uninstaller script.

### Method 3: AUR (Future)

[![AUR version](https://img.shields.io/aur/version/nvidia-control-gui)](https://aur.archlinux.org/packages/nvidia-control-gui)
[![AUR votes](https://img.shields.io/aur/votes/nvidia-control-gui)](https://aur.archlinux.org/packages/nvidia-control-gui)
[![AUR popularity](https://img.shields.io/aur/popularity/nvidia-control-gui)](https://aur.archlinux.org/packages/nvidia-control-gui)

Once published to AUR:

```bash
yay -S nvidia-control-gui
# or
paru -S nvidia-control-gui
```

See [INSTALL.md](INSTALL.md) for detailed installation instructions, troubleshooting, and post-installation setup.

## Uninstallation

### If Installed via PKGBUILD

```bash
sudo pacman -R nvidia-control-gui
```

This removes all installed files except user configuration files in `~/.config/nvidia-control/`.

### If Installed via install.sh

```bash
# Use the uninstaller script
chmod +x uninstall.sh
./uninstall.sh

# Or use the installed uninstaller
nvidia-control-uninstall
```

The uninstaller will ask if you want to remove configuration files.

## Usage

### Starting the Application

The application can be started in three ways:

- **Terminal**: Run `nvidia-control-gui` from the command line
- **Application Menu**: Look for "NVIDIA GPU Control" in your desktop environment's application menu
- **System Tray**: If running, double-click the tray icon to show/hide the window

### Keyboard Shortcuts

Keyboard shortcuts provide quick access to common functions:

| Shortcut | Action |
|----------|--------|
| `F5` | Refresh GPU information |
| `Ctrl+L` | Apply clock lock settings |
| `Ctrl+R` | Reset clocks to default |
| `Ctrl+S` | Save current settings as profile |
| `Ctrl+O` | Load saved profile |
| `Ctrl+1` | Switch to Clock Control tab |
| `Ctrl+2` | Switch to Power Management tab |
| `Ctrl+3` | Switch to Fan Control tab |
| `Ctrl+4` | Switch to Profiles tab |
| `Ctrl+5` | Switch to Monitoring tab |
| `F1` | Show help dialog |

### Preventing GPU Downclocking During Gaming

**Problem**: GPU downclocks during gaming, causing inconsistent performance.

**Solution**: Lock the GPU to a specific clock range.

1. Go to the **Clock Control** tab
2. Set your desired minimum clock (recommended: 2400+ MHz for RTX 4090)
3. Set your desired maximum clock (typically 2850 MHz)
4. Click **Apply Clock Settings** (or press `Ctrl+L`)

The GPU will now maintain clocks within this range, preventing downclocking. Use **Reset to Default** (or `Ctrl+R`) to remove the lock.

### Reducing Power Consumption and Heat

**Problem**: GPU consumes too much power or generates too much heat.

**Solution**: Lower the power limit.

1. Go to the **Power Management** tab
2. Adjust the power limit slider to a lower value (e.g., 300W instead of 450W)
3. Click **Apply Power Limit**

This caps maximum power consumption, reducing heat output and power draw. Monitor temperatures to ensure adequate cooling.

### Controlling Fan Speed Manually

**Problem**: GPU fan is too loud or not cooling adequately.

**Solution**: Manual fan control (requires Coolbits setup).

1. First, enable Coolbits in your X configuration (see [Coolbits Setup](#coolbits-setup))
2. Restart X server or reboot
3. Go to the **Fan Control** tab
4. Select **Manual Fan Control**
5. Adjust the fan speed slider (recommended: 30-70% for balance)
6. Click **Apply Fan Speed**

**Warning**: Very low fan speeds (<20%) may cause overheating. Monitor temperatures carefully.

### Creating and Using Profiles

**Problem**: Need to quickly switch between different GPU configurations for different use cases.

**Solution**: Use profiles.

**Quick Profiles**:
- Select a profile from the **Profiles** tab
- Click the profile button (Gaming, Balanced, Quiet, or Mining)
- Confirm the application

**Custom Profiles**:
1. Configure your desired settings (clocks, power, performance mode)
2. Go to **Profiles** tab
3. Click **Save Current Settings** (or press `Ctrl+S`)
4. To load later, click **Load Saved Profile** (or press `Ctrl+O`)

### Managing Multiple GPUs

**Problem**: System has multiple NVIDIA GPUs that need different settings.

**Solution**: Use the GPU selector.

1. The GPU selector dropdown appears automatically when multiple GPUs are detected
2. Select the GPU you want to configure from the dropdown in the header
3. Configure settings independently for each GPU
4. Settings are automatically saved per-GPU (`settings_gpu0.json`, `settings_gpu1.json`, etc.)

### Restoring Settings After Reboot

**Problem**: Settings are lost after reboot.

**Solution**: Enable settings restoration.

1. Go to **Settings** menu → **Restore All Settings on Startup**
2. Check the option to enable automatic restoration
3. Your settings will be restored automatically on next startup

Alternatively, generate a systemd service file:
1. Go to **Settings** menu → **Generate Systemd Service**
2. Follow the instructions to install and enable the service

## Coolbits Setup

Coolbits is required for fan control and some advanced features. It's an X configuration option that enables additional GPU control capabilities.

### Why Coolbits is Needed

Without Coolbits, the NVIDIA driver restricts certain operations for safety. Enabling Coolbits allows:
- Manual fan control
- Power limit adjustment (on some systems)
- Advanced overclocking features

### How to Enable Coolbits

1. **Create X11 config directory** (if it doesn't exist):
   ```bash
   sudo mkdir -p /etc/X11/xorg.conf.d
   ```

2. **Create or edit the NVIDIA config file**:
   ```bash
   sudo nano /etc/X11/xorg.conf.d/20-nvidia.conf
   ```

3. **Add the following configuration**:
   ```ini
   Section "Device"
       Identifier "NVIDIA Card"
       Driver "nvidia"
       Option "Coolbits" "4"
   EndSection
   ```

4. **Restart X server or reboot**:
   - Restart your display manager (e.g., `sudo systemctl restart sddm`)
   - Or simply reboot: `sudo reboot`

### Coolbits Values

Different Coolbits values enable different features:

- `4`: Manual fan control
- `8`: Power limit adjustment
- `12`: Fan control + Power limit
- `28`: Full overclocking support (fan, power, voltage, clock offsets)

**Recommendation**: Start with `4` for fan control. Increase if you need additional features.

### Verifying Coolbits

After enabling Coolbits and restarting, check the **Fan Control** tab in the application. The Coolbits status should show "Enabled" in green.

## Troubleshooting

### Command Failed Errors

**Symptoms**: Operations fail with "Command Failed" error messages.

**Possible Causes and Solutions**:

1. **Missing root privileges**:
   - Ensure `polkit` is installed: `pacman -Q polkit`
   - Verify `pkexec` is available: `which pkexec`
   - You may need to enter your password when prompted

2. **NVIDIA drivers not installed**:
   - Install drivers: `sudo pacman -S nvidia nvidia-utils`
   - Verify: `nvidia-smi` should work

3. **Missing nvidia-settings**:
   - Install: `sudo pacman -S nvidia-settings`
   - Required for fan control and memory offset

### GPU Not Detected

**Symptoms**: Application shows "GPU: Detecting..." or no GPU information.

**Possible Causes and Solutions**:

1. **NVIDIA drivers not loaded**:
   ```bash
   # Check if drivers are loaded
   lsmod | grep nvidia
   
   # If not, install and load drivers
   sudo pacman -S nvidia nvidia-utils
   sudo modprobe nvidia
   ```

2. **Driver version incompatible**:
   ```bash
   # Check driver version
   nvidia-smi --query-gpu=driver_version --format=csv
   
   # Update if needed
   sudo pacman -Syu nvidia nvidia-utils
   ```

3. **GPU not visible to system**:
   ```bash
   # List all GPUs
   nvidia-smi --list-gpus
   
   # If empty, check hardware connection
   ```

### Clock Settings Not Applying

**Symptoms**: Clock lock settings don't seem to take effect.

**Possible Causes and Solutions**:

1. **Clock values out of GPU range**:
   - Check GPU's supported clock range
   - Try more conservative values
   - Some GPUs have hardware limitations

2. **Thermal throttling**:
   - Monitor temperature (should be <80°C)
   - Ensure adequate cooling
   - GPU may downclock if overheating

3. **Power limit too low**:
   - Increase power limit to allow higher clocks
   - Check if power limit is sufficient for desired clocks

### Fan Control Not Working

**Symptoms**: Manual fan control doesn't work or shows errors.

**Possible Causes and Solutions**:

1. **Coolbits not enabled**:
   - Verify Coolbits is enabled in X config
   - Restart X server or reboot after enabling
   - Check Coolbits status in the Fan Control tab

2. **GPU doesn't support manual fan control**:
   - Some GPUs have locked fan control
   - Check GPU documentation
   - Use automatic mode instead

3. **nvidia-settings not installed**:
   - Install: `sudo pacman -S nvidia-settings`
   - Required for fan control

### Application Won't Start

**Symptoms**: Application doesn't launch or crashes immediately.

**Possible Causes and Solutions**:

1. **Python version too old**:
   ```bash
   python3 --version  # Should be 3.6 or higher
   ```

2. **PyQt6 not installed**:
   ```bash
   python3 -c "import PyQt6"  # Should not error
   sudo pacman -S python-pyqt6
   ```

3. **Missing dependencies**:
   ```bash
   # Check all dependencies
   pacman -Q python python-pyqt6 polkit nvidia-utils nvidia-settings
   ```

4. **Check error messages**:
   - Run from terminal: `nvidia-control-gui`
   - Read error output for specific issues

### Application Not Appearing in Menu (KDE Plasma)

**Symptoms**: Application doesn't show in application launcher.

**Solution**:

1. **Update desktop database**:
   ```bash
   sudo update-desktop-database
   ```

2. **Rebuild KDE menu cache**:
   ```bash
   # For KDE 5
   kbuildsycoca5 --noincremental
   
   # For KDE 6
   kbuildsycoca6 --noincremental
   ```

3. **Restart Plasma**:
   ```bash
   kquitapp5 plasmashell && kstart5 plasmashell
   ```

4. **Or use the provided script**:
   ```bash
   ./fix-kde-menu.sh
   ```

### RTX 4090 Specific Issues

**Problem**: RTX 4090 experiences aggressive downclocking.

**Solution**:

1. Set minimum clock to 2400+ MHz to prevent aggressive downclocking
2. Ensure power limit is set appropriately (450W recommended)
3. Monitor thermal conditions - GPU may downclock due to temperature
4. Use "Prefer Maximum Performance" mode for consistent clocks
5. Consider enabling persistence mode for faster response

## File Locations

Reference for where files are installed and stored:

| Component | Location |
|-----------|----------|
| Application | `/opt/nvidia-control/nvidia_control_gui.py` |
| Wrapper Script | `/usr/bin/nvidia-control-gui` |
| Desktop Entry | `/usr/share/applications/nvidia-control.desktop` |
| Systemd Service | `/usr/lib/systemd/user/nvidia-control.service` |
| User Config Directory | `~/.config/nvidia-control/` |
| Settings (per GPU) | `~/.config/nvidia-control/settings_gpu*.json` |
| Clock Locks (per GPU) | `~/.config/nvidia-control/clock_lock_status_gpu*.txt` |

## Security

This application includes security measures to protect against common vulnerabilities:

- **Input Validation**: All user inputs are validated before use
- **Path Validation**: File paths are validated to prevent directory traversal attacks
- **JSON Validation**: JSON structures are validated before parsing
- **File Size Limits**: Limits prevent denial-of-service attacks via large files
- **Atomic Operations**: File writes use atomic operations to prevent corruption
- **Command Whitelist**: Only allowed commands (nvidia-smi, nvidia-settings) can be executed
- **GPU ID Validation**: GPU IDs are validated before use in commands

For details on security implementation, see the code documentation.

## Contributing

[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](.github/CONTRIBUTING.md)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/ritzdacat/nvidia-control-gui/pulls)

Contributions are welcome. Please see [CONTRIBUTING.md](.github/CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone repository
git clone https://github.com/ritzdacat/nvidia-control-gui.git
cd nvidia-control-gui

# Install dependencies
sudo pacman -S python python-pyqt6 polkit nvidia-utils nvidia-settings

# Run directly
python3 nvidia_control_gui.py
```

### Code Style

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Add docstrings to all public methods
- Test changes thoroughly before submitting

## License

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

This project is licensed under the GPL3 License - see the [LICENSE](LICENSE) file for details.

## Safety Notes

**Important Warnings**:

- Incorrect clock or voltage settings can cause system instability
- Excessive overclocking may damage your GPU
- Always monitor temperatures when adjusting settings
- Use profiles as a starting point and adjust carefully
- Very low fan speeds may cause overheating - use with caution
- The application includes safety checks, but use at your own risk

## Documentation

Additional documentation is available:

- [INSTALL.md](INSTALL.md) - Detailed installation guide
- [PACKAGING.md](PACKAGING.md) - Arch Linux packaging guide
- [AUR-SUBMISSION.md](AUR-SUBMISSION.md) - AUR submission guide
- [CHANGELOG.md](CHANGELOG.md) - Version history and changes
- [CONTRIBUTING.md](.github/CONTRIBUTING.md) - Contribution guidelines

## Acknowledgments

- Built with [PyQt6](https://www.riverbankcomputing.com/software/pyqt/)
- Uses `nvidia-smi` and `nvidia-settings` for GPU control
- Designed for Arch Linux and CachyOS
- Created for the Linux gaming and power user community
