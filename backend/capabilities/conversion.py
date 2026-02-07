import pandas as pd
from typing import Optional

def convert_csv_to_xlsx(csv_path: str, xlsx_path: str):
    """Convert CSV file to Excel XLSX format."""
    try:
        df = pd.read_csv(csv_path)
        df.to_excel(xlsx_path, index=False)
        return f"Converted {csv_path} to {xlsx_path}"
    except Exception as e:
        return f"Error converting CSV to XLSX: {str(e)}"

def convert_xlsx_to_csv(xlsx_path: str, csv_path: str):
    """Convert Excel XLSX file to CSV format."""
    try:
        df = pd.read_excel(xlsx_path)
        df.to_csv(csv_path, index=False)
        return f"Converted {xlsx_path} to {csv_path}"
    except Exception as e:
        return f"Error converting XLSX to CSV: {str(e)}"

def convert_json_to_csv(json_path: str, csv_path: str):
    """Convert JSON file to CSV format."""
    try:
        df = pd.read_json(json_path)
        df.to_csv(csv_path, index=False)
        return f"Converted {json_path} to {csv_path}"
    except Exception as e:
        return f"Error converting JSON to CSV: {str(e)}"
