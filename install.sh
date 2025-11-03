#!/bin/bash

# NVIDIA GPU Control Panel Installation Script for Arch/CachyOS

# Use set -euo pipefail for better error handling, but handle expected failures
set -uo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track installation steps for cleanup on failure
INSTALLED_FILES=()
INSTALLED_DIRS=()

# Cleanup function
cleanup_on_failure() {
    if [ ${#INSTALLED_FILES[@]} -gt 0 ] || [ ${#INSTALLED_DIRS[@]} -gt 0 ]; then
        echo -e "\n${YELLOW}Cleaning up partial installation...${NC}"
        for file in "${INSTALLED_FILES[@]}"; do
            [ -f "$file" ] && sudo rm -f "$file" 2>/dev/null || true
        done
        for dir in "${INSTALLED_DIRS[@]}"; do
            [ -d "$dir" ] && sudo rmdir "$dir" 2>/dev/null || true
        done
    fi
}

trap cleanup_on_failure ERR

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}NVIDIA GPU Control Panel Installer${NC}"
echo -e "${GREEN}======================================${NC}"

# Check if running Arch-based system
if [ ! -f /etc/arch-release ]; then
    echo -e "${RED}This installer is designed for Arch-based systems only${NC}"
    exit 1
fi

# Check for root/sudo
if [ "$EUID" -eq 0 ]; then
   echo -e "${RED}Please don't run this script as root${NC}"
   exit 1
fi

# Check if sudo is available
if ! command -v sudo &> /dev/null; then
    echo -e "${RED}sudo is not installed or not available${NC}"
    echo "Please install sudo or run as root (not recommended)"
    exit 1
fi

# Test sudo access
if ! sudo -n true 2>/dev/null; then
    echo -e "${YELLOW}This script requires sudo privileges. You may be prompted for your password.${NC}"
    sudo -v || {
        echo -e "${RED}Failed to get sudo privileges${NC}"
        exit 1
    }
fi

echo -e "${YELLOW}Checking system requirements...${NC}"

# Check for NVIDIA driver
if ! command -v nvidia-smi &> /dev/null; then
    echo -e "${RED}NVIDIA driver not found. Please install nvidia drivers first${NC}"
    echo "For CachyOS: sudo pacman -S nvidia-dkms nvidia-utils"
    exit 1
fi

# Check for required files
REQUIRED_FILES=("nvidia_control_gui.py" "nvidia-control.desktop")
MISSING_FILES=()

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    echo -e "${RED}Missing required files:${NC}"
    for file in "${MISSING_FILES[@]}"; do
        echo "  - $file"
    done
    echo -e "${RED}Please run this script from the project directory${NC}"
    exit 1
fi

# Function to check Python version
check_python_version() {
    local python_cmd=""
    
    # Try python3 first, then python
    if command -v python3 &> /dev/null; then
        python_cmd="python3"
    elif command -v python &> /dev/null; then
        python_cmd="python"
    else
        echo -e "${RED}Python is not installed${NC}"
        return 1
    fi
    
    # Check Python version (needs 3.6+)
    local version=$($python_cmd --version 2>&1 | awk '{print $2}')
    local major=$(echo "$version" | cut -d. -f1)
    local minor=$(echo "$version" | cut -d. -f2)
    
    if [ "$major" -lt 3 ] || ([ "$major" -eq 3 ] && [ "$minor" -lt 6 ]); then
        echo -e "${RED}Python 3.6+ is required. Found: Python $version${NC}"
        return 1
    fi
    
    echo -e "${GREEN}Found Python $version${NC}"
    return 0
}

# Function to install packages
install_packages() {
    echo -e "${YELLOW}Installing required packages...${NC}"
    
    # Always use pacman for official packages (more reliable and faster)
    echo "Installing official packages..."
    if ! sudo pacman -S --needed --noconfirm python python-pyqt6 python-pip polkit nvidia-settings 2>/dev/null; then
        echo -e "${YELLOW}Some packages may require confirmation. Retrying with confirmation...${NC}"
        sudo pacman -S --needed python python-pyqt6 python-pip polkit nvidia-settings || {
            echo -e "${RED}Failed to install required packages${NC}"
            exit 1
        }
    fi
    
    # Verify Python installation
    if ! check_python_version; then
        echo -e "${RED}Python version check failed after installation${NC}"
        exit 1
    fi
    
    # Verify PyQt6 installation
    echo "Verifying PyQt6 installation..."
    if ! python3 -c "import PyQt6" 2>/dev/null; then
        echo -e "${RED}PyQt6 installation verification failed${NC}"
        echo "Try: python3 -c 'import PyQt6' to see the error"
        exit 1
    fi
    
    echo -e "${GREEN}All packages installed successfully${NC}"
}

# Function to setup the application
setup_application() {
    echo -e "${YELLOW}Setting up NVIDIA Control Panel...${NC}"
    
    # Create installation directory
    INSTALL_DIR="/opt/nvidia-control"
    if ! sudo mkdir -p "$INSTALL_DIR"; then
        echo -e "${RED}Failed to create installation directory${NC}"
        exit 1
    fi
    INSTALLED_DIRS+=("$INSTALL_DIR")
    
    # Copy application files
    if ! sudo cp nvidia_control_gui.py "$INSTALL_DIR/"; then
        echo -e "${RED}Failed to copy application file${NC}"
        exit 1
    fi
    
    if ! sudo chmod 755 "$INSTALL_DIR/nvidia_control_gui.py"; then
        echo -e "${RED}Failed to set permissions on application file${NC}"
        exit 1
    fi
    
    # Determine Python command (prefer python3)
    PYTHON_CMD="python3"
    if ! command -v python3 &> /dev/null; then
        PYTHON_CMD="python"
    fi
    
    # Create wrapper script
    if ! sudo tee /usr/bin/nvidia-control-gui > /dev/null << EOF
#!/bin/bash
cd /opt/nvidia-control
exec $PYTHON_CMD /opt/nvidia-control/nvidia_control_gui.py "\$@"
EOF
    then
        echo -e "${RED}Failed to create wrapper script${NC}"
        exit 1
    fi
    INSTALLED_FILES+=("/usr/bin/nvidia-control-gui")
    
    if ! sudo chmod 755 /usr/bin/nvidia-control-gui; then
        echo -e "${RED}Failed to set permissions on wrapper script${NC}"
        exit 1
    fi
    
    # Install desktop entry
    if [ ! -f "nvidia-control.desktop" ]; then
        echo -e "${RED}Desktop entry file not found${NC}"
        exit 1
    fi
    
    if ! sudo cp nvidia-control.desktop /usr/share/applications/; then
        echo -e "${RED}Failed to install desktop entry${NC}"
        exit 1
    fi
    INSTALLED_FILES+=("/usr/share/applications/nvidia-control.desktop")
    
    if ! sudo chmod 644 /usr/share/applications/nvidia-control.desktop; then
        echo -e "${RED}Failed to set permissions on desktop entry${NC}"
        exit 1
    fi
    
    # Update desktop database
    if command -v update-desktop-database &> /dev/null; then
        echo "Updating desktop database..."
        sudo update-desktop-database 2>/dev/null || {
            echo -e "${YELLOW}Warning: Failed to update desktop database${NC}"
        }
    fi
    
    # Create config directory
    CONFIG_DIR="$HOME/.config/nvidia-control"
    if ! mkdir -p "$CONFIG_DIR"; then
        echo -e "${YELLOW}Warning: Failed to create config directory${NC}"
    fi
    
    echo -e "${GREEN}Application installed successfully!${NC}"
}

# Function to setup autostart (optional)
setup_autostart() {
    echo -e "${YELLOW}Do you want to enable autostart? (y/n)${NC}"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        # Check if service file exists
        if [ ! -f "nvidia-control.service" ]; then
            echo -e "${YELLOW}Service file not found, skipping autostart setup${NC}"
            return 0
        fi
        
        # Create systemd user directory
        SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
        if ! mkdir -p "$SYSTEMD_USER_DIR"; then
            echo -e "${RED}Failed to create systemd user directory${NC}"
            return 1
        fi
        
        # Copy service file (already cleaned, no --minimized flag)
        if ! cp nvidia-control.service "$SYSTEMD_USER_DIR/nvidia-control.service"; then
            echo -e "${RED}Failed to copy service file${NC}"
            return 1
        fi
        
        # Enable and start the service
        if ! systemctl --user daemon-reload; then
            echo -e "${YELLOW}Warning: Failed to reload systemd daemon${NC}"
        fi
        
        if ! systemctl --user enable nvidia-control.service; then
            echo -e "${YELLOW}Warning: Failed to enable service${NC}"
        else
            echo -e "${GREEN}Autostart enabled${NC}"
            echo -e "${YELLOW}Note: The service will start automatically on next login${NC}"
        fi
    fi
}

# Function to create uninstaller
create_uninstaller() {
    sudo tee /usr/bin/nvidia-control-uninstall > /dev/null << 'EOF'
#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Uninstalling NVIDIA GPU Control Panel...${NC}"

# Stop and disable service if exists
if systemctl --user is-active --quiet nvidia-control.service 2>/dev/null; then
    echo "Stopping service..."
    systemctl --user stop nvidia-control.service 2>/dev/null
fi

if systemctl --user is-enabled --quiet nvidia-control.service 2>/dev/null; then
    echo "Disabling service..."
    systemctl --user disable nvidia-control.service 2>/dev/null
fi

if [ -f "$HOME/.config/systemd/user/nvidia-control.service" ]; then
    echo "Removing service file..."
    rm -f "$HOME/.config/systemd/user/nvidia-control.service"
    systemctl --user daemon-reload 2>/dev/null
fi

# Also check system-wide service location
if [ -f "/usr/lib/systemd/user/nvidia-control.service" ]; then
    echo "Note: System-wide service file at /usr/lib/systemd/user/nvidia-control.service"
    echo "      This will be removed by pacman if installed via package"
fi

# Remove application files (check existence first)
if [ -d "/opt/nvidia-control" ]; then
    echo "Removing application files..."
    sudo rm -rf /opt/nvidia-control
fi

if [ -f "/usr/bin/nvidia-control-gui" ]; then
    echo "Removing wrapper script..."
    sudo rm -f /usr/bin/nvidia-control-gui
fi

if [ -f "/usr/share/applications/nvidia-control.desktop" ]; then
    echo "Removing desktop entry..."
    sudo rm -f /usr/share/applications/nvidia-control.desktop
fi

# Update desktop database
if command -v update-desktop-database &> /dev/null; then
    echo "Updating desktop database..."
    sudo update-desktop-database 2>/dev/null || true
fi

# Remove config directory (optional)
if [ -d "$HOME/.config/nvidia-control" ]; then
    echo -e "${YELLOW}Remove configuration files? (y/n)${NC}"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        rm -rf "$HOME/.config/nvidia-control"
        echo -e "${GREEN}Configuration files removed${NC}"
    else
        echo -e "${YELLOW}Configuration files kept at $HOME/.config/nvidia-control${NC}"
    fi
fi

# Remove uninstaller itself (last)
if [ -f "/usr/bin/nvidia-control-uninstall" ]; then
    sudo rm -f /usr/bin/nvidia-control-uninstall
fi

echo -e "${GREEN}NVIDIA GPU Control Panel uninstalled successfully!${NC}"
EOF
    
    if ! sudo chmod 755 /usr/bin/nvidia-control-uninstall; then
        echo -e "${YELLOW}Warning: Failed to set permissions on uninstaller${NC}"
    else
        INSTALLED_FILES+=("/usr/bin/nvidia-control-uninstall")
        echo -e "${GREEN}Uninstaller created at /usr/bin/nvidia-control-uninstall${NC}"
    fi
}

# Main installation process
main() {
    echo -e "${YELLOW}This will install NVIDIA GPU Control Panel${NC}"
    echo "The following will be installed:"
    echo "  - Python 3.6+ and PyQt6 packages"
    echo "  - NVIDIA Control GUI application"
    echo "  - Desktop entry for application menu"
    echo "  - nvidia-settings (for advanced features)"
    echo "  - Optional: Autostart service"
    echo ""
    echo -e "${YELLOW}Continue with installation? (y/n)${NC}"
    read -r response
    
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "Installation cancelled"
        exit 0
    fi
    
    # Run installation steps
    install_packages || {
        echo -e "${RED}Package installation failed${NC}"
        exit 1
    }
    
    setup_application || {
        echo -e "${RED}Application setup failed${NC}"
        exit 1
    }
    
    setup_autostart || {
        echo -e "${YELLOW}Warning: Autostart setup had issues${NC}"
    }
    
    create_uninstaller || {
        echo -e "${YELLOW}Warning: Uninstaller creation had issues${NC}"
    }
    
    # Clear trap since installation succeeded
    trap - ERR
    
    echo ""
    echo -e "${GREEN}======================================${NC}"
    echo -e "${GREEN}Installation Complete!${NC}"
    echo -e "${GREEN}======================================${NC}"
    echo ""
    echo "You can now run the application:"
    echo "  - From terminal: nvidia-control-gui"
    echo "  - From application menu: Look for 'NVIDIA GPU Control'"
    echo ""
    echo "To uninstall, run: nvidia-control-uninstall"
    echo ""
    echo -e "${YELLOW}Note: Some features require root privileges via polkit${NC}"
    echo -e "${YELLOW}The application will prompt for password when needed${NC}"
}

# Run main installation
main