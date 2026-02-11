#!/bin/bash
# Plot Organizer Batch Processor
# Processes all ZIPs in Raw-Data-EFS folder through the full pipeline
# Output: Final PDFs named after part IDs in v2-Analysis-EFS/

set -e  # Exit on error

# Configuration
RAW_DATA_DIR="/mnt/c/Users/Amehra/Documents/data/CM_data/Raw-Data-EFS"
ANALYSIS_BASE_DIR="/mnt/c/Users/Amehra/Documents/data/CM_data/v2-Analysis-EFS"
SIGNAL_INJECTION_SCRIPT="/mnt/c/Users/amehra/github/fas-protocol-tools/saline-testing/analysis/signal_injection.py"
IMPEDANCE_YIELD_SCRIPT="/mnt/c/Users/amehra/github/fas-protocol-tools/saline-testing/analysis/impedance_yield.py"
MFG_CRITERIA="/mnt/c/Users/amehra/github/fas-protocol-tools/saline-testing/configs/mfg_acceptance_criteria.yml"
PLOT_ORGANIZER_DIR="/mnt/c/Users/Amehra/github/plot-organizer"
PROCESS_DATA_SCRIPT="$PLOT_ORGANIZER_DIR/scripts/process_data.py"
CHANNEL_MAP="n2d"

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Find all ZIPs in Raw-Data-EFS and process each
log "Starting batch processing of ZIPs in $RAW_DATA_DIR"

for zip_file in "$RAW_DATA_DIR"/*.zip; do
    if [ ! -f "$zip_file" ]; then
        log "No ZIP files found in $RAW_DATA_DIR"
        exit 1
    fi

    # Extract part ID from filename (remove .zip extension)
    part_id=$(basename "$zip_file" .zip)
    log "Processing: $part_id"

    # Create analysis output directory
    analysis_dir="$ANALYSIS_BASE_DIR/$part_id"
    mkdir -p "$analysis_dir"

    # Step 1: Unzip files
    log "  [1/4] Unzipping..."
    if command -v unzip &> /dev/null; then
        unzip -q "$zip_file" -d "$RAW_DATA_DIR/$part_id" || { log "ERROR: Failed to unzip $zip_file"; continue; }
    elif command -v 7z &> /dev/null; then
        7z x "$zip_file" -o"$RAW_DATA_DIR/$part_id" > /dev/null || { log "ERROR: Failed to unzip $zip_file"; continue; }
    elif command -v python &> /dev/null; then
        python -m zipfile -e "$zip_file" "$RAW_DATA_DIR/$part_id" || { log "ERROR: Failed to unzip $zip_file"; continue; }
    else
        log "ERROR: No unzip tool found (unzip, 7z, or python)"
        continue
    fi

    # Step 2: Discover test date and config files
    # Find the date directory (assuming structure: part_id/part_id/YYMMDD/...)
    # Look for numeric-only directories (6 digits = YYMMDD)
    date_dir=$(find "$RAW_DATA_DIR/$part_id" -type d -name "[0-9][0-9][0-9][0-9][0-9][0-9]" | head -1)
    if [ -z "$date_dir" ]; then
        log "ERROR: Could not find test date directory in $RAW_DATA_DIR/$part_id"
        continue
    fi
    test_date=$(basename "$date_dir")
    log "  Found test date: $test_date"

    # Find signal injection config in date directory
    config_file=$(find "$date_dir" -maxdepth 1 -name "*-config.yml" ! -name "*impedance*" | head -1)
    
    # Find impedance config (nested inside impedance-yield-* folder) - OPTIONAL
    impedance_config=$(find "$date_dir" -name "*-impedance-yield-config.yml" | head -1)

    # Signal config is required
    if [ -z "$config_file" ]; then
        log "ERROR: Could not find signal injection config in $date_dir"
        continue
    fi
    
    # Impedance config is optional
    if [ -z "$impedance_config" ]; then
        log "  WARNING: No impedance config found. Skipping impedance analysis."
    fi

    # Step 2: Signal Injection Analysis
    log "  [2/4] Running signal injection analysis..."
    python3 "$SIGNAL_INJECTION_SCRIPT" "$config_file" "$MFG_CRITERIA" --channel-map "$CHANNEL_MAP" --output-dir "$analysis_dir" || {
        log "ERROR: Signal injection failed for $part_id"
        continue
    }

    # Step 3: Impedance Yield Analysis (optional)
    if [ -n "$impedance_config" ]; then
        log "  [3/4] Running impedance yield analysis..."
        python3 "$IMPEDANCE_YIELD_SCRIPT" "$impedance_config" "$MFG_CRITERIA" --channel-map "$CHANNEL_MAP" --output-dir "$analysis_dir" || {
            log "ERROR: Impedance yield failed for $part_id"
            continue
        }
    else
        log "  [3/4] Skipping impedance yield analysis (no config found)"
    fi

    # Step 4: Generate PDF Report
    log "  [4/4] Generating PDF report..."
    cd "$PLOT_ORGANIZER_DIR"
    python ./scripts/process_data.py --dir "$analysis_dir" --output "$analysis_dir" || {
        log "ERROR: PDF generation failed for $part_id"
        continue
    }

    # Rename PDF to match part ID
    pdf_file=$(find "$analysis_dir" -maxdepth 1 -name "*.pdf" | head -1)
    if [ -f "$pdf_file" ]; then
        mv "$pdf_file" "$analysis_dir/${part_id}.pdf"
        log "✅ Complete: $analysis_dir/${part_id}.pdf"
    else
        log "ERROR: No PDF generated for $part_id"
    fi

    # Cleanup: Remove unzipped folder from Raw-Data-EFS
    log "  Cleaning up unzipped files..."
    rm -rf "$RAW_DATA_DIR/$part_id" || log "WARNING: Could not delete $RAW_DATA_DIR/$part_id"

done

log "✅ Batch processing complete!"
