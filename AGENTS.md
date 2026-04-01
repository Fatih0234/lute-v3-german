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

## Features

### YouGlish Integration

A YouGlish sidebar tab has been added for pronunciation lookup:

- **Location**: Appears in the dictionary tabs alongside "Sentences" and "Images"
- **Behavior**: Opens YouGlish.com in a popup window (1000x700) with the selected text
- **URL Format**: `https://youglish.com/pronounce/{text}/{language}`
- **Supported Languages**: English (english), German/Deutsch (german)
- **Word Count**: Works with any number of words (single or multiple)

**Implementation Details:**
- `lute/static/js/dict-tabs.js`: Added `YouGlishLookupButton` class extending `GeneralLookupButton`
- `lute/read/routes.py`: Passes `lang_name` to template for language detection
- `lute/templates/read/index.html`: Sets `LookupButton.LANG_NAME` variable
- `lute/static/css/styles.css`: Orange branded button styling (#ff6b35)
