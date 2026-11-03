from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.graph import Graph, StrictModel
from app.schemas.time import UtcDatetime


class DocumentInput(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=100_000)
    source_type: Literal["text", "markdown"] = "markdown"

    @field_validator("title", "content")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class SegmentOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    ordinal: int
    text: str
    start_offset: int
    end_offset: int
    page_number: int | None = None


class DocumentOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    content: str
    content_hash: str
    source_type: str
    created_at: UtcDatetime
    segments: list[SegmentOutput]
    original_file_hash: str | None = None
    page_count: int | None = None
    empty_pages: list[int] = Field(default_factory=list)


class PlaybookInput(StrictModel):
    document_id: str
    title: str = Field(min_length=1, max_length=200)
    graph: Graph


class PlaybookOutput(BaseModel):
    id: str
    document_id: str
    title: str
    version: int
    status: Literal["draft", "approved"]
    graph: Graph
    parent_version_id: str | None
    graph_hash: str


class DemoEntry(BaseModel):
    id: str
    title: str
    description: str
    document_id: str
    playbook_id: str
    scenario_id: str
    fictional: bool = True
    scenario_status: Literal["ready"] = "ready"


class DemoWorkspace(BaseModel):
    mode: Literal["temporary"] = "temporary"
    expires_at: int
    notice: str = "Temporary demo workspace. Use fictional procedures and export reports before it expires. Clearing cookies loses access."


class DemoCatalog(BaseModel):
    demos: list[DemoEntry]
    workspace: DemoWorkspace | None = None


class ResetInput(StrictModel):
    pass


class Health(BaseModel):
    status: Literal["ok"] = "ok"
    milestone: int = 6
