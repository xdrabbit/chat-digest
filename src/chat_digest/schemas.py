from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

Role = Literal["user", "assistant", "system", "unknown"]


class Message(BaseModel):
    order: int
    role: Role
    content: str
    tags: List[str] = Field(default_factory=list)
    timestamp: Optional[str] = None
    importance_score: float = 5.0  # 0-10 scale, default neutral


class ThreadMetadata(BaseModel):
    id: str
    title: Optional[str] = None
    source_file: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    schema_version: int = 1


class Summary(BaseModel):
    brief: str
    decisions: List[str] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    code_summary: Optional[dict] = None  # Summary of code blocks


class ThreadDigest(BaseModel):
    thread: ThreadMetadata
    messages: List[Message]
    summary: Summary
