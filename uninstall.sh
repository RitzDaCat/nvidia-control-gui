#!/bin/bash

# NVIDIA GPU Control Panel Uninstaller
# Handles uninstallation for packages installed via install.sh

set -uo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}NVIDIA GPU Control Panel Uninstaller${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# Check if running Arch-based system
if [ ! -f /etc/arch-release ]; then
    echo -e "${YELLOW}Warning: This script is designed for Arch-based systems${NC}"
    echo -e "${YELLOW}Continuing anyway...${NC}"
    echo ""
fi

# Check if package is installed via pacman
if pacman -Q nvidia-control-gui &>/dev/null; then
    echo -e "${YELLOW}Package installed via pacman detected${NC}"
    echo -e "${YELLOW}It is recommended to uninstall using:${NC}"
    echo -e "${GREEN}  sudo pacman -R nvidia-control-gui${NC}"
    echo ""
    echo -e "${YELLOW}Do you want to continue with manual uninstallation anyway? (y/n)${NC}"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "Uninstallation cancelled"
        exit 0
    fi
    echo ""
fi

# Check if running as root
if [ "$EUID" -eq 0 ]; then
   echo -e "${RED}Please don't run this script as root${NC}"
   echo -e "${YELLOW}The script will use sudo when needed${NC}"
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

echo -e "${YELLOW}Starting uninstallation...${NC}"
echo ""

# Track what we're removing
REMOVED_FILES=0
REMOVED_DIRS=0

# Stop and disable systemd service if exists
echo -e "${BLUE}[1/6]${NC} Checking systemd services..."

# User service
if systemctl --user is-active --quiet nvidia-control.service 2>/dev/null; then
    echo "  Stopping user service..."
    systemctl --user stop nvidia-control.service 2>/dev/null || true
fi

if systemctl --user is-enabled --quiet nvidia-control.service 2>/dev/null; then
    echo "  Disabling user service..."
    systemctl --user disable nvidia-control.service 2>/dev/null || true
fi

if [ -f "$HOME/.config/systemd/user/nvidia-control.service" ]; then
    echo "  Removing user service file..."
    rm -f "$HOME/.config/systemd/user/nvidia-control.service"
    systemctl --user daemon-reload 2>/dev/null || true
    ((REMOVED_FILES++))
fi

# System-wide service (informational)
if [ -f "/usr/lib/systemd/user/nvidia-control.service" ]; then
    echo -e "${YELLOW}  Note: System-wide service file found at /usr/lib/systemd/user/nvidia-control.service${NC}"
    echo -e "${YELLOW}        This will be removed by pacman if package was installed via pacman${NC}"
fi

echo -e "${GREEN}  ✓ Service cleanup complete${NC}"
echo ""

# Remove application files
echo -e "${BLUE}[2/6]${NC} Removing application files..."

if [ -d "/opt/nvidia-control" ]; then
    echo "  Removing /opt/nvidia-control..."
    sudo rm -rf /opt/nvidia-control
    ((REMOVED_DIRS++))
    echo -e "${GREEN}  ✓ Application directory removed${NC}"
else
    echo -e "${YELLOW}  Application directory not found${NC}"
fi

echo ""

# Remove wrapper script
echo -e "${BLUE}[3/6]${NC} Removing wrapper script..."

if [ -f "/usr/bin/nvidia-control-gui" ]; then
    echo "  Removing /usr/bin/nvidia-control-gui..."
    sudo rm -f /usr/bin/nvidia-control-gui
    ((REMOVED_FILES++))
    echo -e "${GREEN}  ✓ Wrapper script removed${NC}"
else
    echo -e "${YELLOW}  Wrapper script not found${NC}"
fi

echo ""

# Remove desktop entry
echo -e "${BLUE}[4/6]${NC} Removing desktop entry..."

if [ -f "/usr/share/applications/nvidia-control.desktop" ]; then
    echo "  Removing desktop entry..."
    sudo rm -f /usr/share/applications/nvidia-control.desktop
    ((REMOVED_FILES++))
    echo -e "${GREEN}  ✓ Desktop entry removed${NC}"
    
    # Update desktop database
    if command -v update-desktop-database &> /dev/null; then
        echo "  Updating desktop database..."
        sudo update-desktop-database 2>/dev/null || {
            echo -e "${YELLOW}  Warning: Failed to update desktop database${NC}"
        }
    fi
else
    echo -e "${YELLOW}  Desktop entry not found${NC}"
fi

echo ""

# Remove uninstaller script (if exists from old installation)
echo -e "${BLUE}[5/6]${NC} Checking for old uninstaller..."

if [ -f "/usr/bin/nvidia-control-uninstall" ]; then
    echo "  Removing old uninstaller script..."
    sudo rm -f /usr/bin/nvidia-control-uninstall
    ((REMOVED_FILES++))
    echo -e "${GREEN}  ✓ Old uninstaller removed${NC}"
else
    echo -e "${YELLOW}  Old uninstaller not found${NC}"
fi

echo ""

# Handle configuration files
echo -e "${BLUE}[6/6]${NC} Configuration files..."

if [ -d "$HOME/.config/nvidia-control" ]; then
    echo -e "${YELLOW}  Configuration directory found at: $HOME/.config/nvidia-control${NC}"
    echo -e "${YELLOW}  This contains your saved settings, profiles, and clock locks${NC}"
    echo ""
    echo -e "${YELLOW}  Remove configuration files? (y/n)${NC}"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo "  Removing configuration files..."
        rm -rf "$HOME/.config/nvidia-control"
        echo -e "${GREEN}  ✓ Configuration files removed${NC}"
    else
        echo -e "${GREEN}  ✓ Configuration files kept at $HOME/.config/nvidia-control${NC}"
        echo -e "${YELLOW}  You can remove them manually later if needed${NC}"
    fi
else
    echo -e "${YELLOW}  No configuration directory found${NC}"
fi

echo ""

# Summary
echo -e "${BLUE}======================================${NC}"
echo -e "${GREEN}Uninstallation Complete!${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""
echo "Summary:"
echo "  Files removed: $REMOVED_FILES"
echo "  Directories removed: $REMOVED_DIRS"
echo ""

# Check if anything is still installed
REMAINING=0

if [ -d "/opt/nvidia-control" ]; then
    echo -e "${YELLOW}Warning: /opt/nvidia-control still exists${NC}"
    ((REMAINING++))
fi

if [ -f "/usr/bin/nvidia-control-gui" ]; then
    echo -e "${YELLOW}Warning: /usr/bin/nvidia-control-gui still exists${NC}"
    ((REMAINING++))
fi

if [ -f "/usr/share/applications/nvidia-control.desktop" ]; then
    echo -e "${YELLOW}Warning: Desktop entry still exists${NC}"
    ((REMAINING++))
fi

if [ $REMAINING -gt 0 ]; then
    echo ""
    echo -e "${RED}Some files could not be removed. You may need to check permissions.${NC}"
    echo -e "${YELLOW}If installed via pacman, use: sudo pacman -R nvidia-control-gui${NC}"
    exit 1
else
    echo -e "${GREEN}All application files have been removed successfully!${NC}"
fi

echo ""
echo -e "${GREEN}Thank you for using NVIDIA GPU Control Panel!${NC}"

