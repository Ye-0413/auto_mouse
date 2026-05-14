"""Accessibility helpers (best-effort; behavior varies by platform / AT)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget


def announce_status(widget: QWidget | None, message: str, *, polite: bool = True) -> None:
    """Post a live-region style announcement when the Qt build supports it."""
    if widget is None:
        return
    text = message.strip()
    if not text:
        return
    try:
        from PySide6.QtGui import QAccessible, QAccessibleAnnouncementEvent

        ev = QAccessibleAnnouncementEvent(widget, text)
        ev.setPoliteness(
            QAccessible.AnnouncementPoliteness.Polite
            if polite
            else QAccessible.AnnouncementPoliteness.Assertive,
        )
        QAccessible.updateAccessibility(ev)
    except Exception:
        return
