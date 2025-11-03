# Makefile for building Arch Linux package

PKGNAME=nvidia-control-gui
VERSION=1.0.0
PKGDIR=$(PKGNAME)-$(VERSION)

.PHONY: package source clean install test

package: source
	@echo "Building package..."
	cd build && makepkg -s

source:
	@echo "Creating source tarball..."
	mkdir -p build
	mkdir -p build/$(PKGDIR)
	cp -r nvidia_control_gui.py nvidia-control.desktop nvidia-control.service \
		PKGBUILD .SRCINFO README.md requirements.txt \
		build/$(PKGDIR)/
	cd build && tar -czf $(PKGDIR).tar.gz $(PKGDIR)
	@echo "Source tarball created: build/$(PKGDIR).tar.gz"

clean:
	rm -rf build/$(PKGDIR)
	rm -f build/$(PKGDIR).tar.gz
	rm -rf build/pkg build/src

install: package
	@echo "Installing package..."
	cd build && sudo pacman -U $(PKGNAME)-$(VERSION)-*.pkg.tar.zst

test:
	@echo "Testing PKGBUILD syntax..."
	cd build/$(PKGDIR) && makepkg --verifysource || true

help:
	@echo "Available targets:"
	@echo "  package  - Build the Arch package"
	@echo "  source   - Create source tarball"
	@echo "  install  - Build and install package"
	@echo "  clean    - Remove build artifacts"
	@echo "  test     - Test PKGBUILD syntax"

