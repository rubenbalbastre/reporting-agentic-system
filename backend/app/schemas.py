from pydantic import BaseModel
from datetime import datetime
from typing import Any, List, Literal, Optional


class Report(BaseModel):
    id: int
    title: str
    created_at: datetime


class Message(BaseModel):
    id: int
    report_id: int
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class CreateReportRequest(BaseModel):
    title: str = "New Report"


class CreateMessageRequest(BaseModel):
    content: str
