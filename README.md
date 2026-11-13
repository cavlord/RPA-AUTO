# Hermes CAS ReportFlow

Automation tool for IBM CAS (Activity Report) workflow using Python, Playwright, openpyxl, and rich.

## Features
- **Discovery**: Automatically discovers form fields, validation constraints, and dropdown options.
- **Excel Template**: Generates an Excel template with dropdown validations and max length rules.
- **Form Filler**: Reads rows from Excel and auto-fills web forms, handling AJAX cascades (Administration -> Absence) and drafts.
- **Monthly Retriever**: Searches and extracts monthly activity reports (e.g. `rpa retrieve oktober`) to Excel.
- **Global CLI**: Quick commands via `rpa` or `RPA` from anywhere.

## Installation (new laptop)
Requirements: Windows + Python 3.10+ (tick "Add python.exe to PATH").

1. Copy the whole project folder to the new laptop (without `.venv` and `.browser_session`).
2. Double-click **`install.bat`**. It will:
   - create `.venv` and install dependencies,
   - install Playwright Chromium,
   - install the global `rpa` command (added to your user PATH),
   - create `Documents\RPA\REPORT` and `Documents\RPA\PARKING`,
   - generate `CAS_Activity_Entry_Template.xlsx` and `Template Parkir MDT.xlsx`.
3. Open a **new** terminal and run `rpa --help`.

Re-generate the Excel files any time with `rpa setup` (`--force` to overwrite).
To use another location, set the `RPA_HOME` environment variable.

Optional: put your real parking template at `templates\Template Parkir MDT.xlsx` before installing; it will be copied instead of the basic generated layout.

## Usage
```bash
# Discover form fields
rpa discover

# Generate Excel entry template
rpa template

# Fill form entries from Excel
rpa fill

# Retrieve activities by month and export to Excel
rpa retrieve oktober
rpa retrieve "january 2024"
```
