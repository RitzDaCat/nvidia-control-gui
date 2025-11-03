#!/bin/bash

# Script to fix KDE Plasma menu visibility after installation

echo "Fixing KDE Plasma menu for NVIDIA GPU Control..."

# Update desktop database
if command -v update-desktop-database &> /dev/null; then
    echo "Updating desktop database..."
    sudo update-desktop-database /usr/share/applications/
fi

# Update KDE menu cache
if command -v kbuildsycoca5 &> /dev/null; then
    echo "Updating KDE menu cache (kbuildsycoca5)..."
    kbuildsycoca5 --noincremental
fi

# Also try kbuildsycoca6 for newer KDE
if command -v kbuildsycoca6 &> /dev/null; then
    echo "Updating KDE menu cache (kbuildsycoca6)..."
    kbuildsycoca6 --noincremental
fi

# Refresh KDE menu
if command -v kquitapp5 &> /dev/null && command -v kstart5 &> /dev/null; then
    echo "Refreshing KDE application launcher..."
    kquitapp5 plasmashell 2>/dev/null || true
    kstart5 plasmashell 2>/dev/null || true
fi

# Try newer KDE commands
if command -v kquitapp6 &> /dev/null && command -v kstart6 &> /dev/null; then
    echo "Refreshing KDE application launcher (KDE6)..."
    kquitapp6 plasmashell 2>/dev/null || true
    kstart6 plasmashell 2>/dev/null || true
fi

echo ""
echo "Done! The application should now appear in the KDE menu."
echo ""
echo "If it still doesn't appear:"
echo "1. Log out and log back in"
echo "2. Or restart KDE: kquitapp5 plasmashell && kstart5 plasmashell"
echo "3. Search for 'NVIDIA GPU Control' in the application launcher"

