#!/bin/bash

# Script to prepare PKGBUILD for AUR submission
# This creates a proper PKGBUILD with source URLs and checksums

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}AUR Preparation Script${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# Check if in git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}Error: Not in a git repository${NC}"
    echo "Please initialize git or run from repository root"
    exit 1
fi

# Get version from PKGBUILD or ask user
if [ -f "PKGBUILD" ]; then
    PKGVER=$(grep "^pkgver=" PKGBUILD | cut -d'=' -f2)
    echo -e "${GREEN}Found version in PKGBUILD: ${PKGVER}${NC}"
else
    echo -e "${YELLOW}PKGBUILD not found. Please enter version:${NC}"
    read -r PKGVER
fi

# Check if version tag exists
if git rev-parse "v${PKGVER}" >/dev/null 2>&1; then
    echo -e "${GREEN}Git tag v${PKGVER} exists${NC}"
else
    echo -e "${YELLOW}Git tag v${PKGVER} does not exist${NC}"
    echo -e "${YELLOW}Do you want to create it? (y/n)${NC}"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        git tag "v${PKGVER}"
        echo -e "${GREEN}Tag v${PKGVER} created${NC}"
        echo -e "${YELLOW}Don't forget to push: git push origin v${PKGVER}${NC}"
    fi
fi

# Get repository URL
REPO_URL=$(git remote get-url origin 2>/dev/null || echo "")
if [ -z "$REPO_URL" ]; then
    echo -e "${YELLOW}Git remote not found. Please enter repository URL:${NC}"
    read -r REPO_URL
fi

# Convert SSH URL to HTTPS if needed
if [[ "$REPO_URL" == git@* ]]; then
    REPO_URL=$(echo "$REPO_URL" | sed 's/git@\([^:]*\):\(.*\)\.git/https:\/\/\1\/\2.git/')
fi

# Convert .git URL to archive URL format
ARCHIVE_URL="${REPO_URL%.git}/archive/v${PKGVER}.tar.gz"

echo ""
echo -e "${BLUE}Configuration:${NC}"
echo "  Version: ${PKGVER}"
echo "  Repository: ${REPO_URL}"
echo "  Archive URL: ${ARCHIVE_URL}"
echo ""

# Download and calculate checksum
echo -e "${YELLOW}Downloading archive to calculate checksum...${NC}"
TEMP_DIR=$(mktemp -d)
ARCHIVE_FILE="${TEMP_DIR}/v${PKGVER}.tar.gz"

if curl -sLf "${ARCHIVE_URL}" -o "${ARCHIVE_FILE}"; then
    SHA256SUM=$(sha256sum "${ARCHIVE_FILE}" | cut -d' ' -f1)
    echo -e "${GREEN}Checksum calculated: ${SHA256SUM}${NC}"
    rm -rf "${TEMP_DIR}"
else
    echo -e "${RED}Failed to download archive${NC}"
    echo -e "${YELLOW}You may need to create a GitHub release first${NC}"
    rm -rf "${TEMP_DIR}"
    exit 1
fi

# Create backup of PKGBUILD
if [ -f "PKGBUILD" ]; then
    cp PKGBUILD PKGBUILD.backup
    echo -e "${GREEN}Backup created: PKGBUILD.backup${NC}"
fi

# Update PKGBUILD
echo ""
echo -e "${YELLOW}Updating PKGBUILD...${NC}"

# Create new PKGBUILD with AUR-ready format
cat > PKGBUILD << EOF
# Maintainer: Your Name <your.email@example.com>
# Contributor: Your Name <your.email@example.com>
pkgname=nvidia-control-gui
pkgver=${PKGVER}
pkgrel=1
pkgdesc="A comprehensive GUI tool for managing NVIDIA GPU settings on Linux"
arch=('any')
url="${REPO_URL%.git}"
license=('GPL3')
depends=(
    'python'
    'python-pyqt6'
    'nvidia-utils'
    'nvidia-settings'
    'polkit'
)
makedepends=()
optdepends=(
    'nvidia-dkms: For kernel module support'
)
source=("v\${pkgver}.tar.gz::${ARCHIVE_URL}")
sha256sums=('${SHA256SUM}')

package() {
    cd "\${srcdir}/nvidia-control-gui-\${pkgver}"
    
    # Install application files
    install -Dm755 nvidia_control_gui.py "\${pkgdir}/opt/nvidia-control/nvidia_control_gui.py"
    
    # Create wrapper script
    install -Dm755 /dev/stdin "\${pkgdir}/usr/bin/nvidia-control-gui" << 'WRAPPER_EOF'
#!/bin/bash
cd /opt/nvidia-control
exec python3 /opt/nvidia-control/nvidia_control_gui.py "\$@"
WRAPPER_EOF
    
    # Install desktop entry
    install -Dm644 nvidia-control.desktop "\${pkgdir}/usr/share/applications/nvidia-control.desktop"
    
    # Install systemd user service (optional, user can enable it)
    install -Dm644 nvidia-control.service "\${pkgdir}/usr/lib/systemd/user/nvidia-control.service"
    
    # Create config directory structure (empty, will be created by application)
    install -dm755 "\${pkgdir}/etc/skel/.config/nvidia-control"
}
EOF

echo -e "${GREEN}PKGBUILD updated${NC}"

# Update .SRCINFO
echo -e "${YELLOW}Updating .SRCINFO...${NC}"
makepkg --printsrcinfo > .SRCINFO
echo -e "${GREEN}.SRCINFO updated${NC}"

echo ""
echo -e "${BLUE}======================================${NC}"
echo -e "${GREEN}Preparation Complete!${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""
echo "Next steps:"
echo "1. Review PKGBUILD and update maintainer information"
echo "2. Test the package: makepkg -si"
echo "3. Check with namcap: namcap PKGBUILD"
echo "4. Create AUR repository:"
echo "   git clone ssh://aur@aur.archlinux.org/nvidia-control-gui.git"
echo "5. Copy PKGBUILD and .SRCINFO to AUR repo"
echo "6. Commit and push to AUR"
echo ""
echo -e "${YELLOW}Backup saved as: PKGBUILD.backup${NC}"

