from pydantic import BaseModel, Field


class AnalyzeResponse(BaseModel):
    analysis_id: str
    status: str
    observed_presence: int
    expected_attendance: int | None = None
    variance: int | None = None
    evidence_peak_frame: str
    report: dict = Field(description="Full analysis document produced by the vision pipeline.")
