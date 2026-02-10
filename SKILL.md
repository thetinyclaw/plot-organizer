---
name: plot-organizer
description: Organize plots from a ZIP file, extract CSV data, and generate a summary report. Use when processing batches of data plots and logs.
---

# Plot Organizer

This skill processes a ZIP file containing data plots (images) and CSV logs. It organizes the files based on filename patterns and generates a report.

## Usage

1.  **Place the ZIP file** in the workspace.
2.  **Run the processing script** with the ZIP filename.

```bash
python3 skills/plot-organizer/scripts/process_data.py --zip <file.zip> --output <output_dir>
```

## Features

-   **Unzipping**: Extracts contents to a temporary or specified directory.
-   **Organization**: Sorts images into folders based on consistent filename substrings.
-   **Data Extraction**: Reads CSVs to extract key metrics (e.g., max/min values, averages).
-   **Reporting**: Generates a Markdown report compiling the plots and metrics.

## Requirements

-   Python 3
-   `pandas` (for CSV processing)
-   `matplotlib` (optional, if generating new plots)
