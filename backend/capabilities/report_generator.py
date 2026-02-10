"""
Report Generator — S1 Orchestrator
Ties together: Data Reading → LLM Analysis → Schema Output → Document Building.

The LLM ONLY outputs structured ReportSchema JSON.
The Builder ONLY renders pre-written document formatting.
Neither has access to the other's domain.
"""

import dspy
import os
import pandas as pd
from typing import Optional
from datetime import datetime

from capabilities.report_schema import ReportSchema, ReportSection, TableConfig
from capabilities.doc_builder import build_report


# ============================================================
# DSPy Signature — LLM outputs ReportSchema JSON, NOT code
# ============================================================
class ReportAnalyzer(dspy.Signature):
    """
    You are a Data Analyst. Analyze the given data and produce a structured report.
    
    RULES:
    1. Output ONLY valid JSON matching the ReportSchema.
    2. Do NOT write any Python code. Do NOT use import statements.
    3. The 'summary' should be a clear executive summary of findings.
    4. Each 'section' should have a descriptive heading and analytical content.
    5. 'pandas_filter_expression' must be a valid pandas expression using 'df' as the variable.
       - Example: "df[df['Salary'] > 50000]"
       - Example: "df[df['Age'] >= 30]"
       - Example: "df" (for no filtering — include all data)
    6. 'filter_description' should be human-readable: "Employees with Salary > 50,000"
    7. Include 2-3 relevant analysis sections (e.g., "Key Findings", "Statistics", "Recommendations").
    """
    task_description: str = dspy.InputField(desc="The user's natural language request")
    data_columns: str = dspy.InputField(desc="Comma-separated column names from the data source")
    data_sample: str = dspy.InputField(desc="First 5 rows of data as a string for context")
    report_json: ReportSchema = dspy.OutputField(desc="Structured report as JSON matching ReportSchema")


# Initialize predictor
report_predictor = dspy.Predict(ReportAnalyzer)


def generate_report_from_data(task: str, file_path: str) -> dict:
    """
    S1 Orchestrator: Read data → LLM generates schema → Builder renders document.
    
    Args:
        task: Natural language task description
        file_path: Path to the source data file (Excel/CSV)
        
    Returns:
        dict with keys: status, output_path, summary, error
    """
    print(f"[DOC_REPORT] Starting report generation for: {task}")
    print(f"[DOC_REPORT] Source file: {file_path}")
    
    result = {
        "status": "error",
        "output_path": None,
        "summary": "",
        "error": None
    }
    
    # ── Step 1: Read Source Data ──
    try:
        if not os.path.exists(file_path):
            result["error"] = f"File not found: {file_path}"
            return result
            
        if file_path.lower().endswith('.csv'):
            df = pd.read_csv(file_path)
        elif file_path.lower().endswith(('.xls', '.xlsx')):
            df = pd.read_excel(file_path)
        else:
            result["error"] = f"Unsupported file format: {file_path}"
            return result
            
        print(f"[DOC_REPORT] Read {len(df)} rows, columns: {list(df.columns)}")
        
    except Exception as e:
        result["error"] = f"Failed to read file: {str(e)}"
        return result

    # ── Step 2: LLM Generates ReportSchema (Data Only, No Code) ──
    try:
        columns_str = ", ".join(str(c) for c in df.columns)
        sample_str = df.head(5).to_string(index=False)
        
        prediction = report_predictor(
            task_description=task,
            data_columns=columns_str,
            data_sample=sample_str
        )
        
        # Extract the ReportSchema from prediction
        report_data = prediction.report_json
        
        # Handle case where DSPy returns a dict instead of Pydantic model
        if isinstance(report_data, dict):
            report_data = ReportSchema(**report_data)
        elif not isinstance(report_data, ReportSchema):
            # Try to parse from string
            import json
            if isinstance(report_data, str):
                parsed = json.loads(report_data)
                report_data = ReportSchema(**parsed)
                
        print(f"[DOC_REPORT] LLM generated schema: title='{report_data.title}'")
        print(f"[DOC_REPORT] Filter expression: {report_data.pandas_filter_expression}")
        
    except Exception as e:
        print(f"[DOC_REPORT] LLM schema generation failed: {e}")
        # Fallback: Create a basic schema manually
        report_data = ReportSchema(
            title=f"Report: {os.path.basename(file_path)}",
            summary=f"Data extracted from {os.path.basename(file_path)}. Task: {task}",
            sections=[
                ReportSection(
                    heading="Data Overview",
                    content=f"The dataset contains {len(df)} rows and {len(df.columns)} columns: {', '.join(str(c) for c in df.columns)}."
                )
            ],
            table_config=TableConfig(include=True, caption="Extracted Data"),
            filtered_row_count=len(df),
            filter_description="All data (no filter applied)",
            pandas_filter_expression="df"
        )
    
    # ── Step 3: Apply Filter (Safely) ──
    filtered_df = df  # Default: no filter
    
    if report_data.pandas_filter_expression and report_data.pandas_filter_expression.strip() != "df":
        try:
            # Safe evaluation: only allow pandas operations on 'df'
            filter_expr = report_data.pandas_filter_expression.strip()
            
            # Security: Reject dangerous expressions
            dangerous = ["import", "exec", "eval", "os.", "sys.", "__", "open(", "subprocess"]
            if any(d in filter_expr.lower() for d in dangerous):
                print(f"[DOC_REPORT] BLOCKED dangerous filter: {filter_expr}")
                result["error"] = "Filter expression contains forbidden operations."
                return result
            
            # Execute filter in restricted scope
            filtered_df = eval(filter_expr, {"df": df, "pd": pd})
            
            if not isinstance(filtered_df, pd.DataFrame):
                print(f"[DOC_REPORT] Filter did not return DataFrame, using unfiltered data")
                filtered_df = df
            else:
                print(f"[DOC_REPORT] Filter applied: {len(df)} → {len(filtered_df)} rows")
                
        except Exception as e:
            print(f"[DOC_REPORT] Filter failed ({e}), using unfiltered data")
            filtered_df = df
    
    # Update row count
    report_data.filtered_row_count = len(filtered_df)
    
    # ── Step 4: Build Document (Deterministic, No LLM) ──
    try:
        output_path = build_report(
            schema=report_data,
            df=filtered_df,
            output_path=None  # Auto-generate path
        )
        
        print(f"[DOC_REPORT] Document saved to: {output_path}")
        
        # Open the document
        try:
            os.startfile(output_path)
        except Exception:
            pass  # Non-critical if startfile fails
        
        result["status"] = "success"
        result["output_path"] = output_path
        result["summary"] = (
            f"Created report '{report_data.title}' with {len(filtered_df)} records. "
            f"Saved to: {os.path.basename(output_path)}"
        )
        
    except Exception as e:
        result["error"] = f"Failed to build document: {str(e)}"
        import traceback
        traceback.print_exc()
    
    return result
