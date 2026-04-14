"""
Cardiovascular Risk Assessment — ACC/AHA Pooled Cohort Equations (2013)
Goff DC Jr, et al. Circulation. 2014;129(25 Suppl 2):S49-73.

Equations validated for:
  • White women            • African American women
  • White men              • African American men
Other race/sex groups: guideline recommends applying White equations
as the best available approximation.
"""

import sys
import math
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QComboBox, QCheckBox,
    QPushButton, QFrame, QScrollArea, QMessageBox, QSizePolicy,
)
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import (
    QFont, QIntValidator, QDoubleValidator,
    QPainter, QColor, QPen, QTextDocument,
)
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog


# ── Module-level patient store ────────────────────────────────────────────────
patient_data: dict = {}


# ═════════════════════════════════════════════════════════════════════════════
# ACC/AHA Pooled Cohort Equations  (Table A, Goff 2014)
# ═════════════════════════════════════════════════════════════════════════════

_COEFFICIENTS = {
    ("White", "Female"): {
        "ln_age":            -29.799,
        "ln_age2":             4.884,
        "ln_total_chol":      13.540,
        "ln_age_total_chol":  -3.114,
        "ln_hdl":            -13.578,
        "ln_age_hdl":          3.149,
        "ln_sbp_treated":      2.019,
        "ln_sbp_untreated":    1.957,
        "smoker":              7.574,
        "ln_age_smoker":      -1.665,
        "diabetes":            0.661,
        "baseline_survival":   0.9665,
        "mean_val":          -29.18,
    },
    ("African American", "Female"): {
        "ln_age":             17.1141,
        "ln_age2":             0.0,
        "ln_total_chol":       0.9396,
        "ln_age_total_chol":   0.0,
        "ln_hdl":            -18.9196,
        "ln_age_hdl":          4.4748,
        "ln_sbp_treated":     29.2907,
        "ln_sbp_untreated":   27.8197,
        "smoker":              0.8738,
        "ln_age_smoker":       0.0,
        "diabetes":            0.8738,
        "baseline_survival":   0.9533,
        "mean_val":           86.6081,
    },
    ("White", "Male"): {
        "ln_age":             12.344,
        "ln_age2":             0.0,
        "ln_total_chol":      11.853,
        "ln_age_total_chol":  -2.664,
        "ln_hdl":             -7.990,
        "ln_age_hdl":          1.769,
        "ln_sbp_treated":      1.797,
        "ln_sbp_untreated":    1.764,
        "smoker":              7.837,
        "ln_age_smoker":      -1.795,
        "diabetes":            0.658,
        "baseline_survival":   0.9144,
        "mean_val":           61.18,
    },
    ("African American", "Male"): {
        "ln_age":              2.469,
        "ln_age2":             0.0,
        "ln_total_chol":       0.302,
        "ln_age_total_chol":   0.0,
        "ln_hdl":             -0.307,
        "ln_age_hdl":          0.0,
        "ln_sbp_treated":      1.916,
        "ln_sbp_untreated":    1.809,
        "smoker":              0.549,
        "ln_age_smoker":       0.0,
        "diabetes":            0.645,
        "baseline_survival":   0.8954,
        "mean_val":           19.54,
    },
}


def _race_key(race: str) -> str:
    if race == "African American":
        return "African American"
    return "White"


def pooled_cohort_risk(age, sex, race, total_chol, hdl_chol,
                       sbp, treated_htn, smoker, diabetes) -> float | None:
    """Return 10-year ASCVD risk as a percentage, or None if outside 40-79."""
    if not (40 <= age <= 79):
        return None

    rk = (_race_key(race), sex)
    if rk not in _COEFFICIENTS:
        rk = ("White", sex)

    c   = _COEFFICIENTS[rk]
    la  = math.log(age)
    ltc = math.log(total_chol)
    lhd = math.log(hdl_chol)
    lsp = math.log(sbp)

    score = (
        c["ln_age"]            * la
      + c["ln_age2"]           * la ** 2
      + c["ln_total_chol"]     * ltc
      + c["ln_age_total_chol"] * la * ltc
      + c["ln_hdl"]            * lhd
      + c["ln_age_hdl"]        * la * lhd
      + (c["ln_sbp_treated"]   * lsp if treated_htn else 0.0)
      + (c["ln_sbp_untreated"] * lsp if not treated_htn else 0.0)
      + c["smoker"]            * (1 if smoker  else 0)
      + c["ln_age_smoker"]     * la * (1 if smoker else 0)
      + c["diabetes"]          * (1 if diabetes else 0)
    )

    risk = 1.0 - c["baseline_survival"] ** math.exp(score - c["mean_val"])
    return round(risk * 100, 1)


