from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db import Base

class Experiment(Base):
    __tablename__ = "experiments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    variants: Mapped[list["Variant"]] = relationship(back_populates="experiment")

class Variant(Base):
    __tablename__ = "variants"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    allocation_pct: Mapped[float] = mapped_column(Float, nullable=False)
    experiment: Mapped["Experiment"] = relationship(back_populates="variants")

class Assignment(Base):
    __tablename__ = "assignments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id"))
    entity_id: Mapped[str] = mapped_column(String, nullable=False)
    variant_id: Mapped[int] = mapped_column(ForeignKey("variants.id"))
    assigned_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id"))
    entity_id: Mapped[str] = mapped_column(String, nullable=False)
    metric_name: Mapped[str] = mapped_column(String, nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    pre_period_value: Mapped[float] = mapped_column(Float, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class Result(Base):
    __tablename__ = "results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id"))
    computed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    method: Mapped[str] = mapped_column(String, nullable=False)
    p_value: Mapped[float] = mapped_column(Float, nullable=True)
    ci_lower: Mapped[float] = mapped_column(Float, nullable=True)
    ci_upper: Mapped[float] = mapped_column(Float, nullable=True)
    effect_size: Mapped[float] = mapped_column(Float, nullable=True)
