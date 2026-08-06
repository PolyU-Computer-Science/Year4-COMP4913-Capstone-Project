from pydantic import BaseModel, Field


class EmailClassification(BaseModel):
    category: str = Field(
        description="question, incident, problem, task, or spam"
    )
    topic: str = Field(
        description="What the email is about, e.g. refund, bug_report, password_reset"
    )
    priority: str = Field(description="low, normal, high, or urgent")
    urgency_score: int = Field(description="Urgency scale from 1 to 10")
    summary: str = Field(description="One-sentence summary of the email content")
    requires_reply: bool = Field(description="Whether a reply draft is needed")
    custom: dict = Field(
        default_factory=dict,
        description="Per-mailbox custom field values",
    )
