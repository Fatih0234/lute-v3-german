# Lute v3 Light (German Only)

## Project Overview

This is a Python/Flask application for learning foreign languages through reading.

## Architecture

- **Backend**: Flask with SQLAlchemy
- **Frontend**: Jinja2 templates with vanilla JavaScript
- **Database**: SQLite
- **Languages**: Python 3.8+

## Development Guidelines

- Follow existing code style (Black formatter)
- Run tests with pytest
- Use pylint for linting
- Maintain test coverage

## Key Directories

- `/lute` - Main application code
- `/tests` - Test files
- `/plugins` - Language-specific plugins
- `/docs` - Documentation

## Build Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
pylint lute
```
