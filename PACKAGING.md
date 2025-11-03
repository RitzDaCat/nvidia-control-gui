# Packaging Guide for Arch Linux

## Overview

This document explains how to package `nvidia-control-gui` for Arch Linux using `pacman`.

## Installation Methods Comparison

### Method 1: PKGBUILD (Recommended for Distribution)

**Pros:**
- Standard Arch Linux packaging method
- Automatic dependency management
- Clean uninstallation via `pacman -R`
- Can be published to AUR
- Follows Arch Linux packaging standards

**Cons:**
- Requires understanding of PKGBUILD syntax
- More setup for first-time users

**Usage:**
```bash
makepkg -si
```

### Method 2: install.sh Script

**Pros:**
- Simple and straightforward
- Interactive prompts
- Creates uninstaller script
- Good for quick installation

**Cons:**
- Not tracked by pacman
- Manual dependency management
- Less "Arch-like"

**Usage:**
```bash
chmod +x install.sh
./install.sh
```

## PKGBUILD Details

### File Structure

```
nvidia-control-gui/
├── PKGBUILD              # Package build script
├── .SRCINFO              # AUR metadata (auto-generated)
├── nvidia_control_gui.py # Main application
├── nvidia-control.desktop # Desktop entry
└── nvidia-control.service # Systemd service
```

### Building the Package

1. **From local directory:**
   ```bash
   makepkg -si
   ```
   - `-s`: Install dependencies automatically
   - `-i`: Install package after building

2. **Build without installing:**
   ```bash
   makepkg
   ```

3. **Check package with namcap:**
   ```bash
   namcap PKGBUILD
   namcap nvidia-control-gui-*.pkg.tar.zst
   ```

### Installing the Built Package

```bash
sudo pacman -U nvidia-control-gui-*.pkg.tar.zst
```

### Uninstalling

```bash
sudo pacman -R nvidia-control-gui
```

## AUR Submission (Future)

To submit to AUR:

1. **Create AUR account** at https://aur.archlinux.org

2. **Clone AUR repository:**
   ```bash
   git clone ssh://aur@aur.archlinux.org/nvidia-control-gui.git
   cd nvidia-control-gui
   ```

3. **Copy files:**
   ```bash
   cp ../nvidia-control-gui/PKGBUILD .
   cp ../nvidia-control-gui/.SRCINFO .
   # Or generate .SRCINFO:
   makepkg --printsrcinfo > .SRCINFO
   ```

4. **Commit and push:**
   ```bash
   git add PKGBUILD .SRCINFO
   git commit -m "Initial package release"
   git push
   ```

5. **Users can then install:**
   ```bash
   yay -S nvidia-control-gui
   # or
   paru -S nvidia-control-gui
   ```

## Version Management

### Updating Version

1. **Update PKGBUILD:**
   ```bash
   pkgver=1.0.1
   pkgrel=1  # Reset to 1 for new version
   ```

2. **Regenerate .SRCINFO:**
   ```bash
   makepkg --printsrcinfo > .SRCINFO
   ```

3. **Build and test:**
   ```bash
   makepkg -si
   ```

### Release Process

1. Create git tag: `git tag v1.0.1`
2. Update PKGBUILD version
3. Build package: `makepkg`
4. Test installation: `sudo pacman -U *.pkg.tar.zst`
5. Test uninstallation: `sudo pacman -R nvidia-control-gui`
6. Upload to AUR (if applicable)

## File Locations After Installation

| Component | Location |
|-----------|----------|
| Application | `/opt/nvidia-control/nvidia_control_gui.py` |
| Wrapper Script | `/usr/bin/nvidia-control-gui` |
| Desktop Entry | `/usr/share/applications/nvidia-control.desktop` |
| Systemd Service | `/usr/lib/systemd/user/nvidia-control.service` |
| User Config | `~/.config/nvidia-control/` |

## Dependencies

### Required
- `python` (>=3.6)
- `python-pyqt6`
- `nvidia-utils` (provides nvidia-smi)
- `nvidia-settings`
- `polkit`

### Optional
- `nvidia-dkms` (for kernel module support)

## Testing the Package

### Before Building

```bash
# Check PKGBUILD syntax
namcap PKGBUILD

# Verify source files exist
ls -la nvidia_control_gui.py nvidia-control.desktop nvidia-control.service
```

### After Building

```bash
# Check package
namcap nvidia-control-gui-*.pkg.tar.zst

# Test installation
sudo pacman -U nvidia-control-gui-*.pkg.tar.zst

# Verify files installed correctly
ls -la /opt/nvidia-control/
ls -la /usr/bin/nvidia-control-gui
ls -la /usr/share/applications/nvidia-control.desktop

# Test application
nvidia-control-gui --help

# Test uninstallation
sudo pacman -R nvidia-control-gui
```

## Troubleshooting

### makepkg Fails

1. **Check dependencies:**
   ```bash
   sudo pacman -S base-devel
   ```

2. **Check PKGBUILD syntax:**
   ```bash
   bash -n PKGBUILD
   ```

3. **Check file permissions:**
   ```bash
   chmod +x nvidia_control_gui.py
   ```

### Package Installation Fails

1. **Check conflicts:**
   ```bash
   pacman -Qo /usr/bin/nvidia-control-gui
   ```

2. **Check dependencies:**
   ```bash
   pacman -Q python python-pyqt6 nvidia-utils nvidia-settings polkit
   ```

### Desktop Entry Not Appearing

1. **Update desktop database:**
   ```bash
   sudo update-desktop-database
   ```

2. **Check desktop entry:**
   ```bash
   desktop-file-validate /usr/share/applications/nvidia-control.desktop
   ```

## Makefile Targets

The included Makefile provides convenient shortcuts:

```bash
make package    # Build package
make source     # Create source tarball
make install    # Build and install
make clean      # Remove build artifacts
make test       # Test PKGBUILD syntax
```

## Notes

- The PKGBUILD uses `SKIP` for sha256sums when building from local files
- For AUR, you'll need to provide proper source URLs and checksums
- The package installs to `/opt/nvidia-control` to follow FHS
- Systemd service is installed but not enabled by default
- User config directory is created in `/etc/skel` for new users

