import polars as pl

def process_large_csv(file_path: str):
    # Polars is much faster than pandas for large datasets
    df = pl.read_csv(file_path)
    
    # Example transformation: aggregate metrics
    # This is a placeholder for actual business logic
    summary = df.describe()
    
    return summary.to_dict()

def filter_data(file_path: str, column: str, value):
    df = pl.read_csv(file_path)
    filtered = df.filter(pl.col(column) == value)
    return filtered.to_dicts()
