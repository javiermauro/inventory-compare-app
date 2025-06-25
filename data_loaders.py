import pandas as pd
import re
from typing import Dict, List, Tuple, Optional
from config import VAUTO_COLUMNS_USED, VAUTO_COLUMNS_NEW, REYNOLDS_COLUMNS, REYNOLDS_COLUMNS_NEW

def normalize_column_name(col_name: str) -> str:
    if pd.isna(col_name):
        return ""
    col_str = str(col_name).strip().lower()
    col_str = re.sub(r'[^\w\s]', ' ', col_str)
    col_str = re.sub(r'\s+', ' ', col_str).strip()
    return col_str

def calculate_similarity_score(target: str, candidate: str) -> float:
    target_norm = normalize_column_name(target)
    candidate_norm = normalize_column_name(candidate)
    if target_norm == candidate_norm:
        return 1.0
    if target_norm in candidate_norm or candidate_norm in target_norm:
        return 0.8
    target_words = set(target_norm.split())
    candidate_words = set(candidate_norm.split())
    if not target_words or not candidate_words:
        return 0.0
    intersection = target_words.intersection(candidate_words)
    union = target_words.union(candidate_words)
    if union:
        return len(intersection) / len(union)
    return 0.0

def find_best_column_match(target_names: List[str], available_columns: List[str], min_similarity: float = 0.3) -> Tuple[Optional[str], float]:
    best_match = None
    best_score = 0.0
    for target in target_names:
        for col in available_columns:
            score = calculate_similarity_score(target, col)
            if score > best_score and score >= min_similarity:
                best_score = score
                best_match = col
    return best_match, best_score

def auto_detect_column_mapping(standard_columns: Dict[str, List[str]], df_columns: List[str]) -> Dict[str, Dict]:
    mapping = {}
    confidence_scores = {}
    for std_col, possible_names in standard_columns.items():
        matched_col, score = find_best_column_match(possible_names, df_columns)
        if matched_col:
            mapping[std_col] = matched_col
            confidence_scores[std_col] = score
        else:
            mapping[std_col] = None
            confidence_scores[std_col] = 0.0
    return {
        'mapping': mapping,
        'confidence_scores': confidence_scores,
        'available_columns': df_columns
    }

def analyze_column_content(df: pd.DataFrame, column: str) -> Dict:
    if column not in df.columns:
        return {}
    col_data = df[column].dropna()
    analysis = {
        'total_rows': len(df),
        'non_null_count': len(col_data),
        'unique_count': col_data.nunique(),
        'sample_values': col_data.head(10).tolist(),
        'data_type': str(df[column].dtype)
    }
    if len(col_data) > 0:
        sample_str = str(col_data.iloc[0])
        analysis['looks_like_vin'] = (
            len(sample_str) == 17 and 
            sample_str.isalnum() and 
            not sample_str.isdigit()
        )
        analysis['looks_like_stock'] = (
            sample_str.isdigit() or 
            (sample_str.isalnum() and len(sample_str) <= 10)
        )
    return analysis

def load_vauto_inventory(filepath, is_new=False, auto_map=True):
    try:
        df = pd.read_excel(filepath, engine=None)
        if auto_map:
            standard_columns = {
                'stock_number': ['Stock #', 'Stock Number', 'Stock#', 'StockNum', 'Stock', 'Stock No', 'Stock Number'],
                'vin': ['VIN', 'Vehicle Identification Number', 'Vehicle ID', 'VIN Number'],
                'store': ['Dealer Name', 'Store', 'Location', 'Dealer', 'Dealership', 'Store Name', 'Dealer Location'],
                'status': ['Status', 'Vehicle Status', 'Car Status', 'Inventory Status'],
                'year': ['Year', 'Model Year', 'Vehicle Year'],
                'make': ['Make', 'Manufacturer', 'Brand'],
                'model': ['Model', 'Vehicle Model', 'Car Model'],
                'type': ['Type', 'Inventory Type', 'New/Used', 'N/U', 'Vehicle Type']
            }
            detection_result = auto_detect_column_mapping(standard_columns, list(df.columns))
            mapping = detection_result['mapping']
            confidence_scores = detection_result['confidence_scores']
            norm = {}
            for std_col, file_col in mapping.items():
                if file_col:
                    norm[std_col] = df[file_col]
                else:
                    norm[std_col] = None
            result_df = pd.DataFrame(norm)
            result_df.attrs['column_mapping'] = mapping
            result_df.attrs['confidence_scores'] = confidence_scores
            result_df.attrs['missing_columns'] = [col for col, mapped in mapping.items() if mapped is None]
            result_df.attrs['original_columns'] = list(df.columns)
            result_df.attrs['column_analysis'] = {
                col: analyze_column_content(df, col) for col in df.columns
            }
            return result_df
        else:
            columns = VAUTO_COLUMNS_NEW if is_new else VAUTO_COLUMNS_USED
            norm = {}
            for std_col, file_col in columns.items():
                if file_col in df.columns:
                    norm[std_col] = df[file_col]
                else:
                    norm[std_col] = None
            return pd.DataFrame(norm)
    except Exception as e:
        raise Exception(f"Error loading VAUTO file: {str(e)}")

