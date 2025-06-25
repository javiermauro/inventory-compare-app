import streamlit as st
import pandas as pd
from data_loaders import load_vauto_inventory, load_reynolds_inventory
from comparison import compare_inventories, analyze_matching_quality
from config import STORES
import io

st.set_page_config(page_title="Inventory Compare App", layout="wide")
st.title("Car Dealership Inventory Comparison Tool")
st.markdown("Upload VAUTO (.xls/.xlsx) and Reynolds (.xlsx) inventory files to compare by VIN and STOCK NUMBER, separated by NEW/USED and by store.")

st.markdown("""
**Instructions for Inventory Files**

- **VAUTO:** Use the report named **ALLINVENTORYVAR**.
- **REYNOLDS:** Use Inventory reports in **DASHBOARDS**. Use the **New** and **Used Inventory Reports**.
- **Do NOT use RMI favorites.**
- **Use only what is already built** in the system.
""")

# --- File Upload ---
vauto_file = st.file_uploader("Upload VAUTO Inventory (.xls/.xlsx)", type=["xls", "xlsx"])
reynolds_file = st.file_uploader("Upload Reynolds Inventory (.xlsx)", type=["xlsx"])

# Show raw Reynolds file content before any mapping or filtering
if reynolds_file is not None:
    try:
        reynolds_raw = pd.read_excel(reynolds_file, engine=None)
        st.markdown("#### Raw Reynolds File Preview (First 10 Rows)")
        st.write('Raw columns:', list(reynolds_raw.columns))
        st.dataframe(reynolds_raw.head(10))
    except Exception as e:
        st.error(f"Error reading Reynolds file: {e}")

# --- Inventory Type Selection ---
inv_type = st.radio("Select Inventory Type", ["USED", "NEW"], horizontal=True)

