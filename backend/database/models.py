"""
SQLAlchemy 2.0 ORM models for MachineSearch.

Tables
------
machines        — scraped machine listings
site_configs    — per-site scraping configuration
scrape_jobs     — history of every scrape run
click_events    — machine detail-page click tracking
search_events   — search query analytics
admin_users     — back-office admin accounts
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# machines
# ---------------------------------------------------------------------------
class Machine(Base):
    __tablename__ = "machines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(200), nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    location: Mapped[str | None] = mapped_column(String(300), nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    specs: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    site_name: Mapped[str] = mapped_column(String(100), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    click_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # Relationships
    click_events: Mapped[list["ClickEvent"]] = relationship(
        "ClickEvent", back_populates="machine", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_machines_site_name", "site_name"),
        Index("idx_machines_created_at", "created_at"),
        # NOTE: GIN FTS index and composite price/location/site index are
        # created via raw DDL in db.init_db() because SQLAlchemy ORM does not
        # natively express GIN to_tsvector() functional indexes.
    )

    def __repr__(self) -> str:
        return (
            f"<Machine id={self.id} name={self.name!r} "
            f"site={self.site_name!r} price={self.price}>"
        )


# ---------------------------------------------------------------------------
# site_configs
# ---------------------------------------------------------------------------
class SiteConfig(Base):
    __tablename__ = "site_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    config_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_scraped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_scraped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    def __repr__(self) -> str:
        return (
            f"<SiteConfig id={self.id} name={self.name!r} "
            f"active={self.is_active}>"
        )


# ---------------------------------------------------------------------------
# scrape_jobs
# ---------------------------------------------------------------------------
class ScrapeJob(Base):
    __tablename__ = "scrape_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    site_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending | running | completed | failed
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    pages_scraped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_new: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    __table_args__ = (
        Index("idx_scrape_jobs_status", "status"),
        Index("idx_scrape_jobs_site_name", "site_name"),
    )

    def __repr__(self) -> str:
        return (
            f"<ScrapeJob id={self.id} site={self.site_name!r} "
            f"status={self.status!r} items_new={self.items_new}>"
        )


# ---------------------------------------------------------------------------
# click_events
# ---------------------------------------------------------------------------
class ClickEvent(Base):
    __tablename__ = "click_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    machine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("machines.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_ip: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    clicked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    machine: Mapped["Machine"] = relationship("Machine", back_populates="click_events")

    def __repr__(self) -> str:
        return (
            f"<ClickEvent id={self.id} machine_id={self.machine_id} "
            f"ip={self.user_ip!r} at={self.clicked_at}>"
        )


# ---------------------------------------------------------------------------
# search_events
# ---------------------------------------------------------------------------
class SearchEvent(Base):
    __tablename__ = "search_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    query: Mapped[str | None] = mapped_column(String(500), nullable=True)
    filters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    results_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    user_ip: Mapped[str | None] = mapped_column(String(50), nullable=True)
    searched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    def __repr__(self) -> str:
        return (
            f"<SearchEvent id={self.id} query={self.query!r} "
            f"results={self.results_count} at={self.searched_at}>"
        )


# ---------------------------------------------------------------------------
# admin_users
# ---------------------------------------------------------------------------
class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    def __repr__(self) -> str:
        return f"<AdminUser id={self.id} email={self.email!r} active={self.is_active}>"
