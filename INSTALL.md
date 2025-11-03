# Installation Guide for NVIDIA GPU Control Panel

## Arch Linux Installation Methods

### Method 1: Using PKGBUILD (Recommended for Development)

1. **Clone or download the repository:**
   ```bash
   git clone https://github.com/RitzDaCat/nvidia-control-gui.git
   cd nvidia-control-gui
   ```

2. **Build and install the package:**
   ```bash
   # Using makepkg directly
   makepkg -si
   
   # Or using the Makefile
   make install
   ```

3. **The package will:**
   - Install all dependencies automatically
   - Install the application to `/opt/nvidia-control/`
   - Create the wrapper script `/usr/bin/nvidia-control-gui`
   - Install desktop entry to `/usr/share/applications/`
   - Install systemd service to `/usr/lib/systemd/user/`

### Method 2: Using install.sh Script

1. **Make the script executable:**
   ```bash
   chmod +x install.sh
   ```

2. **Run the installer:**
   ```bash
   ./install.sh
   ```

3. **Follow the prompts:**
   - The script will check for dependencies
   - Install required packages via pacman
   - Set up the application
   - Optionally enable autostart

### Method 3: AUR Package (Future)

Once published to AUR, install with:
```bash
yay -S nvidia-control-gui
# or
paru -S nvidia-control-gui
```

## Uninstallation

### If installed via PKGBUILD:
```bash
sudo pacman -R nvidia-control-gui
```

### If installed via install.sh:
```bash
nvidia-control-uninstall
```

### Manual Uninstallation:

1. **Remove application files:**
   ```bash
   sudo rm -rf /opt/nvidia-control
   sudo rm -f /usr/bin/nvidia-control-gui
   sudo rm -f /usr/share/applications/nvidia-control.desktop
   ```

2. **Remove systemd service (if enabled):**
   ```bash
   systemctl --user stop nvidia-control.service
   systemctl --user disable nvidia-control.service
   rm -f ~/.config/systemd/user/nvidia-control.service
   systemctl --user daemon-reload
   ```

3. **Remove configuration (optional):**
   ```bash
   rm -rf ~/.config/nvidia-control
   ```

## Dependencies

The following packages are required:
- `python` (>=3.6)
- `python-pyqt6`
- `nvidia-utils` (provides nvidia-smi)
- `nvidia-settings` (for advanced features)
- `polkit` (for privilege escalation)

Optional:
- `nvidia-dkms` (for kernel module support)

## Post-Installation

### Enable Autostart (Optional)

If you want the application to start automatically on login:

```bash
systemctl --user enable nvidia-control.service
systemctl --user start nvidia-control.service
```

### Enable Coolbits (Required for Fan Control)

To enable fan control and advanced overclocking features:

1. **Create X11 config directory:**
   ```bash
   sudo mkdir -p /etc/X11/xorg.conf.d
   ```

2. **Create/edit the NVIDIA config:**
   ```bash
   sudo nano /etc/X11/xorg.conf.d/20-nvidia.conf
   ```

3. **Add the following:**
   ```ini
   Section "Device"
       Identifier "NVIDIA Card"
       Driver "nvidia"
       Option "Coolbits" "4"
   EndSection
   ```

4. **Restart X server or reboot**

   **Note:** Value "4" enables manual fan control. Higher values enable more features:
   - 4: Manual fan control
   - 8: Power limit adjustment
   - 12: Fan control + Power limit
   - 28: Full overclocking support (fan, power, voltage, clock offsets)

### Verifying Installation

1. **Check if the application is accessible:**
   ```bash
   which nvidia-control-gui
   nvidia-control-gui --help
   ```

2. **Check desktop entry:**
   ```bash
   desktop-file-validate /usr/share/applications/nvidia-control.desktop
   ```

3. **Verify dependencies:**
   ```bash
   python3 -c "import PyQt6; print('PyQt6 OK')"
   nvidia-smi
   nvidia-settings --version
   ```

## Troubleshooting

### Application won't start

1. **Check Python installation:**
   ```bash
   python3 --version
   python3 -c "import PyQt6"
   ```

2. **Check NVIDIA drivers:**
   ```bash
   nvidia-smi
   ```

3. **Check permissions:**
   ```bash
   ls -l /usr/bin/nvidia-control-gui
   ls -l /opt/nvidia-control/nvidia_control_gui.py
   ```

### Permission errors

The application uses `pkexec` (polkit) for privilege escalation. Ensure:
- `polkit` is installed
- Your user is in the appropriate group
- Password prompts work correctly

### Fan control not working

- Ensure Coolbits is enabled in X config (see above)
- Restart X server or reboot after enabling Coolbits
- Check if your GPU supports manual fan control

### Package build fails

If `makepkg` fails:
1. Check PKGBUILD syntax: `namcap PKGBUILD`
2. Ensure all dependencies are installed
3. Check source file paths in PKGBUILD

## Building for Distribution

To create a package for distribution:

```bash
# Update version in PKGBUILD
# Create source tarball
make source

# Build package
cd build && makepkg

# Install locally
sudo pacman -U nvidia-control-gui-*.pkg.tar.zst

# Or upload to AUR (requires AUR account)
```

## File Locations

- **Application:** `/opt/nvidia-control/nvidia_control_gui.py`
- **Wrapper script:** `/usr/bin/nvidia-control-gui`
- **Desktop entry:** `/usr/share/applications/nvidia-control.desktop`
- **Systemd service:** `/usr/lib/systemd/user/nvidia-control.service`
- **User config:** `~/.config/nvidia-control/`
- **Settings:** `~/.config/nvidia-control/settings_gpu*.json`
- **Clock locks:** `~/.config/nvidia-control/clock_lock_status_gpu*.txt`

