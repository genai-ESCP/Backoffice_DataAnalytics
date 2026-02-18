import pandas as pd
import streamlit as st

from utils.auth import require_auth
from utils.loaders import (
    load_all_extractions,
    load_certified_emails,
    load_student_data,
    normalize_email,
    normalize_student_id_e,
)
from utils.ui import apply_dashboard_style, card, divider, render_sidebar

COURSE_MAIN = "2526ALL_OL_GENAI_00"
COURSE_RETAKE = "2526ALL_OL_GENAI_02"
COURSE_OLD = "2425ALL_OL_GENAI_00"
COURSE_POC = "poc_students"

COURSE_LABELS = {
    COURSE_MAIN: "Fall 2526 course",
    COURSE_RETAKE: "Retake Fall 2526",
    COURSE_OLD: "Spring 2425",
}
COURSE_ORDER = [COURSE_MAIN, COURSE_RETAKE, COURSE_OLD]

st.set_page_config(page_title="Student search", page_icon="S", layout="wide", initial_sidebar_state="expanded")
apply_dashboard_style()
require_auth()
render_sidebar("Student search")

st.markdown("# Student search")
st.markdown('<div class="small-muted">Search by email or student ID, then filter analytics by course or view generalized analytics.</div>', unsafe_allow_html=True)
st.markdown(
    """
    <style>
    .verdict-chip {
      display: inline-block;
      padding: 4px 9px;
      border-radius: 999px;
      font-size: 0.80rem;
      font-weight: 700;
      border: 1px solid transparent;
    }
    .verdict-pass {
      color: #166534;
      background: #dcfce7;
      border-color: #86efac;
    }
    .verdict-fail {
      color: #991b1b;
      background: #fee2e2;
      border-color: #fca5a5;
    }
    .verdict-unknown {
      color: #334155;
      background: #e2e8f0;
      border-color: #cbd5e1;
    }
    .license-chip {
      display: inline-block;
      padding: 4px 9px;
      border-radius: 999px;
      font-size: 0.80rem;
      font-weight: 700;
      border: 1px solid transparent;
    }
    .license-enabled {
      color: #166534;
      background: #dcfce7;
      border-color: #86efac;
    }
    .license-pending {
      color: #9a3412;
      background: #ffedd5;
      border-color: #fdba74;
    }
    .license-grey {
      color: #334155;
      background: #e2e8f0;
      border-color: #cbd5e1;
    }
    .cert-chip {
      display: inline-block;
      padding: 4px 9px;
      border-radius: 999px;
      font-size: 0.80rem;
      font-weight: 700;
      border: 1px solid transparent;
    }
    .cert-ok {
      color: #166534;
      background: #dcfce7;
      border-color: #86efac;
    }
    .cert-no {
      color: #991b1b;
      background: #fee2e2;
      border-color: #fca5a5;
    }
    .profile-grid {
      display: grid;
      grid-template-columns: 1fr;
      row-gap: 8px;
      margin-top: 8px;
    }
    .profile-row {
      display: grid;
      grid-template-columns: 135px 1fr;
      column-gap: 8px;
      align-items: start;
      line-height: 1.35;
    }
    .profile-key {
      color: rgba(15,23,42,0.62);
      font-weight: 600;
      font-size: 0.88rem;
    }
    .profile-val {
      color: #0f172a;
      font-size: 0.92rem;
      word-break: break-word;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

df = load_all_extractions()
if df.empty:
    st.warning("No extraction files found under data/extractions/.")
    st.stop()

q = st.text_input("Email or Student ID", placeholder="email@domain.com or 123456")
if not q:
    st.stop()

email = normalize_email(q)
sid = q.strip()
if sid.lower().startswith("id:"):
    sid = sid[3:].strip()

m = df.copy()
if email:
    m = m[m["email_norm"] == email]
else:
    m = m[m["student_id"].astype(str).str.strip() == sid]

if m.empty:
    st.warning("Student not found across all extractions.")
    st.stop()

if email:
    distinct_ids = set([x for x in m["student_id"].unique().tolist() if x])
    if len(distinct_ids) > 1:
        card(
            "Needs review",
            "<div class='small-muted'>Multiple student IDs match the same email across extractions.</div>",
            muted=True,
        )
        st.stop()

m_sorted = m.sort_values(["extracted_at", "file_name"], na_position="last")
latest_row = m_sorted.iloc[-1]

identity = {
    "first_name": latest_row.get("first_name", ""),
    "last_name": latest_row.get("last_name", ""),
    "student_id": latest_row.get("student_id", ""),
    "email_norm": latest_row.get("email_norm", ""),
}

student_data = load_student_data()
student_extra = {
    "campus": "",
    "program": "",
    "promotion": "",
    "chatgpt_status": "",
}
if not student_data.empty:
    sid_candidates = set(
        [
            normalize_student_id_e(sid),
            normalize_student_id_e(identity.get("student_id", "")),
        ]
    )
    sid_candidates = set([x for x in sid_candidates if x])

    extra_match = student_data[student_data["email_norm"] == email] if email else student_data.iloc[0:0]
    if extra_match.empty and identity.get("email_norm"):
        extra_match = student_data[student_data["email_norm"] == identity.get("email_norm")]
    if extra_match.empty and sid_candidates:
        extra_match = student_data[student_data["student_id_e"].isin(sid_candidates)]

    if not extra_match.empty:
        extra = extra_match.iloc[0]
        student_extra = {
            "campus": str(extra.get("campus", "")).strip(),
            "program": str(extra.get("program", "")).strip(),
            "promotion": str(extra.get("promotion", "")).strip(),
            "chatgpt_status": str(extra.get("chatgpt_status", "")).strip(),
        }


def chatgpt_chip_html(status: str) -> str:
    s = str(status or "").strip()
    sl = s.lower()
    if sl == "enabled":
        return f"<span class='license-chip license-enabled'>{s}</span>"
    if sl == "pending":
        return f"<span class='license-chip license-pending'>{s}</span>"
    if sl in {"deleted", "not invited"}:
        return f"<span class='license-chip license-grey'>{s}</span>"
    if not s:
        return "<span class='license-chip license-grey'>Unknown</span>"
    return f"<span class='license-chip license-grey'>{s}</span>"


def certification_chip_html(is_certified: bool) -> str:
    if is_certified:
        return "<span class='cert-chip cert-ok'>Certified</span>"
    return "<span class='cert-chip cert-no'>Not certified</span>"


certified_emails = load_certified_emails()
email_for_cert_check = normalize_email(email or identity.get("email_norm", ""))
is_certified_student = bool(email_for_cert_check and email_for_cert_check in certified_emails)

latest_by_course = df.groupby("course_type")["extracted_at"].max().to_dict()


def in_latest_snapshot(course_code: str) -> bool:
    dt = latest_by_course.get(course_code)
    if dt is None or pd.isna(dt):
        return False
    return len(m[(m["course_type"] == course_code) & (m["extracted_at"] == dt)]) > 0


membership = {code: in_latest_snapshot(code) for code in COURSE_ORDER}
active_course_labels = [COURSE_LABELS[c] for c in COURSE_ORDER if membership[c]]

verdicts_old = []
old_dt = latest_by_course.get(COURSE_OLD)
if old_dt is not None and pd.notna(old_dt):
    rows_old = m[(m["course_type"] == COURSE_OLD) & (m["extracted_at"] == old_dt)]
    verdicts_old = rows_old["verdict"].fillna("").tolist()

passed_old = any("PASS" in str(v).upper() for v in verdicts_old if v)
failed_old = any("FAIL" in str(v).upper() for v in verdicts_old if v)


def latest_verdict_for_course(course_code: str) -> str:
    dt = latest_by_course.get(course_code)
    if dt is None or pd.isna(dt):
        return "Unknown"
    rows = m[(m["course_type"] == course_code) & (m["extracted_at"] == dt)]
    if rows.empty:
        return "Unknown"
    verdicts = rows["verdict"].fillna("").astype(str).tolist()
    if any("PASS" in v.upper() for v in verdicts if v.strip()):
        return "Passed"
    if any("FAIL" in v.upper() for v in verdicts if v.strip()):
        return "Failed"
    return "Unknown"


latest_verdict_by_course = {code: latest_verdict_for_course(code) for code in COURSE_ORDER}
completed_genai = any(v == "Passed" for v in latest_verdict_by_course.values())
only_failed_main = (
    latest_verdict_by_course.get(COURSE_MAIN) == "Failed"
    and not membership.get(COURSE_RETAKE, False)
    and not membership.get(COURSE_OLD, False)
)
retake_not_completed = membership.get(COURSE_RETAKE, False) and latest_verdict_by_course.get(COURSE_RETAKE) != "Passed"
is_poc_student = m["course_type"].astype(str).str.strip().str.lower().eq(COURSE_POC.lower()).any()

if is_poc_student:
    st.success("poc_student")
elif completed_genai:
    st.success("Completed the GenAI course")
elif retake_not_completed:
    st.error("Failed to complete the GenAI course in retake. Student cannot redo it again.")
elif only_failed_main:
    st.info("In progress: failed the new students course and currently not enrolled in another track.")

conflicts = []
if membership[COURSE_MAIN] and membership[COURSE_RETAKE]:
    conflicts.append(f"Student in both {COURSE_LABELS[COURSE_MAIN]} and {COURSE_LABELS[COURSE_RETAKE]}")
if membership[COURSE_RETAKE] and passed_old:
    conflicts.append(f"In {COURSE_LABELS[COURSE_RETAKE]} but passed {COURSE_LABELS[COURSE_OLD]}")
if membership[COURSE_MAIN] and failed_old:
    conflicts.append(f"In {COURSE_LABELS[COURSE_MAIN]} but failed {COURSE_LABELS[COURSE_OLD]}")

situation = "Needs review"
if passed_old:
    situation = f"Passed ({COURSE_LABELS[COURSE_OLD]})"
elif failed_old:
    situation = f"Retake required ({COURSE_LABELS[COURSE_RETAKE]})"
elif membership[COURSE_MAIN]:
    situation = f"In progress ({COURSE_LABELS[COURSE_MAIN]})"
elif membership[COURSE_RETAKE]:
    situation = f"In progress ({COURSE_LABELS[COURSE_RETAKE]})"
if conflicts:
    situation = "Needs review"

left, right = st.columns([1.05, 1.95], gap="large")

with left:
    student_id_display = identity.get("student_id", "")
    student_id_with_e = normalize_student_id_e(student_id_display)
    student_id_label = student_id_with_e if student_id_with_e else "-"
    card(
        "Student profile",
        f"""
        <div><b>{identity.get('first_name','')} {identity.get('last_name','')}</b></div>
        <div class="profile-grid">
          <div class="profile-row"><div class="profile-key">Email</div><div class="profile-val">{identity.get('email_norm','-')}</div></div>
          <div class="profile-row"><div class="profile-key">ID</div><div class="profile-val">{student_id_label}</div></div>
          <div class="profile-row"><div class="profile-key">Campus</div><div class="profile-val">{student_extra.get('campus') or '-'}</div></div>
          <div class="profile-row"><div class="profile-key">Program</div><div class="profile-val">{student_extra.get('program') or '-'}</div></div>
          <div class="profile-row"><div class="profile-key">Promotion</div><div class="profile-val">{student_extra.get('promotion') or '-'}</div></div>
          <div class="profile-row"><div class="profile-key">ChatGPT license</div><div class="profile-val">{chatgpt_chip_html(student_extra.get('chatgpt_status',''))}</div></div>
          <div class="profile-row"><div class="profile-key">Certificate</div><div class="profile-val">{certification_chip_html(is_certified_student)}</div></div>
        </div>
        """,
    )

    divider()

    enrollment_text = " | ".join(active_course_labels) if active_course_labels else "No course found in latest snapshots"
    card("Current enrollment", f"<div><b>{enrollment_text}</b></div>")
    card("Latest situation", f"<div><b>{situation}</b></div>")
    if conflicts:
        card("Needs review", f"<div class='small-muted'>{' | '.join(conflicts)}</div>", muted=True)

with right:
    cols = st.columns(3, gap="large")
    for idx, course_code in enumerate(COURSE_ORDER):
        with cols[idx]:
            verdict = latest_verdict_by_course[course_code]
            chip_class = (
                "verdict-pass"
                if verdict == "Passed"
                else "verdict-fail"
                if verdict == "Failed"
                else "verdict-unknown"
            )
            card(
                COURSE_LABELS[course_code],
                (
                    f"<div class='small-muted'>"
                    f"{'In latest extraction' if membership[course_code] else 'Not in latest extraction'}"
                    f"</div><br><div><span class='verdict-chip {chip_class}'>Latest verdict: {verdict}</span></div>"
                ),
            )

    divider()

    if "student_scope" not in st.session_state:
        st.session_state["student_scope"] = "Generalized analytics"

    scope_options = ["Generalized analytics"] + [COURSE_LABELS[c] for c in COURSE_ORDER]

    current_scope = st.radio(
        "Analytics scope",
        options=scope_options,
        index=scope_options.index(st.session_state["student_scope"]) if st.session_state["student_scope"] in scope_options else 0,
        horizontal=True,
    )
    st.session_state["student_scope"] = current_scope

    if st.button("Generalize analytics"):
        st.session_state["student_scope"] = "Generalized analytics"
        st.rerun()

    card(
        "Student analytics",
        "<div class='small-muted'>Charts below update based on selected scope.</div>",
        muted=True,
    )

    timeline = m.dropna(subset=["extracted_at"]).sort_values("extracted_at").copy()

    selected_course_code = None
    for code, label in COURSE_LABELS.items():
        if st.session_state["student_scope"] == label:
            selected_course_code = code
            break

    if selected_course_code:
        timeline = timeline[timeline["course_type"] == selected_course_code].copy()

    if timeline.empty:
        st.info("No timeline data available for the selected scope.")
        st.stop()

    def to_float(x):
        try:
            return float(str(x).replace(",", "."))
        except Exception:
            return None

    timeline["hours_num"] = timeline["hours"].map(to_float)
    timeline["grade_num"] = timeline["grade"].map(to_float)

    st.markdown("<div class='chart-title'>Presence Over Time</div>", unsafe_allow_html=True)
    if selected_course_code:
        presence_ts = timeline.groupby("extracted_at").size().sort_index()
        st.line_chart(presence_ts)
    else:
        presence_ts = (
            timeline.groupby(["extracted_at", "course_type"])
            .size()
            .reset_index(name="present")
            .pivot(index="extracted_at", columns="course_type", values="present")
            .fillna(0)
            .sort_index()
        )
        presence_ts = presence_ts.rename(columns=COURSE_LABELS)
        st.line_chart(presence_ts)

    st.markdown("<div class='chart-title'>Hours Over Time</div>", unsafe_allow_html=True)
    if selected_course_code:
        hours_ts = timeline.groupby("extracted_at")["hours_num"].max().sort_index()
        st.line_chart(hours_ts)
    else:
        hours_ts = (
            timeline.groupby(["extracted_at", "course_type"])["hours_num"]
            .max()
            .reset_index()
            .pivot(index="extracted_at", columns="course_type", values="hours_num")
            .sort_index()
        )
        hours_ts = hours_ts.rename(columns=COURSE_LABELS)
        st.line_chart(hours_ts)

    st.markdown("<div class='chart-title'>Grade Over Time</div>", unsafe_allow_html=True)
    if selected_course_code:
        grade_ts = timeline.groupby("extracted_at")["grade_num"].max().sort_index()
        st.line_chart(grade_ts)
    else:
        grade_ts = (
            timeline.groupby(["extracted_at", "course_type"])["grade_num"]
            .max()
            .reset_index()
            .pivot(index="extracted_at", columns="course_type", values="grade_num")
            .sort_index()
        )
        grade_ts = grade_ts.rename(columns=COURSE_LABELS)
        st.line_chart(grade_ts)

    with st.expander("Matched rows (selected scope)"):
        show_cols = ["extracted_at", "course_type", "hours", "grade", "verdict", "file_name"]
        table = timeline[show_cols].sort_values("extracted_at").copy()
        table["course_type"] = table["course_type"].map(lambda c: COURSE_LABELS.get(c, c))
        st.dataframe(table, use_container_width=True)
