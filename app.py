import streamlit as st
from utils.auth import require_auth
from utils.ui import apply_dashboard_style, card, divider, render_sidebar

st.set_page_config(page_title="Archivage Blackboard", page_icon="A", layout="wide", initial_sidebar_state="expanded")
apply_dashboard_style()
require_auth()
render_sidebar("Home")

st.markdown("# Archivage Blackboard")
st.markdown('<div class="small-muted">Internal dashboard for student status and analytics across Blackboard extractions.</div>', unsafe_allow_html=True)

col1, col2 = st.columns([1.25, 0.85], gap="large")

with col1:
    card(
        "How it works",
        """
        <div class="small-muted">
          <ul>
            <li><b>Student search</b>: search by email or student ID, then review latest status and timeline analytics.</li>
            <li><b>Student stats</b>: global analytics across all extraction files.</li>
            <li><b>Extraction</b>: merge gradebook + hours files and download the output workbook.</li>
          </ul>
        </div>
        """
    )

with col2:
    card(
        "Data source",
        """
        <div class="small-muted">
          The app reads Excel extraction files stored in:
          <br><br>
          <code>data/extractions/&lt;BLACKBOARD_CODE&gt;/</code>
          <br><br>
          Add new extraction files to the relevant course folder and push to update dashboards.
        </div>
        """,
        muted=True
    )

divider()
card(
    "Navigation",
    "<div class='small-muted'>Use the top navigation bar to switch pages.</div>",
    muted=False,
)
