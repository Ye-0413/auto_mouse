from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PlaceholderPage(QWidget):
    """Skeleton page until feature UI lands."""

    def __init__(self, title: str, hint: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        title_lbl = QLabel(f"<h2>{title}</h2>")
        hint_lbl = QLabel(hint)
        hint_lbl.setWordWrap(True)
        layout.addWidget(title_lbl)
        layout.addWidget(hint_lbl)
        layout.addStretch(1)
