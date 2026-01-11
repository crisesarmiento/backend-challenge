"""
Pydantic models for the Task Management API.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from datetime import datetime


class TaskCreate(BaseModel):
    """Model for creating a new task."""

    title: str = Field(..., min_length=1, max_length=200, description="Task title")
    description: str = Field(..., min_length=1, max_length=2000, description="Task description")
    priority: Literal["low", "medium", "high"] = Field(..., description="Task priority level")
    due_date: Optional[str] = Field(None, description="ISO 8601 timestamp for task due date")

    @field_validator("title", "description")
    @classmethod
    def sanitize_string(cls, v: str) -> str:
        """Sanitize input strings by stripping whitespace."""
        if v:
            return v.strip()
        return v

    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, v: Optional[str]) -> Optional[str]:
        """Validate that due_date is a valid ISO 8601 timestamp."""
        if v is not None:
            try:
                # Parse to validate ISO 8601 format
                datetime.fromisoformat(v.replace("Z", "+00:00"))
            except (ValueError, AttributeError) as e:
                raise ValueError(f"Invalid ISO 8601 timestamp format: {e}") from e
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "title": "Complete project documentation",
                    "description": "Write comprehensive documentation for the API",
                    "priority": "high",
                    "due_date": "2026-01-15T18:00:00Z",
                }
            ]
        }
    }


class TaskResponse(BaseModel):
    """Model for task creation response."""

    task_id: str = Field(..., description="Unique task identifier")
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Task description")
    priority: Literal["low", "medium", "high"] = Field(..., description="Task priority level")
    due_date: Optional[str] = Field(None, description="ISO 8601 timestamp for task due date")
    created_at: str = Field(..., description="ISO 8601 timestamp when task was created")
    status: str = Field(default="queued", description="Current task status")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "task_id": "550e8400-e29b-41d4-a716-446655440000",
                    "title": "Complete project documentation",
                    "description": "Write comprehensive documentation for the API",
                    "priority": "high",
                    "due_date": "2026-01-15T18:00:00Z",
                    "created_at": "2026-01-10T12:00:00Z",
                    "status": "queued",
                }
            ]
        }
    }


class HealthResponse(BaseModel):
    """Model for health check response."""

    status: str = Field(..., description="Health status")
    timestamp: str = Field(..., description="Current timestamp")