if vauto_file and reynolds_file:
    is_new = (inv_type == "NEW")
    # Load and normalize with auto-mapping
    vauto_df = load_vauto_inventory(vauto_file, is_new=is_new, auto_map=True)
    reynolds_df = load_reynolds_inventory(reynolds_file, is_new=is_new, auto_map=True)

    # Debug: Show mapped Reynolds DataFrame after mapping, before filtering
    st.markdown('#### Reynolds DataFrame After Mapping (First 10 Rows)')
    st.write('Mapped columns:', list(reynolds_df.columns))
    st.dataframe(reynolds_df.head(10))
    st.write('Non-null stock_number count:', reynolds_df["stock_number"].notna().sum())

    # --- Show detected column mappings and confidence scores ---
    st.markdown("#### VAUTO Detected Column Mapping")
    vauto_mapping = vauto_df.attrs.get('column_mapping', {})
    vauto_conf = vauto_df.attrs.get('confidence_scores', {})
    vauto_missing = vauto_df.attrs.get('missing_columns', [])
    if vauto_mapping:
        for std_col, mapped_col in vauto_mapping.items():
            conf = vauto_conf.get(std_col, 0)
            if mapped_col:
                st.write(f"✅ {std_col} → {mapped_col} (confidence: {conf:.2f})")
            else:
                st.write(f"❌ {std_col} (not found)")
    if vauto_missing:
        st.warning(f"Missing VAUTO columns: {vauto_missing}")

    st.markdown("#### Reynolds Detected Column Mapping")
    reynolds_mapping = reynolds_df.attrs.get('column_mapping', {})
    reynolds_conf = reynolds_df.attrs.get('confidence_scores', {})
    reynolds_missing = reynolds_df.attrs.get('missing_columns', [])
    if reynolds_mapping:
        for std_col, mapped_col in reynolds_mapping.items():
            conf = reynolds_conf.get(std_col, 0)
            if mapped_col:
                st.write(f"✅ {std_col} → {mapped_col} (confidence: {conf:.2f})")
            else:
                st.write(f"❌ {std_col} (not found)")
    if reynolds_missing:
        st.warning(f"Missing Reynolds columns: {reynolds_missing}")

    # --- Debug: Check for missing columns after normalization ---
    required_vauto_cols = ['stock_number', 'vin', 'store']
    missing_vauto_cols = [col for col in required_vauto_cols if col not in vauto_df.columns or vauto_df[col].isnull().all()]
    if missing_vauto_cols:
        st.warning(f"VAUTO file is missing required columns after normalization: {missing_vauto_cols}. Please check your file and config.py mappings.")
        st.write('Normalized VAUTO columns:', list(vauto_df.columns))
        st.dataframe(vauto_df.head(5))

    required_reynolds_cols = ['stock_number', 'vin']
    missing_reynolds_cols = [col for col in required_reynolds_cols if col not in reynolds_df.columns or reynolds_df[col].isnull().all()]
    if missing_reynolds_cols:
        st.warning(f"Reynolds file is missing required columns after normalization: {missing_reynolds_cols}. Please check your file and config.py mappings.")
        st.write('Normalized Reynolds columns:', list(reynolds_df.columns))
        st.dataframe(reynolds_df.head(5))

    # --- Debug: Show unique store names in both files ---
    st.write('Unique stores in VAUTO:', vauto_df['store'].dropna().unique().tolist())
    if 'store' in reynolds_df.columns:
        st.write('Unique stores in Reynolds:', reynolds_df['store'].dropna().unique().tolist())
    elif 'Location' in reynolds_df.columns:
        st.write('Unique stores in Reynolds (Location):', reynolds_df['Location'].dropna().unique().tolist())

    # --- Debug: Show Reynolds columns and first few rows before filtering
    st.write('Reynolds columns:', list(reynolds_df.columns))
    st.write('First 5 rows of Reynolds:', reynolds_df.head())

    # --- Store Selection (Enhanced) ---
    # Clean, dropna, strip, and sort unique store names
    stores_vauto = (
        vauto_df['store']
        .dropna()
        .astype(str)
        .map(str.strip)
        .replace('', pd.NA)
        .dropna()
        .unique()
        .tolist()
    )
    stores_vauto = sorted(set(stores_vauto))

    if not stores_vauto:
        st.error("No valid stores found in VAUTO file. Please check your VAUTO file or column mapping in config.py.")
        store = st.text_input("Enter Store Name (manual entry)", value="")
    else:
        st.markdown(f"**Detected stores in VAUTO:** {', '.join(stores_vauto)}")
        store = st.selectbox("Select Store (from VAUTO)", options=stores_vauto)

    st.markdown(f"### Working on Store: **{store}**")
    st.info("Note: Reynolds file should contain inventory for the selected store only. VAUTO is filtered by store.")

    # Filter VAUTO by store only if store is not blank
    if store:
        vauto_sub = vauto_df[
            vauto_df['store'].astype(str).str.strip().str.upper() == store.strip().upper()
        ]
    else:
        vauto_sub = vauto_df.iloc[0:0]  # Empty DataFrame if store not selected

    # Filter Reynolds by store as well (if store column exists and is not empty)
    if 'store' in reynolds_df.columns and reynolds_df['store'].notna().any():
        reynolds_sub = reynolds_df[
            reynolds_df['store'].astype(str).str.strip().str.upper() == store.strip().upper()
        ]
    elif 'Location' in reynolds_df.columns and reynolds_df['Location'].notna().any():
        reynolds_sub = reynolds_df[
            reynolds_df['Location'].astype(str).str.strip().str.upper() == store.strip().upper()
        ]
        reynolds_sub = reynolds_sub.copy()
        reynolds_sub['store'] = reynolds_sub['Location']
    else:
        st.info("Reynolds file does not have a valid store column. All rows will be compared. Please ensure the Reynolds file only contains inventory for the selected store.", icon="ℹ️")
        reynolds_sub = reynolds_df

    # --- Debug: Show unique stock numbers for selected store ---
    st.write(f"Unique stock numbers in VAUTO for {store}:", vauto_sub['stock_number'].dropna().unique().tolist())
    st.write(f"Unique stock numbers in Reynolds for {store}:", reynolds_sub['stock_number'].dropna().unique().tolist())

    # Filter by type if possible (for Reynolds)
    if 'type' in reynolds_sub.columns and reynolds_sub['type'].notna().any():
        reynolds_sub = reynolds_sub[reynolds_sub['type'].str.upper() == inv_type]

    # --- Compare inventories with improved stock number matching ---
    result = compare_inventories(vauto_sub, reynolds_sub)
    analysis = analyze_matching_quality(vauto_sub, reynolds_sub, result)

    # Show matching analysis
    st.markdown("### Matching Analysis")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total VAUTO", result['summary']['total_vauto'])
    with col2:
        st.metric("Total Reynolds", result['summary']['total_reynolds'])
    with col3:
        st.metric("Exact Matches", result['summary']['exact_matches'])
    with col4:
        match_rate = (result['summary']['exact_matches'] / max(result['summary']['total_vauto'], result['summary']['total_reynolds'])) * 100 if max(result['summary']['total_vauto'], result['summary']['total_reynolds']) > 0 else 0
        st.metric("Match Rate", f"{match_rate:.1f}%")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Missing in Reynolds", result['summary']['missing_in_reynolds'])
        st.metric("Missing in VAUTO", result['summary']['missing_in_vauto'])
    with col2:
        st.metric("VIN Mismatches", result['summary']['vin_mismatches'])
        st.metric("Status Mismatches", result['summary']['status_mismatches'])

    if 'warning' in analysis:
        st.warning(analysis['warning'])

    if 'vauto_stock_samples' in analysis or 'reynolds_stock_samples' in analysis:
        with st.expander("Stock Number Samples (for debugging)"):
            col1, col2 = st.columns(2)
            with col1:
                st.write("VAUTO stock numbers:", analysis.get('vauto_stock_samples', []))
            with col2:
                st.write("Reynolds stock numbers:", analysis.get('reynolds_stock_samples', []))

    st.markdown("### Detailed Results")
    with st.expander("Exact Matches (Stock Number + VIN + Status)"):
        if not result['exact_matches'].empty:
            st.dataframe(result['exact_matches'])
        else:
            st.info("No exact matches found")
    with st.expander("Missing in Reynolds"):
        if not result['missing_in_reynolds'].empty:
            st.dataframe(result['missing_in_reynolds'])
        else:
            st.info("No vehicles missing in Reynolds")
    with st.expander("Missing in VAUTO"):
        if not result['missing_in_vauto'].empty:
            st.dataframe(result['missing_in_vauto'])
        else:
            st.info("No vehicles missing in VAUTO")
    with st.expander("VIN Mismatches (Same Stock Number, Different VIN)"):
        if not result['vin_mismatches'].empty:
            st.dataframe(result['vin_mismatches'])
        else:
            st.info("No VIN mismatches found")
    with st.expander("Status Mismatches (Same Stock Number, Different Status)"):
        if not result['status_mismatches'].empty:
            st.dataframe(result['status_mismatches'])
        else:
            st.info("No status mismatches found")

    # --- Download Enhanced Report ---
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        result['missing_in_reynolds_by_vin'].to_excel(writer, sheet_name='Missing in Reynolds VIN', index=False)
        result['missing_in_vauto_by_vin'].to_excel(writer, sheet_name='Missing in VAUTO VIN', index=False)
        result['status_mismatches'].to_excel(writer, sheet_name='Status Mismatches', index=False)
        # Keep all categories in Excel for full audit
        result['exact_matches'].to_excel(writer, sheet_name='Exact Matches', index=False)
        result['vin_matches_stock_diff'].to_excel(writer, sheet_name='VIN Match Stock Diff', index=False)
        result['stock_matches_vin_diff'].to_excel(writer, sheet_name='Stock Match VIN Diff', index=False)
        result['missing_in_reynolds_by_stock'].to_excel(writer, sheet_name='Missing in Reynolds Stock', index=False)
        result['missing_in_vauto_by_stock'].to_excel(writer, sheet_name='Missing in VAUTO Stock', index=False)
    st.download_button(
        label="Download Full Excel Report",
        data=output.getvalue(),
        file_name=f'inventory_comparison_{store}_{inv_type}_full.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    # Show number of records in each DataFrame before matching
    st.info(f"Filtered VAUTO records for '{store}': {len(vauto_sub)}")
    st.info(f"Reynolds records: {len(reynolds_sub)}")
    if len(vauto_sub) == 0:
        st.warning(f"No VAUTO records found for store '{store}'. Please check the store name and try again.")

    # Debug: Show filtered stock numbers side by side
    with st.expander("Filtered Stock Numbers (Debug)"):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"VAUTO stock numbers for '{store}':")
            st.write(vauto_sub['stock_number'].dropna().astype(str).unique().tolist())
        with col2:
            st.write("Reynolds stock numbers:")
            st.write(reynolds_sub['stock_number'].dropna().astype(str).unique().tolist())

    # Add comprehensive debugging information
    st.markdown("### Debug Information")
    with st.expander("Detailed Debug Info"):
        col1, col2 = st.columns(2)
        with col1:
            st.write("**VAUTO Data:**")
            st.write(f"Shape: {vauto_sub.shape}")
            st.write(f"Stock number column: {vauto_sub['stock_number'].dtype}")
            st.write("Sample stock numbers (original):")
            st.write(vauto_sub['stock_number'].dropna().head(10).tolist())
            if 'stock_number_norm' in vauto_sub.columns:
                st.write("Sample stock numbers (normalized):")
                st.write(vauto_sub['stock_number_norm'].dropna().head(10).tolist())
        with col2:
            st.write("**Reynolds Data:**")
            st.write(f"Shape: {reynolds_sub.shape}")
            st.write(f"Stock number column: {reynolds_sub['stock_number'].dtype}")
            st.write("Sample stock numbers (original):")
            st.write(reynolds_sub['stock_number'].dropna().head(10).tolist())
            if 'stock_number_norm' in reynolds_sub.columns:
                st.write("Sample stock numbers (normalized):")
                st.write(reynolds_sub['stock_number_norm'].dropna().head(10).tolist())
        st.write("**Merge Results:**")
        if 'debug_info' in result:
            st.write("Merge counts:", result['debug_info'].get('merge_counts', {}))
        vauto_stocks = set(vauto_sub['stock_number'].dropna().astype(str))
        reynolds_stocks = set(reynolds_sub['stock_number'].dropna().astype(str))
        intersection = vauto_stocks.intersection(reynolds_stocks)
        st.write(f"**Stock Number Analysis:**")
        st.write(f"VAUTO unique stock numbers: {len(vauto_stocks)}")
        st.write(f"Reynolds unique stock numbers: {len(reynolds_stocks)}")
        st.write(f"Exact string matches: {len(intersection)}")
        if intersection:
            st.write("Matching stock numbers:", list(intersection)[:10])
        else:
            st.write("No exact string matches found!")
            st.write("**Sample comparison:**")
            vauto_sample = list(vauto_stocks)[:5]
            reynolds_sample = list(reynolds_stocks)[:5]
            st.write("VAUTO samples:", vauto_sample)
            st.write("Reynolds samples:", reynolds_sample)
else:
    st.info("Please upload both VAUTO and Reynolds files to begin.")
