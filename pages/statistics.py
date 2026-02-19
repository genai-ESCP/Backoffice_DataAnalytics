import streamlit as st
import pandas as pd

from utils.auth import require_auth
from utils.loaders import load_all_extractions, load_certified_emails, normalize_email
from utils.ui import apply_dashboard_style, card, kpi, divider, render_sidebar

COURSE_2425 = "2425ALL_OL_GENAI_00"
COURSE_2526_FALL_NEW = "2526ALL_OL_GENAI_00"
COURSE_2526_FALL_RETAKE = "2526ALL_OL_GENAI_02"
COURSE_2526_SPRING_NEW = "2526ALL_SPR_GENAI_00"
COURSE_2526_SPRING_RETAKE = "2526ALL_SPR_GENAI_02"
COURSE_POC = "Poc_Students"

TRACKED_COURSES = [
    COURSE_2425,
    COURSE_2526_FALL_NEW,
    COURSE_2526_FALL_RETAKE,
    COURSE_2526_SPRING_NEW,
    COURSE_2526_SPRING_RETAKE,
]

COURSE_LABELS = {
    COURSE_2425: "Spring 2425",
    COURSE_2526_FALL_NEW: "Fall 2526 new students",
    COURSE_2526_FALL_RETAKE: "Fall 2526 retake",
    COURSE_2526_SPRING_NEW: "Spring 2526 new students",
    COURSE_2526_SPRING_RETAKE: "Spring 2526 retake",
    COURSE_POC: "POC students",
}

st.set_page_config(page_title="Student stats", page_icon="📈", layout="wide", initial_sidebar_state="expanded")
apply_dashboard_style()
require_auth()
render_sidebar("Student stats")

st.markdown("# Student stats")
st.markdown('<div class="small-muted">Global analytics across all extraction files currently stored in the app.</div>', unsafe_allow_html=True)

df = load_all_extractions()
if df.empty:
    st.warning("No extraction files found under data/extractions/.")
    st.stop()

# numeric parsing
def to_float(x):
    try:
        return float(str(x).replace(",", "."))
    except:
        return None

def is_passed(verdict: str) -> bool:
    return "PASS" in str(verdict or "").upper()

df["hours_num"] = df["hours"].map(to_float)
df["grade_num"] = df["grade"].map(to_float)

# Latest extraction date per course_type
latest_by_course = df.groupby("course_type")["extracted_at"].max().to_dict()

card(
    "Latest extraction used (per course folder)",
    "<div class='small-muted'>Dates are parsed from filenames (e.g., _27_Janv). If a filename has no parseable date, it will not appear in time series.</div>",
    muted=True
)
if latest_by_course:
    course_items = sorted(latest_by_course.items(), key=lambda x: str(x[0]))
    cols = st.columns(min(4, len(course_items)), gap="large")
    for idx, (course, dt) in enumerate(course_items):
        date_label = dt.date().isoformat() if pd.notna(dt) else "No parseable date"
        with cols[idx % len(cols)]:
            card(
                str(course),
                f"<div class='small-muted'><b>{date_label}</b></div>",
                muted=False,
            )
else:
    st.info("No extraction dates available.")

divider()

# Latest snapshot rows (per course)
# If no parseable date exists for a course, fallback to latest file_name.
latest_rows = []
for course_type in sorted(df["course_type"].dropna().unique().tolist()):
    cdf = df[df["course_type"] == course_type].copy()
    cdf_with_dt = cdf.dropna(subset=["extracted_at"])
    if not cdf_with_dt.empty:
        latest_dt = cdf_with_dt["extracted_at"].max()
        snap = cdf_with_dt[cdf_with_dt["extracted_at"] == latest_dt].copy()
    else:
        latest_file = cdf["file_name"].astype(str).max()
        snap = cdf[cdf["file_name"].astype(str) == latest_file].copy()
    latest_rows.append(snap)

latest_df = pd.concat(latest_rows, ignore_index=True) if latest_rows else df.iloc[0:0].copy()

