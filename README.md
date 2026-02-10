# Plot Organizer Tool

A portable tool to organize data plots from ZIP files and generate summary reports.

## Installation

1.  **Prerequisites**: Python 3.8+
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Run the tool against a ZIP file containing your data:

```bash
python process_data.py --zip /path/to/data.zip --output ./my_report
```

### Options

-   `--zip`: Path to the input ZIP file (required).
-   `--output`: Directory where the organized folders and `report.md` will be created.

## Output Structure

The tool creates the following structure in your output directory:

```
my_report/
├── report.md          # Summary report with images and CSV stats
├── plots/             # Organized plots
│   ├── group_A/       # Plots matching "group_A" pattern
│   └── group_B/       # Plots matching "group_B" pattern
└── csv_summaries/     # (Optional) Extracted CSV data summaries
```

## Customization

-   **Filename Patterns**: Edit `process_data.py` (look for `organize_files` function) to change how filenames are parsed and grouped.
-   **CSV Extraction**: Edit `process_data.py` (look for `pd.read_csv`) to change which columns or statistics are extracted.
