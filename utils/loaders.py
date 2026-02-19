from __future__ import annotations
import re
import unicodedata
from pathlib import Path
from typing import Optional, List

import pandas as pd
import streamlit as st

DATA_ROOT = Path("data/extractions")
STUDENT_DATA_PATH = Path("data/Student_Data/Student_data.xlsx")
CERTIFIED_STUDENTS_PATH = Path("data/Student_Data/Certified_Students.xlsx")

COL_TOKENS = {
    "email": ["email"],
    "student_id": ["student id", "studentid", "id etudiant", "idetudiant", "id"],
    "first_name": ["first name", "prénom", "prenom"],
    "last_name": ["last name", "nom"],
    "hours": ["hours in course", "hoursincourse", "hours", "time spent", "temps passe", "heures"],
    "grade": ["overall grade", "overallgrade", "final grade", "grade finale", "grade"],
    "verdict": ["verdict", "outcome", "result", "pass", "fail"],
}

EMAIL_RE = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", flags=re.IGNORECASE)

def normalize_email(x: str) -> str:
    s = str(x or "").replace("\u00A0", " ").strip().lower()
    if not s:
        return ""
    m = EMAIL_RE.search(s)
    return m.group(0).lower() if m else ""


def first_email_in_row(row: pd.Series) -> str:
    for v in row.tolist():
        e = normalize_email(v)
        if e:
            return e
    return ""

def _normalize_text(s: str) -> str:
    raw = str(s or "").strip().lower()
    raw = unicodedata.normalize("NFKD", raw)
    no_accents = "".join(ch for ch in raw if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "", no_accents)


def _detect_header_row(raw_df: pd.DataFrame, max_scan_rows: int = 30) -> int:
    if raw_df.empty:
        return 0

    expected = {
        "lastname",
        "firstname",
        "studentid",
        "email",
        "verdict",
        "hoursincourse",
        "overallgrade",
    }

    max_rows = min(max_scan_rows, len(raw_df))
    best_idx = 0
    best_score = -1

    for i in range(max_rows):
        vals = [str(v).strip() for v in raw_df.iloc[i].tolist()]
        norm_vals = [_normalize_text(v) for v in vals if v and v.lower() != "nan"]
        if not norm_vals:
            continue

        row_join = " ".join(norm_vals)
        score = 0
        for token in expected:
            if token in row_join:
                score += 1

        if score > best_score:
            best_score = score
            best_idx = i

    return best_idx

def find_col_by_tokens(cols: List[str], tokens: List[str]) -> Optional[str]:
    cols_l = [str(c).lower() for c in cols]
    cols_n = [_normalize_text(c) for c in cols]
    tokens_n = [_normalize_text(t) for t in tokens]
    for t in tokens:
        for i, c in enumerate(cols_l):
            if t in c:
                return cols[i]
    for t in tokens_n:
        if not t:
            continue
        for i, c in enumerate(cols_n):
            if t in c:
                return cols[i]
    return None

def infer_year_from_course_month(course_code: str, month: int) -> int:
    """
    Infer calendar year from a Blackboard academic code and month.
    Example:
      2425... -> Oct-Dec 2024, Jan-Sep 2025
      2526... -> Oct-Dec 2025, Jan-Sep 2026
    """
    m = re.match(r"^(\d{2})(\d{2})", (course_code or ""))
    if not m:
        return pd.Timestamp.utcnow().year

    start_year = 2000 + int(m.group(1))
    end_year = 2000 + int(m.group(2))
    return start_year if month >= 10 else end_year