card(
    "Total amount of students",
    "<div class='small-muted'>Latest snapshot student count per course folder.</div>",
    muted=True,
)

latest_kpi_courses = TRACKED_COURSES + [COURSE_POC]
kpi_cols = st.columns(min(3, len(latest_kpi_courses)), gap="large")
for idx, course_code in enumerate(latest_kpi_courses):
    with kpi_cols[idx % len(kpi_cols)]:
        kpi(
            f"{COURSE_LABELS.get(course_code, course_code)} (latest)",
            str(int((latest_df["course_type"] == course_code).sum())),
        )

divider()

# Passed students by course (latest snapshot)
pass_counts = {}
for course_type, snap in latest_df.groupby("course_type"):
    if course_type == COURSE_POC:
        # POC students are counted as certified/completed population for this KPI.
        pass_counts[course_type] = int(len(snap))
    else:
        pass_counts[course_type] = int(snap["verdict"].map(is_passed).sum())

total_passed = int(sum(pass_counts.values()))
kpi("Total passed students (incl. POC)", str(total_passed))

# Top KPI cards (non-table)
certified_emails = load_certified_emails()

def snapshot_keys_for_course(course_df: pd.DataFrame):
    with_dt = course_df.dropna(subset=["extracted_at"])[["extracted_at", "file_name"]].drop_duplicates()
    with_dt = with_dt.sort_values(["extracted_at", "file_name"])
    if not with_dt.empty:
        return [tuple(x) for x in with_dt[["extracted_at", "file_name"]].to_records(index=False)]
    by_file = course_df[["file_name"]].drop_duplicates().sort_values("file_name")
    return [(pd.NaT, fn) for fn in by_file["file_name"].tolist()]

def fmt_num(v, suffix=""):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "-"
    return f"{v}{suffix}"

