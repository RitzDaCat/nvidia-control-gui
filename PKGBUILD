# Maintainer: Your Name <your.email@example.com>
# Contributor: Your Name <your.email@example.com>
pkgname=nvidia-control-gui
pkgver=1.0.0
pkgrel=1
pkgdesc="A comprehensive GUI tool for managing NVIDIA GPU settings on Linux"
arch=('any')
url="https://github.com/ritzdacat/nvidia-control-gui"
license=('GPL3')
# For AUR submission, update the source and sha256sums below:
# source=("https://github.com/ritzdacat/nvidia-control-gui/archive/v${pkgver}.tar.gz")
# sha256sums=('your_sha256_sum_here')
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
# For building from local directory (developers)
# Remove source and sha256sums, then run: makepkg -s
source=(
    "nvidia_control_gui.py"
    "nvidia-control.desktop"
    "nvidia-control.service"
)
sha256sums=('SKIP' 'SKIP' 'SKIP')

package() {
    # Install application files
    install -Dm755 nvidia_control_gui.py "$pkgdir/opt/nvidia-control/nvidia_control_gui.py"
    
    # Create wrapper script
    install -Dm755 /dev/stdin "$pkgdir/usr/bin/nvidia-control-gui" << 'EOF'
#!/bin/bash
cd /opt/nvidia-control
exec python3 /opt/nvidia-control/nvidia_control_gui.py "$@"
EOF
    
    # Install desktop entry
    install -Dm644 nvidia-control.desktop "$pkgdir/usr/share/applications/nvidia-control.desktop"
    
    # Ensure desktop database is updated (post-install hook handles this, but we ensure the file is valid)
    # The post-install hook will run: update-desktop-database
    
    # Install systemd user service (optional, user can enable it)
    install -Dm644 nvidia-control.service "$pkgdir/usr/lib/systemd/user/nvidia-control.service"
    
    # Create config directory structure (empty, will be created by application)
    install -dm755 "$pkgdir/etc/skel/.config/nvidia-control"
}

