import pandas as pd

def normalize_stock_number(stock_num):
    """
    Normalize stock numbers for consistent matching.
    Removes leading zeros, spaces, and converts to uppercase.
    """
    if pd.isna(stock_num):
        return ''
    stock_str = str(stock_num).strip().upper()
    if stock_str.isdigit():
        stock_str = str(int(stock_str))
    return stock_str

def normalize_vin(vin):
    """
    Normalize VIN for consistent matching.
    Removes spaces and converts to uppercase.
    """
    if pd.isna(vin):
        return ''
    vin_str = str(vin).strip().upper()
    vin_str = ''.join(c for c in vin_str if c.isalnum())
    return vin_str

def compare_inventories(df_vauto, df_reynolds):
    """
    Compare inventories primarily by stock number, with VIN as secondary validation.
    Stock number is the primary key for matching inventory between systems.
    """
    df_vauto = df_vauto.copy()
    df_reynolds = df_reynolds.copy()

    # Normalize stock numbers (primary key)
    df_vauto['stock_number_norm'] = df_vauto['stock_number'].apply(normalize_stock_number)
    df_reynolds['stock_number_norm'] = df_reynolds['stock_number'].apply(normalize_stock_number)

    # Normalize VINs if available (secondary validation)
    has_vin_vauto = 'vin' in df_vauto.columns and not df_vauto['vin'].isnull().all()
    has_vin_reynolds = 'vin' in df_reynolds.columns and not df_reynolds['vin'].isnull().all()
    
    if has_vin_vauto:
        df_vauto['vin_norm'] = df_vauto['vin'].apply(normalize_vin)
    if has_vin_reynolds:
        df_reynolds['vin_norm'] = df_reynolds['vin'].apply(normalize_vin)

    # Primary matching by stock number
    merged_by_stock = pd.merge(
        df_vauto, df_reynolds,
        on='stock_number_norm',
        how='outer',
        suffixes=('_vauto', '_reynolds'),
        indicator=True
    )

    # Categorize results
    exact_matches = merged_by_stock[merged_by_stock['_merge'] == 'both']
    missing_in_reynolds = merged_by_stock[merged_by_stock['_merge'] == 'left_only']
    missing_in_vauto = merged_by_stock[merged_by_stock['_merge'] == 'right_only']

    # Check for VIN mismatches in stock number matches
    vin_mismatches = pd.DataFrame()
    if has_vin_vauto and has_vin_reynolds and not exact_matches.empty:
        vin_mismatches = exact_matches[
            (exact_matches['vin_norm_vauto'] != exact_matches['vin_norm_reynolds']) &
            (exact_matches['vin_norm_vauto'] != '') &
            (exact_matches['vin_norm_reynolds'] != '')
        ]

    # Check for status mismatches in exact matches
    status_mismatches = pd.DataFrame()
    if 'status_vauto' in exact_matches.columns and 'status_reynolds' in exact_matches.columns:
        status_mismatches = exact_matches[
            exact_matches['status_vauto'].notna() & 
            exact_matches['status_reynolds'].notna() &
            (exact_matches['status_vauto'] != exact_matches['status_reynolds'])
        ]

    # Create summary statistics
    summary = {
        'total_vauto': len(df_vauto),
        'total_reynolds': len(df_reynolds),
        'exact_matches': len(exact_matches),
        'missing_in_reynolds': len(missing_in_reynolds),
        'missing_in_vauto': len(missing_in_vauto),
        'vin_mismatches': len(vin_mismatches),
        'status_mismatches': len(status_mismatches)
    }

    return {
        'exact_matches': exact_matches,
        'missing_in_reynolds': missing_in_reynolds,
        'missing_in_vauto': missing_in_vauto,
        'vin_mismatches': vin_mismatches,
        'status_mismatches': status_mismatches,
        'summary': summary,
        # Keep legacy keys for backward compatibility
        'missing_in_reynolds_by_stock': missing_in_reynolds,
        'missing_in_vauto_by_stock': missing_in_vauto,
        'missing_in_reynolds_by_vin': pd.DataFrame(),
        'missing_in_vauto_by_vin': pd.DataFrame(),
        'vin_matches_stock_diff': pd.DataFrame(),
        'stock_matches_vin_diff': vin_mismatches
    }

def analyze_matching_quality(df_vauto, df_reynolds, results):
    """
    Analyze the quality of the matching results.
    """
    analysis = {}
    
    # Check stock number format consistency
    if 'stock_number' in df_vauto.columns:
        vauto_stock_samples = df_vauto['stock_number'].dropna().head(10).tolist()
        analysis['vauto_stock_samples'] = vauto_stock_samples
    
    if 'stock_number' in df_reynolds.columns:
        reynolds_stock_samples = df_reynolds['stock_number'].dropna().head(10).tolist()
        analysis['reynolds_stock_samples'] = reynolds_stock_samples
    
    # Check for potential matching issues
    if results['summary']['exact_matches'] == 0:
        analysis['warning'] = "No exact matches found. Check stock number formats."
    
    if results['summary']['vin_mismatches'] > 0:
        analysis['warning'] = f"Found {results['summary']['vin_mismatches']} stock numbers with different VINs."
    
    return analysis