def fmt_delta(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "-"
    sign = "+" if v > 0 else ""
    return f"{sign}{v}"

course_cards = []
for course_type, snap in latest_df.groupby("course_type"):
    students_latest = int(len(snap))
    passed_latest = int(pass_counts.get(course_type, 0))
    pass_rate = round((passed_latest / students_latest) * 100, 2) if students_latest else None
    avg_hours = round(snap["hours_num"].dropna().mean(), 2) if not snap["hours_num"].dropna().empty else None
    avg_grade = round(snap["grade_num"].dropna().mean(), 2) if not snap["grade_num"].dropna().empty else None
    median_hours = round(snap["hours_num"].dropna().median(), 2) if not snap["hours_num"].dropna().empty else None
    inactive_count = int(((snap["hours_num"].isna()) | (snap["hours_num"] <= 0)).sum())

    course_all = df[df["course_type"] == course_type].copy()
    keys = snapshot_keys_for_course(course_all)
    grade_delta = None
    if len(keys) >= 2:
        prev_key = keys[-2]
        cur_key = keys[-1]
        prev_snap = course_all[
            (course_all["file_name"].astype(str) == str(prev_key[1]))
            & (
                (course_all["extracted_at"] == prev_key[0])
                if pd.notna(prev_key[0])
                else course_all["extracted_at"].isna()
            )
        ]
        cur_snap = course_all[
            (course_all["file_name"].astype(str) == str(cur_key[1]))
            & (
                (course_all["extracted_at"] == cur_key[0])
                if pd.notna(cur_key[0])
                else course_all["extracted_at"].isna()
            )
        ]
        prev_mean = prev_snap["grade_num"].dropna().mean()
        cur_mean = cur_snap["grade_num"].dropna().mean()
        if pd.notna(prev_mean) and pd.notna(cur_mean):
            grade_delta = round(cur_mean - prev_mean, 2)

    passed_rows = snap[snap["verdict"].map(is_passed)].copy()
    passed_emails = set(
        [normalize_email(x) for x in passed_rows["email_norm"].astype(str).tolist() if normalize_email(x)]
    )
    cert_rate = round((len(passed_emails & certified_emails) / len(passed_emails)) * 100, 2) if passed_emails else None

    course_cards.append(
        {
            "course": COURSE_LABELS.get(course_type, course_type),
            "students": students_latest,
            "passed": passed_latest,
            "pass_rate": pass_rate,
            "avg_hours": avg_hours,
            "avg_grade": avg_grade,
            "median_hours": median_hours,
            "inactive": inactive_count,
            "grade_delta": grade_delta,
            "cert_rate": cert_rate,
        }
    )

if course_cards:
    card(
        "Course KPIs (top view)",
        "<div class='small-muted'>Per-course KPI cards from latest snapshots.</div>",
        muted=True,
    )
    cols = st.columns(len(course_cards), gap="large")
    for idx, row in enumerate(sorted(course_cards, key=lambda x: x["course"])):
        with cols[idx]:
            card(
                row["course"],
                (
                    f"<div class='small-muted'>Students: <b>{row['students']}</b></div>"
                    f"<div class='small-muted'>Passed: <b>{row['passed']}</b> ({fmt_num(row['pass_rate'], '%')})</div>"
                    f"<div class='small-muted'>Avg hours: <b>{fmt_num(row['avg_hours'])}</b></div>"
                    f"<div class='small-muted'>Avg grade: <b>{fmt_num(row['avg_grade'])}</b></div>"
                    f"<div class='small-muted'>Median hours: <b>{fmt_num(row['median_hours'])}</b></div>"
                    f"<div class='small-muted'>Inactive: <b>{row['inactive']}</b></div>"
                    f"<div class='small-muted'>Grade delta: <b>{fmt_delta(row['grade_delta'])}</b></div>"
                    f"<div class='small-muted'>Cert rate (passed): <b>{fmt_num(row['cert_rate'], '%')}</b></div>"
                ),
            )

if pass_counts:
    pass_series = pd.Series(pass_counts).sort_index()
    pass_series.index = [COURSE_LABELS.get(c, c) for c in pass_series.index]
    card(
        "Passed students by course (latest snapshot)",
        "<div class='small-muted'>POC is included in total passed as requested.</div>",
        muted=True,
    )
    st.bar_chart(pass_series)

divider()

# Verdict distribution (latest old)
old_latest_dt = latest_by_course.get(COURSE_2425)
if old_latest_dt is not None and pd.notna(old_latest_dt):
    old_latest = df[(df["course_type"] == COURSE_2425) & (df["extracted_at"] == old_latest_dt)]
    verdict_counts = old_latest["verdict"].fillna("").replace("", "Unknown").value_counts()
    card("Verdict distribution (latest OLD)", "<div class='small-muted'>Passed / Failed / Unknown</div>", muted=True)
    st.bar_chart(verdict_counts)
else:
    card("Verdict distribution (latest OLD)", "<div class='small-muted'>No parseable extraction date found for OLD filenames.</div>", muted=True)

divider()

# Evolution over time (counts per course)
time_df = df.dropna(subset=["extracted_at"]).copy()
counts = (time_df.groupby(["extracted_at", "course_type"])
                .size()
                .reset_index(name="count")
                .pivot(index="extracted_at", columns="course_type", values="count")
                .sort_index())

card("Evolution over time (counts)", "<div class='small-muted'>Count of students per extraction date by course folder.</div>", muted=True)
st.line_chart(counts)

divider()

# Distributions
c4, c5 = st.columns(2, gap="large")
with c4:
    card("Hours distribution (numeric only)", "<div class='small-muted'>Across all extractions; non-numeric rows ignored.</div>", muted=True)
    h = df["hours_num"].dropna()
    if len(h) == 0:
        st.info("No numeric hours detected.")
    else:
        st.bar_chart(h.value_counts().sort_index().head(30))

with c5:
    card("Grade distribution (numeric only)", "<div class='small-muted'>Across all extractions; non-numeric rows ignored.</div>", muted=True)
    g = df["grade_num"].dropna()
    if len(g) == 0:
        st.info("No numeric grades detected.")
    else:
        st.bar_chart(g.value_counts().sort_index().head(30))

with st.expander("Preview normalized dataset"):
    st.dataframe(df.head(100), use_container_width=True)
