# Documentation Structure

This document outlines the documentation structure following Diataxis principles and GitHub Markdown standards.

## Documentation Types (Diataxis)

### 1. Tutorials (Learning-Oriented)
**Purpose**: Teach users how to accomplish a specific task from start to finish.

**Location**: Usage section in README.md
- Preventing GPU Downclocking During Gaming
- Reducing Power Consumption and Heat
- Controlling Fan Speed Manually
- Creating and Using Profiles
- Managing Multiple GPUs
- Restoring Settings After Reboot

**Format**: Problem → Solution → Steps

### 2. How-To Guides (Problem-Oriented)
**Purpose**: Show users how to solve a specific problem.

**Location**: 
- Installation section (README.md)
- Coolbits Setup section (README.md)
- Troubleshooting section (README.md)
- INSTALL.md (detailed installation guide)

**Format**: Clear steps, commands, explanations

### 3. Reference (Information-Oriented)
**Purpose**: Provide technical details and specifications.

**Location**:
- Features section (README.md)
- Requirements section (README.md)
- File Locations section (README.md)
- Keyboard Shortcuts table (README.md)
- Security section (README.md)

**Format**: Lists, tables, specifications

### 4. Explanation (Understanding-Oriented)
**Purpose**: Help users understand concepts and decisions.

**Location**:
- Overview section (README.md)
- What This Tool Does (README.md)
- When to Use This Tool (README.md)
- Why Coolbits is Needed (README.md)
- Security section (README.md)

**Format**: Explanatory text, concepts, rationale

## README.md Structure

```
1. Title & Badges (GitHub Markdown)
2. Overview (Explanation)
   - What This Tool Does
   - When to Use This Tool
3. Features (Reference)
   - Feature descriptions with details
4. Requirements (Reference)
   - System requirements
   - Dependency list
   - Verification steps
5. Installation (How-To)
   - Multiple methods
   - Step-by-step instructions
6. Uninstallation (How-To)
   - Clear removal steps
7. Usage (Tutorial/How-To)
   - Starting the application
   - Keyboard shortcuts (Reference table)
   - Common tasks (Problem-Solution format)
8. Coolbits Setup (How-To)
   - Why needed (Explanation)
   - How to enable (Steps)
   - Values reference (Reference)
9. Troubleshooting (How-To)
   - Problem-Solution format
   - Symptoms → Causes → Solutions
10. File Locations (Reference)
    - Table format
11. Security (Explanation/Reference)
    - Security measures listed
12. Contributing (How-To)
    - Development setup
    - Code style guidelines
13. License (Reference)
14. Safety Notes (Explanation)
15. Documentation (Reference)
    - Links to other docs
16. Acknowledgments (Reference)
```

## GitHub Markdown Compliance

### Used Features
- Headers (H1, H2, H3)
- Code blocks with syntax highlighting
- Tables
- Lists (ordered and unordered)
- Bold and italic text
- Links (internal and external)
- Badges (shields.io)
- Inline code with backticks

### Best Practices Followed
- Clear hierarchy (H1 → H2 → H3)
- Consistent formatting
- Code blocks with language specification
- Tables for structured data
- Links to related documentation
- Badges for quick information

## Documentation Files

| File | Type | Purpose |
|------|------|---------|
| README.md | Mixed | Main documentation (Overview, Quick Start, Reference) |
| INSTALL.md | How-To | Detailed installation instructions |
| PACKAGING.md | How-To/Reference | Arch Linux packaging guide |
| AUR-SUBMISSION.md | How-To | AUR submission process |
| CHANGELOG.md | Reference | Version history |
| CONTRIBUTING.md | How-To | Contribution guidelines |
| REVIEW-PLAN.md | Reference | Development review plan |
| REVIEW-SUMMARY.md | Reference | Review implementation summary |

## Documentation Standards

### Language
- Clear, concise English
- Active voice preferred
- Second person ("you") for user-facing docs
- Technical terms explained when first used

### Formatting
- Consistent markdown syntax
- Proper heading hierarchy
- Code blocks with language tags
- Tables for structured data
- Lists for sequences and options

### Structure
- Logical flow (Overview → Install → Use → Troubleshoot)
- Problem-solution format for how-to guides
- Reference material in tables/lists
- Explanations before procedures

## Verification Checklist

- [x] No emojis in documentation
- [x] Proper GitHub Markdown syntax
- [x] Diataxis principles followed
- [x] Clear hierarchy and structure
- [x] Consistent formatting
- [x] All links work (relative paths)
- [x] Code blocks properly formatted
- [x] Tables properly formatted
- [x] Clear, concise language
- [x] Problem-solution format for tutorials

