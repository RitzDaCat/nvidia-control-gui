# AUR Submission Guide

This guide will help you submit `nvidia-control-gui` to the Arch User Repository (AUR).

## Prerequisites

1. **AUR Account**: Create an account at https://aur.archlinux.org
2. **SSH Key**: Add your SSH public key to your AUR account
3. **Git**: Ensure git is installed and configured

## Step-by-Step Submission

### 1. Prepare the Package

Run the preparation script:

```bash
./prepare-aur.sh
```

This will:
- Check git repository and tags
- Calculate checksums
- Update PKGBUILD with proper source URLs
- Update .SRCINFO

**Important**: Update the maintainer information in PKGBUILD before proceeding!

### 2. Test the Package Locally

```bash
# Build the package
makepkg -s

# Check for issues
namcap PKGBUILD
namcap nvidia-control-gui-*.pkg.tar.zst

# Test installation
sudo pacman -U nvidia-control-gui-*.pkg.tar.zst

# Test the application
nvidia-control-gui

# Test uninstallation
sudo pacman -R nvidia-control-gui
```

### 3. Create AUR Repository

```bash
# Clone the AUR repository (creates empty repo)
git clone ssh://aur@aur.archlinux.org/nvidia-control-gui.git
cd nvidia-control-gui
```

### 4. Copy Package Files

```bash
# Copy PKGBUILD and .SRCINFO
cp ../nvidia-control-gui/PKGBUILD .
cp ../nvidia-control-gui/.SRCINFO .

# Or if you're in the project root:
cp PKGBUILD ../nvidia-control-gui/
cp .SRCINFO ../nvidia-control-gui/
```

### 5. Commit and Push

```bash
# Add files
git add PKGBUILD .SRCINFO

# Commit
git commit -m "Initial package release v1.0.0"

# Push to AUR
git push origin master
```

### 6. Verify Submission

1. Visit: https://aur.archlinux.org/packages/nvidia-control-gui
2. Verify all information is correct
3. Check that the package builds successfully

## Updating the Package

### For New Versions

1. **Update version in PKGBUILD:**
   ```bash
   pkgver=1.0.1
   pkgrel=1  # Reset to 1 for new version
   ```

2. **Create git tag:**
   ```bash
   git tag v1.0.1
   git push origin v1.0.1
   ```

3. **Run preparation script:**
   ```bash
   ./prepare-aur.sh
   ```

4. **Update AUR repository:**
   ```bash
   cd nvidia-control-gui  # AUR repo
   git pull
   cp ../nvidia-control-gui/PKGBUILD .
   cp ../nvidia-control-gui/.SRCINFO .
   makepkg --printsrcinfo > .SRCINFO  # Regenerate
   git add PKGBUILD .SRCINFO
   git commit -m "Update to v1.0.1"
   git push
   ```

### For Bug Fixes (Same Version)

1. **Increment pkgrel:**
   ```bash
   pkgrel=2  # Increment from previous
   ```

2. **Update AUR repository:**
   ```bash
   cd nvidia-control-gui  # AUR repo
   git pull
   # Make necessary changes
   makepkg --printsrcinfo > .SRCINFO
   git add PKGBUILD .SRCINFO
   git commit -m "Fix: description of fix"
   git push
   ```

## Package Maintenance

### Testing Updates

Always test locally before pushing:

```bash
# In project directory
makepkg -si

# Test installation
sudo pacman -U nvidia-control-gui-*.pkg.tar.zst

# Test application
nvidia-control-gui

# Test uninstallation
sudo pacman -R nvidia-control-gui
```

### Common Issues

**PKGBUILD validation fails:**
- Check syntax: `bash -n PKGBUILD`
- Run namcap: `namcap PKGBUILD`

**Checksum mismatch:**
- Ensure git tag exists and matches version
- Verify source URL is accessible
- Re-run `prepare-aur.sh`

**AUR build fails:**
- Check dependencies are available in repositories
- Verify file paths in package() function
- Test locally first

## AUR Package Guidelines

### Requirements

- ✅ PKGBUILD follows Arch Linux packaging standards
- ✅ All dependencies are in official repositories or AUR
- ✅ Package builds successfully
- ✅ No bundled dependencies (use system packages)
- ✅ Proper license specification
- ✅ Valid .SRCINFO file

### Best Practices

1. **Version Management:**
   - Use semantic versioning (x.y.z)
   - Create git tags for releases
   - Increment pkgrel for fixes without version change

2. **Dependencies:**
   - Use exact version requirements when needed
   - Mark optional dependencies with optdepends
   - Document why dependencies are needed

3. **Documentation:**
   - Include clear pkgdesc
   - Add comments in PKGBUILD for complex operations
   - Link to project README/INSTALL docs

4. **Testing:**
   - Always test locally before pushing
   - Test installation and uninstallation
   - Verify application functionality

## Troubleshooting

### Permission Denied

```bash
# Ensure SSH key is added to AUR account
ssh -T aur@aur.archlinux.org
```

### Build Fails on AUR

Check build logs on AUR website. Common issues:
- Missing dependencies
- Incorrect file paths
- Permission issues

### .SRCINFO Out of Sync

```bash
makepkg --printsrcinfo > .SRCINFO
```

## Resources

- [AUR Submission Guidelines](https://wiki.archlinux.org/title/AUR_submission_guidelines)
- [PKGBUILD Reference](https://wiki.archlinux.org/title/PKGBUILD)
- [Arch Linux Packaging Standards](https://wiki.archlinux.org/title/Arch_packaging_standards)
- [AUR Website](https://aur.archlinux.org)

## Notes

- AUR packages are community-maintained
- Users can vote and comment on packages
- Respond to user feedback and issues promptly
- Keep package updated with upstream releases
- Maintainer information must be accurate