def risk_category(pct: float) -> tuple[str, str]:
    """Return (label, hex colour)."""
    if pct < 5:
        return "Low Risk",          "#26d97f"
    elif pct < 7.5:
        return "Borderline Risk",   "#f0c040"
    elif pct < 20:
        return "Intermediate Risk", "#f08030"
    else:
        return "High Risk",         "#e03030"


_GUIDELINE_NOTE = {
    "Low Risk":          "Risk-reducing lifestyle changes recommended.",
    "Borderline Risk":   "Discuss risk-enhancing factors; consider statin if benefit uncertain.",
    "Intermediate Risk": "Moderate- to high-intensity statin therapy recommended.",
    "High Risk":         "High-intensity statin therapy strongly recommended.",
}


# ═════════════════════════════════════════════════════════════════════════════
# Custom Widgets
# ═════════════════════════════════════════════════════════════════════════════

class SectionCard(QFrame):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("sectionCard")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 20)
        lay.setSpacing(12)
        hdr = QLabel(title)
        hdr.setObjectName("cardHeader")
        lay.addWidget(hdr)
        self.content = QWidget()
        self.content_layout = QGridLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setHorizontalSpacing(20)
        self.content_layout.setVerticalSpacing(10)
        lay.addWidget(self.content)


class RiskGauge(QWidget):
    """Semi-circular arc gauge."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pct   = 0.0
        self._color = QColor("#26d97f")
        self.setMinimumSize(170, 95)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def set_risk(self, pct: float, color: str):
        self._pct   = min(pct, 100.0)
        self._color = QColor(color)
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx = w // 2
        r  = min(cx - 10, h - 10)
        rect = QRect(cx - r, h - r - 2, r * 2, r * 2)

        # Track arc
        pen = QPen(QColor("#252a3a"), 11, Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(rect, 180 * 16, -180 * 16)

        # Filled arc
        fill = int((self._pct / 100.0) * 180 * 16)
        pen.setColor(self._color)
        p.setPen(pen)
        p.drawArc(rect, 180 * 16, -fill)
        p.end()


class ResultPanel(QFrame):
    """Result card shown after calculation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("resultCard")
        self.setVisible(False)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 24)
        outer.setSpacing(0)

        hdr = QLabel("10-YEAR ASCVD RISK  ·  ACC/AHA POOLED COHORT EQUATIONS")
        hdr.setObjectName("cardHeader")
        outer.addWidget(hdr)
        outer.addSpacing(16)

        body = QHBoxLayout()
        body.setSpacing(24)
        outer.addLayout(body)

        self.gauge = RiskGauge()
        body.addWidget(self.gauge, 0, Qt.AlignmentFlag.AlignBottom)

        right = QVBoxLayout()
        right.setSpacing(4)
        body.addLayout(right, 1)

        self.pct_label    = QLabel("—")
        self.pct_label.setObjectName("riskPct")
        self.cat_label    = QLabel("")
        self.cat_label.setObjectName("riskCat")
        self.detail_label = QLabel("")
        self.detail_label.setObjectName("riskDetail")
        self.detail_label.setWordWrap(True)

        right.addWidget(self.pct_label)
        right.addWidget(self.cat_label)
        right.addSpacing(8)
        right.addWidget(self.detail_label)
        right.addStretch()

        outer.addSpacing(12)
        self.note_label = QLabel("")
        self.note_label.setObjectName("riskNote")
        self.note_label.setWordWrap(True)
        outer.addWidget(self.note_label)

    def show_result(self, pct: float | None, data: dict):
        if pct is None:
            self.pct_label.setText("N/A")
            self.pct_label.setStyleSheet("color:#555f7e;font-size:34px;font-weight:800;")
            self.cat_label.setText("Outside validated age range (40–79 yrs)")
            self.cat_label.setStyleSheet("color:#555f7e;font-size:14px;font-weight:600;")
            self.detail_label.setText(
                "The ACC/AHA Pooled Cohort Equations are validated for patients "
                "aged 40–79. A risk estimate cannot be computed for this patient."
            )
            self.gauge.set_risk(0, "#555f7e")
            self.note_label.setText("")
        else:
            cat, color = risk_category(pct)
            self.pct_label.setText(f"{pct:.1f}%")
            self.pct_label.setStyleSheet(
                f"color:{color};font-size:40px;font-weight:800;")
            self.cat_label.setText(cat)
            self.cat_label.setStyleSheet(
                f"color:{color};font-size:15px;font-weight:600;")
            self.gauge.set_risk(pct, color)

            race_note = ""
            if _race_key(data["race"]) == "White" and data["race"] != "White":
                race_note = (f" Note: White-race coefficients applied — no validated "
                             f"equation exists for {data['race']} patients.")

            self.detail_label.setText(
                f"Estimated probability of a first ASCVD event (MI or fatal/non-fatal "
                f"stroke) within 10 years for a {data['age']}-year-old "
                f"{data['race']} {data['sex'].lower()}.{race_note}"
            )
            self.detail_label.setStyleSheet("color:#8892b0;font-size:12px;")
            self.note_label.setText(
                "Guideline note: " + _GUIDELINE_NOTE.get(cat, ""))
            self.note_label.setStyleSheet("color:#555f7e;font-size:11px;")

        self.setVisible(True)


