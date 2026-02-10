"""
Report Schema — S1 Schema-Driven Document Intelligence
Pydantic models that define the strict contract for report generation.
The LLM outputs these schemas; the Builder renders them into documents.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class ReportSection(BaseModel):
    """A single section in the report (heading + content paragraph)."""
    heading: str = Field(description="Section heading text")
    content: str = Field(description="Section body text / analysis")


class TableConfig(BaseModel):
    """Configuration for the data table in the report."""
    include: bool = Field(default=True, description="Whether to include a data table")
    caption: str = Field(default="Data Table", description="Caption above the table")


class ReportSchema(BaseModel):
    """
    The master schema for a generated report.
    The LLM fills this with content; the Builder renders it into a Word document.
    """
    title: str = Field(description="Report title")
    summary: str = Field(description="Executive summary paragraph")
    sections: List[ReportSection] = Field(
        default_factory=list,
        description="List of analysis sections"
    )
    table_config: TableConfig = Field(
        default_factory=TableConfig,
        description="Data table configuration"
    )
    filtered_row_count: int = Field(
        default=0,
        description="Number of rows in the filtered dataset"
    )
    filter_description: Optional[str] = Field(
        default=None,
        description="Human-readable description of the filter applied (e.g., 'Salary > 50000')"
    )
    pandas_filter_expression: Optional[str] = Field(
        default=None,
        description="The pandas filter expression to apply to the DataFrame (e.g., \"df[df['Salary'] > 50000]\")"
    )
