"""Global Qt Fusion + QSS theme for a cohesive, premium-feeling desktop shell."""

from __future__ import annotations

import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

# Dark shell: cool slate + teal accent (readable, non-gamery)
STYLESHEET = """
 QWidget {
   background-color: #0e1318;
   color: #e8edf3;
   font-size: 13px;
   selection-background-color: #1e4d45;
   selection-color: #f0fffc;
 }

 QMainWindow::separator {
   background: #1a222c;
   width: 1px;
 }

 QMenuBar {
   background-color: #0e1318;
   color: #c8d0da;
   padding: 2px 8px;
   border-bottom: 1px solid #1f2a36;
 }
 QMenuBar::item:selected {
   background: #1a2630;
   border-radius: 4px;
 }
 QMenu {
   background-color: #141c24;
   border: 1px solid #2a3644;
   padding: 6px;
 }
 QMenu::item { padding: 8px 28px; border-radius: 6px; }
 QMenu::item:selected { background: #1e3d38; }

 QStatusBar {
   background: #0c1014;
   color: #8b98a8;
   border-top: 1px solid #1f2a36;
   padding: 4px 8px;
 }

 QFrame#Sidebar {
   background-color: #0a0e12;
   border: none;
 }
 QFrame#SidebarDivider {
   background-color: #1a222c;
   max-width: 1px;
   min-width: 1px;
 }
 QFrame#ContentShell {
   background-color: #121920;
   border: none;
   border-radius: 0px;
 }

 QLabel#BrandTitle {
   font-size: 18px;
   font-weight: 600;
   letter-spacing: -0.02em;
   color: #f2f6fa;
   padding: 4px 2px 2px 2px;
 }
 QLabel#BrandTagline {
   font-size: 12px;
   color: #7d8b99;
   padding: 0 2px 14px 2px;
 }

 QListWidget#SideNav {
   background: transparent;
   border: none;
   outline: none;
   padding: 4px;
 }
 QListWidget#SideNav::item {
   color: #aab6c2;
   padding: 11px 14px;
   margin: 3px 6px;
   border-radius: 9px;
 }
 QListWidget#SideNav::item:hover {
   background: #141c24;
   color: #e8edf3;
 }
 QListWidget#SideNav::item:selected {
   background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
     stop:0 #15332f, stop:1 #1a2e30);
   color: #d8fff8;
   border: 1px solid #2a6b62;
 }

 QLabel#PageTitle {
   font-size: 20px;
   font-weight: 600;
   letter-spacing: -0.03em;
   color: #f0f4f8;
   padding: 0 0 4px 0;
 }
 QLabel#PageSubtitle {
   font-size: 12px;
   color: #8896a6;
   padding: 0 0 16px 0;
 }

 QScrollBar:vertical {
   background: #0e1318;
   width: 10px;
   margin: 0px;
   border-radius: 5px;
 }
 QScrollBar::handle:vertical {
   background: #323d4a;
   min-height: 36px;
   border-radius: 5px;
 }
 QScrollBar::handle:vertical:hover { background: #3d4c5c; }
 QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
   height: 0;
 }

 QGroupBox {
   font-weight: 600;
   border: 1px solid #273240;
   border-radius: 11px;
   margin-top: 18px;
   padding: 16px 14px 14px 14px;
   background: #141b22;
 }
 QGroupBox::title {
   subcontrol-origin: margin;
   left: 14px;
   padding: 0 8px;
   color: #9aa8b6;
 }

 QLineEdit, QPlainTextEdit, QSpinBox, QComboBox {
   background: #0d1217;
   border: 1px solid #2d3a48;
   border-radius: 8px;
   padding: 8px 11px;
   min-height: 20px;
 }
 QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {
   border: 1px solid #3d8b82;
   outline: 2px solid rgba(61, 139, 130, 0.45);
   outline-offset: 1px;
 }

 QPushButton:focus {
   border: 1px solid #4a9e94;
   outline: 2px solid rgba(61, 172, 154, 0.45);
   outline-offset: 1px;
 }

 QListWidget#SideNav:focus {
   outline: 2px solid rgba(61, 172, 154, 0.45);
   outline-offset: 2px;
 }

 QTableWidget:focus {
   outline: 2px solid rgba(61, 172, 154, 0.45);
   outline-offset: 0px;
 }
 QComboBox::drop-down {
   border: none;
   width: 26px;
 }

 QPushButton {
   background: #1e2a34;
   border: 1px solid #334155;
   border-radius: 9px;
   padding: 9px 18px;
   min-height: 20px;
 }
 QPushButton:hover {
   background: #243240;
   border-color: #455a6f;
 }
 QPushButton:pressed { background: #182028; }
 QPushButton:disabled {
   color: #5c6670;
   border-color: #242d36;
   background: #151a1f;
 }

 QPushButton#PrimaryButton {
   background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
     stop:0 #1f7a72, stop:1 #1a9b8a);
   border: 1px solid #2bbd9f;
   color: #f4fffd;
   font-weight: 600;
 }
 QPushButton#PrimaryButton:hover {
   background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
     stop:0 #258a80, stop:1 #20a896);
 }
 QPushButton#PrimaryButton:pressed {
   background: #186b64;
 }

 QTableWidget {
   background: #0f1419;
   alternate-background-color: #121a21;
   gridline-color: #222d3a;
   border: 1px solid #273240;
   border-radius: 10px;
 }
 QTableWidget::item:selected {
   background: #1e3d38;
 }
 QHeaderView::section {
   background: #151d25;
   color: #9aa8b6;
   padding: 10px 8px;
   border: none;
   border-bottom: 1px solid #273240;
   font-weight: 600;
 }

 QCheckBox { spacing: 8px; color: #cdd6df; }
 QCheckBox::indicator {
   width: 18px;
   height: 18px;
   border-radius: 5px;
   border: 1px solid #455a6f;
   background: #0d1217;
 }
 QCheckBox::indicator:checked {
   background: #1a9b8a;
   border-color: #2fc4b0;
 }

 QTextEdit {
   background: #0d1217;
   border: 1px solid #2d3a48;
   border-radius: 9px;
 }

 QDialog {
   background: #121920;
 }

 QMessageBox {
   background: #121920;
 }
 QMessageBox QLabel {
   color: #e8edf3;
 }

 QTabWidget::pane {
   border: 1px solid #273240;
   border-radius: 10px;
   background: #141b22;
 }
 QTabBar::tab {
   background: #151d25;
   color: #8b98a8;
   padding: 9px 16px;
   margin-right: 4px;
   border-top-left-radius: 8px;
   border-top-right-radius: 8px;
   border: 1px solid #273240;
   border-bottom: none;
 }
 QTabBar::tab:selected {
   background: #1a2632;
   color: #e8edf3;
   border-bottom-color: #1a2632;
 }
"""


def configure_application_font(app: QApplication) -> None:
    f = QFont(app.font())
    if sys.platform == "darwin":
        f.setFamily(".AppleSystemUIFont")
    elif sys.platform.startswith("win"):
        f.setFamily("Segoe UI")
    sz = float(f.pointSizeF() or f.pointSize() or 11)
    if sz < 11.0:
        sz = 11.0
    f.setPointSizeF(min(13.25, sz * 1.04))
    app.setFont(f)


def apply_application_theme(app: QApplication, *, stylesheet: str = STYLESHEET) -> None:
    """Apply Fusion style + theme QSS."""
    try:
        app.setStyle("Fusion")
    except Exception:
        pass
    configure_application_font(app)
    app.setStyleSheet(stylesheet)
