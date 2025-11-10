# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This repository contains HLA (Human Leukocyte Antigen) metadata for proteomics datasets. Currently, it consists of a single data file listing dataset identifiers from multiple proteomics repositories.

## Data Structure

### metadata_list
A plain text file containing 147 proteomics dataset identifiers, one per line. The datasets are sourced from:
- **PXD**: ProteomeXchange Database identifiers (majority of entries)
- **MSV**: MassIVE repository identifiers
- **JPST**: Japan ProteomeStandard Repository/Database identifiers
- **PASS**: PeptideAtlas SRM/MRM Experiment Library identifiers

The file uses a simple format with one dataset ID per line (e.g., `PXD012348`).

## Context

This repository is part of the yang_ylab working directory structure, which includes related projects for:
- GIST proteomics and transcriptome analysis
- Cancer dataset processing
- Tumor PTM (Post-Translational Modification) studies
- Spectra analysis

## Automated Metadata Collection System

This repository includes a complete automated system for collecting and organizing metadata from proteomics datasets.

### Project Structure

```
HLA_metadata/
├── data/
│   ├── raw/                        # Raw data from APIs
│   │   ├── pride_api_responses/   # PRIDE API JSON responses
│   │   ├── sdrf_files/            # SDRF sample metadata files
│   │   └── manual_extracts/       # Manually extracted data
│   ├── processed/                  # Processed and classified data
│   └── validation/                 # Quality reports
├── scripts/                        # Python scripts
│   ├── collect_metadata.py        # Main collection script
│   ├── parse_sdrf.py             # SDRF file parser
│   ├── classify_metadata.py      # HLA/sample/disease classifier
│   └── generate_excel.py         # Excel report generator
├── docs/                          # Documentation
│   └── manual_review_guide.md    # Manual review instructions
├── metadata_list                  # Dataset ID list (147 datasets)
├── requirements.txt               # Python dependencies
└── README.md                      # Usage instructions
```

### Running the Metadata Collection Pipeline

**1. Install dependencies:**
```bash
pip install -r requirements.txt
```

**2. Collect metadata from APIs:**
```bash
python scripts/collect_metadata.py
```
This script:
- Fetches metadata from PRIDE API for all PXD datasets (~126 datasets)
- Downloads SDRF files for detailed sample information
- Collects MSV dataset metadata (using ppx if available)
- Marks JPST/PASS datasets for manual extraction
- Estimated runtime: 3-5 hours

**3. Parse SDRF files:**
```bash
python scripts/parse_sdrf.py
```
This extracts detailed sample characteristics from SDRF files and enriches the main metadata.

**4. Classify metadata:**
```bash
python scripts/classify_metadata.py
```
This automatically classifies:
- HLA types (HLA I, HLA II, HLA I/II, or needs manual review)
- Sample types (Tissue, Blood, Cell line)
- Disease types and categories
- Metadata quality scores

**5. Generate Excel report:**
```bash
python scripts/generate_excel.py
```
This creates a multi-sheet Excel file with:
- Sheet 1: Main metadata table (all datasets)
- Sheet 2: Disease type summary
- Sheet 3: HLA classification summary
- Sheet 4: Sample type distribution
- Sheet 5: Technical information summary
- Sheet 6: Data quality report

Output: `data/processed/proteomics_metadata_complete.xlsx`

### Key Metadata Fields Collected

**Core Fields:**
- `hla_type`: HLA I, HLA II, HLA I/II, or needs manual confirmation
- `disease_type`: Specific disease name
- `disease_category`: Cancer, Neurodegenerative, Infectious Disease, etc.
- `sample_type`: Tissue/Blood/Cell line with specifics
- `organisms`: Species information
- `tissues`: Tissue/organ source
- `instruments`: Mass spectrometry instruments used
- `ptms`: Post-translational modifications detected

**Quality Indicators:**
- `metadata_quality`: High/Medium/Low
- `needs_manual_review`: Boolean flag for datasets requiring human verification
- `has_sdrf`: Whether SDRF file is available

### APIs and Data Sources

**PRIDE API (for PXD datasets):**
- Base URL: `https://www.ebi.ac.uk/pride/ws/archive/v2`
- Returns comprehensive metadata including diseases, tissues, instruments, PTMs
- SDRF files provide sample-level details

**ppx Package (for MSV datasets):**
- Python interface to MassIVE repository
- Install: `pip install ppx` or `conda install -c bioconda ppx`

**Manual Extraction (for JPST/PASS):**
- See `docs/manual_review_guide.md` for detailed instructions
- JPST: https://repository.jpostdb.org/entry/{JPST_ID}
- PASS: http://www.peptideatlas.org/PASS/{PASS_ID}

### Classification Logic

**HLA Type Classification:**
- Searches title, description, keywords, and project tags for HLA/MHC terms
- HLA I: Keywords like "HLA-A", "HLA-B", "HLA-C", "class I"
- HLA II: Keywords like "HLA-DR", "HLA-DQ", "class II"
- Marks as "needs manual confirmation" if HLA-related but class unclear

**Sample Type Classification:**
- Cell line: Highest priority, identified by known cell line names
- Blood: plasma, serum, PBMC, whole blood
- Tissue: organ names, tumor, biopsy

**Disease Classification:**
- Healthy controls identified by "healthy", "normal", "control" keywords
- Disease categories: Cancer, Neurodegenerative, Infectious Disease
- Uses disease fields from API and SDRF files

### Data Quality

**Quality Score Calculation:**
- High: 8+ key fields populated, has SDRF, has publication
- Medium: 5-7 key fields populated
- Low: <5 key fields populated

**Manual Review Triggers:**
- HLA type unclear from automated analysis
- Sample type is "Unknown"
- Disease type is "Unknown"
- Repository has no API (JPST, PASS)

### Expected Output Statistics

Based on 147 datasets:
- ~126 PXD datasets (fully automated)
- ~9 MSV datasets (automated with ppx)
- ~7 JPST datasets (manual extraction)
- ~1 PASS dataset (manual extraction)

Estimated completion time:
- Automated collection: 4-5 hours
- Manual extraction and review: 3-6 hours
- Total: 7-11 hours

### Development Notes

- The scripts use rate limiting (1-2 second delays) to respect API limits
- All raw API responses are saved for reproducibility
- The system is idempotent - can safely re-run scripts
- Excel formatting requires openpyxl package
- For large-scale updates, consider implementing caching
