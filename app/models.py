from datetime import datetime
from sqlalchemy import (
    String, Float, Integer, DateTime, ForeignKey, func, UniqueConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db import Base


class Experiment(Base):
    __tablename__ = "experiments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    # entity_type — свободная строка ("user", "sku", "region"): платформа
    # не знает домена подключённого продукта и не должна его знать.
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    stopped_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    variants: Mapped[list["Variant"]] = relationship(back_populates="experiment")


class Variant(Base):
    __tablename__ = "variants"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    allocation_pct: Mapped[float] = mapped_column(Float, nullable=False)
    experiment: Mapped["Experiment"] = relationship(back_populates="variants")

    __table_args__ = (
        UniqueConstraint("experiment_id", "name", name="uq_variant_experiment_name"),
    )


class Assignment(Base):
    __tablename__ = "assignments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id"))
    entity_id: Mapped[str] = mapped_column(String, nullable=False)
    variant_id: Mapped[int] = mapped_column(ForeignKey("variants.id"))
    assigned_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Без этого ограничения параллельные запросы assignment для одной сущности
    # создают дубли, которые ломают SRM-проверку (одна сущность считается дважды).
    __table_args__ = (
        UniqueConstraint("experiment_id", "entity_id", name="uq_assignment_entity"),
    )


class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id"))
    entity_id: Mapped[str] = mapped_column(String, nullable=False)
    metric_name: Mapped[str] = mapped_column(String, nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    pre_period_value: Mapped[float] = mapped_column(Float, nullable=True)
    # Ключ идемпотентности: клиент передаёт его при retry, чтобы сетевой
    # повтор не задвоил метрику. NULL допускается — Postgres не считает
    # NULL-значения равными, поэтому события без ключа не конфликтуют.
    event_key: Mapped[str] = mapped_column(String, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("experiment_id", "event_key", name="uq_event_key"),
        Index("ix_events_lookup", "experiment_id", "metric_name", "entity_id"),
    )


class Result(Base):
    __tablename__ = "results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id"))
    computed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    metric_name: Mapped[str] = mapped_column(String, nullable=True)
    method: Mapped[str] = mapped_column(String, nullable=False)
    n_control: Mapped[int] = mapped_column(Integer, nullable=True)
    n_treatment: Mapped[int] = mapped_column(Integer, nullable=True)
    p_value: Mapped[float] = mapped_column(Float, nullable=True)
    ci_lower: Mapped[float] = mapped_column(Float, nullable=True)
    ci_upper: Mapped[float] = mapped_column(Float, nullable=True)
    effect_size: Mapped[float] = mapped_column(Float, nullable=True)