def load_reynolds_inventory(filepath, is_new=False, auto_map=True):
    try:
        df = pd.read_excel(filepath, engine=None)
        if auto_map:
            standard_columns = {
                'stock_number': ['Stock #', 'Stock Number', 'Stock#', 'StockNum', 'Stock', 'Stock No', 'Stock Number'],
                'vin': ['VIN', 'Vehicle Identification Number', 'Vehicle ID', 'VIN Number'],
                'store': ['Store', 'Dealer', 'Dealership', 'Store Name', 'Dealer Name'],
                'status': ['Status', 'Vehicle Status', 'Car Status', 'Inventory Status'],
                'year': ['Year', 'Model Year', 'Vehicle Year'],
                'make': ['Make', 'Manufacturer', 'Brand'],
                'model': ['Model', 'Vehicle Model', 'Car Model'],
                'type': ['N/U', 'Type', 'Inventory Type', 'New/Used', 'Vehicle Type']
            }
            detection_result = auto_detect_column_mapping(standard_columns, list(df.columns))
            mapping = detection_result['mapping']
            confidence_scores = detection_result['confidence_scores']
            norm = {}
            for std_col, file_col in mapping.items():
                if file_col:
                    norm[std_col] = df[file_col]
                else:
                    norm[std_col] = None
            result_df = pd.DataFrame(norm)
            result_df.attrs['column_mapping'] = mapping
            result_df.attrs['confidence_scores'] = confidence_scores
            result_df.attrs['missing_columns'] = [col for col, mapped in mapping.items() if mapped is None]
            result_df.attrs['original_columns'] = list(df.columns)
            result_df.attrs['column_analysis'] = {
                col: analyze_column_content(df, col) for col in df.columns
            }
            return result_df
        else:
            columns = REYNOLDS_COLUMNS_NEW if is_new else REYNOLDS_COLUMNS
            norm = {}
            for std_col, file_col in columns.items():
                if file_col in df.columns:
                    norm[std_col] = df[file_col]
                else:
                    norm[std_col] = None
            return pd.DataFrame(norm)
    except Exception as e:
        raise Exception(f"Error loading Reynolds file: {str(e)}")

def inspect_excel_file(filepath, engine=None, nrows=5):
    try:
        df = pd.read_excel(filepath, engine=engine)
        print(f"File: {filepath}")
        print("Columns:", list(df.columns))
        print("Data types:", df.dtypes.to_dict())
        print("Sample rows:")
        print(df.head(nrows))
        print("-" * 40)
        return df
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None

if __name__ == "__main__":
    vauto_used_file = "ALLINVENTORYVAR-AMSI - REZI HQ-2025-04-28-1100.xls"
    reynolds_file = "Reynolds MRN.xlsx"
    print("Testing auto-detection...")
    print("USED VAUTO (auto-detected):")
    try:
        vauto_df = load_vauto_inventory(vauto_used_file, is_new=False, auto_map=True)
        print(vauto_df.head())
        print("Mapping:", vauto_df.attrs.get('column_mapping', {}))
        print("Confidence:", vauto_df.attrs.get('confidence_scores', {}))
    except Exception as e:
        print(f"Error: {e}")
    print("\nREYNOLDS (auto-detected):")
    try:
        reynolds_df = load_reynolds_inventory(reynolds_file, auto_map=True)
        print(reynolds_df.head())
        print("Mapping:", reynolds_df.attrs.get('column_mapping', {}))
        print("Confidence:", reynolds_df.attrs.get('confidence_scores', {}))
    except Exception as e:
        print(f"Error: {e}")
