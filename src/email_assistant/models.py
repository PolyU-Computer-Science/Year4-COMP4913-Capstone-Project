from pydantic import BaseModel, Field


class EmailClassification(BaseModel):
    intent: str = Field(
        description="Detected category: urgent, meeting, inquiry, notification, or spam"
    )
    urgency_score: int = Field(description="Urgency scale from 1 to 10")
    summary: str = Field(description="One-sentence summary of the email content")
    requires_reply: bool = Field(description="Whether a reply draft is needed")
