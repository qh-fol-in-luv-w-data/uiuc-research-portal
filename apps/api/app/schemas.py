from __future__ import annotations

from datetime import date, datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel

T = TypeVar("T")
StatsKey = Literal["monthly", "types", "fields", "rising_topics", "top_venues", "top_partners", "top_faculty"]


class ErrorBody(BaseModel):
    error: str
    detail: str


class Health(BaseModel):
    db: bool
    ollama: bool
    models: list[str]
    missing_models: list[str]


class Institution(BaseModel):
    name: str
    founded: int | None = None
    city: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    homepage: str | None = None
    description: str | None = None
    images: list[dict] = []


class Overview(BaseModel):
    works: int
    citations: int
    oa_share: float
    faculty: int
    faculty_linked: int
    partner_institutions: int
    outliers: int
    duplicates: int = 0
    computed_at: datetime | None = None
    institution: Institution | None = None


class StatsPayload(BaseModel):
    key: StatsKey
    computed_at: datetime
    data: list[dict]


class AuthorRef(BaseModel):
    name: str
    faculty_id: int | None = None


class WorkCard(BaseModel):
    id: str
    title: str
    publication_date: date | None
    type: str | None
    venue: str | None
    cited_by_count: int
    is_oa: bool
    doi: str | None
    field: str | None
    uiuc_authors: list[AuthorRef] = []


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class FacultyCard(BaseModel):
    id: int
    name: str
    position: str | None
    photo_url: str | None
    primary_field: str | None
    keywords: list[str]
    matched_keywords: list[str] = []
    link_confidence: float | None = None


class TopicCount(BaseModel):
    name: str
    count: int


class FacultyProfile(FacultyCard):
    link_method: str | None = None
    openalex_author_ids: list[str] = []
    recent_works: list[WorkCard] = []
    topics: list[TopicCount] = []
