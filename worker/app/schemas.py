from pydantic import BaseModel


class InvokeRequest(BaseModel):
    query: str
    report_id: int