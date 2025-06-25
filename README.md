# Inventory Compare App for Car Dealership

This Streamlit app lets you compare inventory lists from VAUTO (.xls) and Reynolds (.xlsx) across six stores, separated by NEW and USED inventory. It highlights missing vehicles and status mismatches, and allows you to download a detailed report.

## Features
- Upload VAUTO (.xls) and Reynolds (.xlsx) files
- Select store and inventory type (NEW/USED)
- See side-by-side comparison, missing vehicles, and status mismatches
- Download Excel report

## Requirements
- Python 3.8+

## Setup
```bash
pip install -r requirements.txt
```

## Running the App
```bash
streamlit run app.py
```

## File Format Assumptions
- Both files have columns: `VIN`, `STOCK NUMBER`, `Store`, `Type` (NEW/USED)
- Reynolds file has a `Status` column

If your columns are named differently, edit them in `app.py` or let your developer know.

---
