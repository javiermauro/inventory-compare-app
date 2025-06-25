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

# --- Sidebar toggles for expanders ---
st.sidebar.header("Show/Hide Sections")
show_raw = st.sidebar.checkbox("Raw Reynolds File Preview", value=False)
show_mapping = st.sidebar.checkbox("Column Mapping Results", value=False)
show_debug = st.sidebar.checkbox("Debug Information", value=False)
show_detailed = st.sidebar.checkbox("Detailed Results", value=True)

# --- File Upload ---
vauto_file = st.file_uploader("Upload VAUTO Inventory (.xls/.xlsx)", type=["xls", "xlsx"])
reynolds_file = st.file_uploader("Upload Reynolds Inventory (.xlsx)", type=["xlsx"])

# Show raw Reynolds file content before any mapping or filtering
if reynolds_file is not None and show_raw:
    with st.expander("📄 Raw Reynolds File Preview", expanded=True):
        try:
            reynolds_raw = pd.read_excel(reynolds_file, engine=None)
            st.write('**Columns:**', list(reynolds_raw.columns))
            st.dataframe(reynolds_raw.head(5))
        except Exception as e:
            st.error(f"Error reading Reynolds file: {e}")

# --- Inventory Type Selection ---
inv_type = st.radio("Select Inventory Type", ["USED", "NEW"], horizontal=True)

if vauto_file and reynolds_file:
    is_new = (inv_type == "NEW")
    # Load and normalize with auto-mapping
    vauto_df = load_vauto_inventory(vauto_file, is_new=is_new, auto_map=True)
    reynolds_df = load_reynolds_inventory(reynolds_file, is_new=is_new, auto_map=True)

    # --- Show detected column mappings and confidence scores ---
    if show_mapping:
        with st.expander("🔧 Column Mapping Results", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
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
            with col2:
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

    # --- Check for missing columns after normalization ---
    required_vauto_cols = ['stock_number', 'vin', 'store']
    missing_vauto_cols = [col for col in required_vauto_cols if col not in vauto_df.columns or vauto_df[col].isnull().all()]
    if missing_vauto_cols:
        st.error(f"VAUTO file is missing required columns: {missing_vauto_cols}")

    required_reynolds_cols = ['stock_number']
    missing_reynolds_cols = [col for col in required_reynolds_cols if col not in reynolds_df.columns or reynolds_df[col].isnull().all()]
    if missing_reynolds_cols:
        st.error(f"Reynolds file is missing required columns: {missing_reynolds_cols}")

    # --- Store Selection ---
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
        st.error("No valid stores found in VAUTO file.")
        store = st.text_input("Enter Store Name (manual entry)", value="")
    else:
        st.markdown(f"**Available stores:** {', '.join(stores_vauto)}")
        store = st.selectbox("Select Store", options=stores_vauto)

    if store:
        st.markdown(f"### Working on Store: **{store}**")

        # Filter VAUTO by store
        vauto_sub = vauto_df[
            vauto_df['store'].astype(str).str.strip().str.upper() == store.strip().upper()
        ]

        # Filter Reynolds by store (if store column exists and is not empty)
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
            st.info("Reynolds file does not have a store column. All rows will be compared.")
            reynolds_sub = reynolds_df

        # Filter by type if possible (for Reynolds)
        if 'type' in reynolds_sub.columns and reynolds_sub['type'].notna().any():
            reynolds_sub = reynolds_sub[reynolds_sub['type'].str.upper() == inv_type]

        # Show record counts
        st.info(f"📊 VAUTO records for '{store}': {len(vauto_sub)} | Reynolds records: {len(reynolds_sub)}")

        if len(vauto_sub) == 0:
            st.warning(f"No VAUTO records found for store '{store}'.")
        else:
            # --- Compare inventories ---
            result = compare_inventories(vauto_sub, reynolds_sub)
            analysis = analyze_matching_quality(vauto_sub, reynolds_sub, result)

            # Show matching analysis
            st.markdown("### 📈 Matching Analysis")
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

            # Show warnings if any
            if 'warning' in analysis:
                st.warning(analysis['warning'])

            # Show detailed results
            if show_detailed:
                st.markdown("### 📋 Detailed Results")
                with st.expander("✅ Exact Matches", expanded=True):
                    if not result['exact_matches'].empty:
                        st.dataframe(result['exact_matches'])
                    else:
                        st.info("No exact matches found")
                with st.expander("❌ Missing in Reynolds", expanded=False):
                    if not result['missing_in_reynolds'].empty:
                        st.dataframe(result['missing_in_reynolds'])
                    else:
                        st.info("No vehicles missing in Reynolds")
                with st.expander("❌ Missing in VAUTO", expanded=False):
                    if not result['missing_in_vauto'].empty:
                        st.dataframe(result['missing_in_vauto'])
                    else:
                        st.info("No vehicles missing in VAUTO")
                with st.expander("⚠️ VIN Mismatches", expanded=False):
                    if not result['vin_mismatches'].empty:
                        st.dataframe(result['vin_mismatches'])
                    else:
                        st.info("No VIN mismatches found")
                with st.expander("⚠️ Status Mismatches", expanded=False):
                    if not result['status_mismatches'].empty:
                        st.dataframe(result['status_mismatches'])
                    else:
                        st.info("No status mismatches found")

            # Debug information (collapsed by default)
            if show_debug:
                with st.expander("🔍 Debug Information", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**VAUTO Data:**")
                        st.write(f"Shape: {vauto_sub.shape}")
                        st.write("Sample stock numbers:")
                        st.write(vauto_sub['stock_number'].dropna().head(5).tolist())
                    with col2:
                        st.write("**Reynolds Data:**")
                        st.write(f"Shape: {reynolds_sub.shape}")
                        st.write("Sample stock numbers:")
                        st.write(reynolds_sub['stock_number'].dropna().head(5).tolist())
                    vauto_stocks = set(vauto_sub['stock_number'].dropna().astype(str))
                    reynolds_stocks = set(reynolds_sub['stock_number'].dropna().astype(str))
                    intersection = vauto_stocks.intersection(reynolds_stocks)
                    st.write(f"**Stock Number Analysis:**")
                    st.write(f"VAUTO unique: {len(vauto_stocks)} | Reynolds unique: {len(reynolds_stocks)} | Matches: {len(intersection)}")
                    if intersection:
                        st.write("Matching stock numbers:", list(intersection)[:10])
                    else:
                        st.write("No exact string matches found!")

            # --- Download Report ---
            st.markdown("### 📥 Download Report")
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                result['exact_matches'].to_excel(writer, sheet_name='Exact Matches', index=False)
                result['missing_in_reynolds'].to_excel(writer, sheet_name='Missing in Reynolds', index=False)
                result['missing_in_vauto'].to_excel(writer, sheet_name='Missing in VAUTO', index=False)
                result['vin_mismatches'].to_excel(writer, sheet_name='VIN Mismatches', index=False)
                result['status_mismatches'].to_excel(writer, sheet_name='Status Mismatches', index=False)
            st.download_button(
                label="📊 Download Excel Report",
                data=output.getvalue(),
                file_name=f'inventory_comparison_{store}_{inv_type}.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
else:
    st.info("Please upload both VAUTO and Reynolds files to begin.")
