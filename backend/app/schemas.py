from pydantic import BaseModel
from datetime import datetime
from typing import Literal


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


class Conversation(BaseModel):
    id: int
    report_id: int
    created_at: datetime


class CreateReportRequest(BaseModel):
    title: str = "New Report"


class CreateMessageRequest(BaseModel):
    content: str


class TeachAgentRequest(BaseModel):
    content: str


class TeachAgentResponse(BaseModel):
    message: str
    skill_filename: str
    skill_path: str


class SkillSummary(BaseModel):
    skill_id: str
    name: str
    description: str
    skill_md_path: str


class Skill(BaseModel):
    id: int
    name: str
    description: str
    slug: str
    skill_md_path: str
    created_at: datetime
    updated_at: datetime


class CreateSkillRequest(BaseModel):
    name: str


class SkillConversation(BaseModel):
    id: int
    skill_id: int
    created_at: datetime


class SkillMessage(BaseModel):
    id: int
    skill_id: int
    skill_conversation_id: int
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class PublishSkillRequest(BaseModel):
    skill_conversation_id: int | None = None
