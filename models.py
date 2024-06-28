from pydantic import BaseModel, Field
from typing import Set, List

class Context(BaseModel):
    skills: Set[str] = Field(default_factory=set)
    employment_type: List[str] = Field(default_factory=lambda: ["full", "part"])
    budget: int = 9999999


class ChatRequest(BaseModel):
    prompt: str
    context:Context = Field(default_factory=Context)

