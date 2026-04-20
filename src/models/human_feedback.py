from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.models.base import TimestampMixin

if TYPE_CHECKING:
    from src.models.decision_log import DecisionLog


class ShouldHaveBeen(str, enum.Enum):
    alerted = "alerted"
    dismissed = "dismissed"
    escalated = "escalated"


class HumanFeedback(Base, TimestampMixin):
    """
    Feedback a posteriori de un operador sobre una decisión del pipeline.
    Los campos de lógica de negocio serán añadidos por claude/2.
    """

    __tablename__ = "human_feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    decision_log_id: Mapped[int] = mapped_column(
        ForeignKey("decision_log.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Estructura mínima — claude/2 añade los campos de lógica ──────────────
    should_have_been: Mapped[str | None] = mapped_column(String(30))

    decision_log: Mapped[DecisionLog] = relationship(
        "DecisionLog", back_populates="human_feedbacks"
    )
