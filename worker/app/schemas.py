from pydantic import BaseModel
from pydantic import model_validator
from typing import Literal


class InvokeRequest(BaseModel):
    query: str
    task_type: Literal["report", "skill"] = "report"
    report_id: int | None = None
    session_id: str | None = None
    workspace_path: str | None = None

    @model_validator(mode="after")
    def validate_target(self):
        if self.report_id is None and not self.session_id and not self.workspace_path:
            raise ValueError("One of report_id, session_id, or workspace_path must be provided")
        return self
