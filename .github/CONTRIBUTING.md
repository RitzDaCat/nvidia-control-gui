# Contributing to NVIDIA GPU Control Panel

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in Issues
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - System information (OS, GPU model, driver version)
   - Relevant error messages or logs

### Suggesting Features

1. Check if the feature has already been suggested
2. Create an issue with:
   - Clear description of the feature
   - Use case and motivation
   - Potential implementation approach (if you have ideas)

### Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes
4. Test thoroughly
5. Commit with clear messages: `git commit -m "Add feature: description"`
6. Push to your fork: `git push origin feature/your-feature-name`
7. Create a Pull Request

## Development Setup

```bash
# Clone repository
git clone https://github.com/yourusername/nvidia-control-gui.git
cd nvidia-control-gui

# Install dependencies
sudo pacman -S python python-pyqt6 polkit nvidia-utils nvidia-settings

# Run directly
python3 nvidia_control_gui.py
```

## Code Style

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Add docstrings to all public methods (Google/NumPy style)
- Keep functions focused and single-purpose
- Add comments for complex logic

## Testing

Before submitting:
- Test on your system with your GPU
- Test all affected features
- Check for regressions
- Verify error handling works correctly

## Security

- Never commit sensitive data (passwords, API keys, etc.)
- Validate all user inputs
- Use secure file operations
- Follow security best practices in code reviews

## Documentation

- Update README.md if adding features
- Add docstrings to new functions/methods
- Update CHANGELOG.md for user-facing changes
- Keep installation instructions up to date

## Questions?

Feel free to open an issue for questions or discussion!

