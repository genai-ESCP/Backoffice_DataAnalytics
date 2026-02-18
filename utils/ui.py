import streamlit as st
from utils.auth import is_authenticated, logout

DASHBOARD_CSS = """
<style>
.block-container { padding-top: 1.25rem; padding-bottom: 2rem; max-width: 1250px; }
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header[data-testid="stHeader"] { display: none; }
div[data-testid="stToolbar"] { display: none; }
div[data-testid="stDecoration"] { display: none; }

h1 { font-size: 1.65rem !important; margin-bottom: 0.25rem !important; }
h2 { font-size: 1.20rem !important; margin-top: 1.25rem !important; }
h3 { font-size: 1.00rem !important; }

.small-muted { color: rgba(15,23,42,0.62); font-size: 0.92rem; line-height: 1.35rem; }

.card {
  background: #FFFFFF;
  border: 1px solid rgba(15,23,42,0.08);
  border-radius: 16px;
  padding: 16px 18px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}

.card-muted {
  background: #F6F8FB;
  border: 1px solid rgba(15,23,42,0.06);
  border-radius: 16px;
  padding: 16px 16px;
}

.card-title {
  font-weight: 800;
  font-size: 0.95rem;
  margin-bottom: 10px;
}

.kpi {
  display:flex; flex-direction:column; gap:6px;
}
.kpi .label { color: rgba(15,23,42,0.62); font-size: 0.86rem; }
.kpi .value { font-size: 1.40rem; font-weight: 900; letter-spacing: -0.02em; }

.badge {
  display:inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 0.82rem;
  font-weight: 800;
  border: 1px solid rgba(15,23,42,0.10);
  background: #F6F8FB;
}

.divider { height: 1px; background: rgba(15,23,42,0.10); margin: 14px 0; }
code { font-size: 0.88rem; }

/* Chart and data framing */
div[data-testid="stVegaLiteChart"] {
  border: 1px solid rgba(15,23,42,0.10);
  border-radius: 14px;
  background: #ffffff;
  padding: 8px 10px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}

div[data-testid="stDataFrame"] {
  border: 1px solid rgba(15,23,42,0.10);
  border-radius: 14px;
  overflow: hidden;
}

/* Labels above charts */
.chart-title {
  font-size: 0.92rem;
  font-weight: 800;
  margin: 10px 0 6px 0;
}

div[data-testid="stPageLink"] a {
  border: 1px solid rgba(15,23,42,0.10);
  border-radius: 10px;
  padding: 8px 10px;
  background: #f8fafc;
  color: #0f172a !important;
  font-weight: 600;
  text-align: center;
  transition: all 120ms ease-out;
}

div[data-testid="stPageLink"] a:hover {
  border-color: rgba(37,99,235,0.40);
  background: #eff6ff;
  box-shadow: 0 2px 8px rgba(37,99,235,0.10);
  transform: translateY(-1px);
}

div[data-testid="stPageLink"] a[aria-disabled="true"] {
  background: #dbeafe;
  border-color: #93c5fd;
  color: #1e3a8a !important;
  opacity: 1 !important;
}
</style>
"""

def apply_dashboard_style() -> None:
    st.markdown(DASHBOARD_CSS, unsafe_allow_html=True)

def card(title: str, body_html: str, muted: bool = False) -> None:
    cls = "card-muted" if muted else "card"
    st.markdown(
        f'<div class="{cls}"><div class="card-title">{title}</div>{body_html}</div>',
        unsafe_allow_html=True
    )

def kpi(label: str, value: str) -> None:
    st.markdown(
        f'<div class="card"><div class="kpi">'
        f'<div class="label">{label}</div>'
        f'<div class="value">{value}</div>'
        f'</div></div>',
        unsafe_allow_html=True
    )

def badge(text: str) -> None:
    st.markdown(f'<span class="badge">{text}</span>', unsafe_allow_html=True)

def divider() -> None:
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

def render_sidebar(current_page: str) -> None:
    pages = [
        ("Home", "app.py"),
        ("Student search", "pages/student_search.py"),
        ("Student stats", "pages/statistics.py"),
        ("Extraction", "pages/extraction.py"),
    ]

    cols = st.columns(len(pages), gap="small")
    for col, (label, path) in zip(cols, pages):
        with col:
            st.page_link(path, label=label, disabled=(label == current_page), use_container_width=True)

    if is_authenticated():
        c1, c2 = st.columns([0.85, 0.15], gap="small")
        with c2:
            if st.button("Logout", use_container_width=True):
                logout()
                st.rerun()

