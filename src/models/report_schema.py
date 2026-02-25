from pydantic import BaseModel, Field
from typing import List, Optional

class ReportSection(BaseModel):
    heading: str = Field(description="The heading of this section")
    content: str = Field(description="The content of this section")

class TableConfig(BaseModel):
    include: bool = Field(True, description="Whether to include the data table")
    caption: str = Field("Data Table", description="Caption for the data table")

class ReportSchema(BaseModel):
    title: str = Field(description="Title of the report")
    summary: str = Field(description="Executive summary of the report")
    sections: List[ReportSection] = Field(description="List of report sections")
    table_config: TableConfig = Field(default_factory=TableConfig, description="Configuration for the data table")
    filtered_row_count: int = Field(0, description="Number of rows after filtering")
    filter_description: str = Field("All data", description="Description of the applied filter")
    pandas_filter_expression: str = Field("df", description="Pandas expression to filter the dataframe, e.g. df[df['Age'] > 30]")