def parse_extraction_date_from_filename(name: str, course_code: str = "") -> Optional[pd.Timestamp]:
    """
    Parses suffix patterns like:
      ..._27_Janv.xlsx
      ..._27_Janv (1).xlsx
      ..._25_Sept.xlsx
      ..._27_Janv_2026.xlsx  (optional year)
    If year missing, infer from the course code + month (academic year logic).
    """
    m = re.search(r"_(\d{1,2})_([A-Za-zÀ-ÿ]+)(?:_(\d{4}))?\s*(?:\(\d+\))?\.xlsx$", name)
    if not m:
        return None

    day = int(m.group(1))
    mon_raw = m.group(2).lower()
    year = int(m.group(3)) if m.group(3) else None

    mon_map = {
        "jan":1, "janv":1, "janvier":1, "january":1,
        "fev":2, "fév":2, "fevr":2, "février":2, "fevrier":2, "feb":2, "february":2,
        "mar":3, "mars":3, "march":3,
        "avr":4, "avril":4, "apr":4, "april":4,
        "mai":5, "may":5,
        "juin":6, "jun":6, "june":6,
        "juil":7, "juillet":7, "jul":7, "july":7,
        "aout":8, "août":8, "aug":8, "august":8,
        "sept":9, "sep":9, "september":9, "septembre":9,
        "oct":10, "october":10, "octobre":10,
        "nov":11, "november":11, "novembre":11,
        "dec":12, "déc":12, "decembre":12, "décembre":12, "december":12,
    }

    mon_norm = (mon_raw
                .replace("é","e").replace("û","u").replace("ô","o")
                .replace("à","a").replace("ù","u").replace("î","i"))
    month = mon_map.get(mon_norm)
    if not month:
        return None

    if year is None:
        year = infer_year_from_course_month(course_code, month)

    return pd.Timestamp(year=year, month=month, day=day)

def _get_extraction_version() -> float:
    if not DATA_ROOT.exists():
        return 0.0
    files = list(DATA_ROOT.rglob("*.xlsx"))
    if not files:
        return 0.0
    return max([p.stat().st_mtime for p in files], default=0.0)


@st.cache_data
def _load_all_extractions_cached(_version: float) -> pd.DataFrame:
    """
    Loads all .xlsx under data/extractions/<COURSE_CODE>/ into a normalized table:
    - course_type: folder name (Blackboard code)
    - extracted_at: parsed from filename (or NaT)
    """
    if not DATA_ROOT.exists():
        return pd.DataFrame(columns=[
            "course_type","file_name","extracted_at","email_norm","student_id",
            "first_name","last_name","hours","grade","verdict"
        ])

    course_folders = [f for f in DATA_ROOT.iterdir() if f.is_dir()]

    frames = []
    for folder in course_folders:
        course_code = folder.name
        for path in sorted(folder.glob("*.xlsx")):
            raw = pd.read_excel(path, sheet_name=0, header=None, dtype=str).fillna("")
            header_idx = _detect_header_row(raw)
            header_vals = [str(c).strip() for c in raw.iloc[header_idx].tolist()]
            df = raw.iloc[header_idx + 1 :].copy()
            df.columns = header_vals
            df = df.loc[:, [c for c in df.columns if str(c).strip() != ""]]
            df.columns = [str(c).strip() for c in df.columns]

            c_email = find_col_by_tokens(df.columns.tolist(), COL_TOKENS["email"])
            c_id = find_col_by_tokens(df.columns.tolist(), COL_TOKENS["student_id"])
            c_fn = find_col_by_tokens(df.columns.tolist(), COL_TOKENS["first_name"])
            c_ln = find_col_by_tokens(df.columns.tolist(), COL_TOKENS["last_name"])
            c_hours = find_col_by_tokens(df.columns.tolist(), COL_TOKENS["hours"])
            c_grade = find_col_by_tokens(df.columns.tolist(), COL_TOKENS["grade"])
            c_verdict = find_col_by_tokens(df.columns.tolist(), COL_TOKENS["verdict"])

            extracted_at = parse_extraction_date_from_filename(path.name, course_code=course_code)

            email_series = (
                df[c_email].map(lambda v: normalize_email(str(v)))
                if c_email
                else df.apply(first_email_in_row, axis=1)
            )

            out = pd.DataFrame({
                "course_type": course_code,
                "file_name": path.name,
                "extracted_at": extracted_at,
                "email_norm": email_series,
                "student_id": df[c_id].astype(str).str.strip() if c_id else "",
                "first_name": df[c_fn].astype(str).str.strip() if c_fn else "",
                "last_name": df[c_ln].astype(str).str.strip() if c_ln else "",
                "hours": df[c_hours].astype(str).str.strip() if c_hours else "",
                "grade": df[c_grade].astype(str).str.strip() if c_grade else "",
                "verdict": df[c_verdict].astype(str).str.strip() if c_verdict else "",
            })

            out = out[(out["email_norm"] != "") | (out["student_id"] != "")]
            frames.append(out)

    if not frames:
        return pd.DataFrame(columns=[
            "course_type","file_name","extracted_at","email_norm","student_id",
            "first_name","last_name","hours","grade","verdict"
        ])

    all_df = pd.concat(frames, ignore_index=True)
    all_df["extracted_at"] = pd.to_datetime(all_df["extracted_at"], errors="coerce")
    return all_df