# ═════════════════════════════════════════════════════════════════════════════
# Main Window
# ═════════════════════════════════════════════════════════════════════════════

class CVDRiskForm(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cardiovascular Risk Assessment")
        self.setMinimumWidth(700)
        self.resize(740, 920)
        self._apply_styles()
        self._build_ui()

    # ── Stylesheet ─────────────────────────────────────────────────────────────
    def _apply_styles(self):
        self.setStyleSheet("""
            QMainWindow, QWidget#root {
                background-color: #0f1117;
            }
            QScrollArea {
                background-color: transparent; border: none;
            }
            QScrollArea > QWidget > QWidget { background-color: transparent; }
            QScrollBar:vertical {
                background: #1a1d27; width: 8px; border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #3a3f55; border-radius: 4px; min-height: 24px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

            QFrame#sectionCard {
                background-color: #161923;
                border: 1px solid #252a3a;
                border-radius: 12px;
            }
            QFrame#resultCard {
                background-color: #161923;
                border: 1.5px solid #3d5afe;
                border-radius: 12px;
            }
            QLabel#cardHeader {
                color: #7c8fc7; font-size: 11px; font-weight: 700;
                letter-spacing: 2px;
                padding-bottom: 4px; border-bottom: 1px solid #252a3a;
            }
            QLabel#fieldLabel { color: #c8cfe8; font-size: 13px; font-weight: 500; }
            QLabel#unitLabel  { color: #555f7e; font-size: 11px; }

            QLineEdit {
                background-color: #1e2235; color: #e8ecf8;
                border: 1.5px solid #2d3350; border-radius: 8px;
                padding: 8px 12px; font-size: 13px;
                selection-background-color: #3d5afe;
            }
            QLineEdit:focus  { border-color: #3d5afe; background-color: #222640; }
            QLineEdit:hover  { border-color: #3a4060; }

            QComboBox {
                background-color: #1e2235; color: #e8ecf8;
                border: 1.5px solid #2d3350; border-radius: 8px;
                padding: 8px 12px; font-size: 13px; min-width: 160px;
            }
            QComboBox:focus { border-color: #3d5afe; }
            QComboBox:hover { border-color: #3a4060; }
            QComboBox::drop-down { border: none; width: 28px; }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #7c8fc7;
                width: 0; height: 0; margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e2235; color: #e8ecf8;
                border: 1px solid #3d5afe; border-radius: 8px;
                selection-background-color: #2d3abe; outline: none;
            }

            QCheckBox { color: #c8cfe8; font-size: 13px; spacing: 10px; }
            QCheckBox::indicator {
                width: 20px; height: 20px; border-radius: 6px;
                border: 1.5px solid #2d3350; background-color: #1e2235;
            }
            QCheckBox::indicator:hover   { border-color: #3d5afe; }
            QCheckBox::indicator:checked { background-color: #3d5afe; border-color: #3d5afe; }

            QPushButton#submitBtn {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #3d5afe, stop:1 #536dfe);
                color: #fff; font-size: 14px; font-weight: 700;
                letter-spacing: 1px; border: none; border-radius: 10px;
                padding: 13px 36px;
            }
            QPushButton#submitBtn:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #536dfe, stop:1 #7986cb);
            }
            QPushButton#submitBtn:pressed {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #2c3fd4, stop:1 #3d5afe);
            }

            QPushButton#printBtn {
                background-color: #1e2235; color: #c8cfe8;
                font-size: 13px; font-weight: 600;
                border: 1.5px solid #2d3350; border-radius: 10px;
                padding: 13px 28px;
            }
            QPushButton#printBtn:hover {
                border-color: #3d5afe; color: #e8ecf8; background-color: #222640;
            }
            QPushButton#printBtn:disabled { color: #2d3350; border-color: #1e2235; }

            QPushButton#resetBtn {
                background-color: transparent; color: #555f7e;
                font-size: 13px; font-weight: 600;
                border: 1.5px solid #252a3a; border-radius: 10px;
                padding: 13px 28px;
            }
            QPushButton#resetBtn:hover { border-color: #e03030; color: #e03030; }

            QLabel#pageTitle {
                color: #e8ecf8; font-size: 22px; font-weight: 700;
                letter-spacing: 0.5px;
            }
            QLabel#pageSubtitle { color: #555f7e; font-size: 12px; }

            QLabel#riskPct    { font-size: 40px; font-weight: 800; }
            QLabel#riskCat    { font-size: 15px; font-weight: 600; }
            QLabel#riskDetail { color: #8892b0; font-size: 12px; }
            QLabel#riskNote   { color: #555f7e; font-size: 11px; }
        """)

    # ── Build UI ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QWidget(); root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root); outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

        inner = QWidget(); inner.setObjectName("root")
        scroll.setWidget(inner)
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(36, 32, 36, 36)
        layout.setSpacing(20)

        # Header
        title = QLabel("Cardiovascular Risk Assessment"); title.setObjectName("pageTitle")
        sub   = QLabel("ACC/AHA Pooled Cohort Equations  ·  10-Year ASCVD Risk")
        sub.setObjectName("pageSubtitle")
        layout.addWidget(title); layout.addWidget(sub); layout.addSpacing(4)

        # Demographics
        demo = SectionCard("DEMOGRAPHICS")
        cl   = demo.content_layout
        self.age_input  = self._le("int",   "e.g. 55")
        self.sex_combo  = self._cb(["Male", "Female"])
        self.race_combo = self._cb(["White", "African American", "Hispanic",
                                    "Asian", "Native American", "Pacific Islander", "Other"])
        self._row(cl, 0, "Age",              self.age_input,  "years")
        self._row(cl, 1, "Sex",              self.sex_combo)
        self._row(cl, 2, "Race / Ethnicity", self.race_combo)
        layout.addWidget(demo)

        # Lipid Panel
        lipid = SectionCard("LIPID PANEL")
        ll    = lipid.content_layout
        self.total_chol_input = self._le("float", "e.g. 200")
        self.hdl_input        = self._le("float", "e.g. 50")
        self._row(ll, 0, "Total Cholesterol", self.total_chol_input, "mg/dL")
        self._row(ll, 1, "HDL Cholesterol",   self.hdl_input,        "mg/dL")
        layout.addWidget(lipid)

        # Vitals
        vitals = SectionCard("VITALS")
        vl     = vitals.content_layout
        self.sbp_input = self._le("int",   "e.g. 120")
        self.bmi_input = self._le("float", "e.g. 27.5")
        self._row(vl, 0, "Systolic Blood Pressure", self.sbp_input, "mmHg")
        self._row(vl, 1, "BMI",                     self.bmi_input, "kg/m²")
        layout.addWidget(vitals)

        # Risk Factors & Meds
        rf = SectionCard("RISK FACTORS & MEDICATIONS")
        rl = rf.content_layout
        self.smoker_cb      = QCheckBox("Current smoker")
        self.diabetes_cb    = QCheckBox("Diabetes mellitus")
        self.lipid_med_cb   = QCheckBox("Lipid-lowering medication")
        self.antihtn_med_cb = QCheckBox("Anti-hypertensive medication")
        for chk in (self.smoker_cb, self.diabetes_cb,
                    self.lipid_med_cb, self.antihtn_med_cb):
            chk.setCursor(Qt.CursorShape.PointingHandCursor)
        rl.addWidget(self.smoker_cb,      0, 0)
        rl.addWidget(self.diabetes_cb,    0, 1)
        rl.addWidget(self.lipid_med_cb,   1, 0)
        rl.addWidget(self.antihtn_med_cb, 1, 1)
        layout.addWidget(rf)

        # Result Panel
        self.result_panel = ResultPanel()
        layout.addWidget(self.result_panel)

        # Buttons
        layout.addSpacing(4)
        btn_row = QHBoxLayout(); btn_row.setSpacing(10)

        self.submit_btn = QPushButton("Calculate Risk")
        self.submit_btn.setObjectName("submitBtn")
        self.submit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.submit_btn.clicked.connect(self._on_submit)

        self.print_btn = QPushButton("⎙  Print Report")
        self.print_btn.setObjectName("printBtn")
        self.print_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.print_btn.clicked.connect(self._on_print)
        self.print_btn.setEnabled(False)

        self.reset_btn = QPushButton("Reset Form")
        self.reset_btn.setObjectName("resetBtn")
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.clicked.connect(self._on_reset)

        btn_row.addWidget(self.submit_btn)
        btn_row.addWidget(self.print_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.reset_btn)
        layout.addLayout(btn_row)
        layout.addStretch()

    # ── Widget helpers ─────────────────────────────────────────────────────────
    def _le(self, validator: str = None, placeholder: str = "") -> QLineEdit:
        le = QLineEdit()
        le.setPlaceholderText(placeholder)
        if validator == "int":
            le.setValidator(QIntValidator(0, 999, self))
        elif validator == "float":
            dv = QDoubleValidator(0.0, 9999.9, 1, self)
            dv.setNotation(QDoubleValidator.Notation.StandardNotation)
            le.setValidator(dv)
        return le

    def _cb(self, items: list[str]) -> QComboBox:
        cb = QComboBox(); cb.addItems(items); return cb

    def _row(self, grid: QGridLayout, row: int, label: str, widget, unit: str = ""):
        lbl = QLabel(label); lbl.setObjectName("fieldLabel")
        grid.addWidget(lbl, row, 0)
        if unit:
            hl = QHBoxLayout(); hl.setContentsMargins(0, 0, 0, 0); hl.setSpacing(6)
            hl.addWidget(widget)
            u = QLabel(unit); u.setObjectName("unitLabel")
            hl.addWidget(u); hl.addStretch()
            c = QWidget(); c.setLayout(hl)
            grid.addWidget(c, row, 1)
        else:
            grid.addWidget(widget, row, 1)

    # ── Submit ─────────────────────────────────────────────────────────────────
    def _on_submit(self):
        errors = []

        def _f(field, name):
            txt = field.text().strip()
            if not txt:
                errors.append(f"• {name} is required.")
                return None
            try:
                return float(txt)
            except ValueError:
                errors.append(f"• {name} must be a number.")
                return None

        def _i(field, name):
            v = _f(field, name); return int(v) if v is not None else None

        age  = _i(self.age_input,          "Age")
        tc   = _f(self.total_chol_input,   "Total Cholesterol")
        hdl  = _f(self.hdl_input,          "HDL Cholesterol")
        sbp  = _i(self.sbp_input,          "Systolic Blood Pressure")
        bmi  = _f(self.bmi_input,          "BMI")

        if errors:
            QMessageBox.warning(self, "Missing / Invalid Data",
                                "Please fix:\n\n" + "\n".join(errors))
            return

        # Soft range check
        warns = []
        if age and not (18 <= age <= 120): warns.append("• Age: 18–120 yrs")
        if tc  and not (50 <= tc  <= 500): warns.append("• Total Chol: 50–500 mg/dL")
        if hdl and not (10 <= hdl <= 150): warns.append("• HDL: 10–150 mg/dL")
        if sbp and not (70 <= sbp <= 250): warns.append("• SBP: 70–250 mmHg")
        if bmi and not (10 <= bmi <= 70):  warns.append("• BMI: 10–70 kg/m²")
        if warns:
            rep = QMessageBox.question(
                self, "Values Out of Typical Range",
                "Outside typical ranges:\n\n" + "\n".join(warns) + "\n\nProceed?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if rep == QMessageBox.StandardButton.No:
                return

        # Store
        patient_data.update({
            "age":                  age,
            "sex":                  self.sex_combo.currentText(),
            "race":                 self.race_combo.currentText(),
            "total_cholesterol":    tc,
            "hdl_cholesterol":      hdl,
            "systolic_bp":          sbp,
            "bmi":                  bmi,
            "smoker":               self.smoker_cb.isChecked(),
            "diabetes":             self.diabetes_cb.isChecked(),
            "lipid_lowering_med":   self.lipid_med_cb.isChecked(),
            "antihypertensive_med": self.antihtn_med_cb.isChecked(),
        })

        # Calculate
        risk_pct = pooled_cohort_risk(
            age        = patient_data["age"],
            sex        = patient_data["sex"],
            race       = patient_data["race"],
            total_chol = patient_data["total_cholesterol"],
            hdl_chol   = patient_data["hdl_cholesterol"],
            sbp        = patient_data["systolic_bp"],
            treated_htn= patient_data["antihypertensive_med"],
            smoker     = patient_data["smoker"],
            diabetes   = patient_data["diabetes"],
        )
        patient_data["ascvd_10yr_risk_pct"] = risk_pct

        self.result_panel.show_result(risk_pct, patient_data)
        self.print_btn.setEnabled(True)

        # Console output
        print("\n" + "═" * 54)
        print("  CARDIOVASCULAR RISK ASSESSMENT")
        print("═" * 54)
        for k, v in patient_data.items():
            print(f"  {k:<28} {v}")
        print("═" * 54 + "\n")

    # ── Print ──────────────────────────────────────────────────────────────────
    def _on_print(self):
        if not patient_data:
            QMessageBox.information(self, "No Data", "Submit patient data first.")
            return

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dlg = QPrintDialog(printer, self)
        if dlg.exec() != QPrintDialog.DialogCode.Accepted:
            return

        risk_pct = patient_data.get("ascvd_10yr_risk_pct")
        cat      = risk_category(risk_pct)[0] if risk_pct is not None else "N/A"
        note     = _GUIDELINE_NOTE.get(cat, "")
        yn       = lambda b: "Yes" if b else "No"

        html = f"""
        <html><body style="font-family:Arial,sans-serif;color:#111;padding:24px;">
        <h2 style="margin-bottom:2px;">Cardiovascular Risk Assessment</h2>
        <p style="color:#666;font-size:12px;margin-top:0;">
            Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} &nbsp;|&nbsp;
            ACC/AHA Pooled Cohort Equations (Goff 2014)</p>
        <hr/>
        <h3>Patient Information</h3>
        <table cellspacing="6" style="width:100%;font-size:13px;border-collapse:collapse;">
          <tr>
            <td style="padding:4px 8px;"><b>Age</b></td>
            <td style="padding:4px 8px;">{patient_data.get('age')} yrs</td>
            <td style="padding:4px 8px;"><b>Sex</b></td>
            <td style="padding:4px 8px;">{patient_data.get('sex')}</td>
          </tr>
          <tr style="background:#f5f5f5;">
            <td style="padding:4px 8px;"><b>Race / Ethnicity</b></td>
            <td style="padding:4px 8px;" colspan="3">{patient_data.get('race')}</td>
          </tr>
          <tr>
            <td style="padding:4px 8px;"><b>Total Cholesterol</b></td>
            <td style="padding:4px 8px;">{patient_data.get('total_cholesterol')} mg/dL</td>
            <td style="padding:4px 8px;"><b>HDL Cholesterol</b></td>
            <td style="padding:4px 8px;">{patient_data.get('hdl_cholesterol')} mg/dL</td>
          </tr>
          <tr style="background:#f5f5f5;">
            <td style="padding:4px 8px;"><b>Systolic BP</b></td>
            <td style="padding:4px 8px;">{patient_data.get('systolic_bp')} mmHg</td>
            <td style="padding:4px 8px;"><b>BMI</b></td>
            <td style="padding:4px 8px;">{patient_data.get('bmi')} kg/m²</td>
          </tr>
          <tr>
            <td style="padding:4px 8px;"><b>Smoker</b></td>
            <td style="padding:4px 8px;">{yn(patient_data.get('smoker'))}</td>
            <td style="padding:4px 8px;"><b>Diabetes</b></td>
            <td style="padding:4px 8px;">{yn(patient_data.get('diabetes'))}</td>
          </tr>
          <tr style="background:#f5f5f5;">
            <td style="padding:4px 8px;"><b>Lipid-lowering med</b></td>
            <td style="padding:4px 8px;">{yn(patient_data.get('lipid_lowering_med'))}</td>
            <td style="padding:4px 8px;"><b>Anti-HTN med</b></td>
            <td style="padding:4px 8px;">{yn(patient_data.get('antihypertensive_med'))}</td>
          </tr>
        </table>
        <hr/>
        <h3>10-Year ASCVD Risk Result</h3>
        <p style="font-size:32px;font-weight:bold;margin:0 0 4px 0;">
          {f"{risk_pct:.1f}%" if risk_pct is not None else "N/A"}</p>
        <p style="font-size:16px;font-weight:bold;margin:0 0 12px 0;">{cat}</p>
        {"<p style='font-size:12px;'><b>Guideline note:</b> " + note + "</p>" if note else ""}
        <p style="font-size:11px;color:#666;margin-top:24px;">
          This report is generated from the 2013 ACC/AHA Pooled Cohort Equations
          and is intended for clinical decision support only. It does not constitute
          a diagnosis or replace clinical judgment.
          Reference: Goff DC Jr, et al. <i>Circulation</i>. 2014;129(25 Suppl 2):S49-73.</p>
        </body></html>
        """

        tdoc = QTextDocument()
        tdoc.setHtml(html)
        tdoc.print(printer)

    # ── Reset ──────────────────────────────────────────────────────────────────
    def _on_reset(self):
        rep = QMessageBox.question(
            self, "Reset Form",
            "Clear all fields and results?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if rep != QMessageBox.StandardButton.Yes:
            return

        for w in (self.age_input, self.total_chol_input,
                  self.hdl_input, self.sbp_input, self.bmi_input):
            w.clear()
        self.sex_combo.setCurrentIndex(0)
        self.race_combo.setCurrentIndex(0)
        for cb in (self.smoker_cb, self.diabetes_cb,
                   self.lipid_med_cb, self.antihtn_med_cb):
            cb.setChecked(False)

        self.result_panel.setVisible(False)
        self.print_btn.setEnabled(False)
        patient_data.clear()


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = CVDRiskForm()
    window.show()
    sys.exit(app.exec())