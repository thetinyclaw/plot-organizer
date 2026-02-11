# Plot Organizer - Memory

## Usage (v2 - Directory Based)
The tool now processes a **directory** structure (not a ZIP file) containing `saline-results` and `impedance-results` folders.

### Command
```bash
skills/plot-organizer/venv/bin/python3 skills/plot-organizer/scripts/process_data.py \
  --dir /path/to/data_directory \
  --output /path/to/output_folder
```

### Workflow
1.  **Receive Data:** User uploads a folder (or zip/7z that needs extraction).
2.  **Extract (if needed):** Extract to a temp directory.
3.  **Run Script:** use the command above.
4.  **Send Report:** `message(filePath=".../report.pdf")`.

### Features
-   **Input:** Directory path (`--dir`).
-   **Order:** Saline (EC0 -> EC1) -> Impedance.
-   **Layout:** Dynamic grid (1-col for <3, 2-col for <7, 3-col for >7 plots).
-   **Titles:** None (clean layout).
-   **Grouping:**
    -   Saline: PSD Signal, PSD Noise, Others (THDN/Gain/Nitara).
    -   Impedance: Electrodes, Nitara, Yield.