def load_all_extractions() -> pd.DataFrame:
    return _load_all_extractions_cached(_get_extraction_version())


def normalize_student_id_e(x: str) -> str:
    s = str(x or "").strip().lower().replace(" ", "")
    if not s:
        return ""
    if s.startswith("e"):
        return s
    if s.isdigit():
        return f"e{s}"
    return s


def _get_student_data_version() -> float:
    if not STUDENT_DATA_PATH.exists():
        return 0.0
    return STUDENT_DATA_PATH.stat().st_mtime


@st.cache_data
def _load_student_data_cached(_version: float) -> pd.DataFrame:
    cols = ["student_id_e", "email_norm", "campus", "program", "promotion", "chatgpt_status"]
    if not STUDENT_DATA_PATH.exists():
        return pd.DataFrame(columns=cols)

    df = pd.read_excel(STUDENT_DATA_PATH, sheet_name=0, dtype=str).fillna("")
    df.columns = [str(c).strip() for c in df.columns]

    c_id = find_col_by_tokens(df.columns.tolist(), ["student_id", "student id", "id etudiant", "id étudiant", "id"])
    c_email = find_col_by_tokens(df.columns.tolist(), ["email", "mail"])
    c_campus = find_col_by_tokens(df.columns.tolist(), ["campus"])
    c_program = find_col_by_tokens(df.columns.tolist(), ["program", "programme"])
    c_promo = find_col_by_tokens(df.columns.tolist(), ["promotion", "cohort"])
    c_chatgpt = find_col_by_tokens(df.columns.tolist(), ["chatgpt", "chat gpt", "license", "licence"])

    out = pd.DataFrame({
        "student_id_e": df[c_id].map(normalize_student_id_e) if c_id else "",
        "email_norm": df[c_email].map(normalize_email) if c_email else "",
        "campus": df[c_campus].astype(str).str.strip() if c_campus else "",
        "program": df[c_program].astype(str).str.strip() if c_program else "",
        "promotion": df[c_promo].astype(str).str.strip() if c_promo else "",
        "chatgpt_status": df[c_chatgpt].astype(str).str.strip() if c_chatgpt else "",
    })
    out = out[(out["student_id_e"] != "") | (out["email_norm"] != "")]
    return out


def load_student_data() -> pd.DataFrame:
    return _load_student_data_cached(_get_student_data_version())


def _get_certified_students_version() -> float:
    if not CERTIFIED_STUDENTS_PATH.exists():
        return 0.0
    return CERTIFIED_STUDENTS_PATH.stat().st_mtime


@st.cache_data
def _load_certified_students_cached(_version: float) -> list[str]:
    if not CERTIFIED_STUDENTS_PATH.exists():
        return []

    df = pd.read_excel(CERTIFIED_STUDENTS_PATH, sheet_name=0, dtype=str).fillna("")
    df.columns = [str(c).strip() for c in df.columns]

    c_email = find_col_by_tokens(df.columns.tolist(), ["email", "mail"])
    if c_email:
        emails = df[c_email].map(normalize_email)
    else:
        emails = df.apply(first_email_in_row, axis=1)

    emails = [e for e in emails.tolist() if e]
    return sorted(set(emails))


def load_certified_emails() -> set[str]:
    return set(_load_certified_students_cached(_get_certified_students_version()))
