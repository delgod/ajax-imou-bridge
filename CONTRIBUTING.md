# CONTRIBUTING TO SIA-BRIDGE

Thank you for considering contributing to the SIA-Bridge project. This document outlines the process and standards for contributing code, documentation, and bug reports.

## CODE OF CONDUCT

By participating in this project, you agree to abide by the principles of professional conduct:
- Be respectful and constructive in all communications
- Focus on technical merit and project goals
- Maintain high engineering standards

## DEVELOPMENT PROCESS

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/your-username/ajax-imou-bridge.git
cd ajax-imou-bridge
git remote add upstream https://github.com/delgod/ajax-imou-bridge.git
```

### 2. Development Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install development dependencies
pip install -r requirements.txt
pip install -e .
pip install ruff pytest pytest-asyncio pytest-cov
```

### 3. Branch Naming Convention

- `feature/description` - New features
- `bugfix/description` - Bug fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring

### 4. Coding Standards

#### Python Style Guide

This project adheres to:
- PEP 8 - Style Guide for Python Code
- PEP 257 - Docstring Conventions
- PEP 484 - Type Hints (where applicable)

#### Code Quality Requirements

- All code must pass `ruff` linter checks
- Functions must include docstrings
- Complex logic requires inline comments
- No commented-out code in commits
- Line length maximum: 88 characters

#### Example Code Style

```python
async def process_event(self, event: SIAEvent) -> None:
    """Process incoming SIA protocol event.
    
    Args:
        event: SIA event object containing alarm state
        
    Raises:
        ValueError: If event code is malformed
    """
    if not self._validate_event(event):
        logger.warning("Invalid event received: %s", event)
        return
        
    # Process based on event type
    await self._dispatch_event(event)
```

### 5. Testing Requirements

- New features require unit tests
- Bug fixes require regression tests
- Maintain or increase code coverage
- Tests must be deterministic and fast

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=sia_bridge tests/
```

### 6. Commit Message Format

Follow the conventional commit format:

```
type(scope): subject

body

footer
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation change
- `style`: Code style change (formatting, etc)
- `refactor`: Code refactoring
- `test`: Test addition or correction
- `chore`: Maintenance tasks

Example:
```
feat(sia): add support for encrypted SIA messages

Implement AES encryption/decryption for SIA protocol messages
as specified in SIA DC-09 Rev. 2 standard.

Closes #42
```

## SUBMISSION PROCESS

### 1. Pre-submission Checklist

- [ ] Code follows style guidelines
- [ ] Tests pass locally
- [ ] Documentation updated if needed
- [ ] Commit messages follow convention
- [ ] Branch is up-to-date with upstream/main

### 2. Pull Request Process

1. Push your branch to your fork
2. Create pull request against `main` branch
3. Fill out the PR template completely
4. Ensure CI checks pass
5. Address review feedback promptly

### 3. Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project style
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings introduced
```

## BUG REPORTS

### Reporting Security Issues

Security issues should be reported privately to: delgod@delgod.com

Do NOT open public issues for security vulnerabilities.

### Bug Report Format

When reporting bugs, include:

```markdown
## Environment
- OS: [e.g., Ubuntu 22.04]
- Python: [e.g., 3.9.7]
- Version: [e.g., 0.1.0 or commit hash]

## Description
Clear description of the bug

## Steps to Reproduce
1. Configuration used
2. Actions taken
3. Expected result
4. Actual result

## Logs
```
Relevant log output with DEBUG level
```

## Additional Context
Any other relevant information
```

## FEATURE REQUESTS

Feature requests should:
- Describe the problem being solved
- Propose a solution approach
- Consider backward compatibility
- Include use case examples

## DOCUMENTATION

Documentation contributions should:
- Use clear, concise language
- Include examples where applicable
- Follow existing documentation style
- Update relevant sections consistently

## RELEASE PROCESS

Releases follow semantic versioning (MAJOR.MINOR.PATCH):
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes

## DEVELOPER CERTIFICATE OF ORIGIN

By contributing, you certify that:

```
Developer Certificate of Origin
Version 1.1

Copyright (C) 2004, 2006 The Linux Foundation and its contributors.

Everyone is permitted to copy and distribute verbatim copies of this
license document, but changing it is not allowed.

Developer's Certificate of Origin 1.1

By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I
    have the right to submit it under the open source license
    indicated in the file; or

(b) The contribution is based upon previous work that, to the best
    of my knowledge, is covered under an appropriate open source
    license and I have the right under that license to submit that
    work with modifications, whether created in whole or in part
    by me, under the same open source license (unless I am
    permitted to submit under a different license), as indicated
    in the file; or

(c) The contribution was provided directly to me by some other
    person who certified (a), (b) or (c) and I have not modified
    it.

(d) I understand and agree that this project and the contribution
    are public and that a record of the contribution (including all
    personal information I submit with it, including my sign-off) is
    maintained indefinitely and may be redistributed consistent with
    this project or the open source license(s) involved.
```

To sign-off commits:
```bash
git commit -s -m "Your commit message"
```

## QUESTIONS?

For questions about contributing:
- Open a discussion on GitHub
- Email: delgod@delgod.com

Thank you for contributing to SIA-Bridge!

---

Last updated: December 2024 