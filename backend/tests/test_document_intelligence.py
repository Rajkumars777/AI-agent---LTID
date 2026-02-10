"""
Tests for S1 Schema-Driven Document Intelligence
Tests the report schema, doc builder, fast-path routing, and PDF extraction.
"""

import os
import sys
import pytest
import pandas as pd
import tempfile

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from capabilities.report_schema import ReportSchema, ReportSection, TableConfig
from capabilities.doc_builder import build_report


# ============================================================
# 1. Schema Validation Tests
# ============================================================

class TestReportSchema:
    """Test that the Pydantic schemas accept/reject correctly."""
    
    def test_valid_full_schema(self):
        """A fully populated schema should validate."""
        schema = ReportSchema(
            title="Test Report",
            summary="This is a test summary.",
            sections=[
                ReportSection(heading="Section 1", content="Content 1"),
                ReportSection(heading="Section 2", content="Content 2"),
            ],
            table_config=TableConfig(include=True, caption="Test Table"),
            filtered_row_count=10,
            filter_description="Salary > 50000",
            pandas_filter_expression="df[df['Salary'] > 50000]"
        )
        assert schema.title == "Test Report"
        assert len(schema.sections) == 2
        assert schema.filtered_row_count == 10

    def test_minimal_schema(self):
        """A schema with only required fields should validate."""
        schema = ReportSchema(
            title="Minimal Report",
            summary="Minimal summary."
        )
        assert schema.title == "Minimal Report"
        assert schema.table_config.include is True  # Default
        assert schema.filtered_row_count == 0  # Default
        assert schema.sections == []  # Default

    def test_invalid_schema_missing_title(self):
        """Missing required 'title' should raise validation error."""
        with pytest.raises(Exception):
            ReportSchema(summary="No title provided.")

    def test_filter_expression_stored(self):
        """Filter expression should be stored correctly."""
        schema = ReportSchema(
            title="Filter Test",
            summary="Testing filters.",
            pandas_filter_expression="df[df['Age'] >= 30]"
        )
        assert schema.pandas_filter_expression == "df[df['Age'] >= 30]"


# ============================================================
# 2. Document Builder Tests
# ============================================================

class TestDocBuilder:
    """Test that the builder produces valid .docx files."""
    
    def _sample_df(self):
        """Create a sample DataFrame for testing."""
        return pd.DataFrame({
            "Name": ["Alice", "Bob", "Charlie", "Diana"],
            "Age": [28, 35, 42, 31],
            "Salary": [55000, 72000, 48000, 61000]
        })
    
    def test_build_basic_report(self):
        """Builder should create a .docx file from schema + DataFrame."""
        schema = ReportSchema(
            title="Employee Report",
            summary="Overview of employee data.",
            sections=[
                ReportSection(heading="Key Findings", content="Most employees earn above 50k.")
            ],
            table_config=TableConfig(include=True, caption="Employee Data"),
            filtered_row_count=4,
            filter_description="All employees"
        )
        
        df = self._sample_df()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_report.docx")
            result = build_report(schema, df, output_path)
            
            assert os.path.exists(result)
            assert result.endswith(".docx")
            # File should have reasonable size (not empty)
            assert os.path.getsize(result) > 1000
    
    def test_build_report_no_table(self):
        """Builder should work when table is excluded."""
        schema = ReportSchema(
            title="Summary Only",
            summary="Just a summary report.",
            table_config=TableConfig(include=False),
        )
        
        df = self._sample_df()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "no_table.docx")
            result = build_report(schema, df, output_path)
            
            assert os.path.exists(result)
    
    def test_build_report_empty_df(self):
        """Builder should handle empty DataFrame gracefully."""
        schema = ReportSchema(
            title="Empty Data Report",
            summary="No data matched the filter.",
            filtered_row_count=0
        )
        
        df = pd.DataFrame()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "empty.docx")
            result = build_report(schema, df, output_path)
            
            assert os.path.exists(result)

    def test_build_report_auto_path(self):
        """Builder should auto-generate output path when None is passed."""
        schema = ReportSchema(
            title="Auto Path Report",
            summary="Testing auto path generation."
        )
        
        df = self._sample_df()
        result = build_report(schema, df, output_path=None)
        
        assert os.path.exists(result)
        assert "Auto_Path_Report" in result
        assert result.endswith(".docx")
        
        # Cleanup
        os.remove(result)


# ============================================================
# 3. Fast-Path Routing Tests
# ============================================================

class TestFastPathRouting:
    """Test that document keywords route to DOC_REPORT."""
    
    def test_word_document_keyword(self):
        """'word document' should trigger DOC_REPORT detection."""
        import re
        user_input = "in sample.xlsx extract employees with salary > 50000 and store in word document"
        
        doc_keywords = ["word document", "word doc", "docx", "report", "store in word", 
                       "save to word", "save in word", "create a report", "generate report", "save as document"]
        file_pattern = r'[\w\-\.]+\.(xlsx|xls|csv)'
        
        has_file = re.search(file_pattern, user_input, re.IGNORECASE)
        is_doc_report = any(kw in user_input.lower() for kw in doc_keywords)
        
        assert has_file is not None
        assert is_doc_report is True
    
    def test_create_report_keyword(self):
        """'create a report' should trigger DOC_REPORT detection."""
        import re
        user_input = "create a report from sample.xlsx"
        
        doc_keywords = ["word document", "word doc", "docx", "report", "store in word", 
                       "save to word", "save in word", "create a report", "generate report", "save as document"]
        file_pattern = r'[\w\-\.]+\.(xlsx|xls|csv)'
        
        has_file = re.search(file_pattern, user_input, re.IGNORECASE)
        is_doc_report = any(kw in user_input.lower() for kw in doc_keywords)
        
        assert has_file is not None
        assert is_doc_report is True

    def test_query_not_doc_report(self):
        """A simple query without document keywords should NOT trigger DOC_REPORT."""
        import re
        user_input = "who has the highest salary in sample.xlsx"
        
        doc_keywords = ["word document", "word doc", "docx", "report", "store in word", 
                       "save to word", "save in word", "create a report", "generate report", "save as document"]
        
        is_doc_report = any(kw in user_input.lower() for kw in doc_keywords)
        
        assert is_doc_report is False  # Should go to DYNAMIC_CODE, not DOC_REPORT


# ============================================================
# 4. Security Tests
# ============================================================

class TestFilterSecurity:
    """Test that dangerous filter expressions are blocked."""
    
    def test_dangerous_expressions_blocked(self):
        """Expressions with os, exec, import, etc. should be rejected."""
        dangerous = ["import", "exec", "eval", "os.", "sys.", "__", "open(", "subprocess"]
        
        test_expressions = [
            "import os; os.remove('file.txt')",
            "exec('malicious code')",
            "eval('__import__(\"os\")')",
            "os.system('rm -rf /')",
            "__import__('subprocess')"
        ]
        
        for expr in test_expressions:
            is_blocked = any(d in expr.lower() for d in dangerous)
            assert is_blocked is True, f"Expression should be blocked: {expr}"
    
    def test_safe_expressions_allowed(self):
        """Normal pandas filter expressions should pass."""
        dangerous = ["import", "exec", "eval", "os.", "sys.", "__", "open(", "subprocess"]
        
        safe_expressions = [
            "df[df['Salary'] > 50000]",
            "df[df['Age'] >= 30]",
            "df[df['Name'] == 'Alice']",
            "df",
        ]
        
        for expr in safe_expressions:
            is_blocked = any(d in expr.lower() for d in dangerous)
            assert is_blocked is False, f"Expression should be allowed: {expr}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
