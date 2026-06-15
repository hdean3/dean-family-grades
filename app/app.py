import streamlit as st
import pandas as pd
import json
import os
from pathlib import Path

# --- 1. STUDENT MANIFEST & PATHS ---
DATA_ROOT  = Path(__file__).parent.parent / "data"
STUD_ROOT  = DATA_ROOT / "students"
STUD_CFG   = STUD_ROOT / "students.json"

def load_student_manifest():
    if STUD_CFG.exists():
        with open(STUD_CFG) as f:
            return json.load(f)
    return {}

manifest = load_student_manifest()
student_ids = list(manifest.keys()) if manifest else ["ben"]

st.set_page_config(page_title="ScholarDash — Dean Family", layout="wide")

# Sidebar: student selector (always visible so you can switch)
st.sidebar.header("👨‍👩‍👧‍👦 ScholarDash")
selected_id = st.sidebar.selectbox(
    "Student",
    student_ids,
    format_func=lambda sid: manifest[sid]["name"] if sid in manifest else sid.title(),
    index=0,
)

cfg          = manifest.get(selected_id, {})
STUDENT_NAME = cfg.get("name", selected_id.title())
rates        = cfg.get("rates", {"A+": 150.0, "A": 125.0, "A-": 100.0,
                                  "B+": 75.0,  "B": 50.0,  "B-": 25.0})
GMU_THRESHOLD = cfg.get("gmu_threshold")  # None for younger kids

VCCS_SCHOOLS = [
    {"school": "George Mason University",  "min_gpa": 3.0, "notes": "NOVA→GMU transfer. Same destination."},
    {"school": "James Madison University", "min_gpa": 3.0, "notes": "Most programs."},
    {"school": "Virginia Commonwealth",    "min_gpa": 3.0, "notes": "Most programs."},
    {"school": "Old Dominion University",  "min_gpa": 3.0, "notes": "Most programs."},
    {"school": "Virginia Tech",            "min_gpa": 3.2, "notes": "Higher bar; competitive majors may require more."},
    {"school": "Radford University",       "min_gpa": 2.5, "notes": "Minimum threshold."},
    {"school": "Christopher Newport",      "min_gpa": 3.0, "notes": "Most programs."},
    {"school": "UVA",                      "min_gpa": None, "notes": "NOT covered by VCCS GAA."},
]


# --- 2. LCPS GRADING SCALE ---
# A+ = 4.3 in LCPS (verified from official transcript — not the standard 4.0)
def score_to_letter_and_gpa(score):
    if score >= 98: return "A+", 4.3
    if score >= 93: return "A",  4.0
    if score >= 90: return "A-", 3.7
    if score >= 87: return "B+", 3.3
    if score >= 83: return "B",  3.0
    if score >= 80: return "B-", 2.7
    if score >= 77: return "C+", 2.3
    if score >= 73: return "C",  2.0
    if score >= 70: return "C-", 1.7
    if score >= 67: return "D+", 1.3
    if score >= 63: return "D",  1.0
    if score >= 60: return "D-", 0.7
    return "F", 0.0


def get_grade_info(score):
    letter, gpa_pts = score_to_letter_and_gpa(score)
    earnings = rates.get(letter, 0.0)
    return letter, earnings, gpa_pts


def row_color(score, missing):
    if missing > 0: return '#d3d3d3'
    if score >= 90: return '#d4edda'
    if score >= 80: return '#cce5ff'
    if score >= 70: return '#fff3cd'
    return '#ffe0e0'


st.markdown(
    "<style>.stMetric { border-left: 5px solid #800000; } h1 { color: #000080; }</style>",
    unsafe_allow_html=True,
)


# --- 3. DATA LOADING (student-aware) ---
def student_data_path(filename):
    """Prefer data/students/{id}/filename; fall back to data/filename for Ben."""
    student_path = STUD_ROOT / selected_id / filename
    if student_path.exists():
        return student_path
    legacy = DATA_ROOT / filename
    if legacy.exists():
        return legacy
    return None


def load_data():
    path = student_data_path("grades.json")
    if not path:
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        return pd.DataFrame(data) if data else None
    except Exception:
        return None


def load_history():
    path = student_data_path("grade_history.json")
    if not path:
        return []
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return []


def compute_cumulative_gpa(history, weighted=False):
    total_pts = 0.0
    total_cred = 0.0
    for year in history:
        for c in year.get("courses", []):
            score = c.get("score", 0)
            if score == 0:
                continue
            credits = c.get("credits", 1.0)
            _, pts = score_to_letter_and_gpa(score)
            if weighted and c.get("honors", False):
                pts = min(pts + 0.5, 5.0)
            total_pts += pts * credits
            total_cred += credits
    if total_cred == 0:
        return None, 0
    return round(total_pts / total_cred, 3), total_cred


def compute_year_gpa(courses, weighted=False):
    total_pts = 0.0
    total_cred = 0.0
    for c in courses:
        score = c.get("score", 0)
        if score == 0:
            continue
        credits = c.get("credits", 1.0)
        _, pts = score_to_letter_and_gpa(score)
        if weighted and c.get("honors", False):
            pts = min(pts + 0.5, 5.0)
        total_pts += pts * credits
        total_cred += credits
    if total_cred == 0:
        return None
    return round(total_pts / total_cred, 3)


# --- 4. RENDER ---
current_df = load_data()
history    = load_history()
cum_gpa_uw, total_credits = compute_cumulative_gpa(history, weighted=False)
cum_gpa_w,  _             = compute_cumulative_gpa(history, weighted=True)

st.title(f"\U0001f393 {STUDENT_NAME}: ScholarDash")

if current_df is None or current_df.empty:
    st.info(f"No current grades loaded for {STUDENT_NAME}. "
            f"Add scores to `data/students/{selected_id}/grades.json` to get started.")
    if history:
        # Still show historical data even if no current-semester grades
        pass
    else:
        st.stop()

if current_df is not None and not current_df.empty:
    if 'missing' not in current_df.columns:
        current_df['missing'] = 0

    # ── Sidebar: Motivation Simulator ─────────────────────────────────────────
    st.sidebar.markdown("---")
    st.sidebar.header("\U0001f680 Motivation Simulator")
    st.sidebar.caption("Drag right from your current grade to see what a bump earns:")
    sim_scores = {}
    for _, row in current_df.iterrows():
        base        = int(row['score'])
        base_letter, _, _ = get_grade_info(base)
        lbl         = row['subject'][:20] + ('…' if len(row['subject']) > 20 else '')
        sim_scores[row['subject']] = st.sidebar.slider(
            f"{lbl}  [{base_letter} · {base}]",
            min_value=max(60, base - 5),
            max_value=100,
            value=base,
            key=f"sim_{row['subject']}",
        )

    if selected_id == "ben":
        st.sidebar.markdown("---")
        st.sidebar.warning("\U0001f9b7 **Reminder**: Ben, put the bands on your braces!")

    current_df['Display Score'] = (
        current_df['subject'].map(sim_scores).fillna(current_df['score']).clip(upper=100).astype(int)
    )
    grade_data = current_df['Display Score'].apply(get_grade_info)
    current_df['Grade'], current_df['Earnings'], current_df['Points'] = zip(*grade_data)

    # ── Summary metrics ────────────────────────────────────────────────────────
    avg_score   = current_df['score'].mean()
    _, _, gpa_v = get_grade_info(avg_score)
    gpa_label   = "Cumulative GPA"

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Current Earnings", f"${current_df['Earnings'].sum():,.2f}")
    m2.metric("Max Potential",    f"${sum(rates.values()):,.2f}")
    m3.metric("This Semester",    f"{gpa_v:.2f}")
    if cum_gpa_uw:
        m4.metric(gpa_label, f"{cum_gpa_uw:.3f}",
                  delta=f"{'✅' if (GMU_THRESHOLD and cum_gpa_uw >= GMU_THRESHOLD) else ('⚠️ ' + str(GMU_THRESHOLD) + ' GMU' if GMU_THRESHOLD else '')}")
        m5.metric("Weighted GPA", f"{cum_gpa_w:.3f}", help="Weighted: Honors +0.5, AP +1.0")
    else:
        m4.metric("Cumul. GPA", "—")
        m5.metric("GMU Target", f"{GMU_THRESHOLD}" if GMU_THRESHOLD else "N/A")

    # ── Reward Breakdown ───────────────────────────────────────────────────────
    st.subheader("\U0001f4b0 Reward Breakdown — Current Semester")
    key_items = [
        ('#d4edda', 'A &nbsp;(90+)'), ('#cce5ff', 'B &nbsp;(80–89)'),
        ('#fff3cd', 'C &nbsp;(70–79)'), ('#ffe0e0', 'D / F &nbsp;(&lt;70)'),
        ('#d3d3d3', '⚠️&nbsp; Missing Work'),
    ]
    key_cols = st.columns(len(key_items))
    for col, (bg, label) in zip(key_cols, key_items):
        col.markdown(
            f'<div style="background:{bg};padding:6px 10px;border-radius:4px;'
            f'text-align:center;font-size:0.82em;border:1px solid #bbb">{label}</div>',
            unsafe_allow_html=True,
        )
    st.markdown("<br>", unsafe_allow_html=True)

    missing_vals   = current_df['missing'].values
    display_scores = current_df['Display Score'].values

    def highlight_row(row):
        color = row_color(display_scores[row.name], missing_vals[row.name])
        return [f'background-color: {color}'] * len(row)

    st.dataframe(
        current_df[['subject', 'Display Score', 'Grade', 'Earnings']]
        .style.apply(highlight_row, axis=1).format({"Earnings": "${:,.2f}"}),
        hide_index=True,
    )
    st.markdown("---")

# ── Grade History ──────────────────────────────────────────────────────────────
if history:
    st.header("\U0001f4ca Grade History & Cumulative GPA")

    for year_data in history:
        courses = year_data.get("courses", [])
        label   = year_data["label"]
        note    = year_data.get("note", "")

        if not courses:
            st.subheader(f"{label} — *grades not yet entered*")
            if note:
                st.caption(f"📋 {note}")
            continue

        yr_gpa_uw = compute_year_gpa(courses, weighted=False)
        yr_gpa_w  = compute_year_gpa(courses, weighted=True)
        gpa_str   = f"Unweighted: {yr_gpa_uw:.3f}  |  Weighted: {yr_gpa_w:.3f}" if yr_gpa_uw else "—"
        st.subheader(f"{label} — GPA {gpa_str}")

        rows = []
        for c in courses:
            score = c.get("score", 0)
            if score == 0:
                continue
            letter, pts = score_to_letter_and_gpa(score)
            w_pts = min(pts + 0.5, 5.0) if c.get("honors") else pts
            rows.append({
                "Subject":  c["subject"],
                "Score":    c["note"] if c.get("note") else score,
                "Grade":    letter,
                "Credits":  c.get("credits", 1.0),
                "GPA (UW)": pts,
                "GPA (W)":  w_pts,
                "Honors":   "H" if c.get("honors") else "",
            })
        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df.style.format({"GPA (UW)": "{:.1f}", "GPA (W)": "{:.1f}"}),
                         hide_index=True)

    st.markdown("---")
    if cum_gpa_uw:
        if GMU_THRESHOLD:
            gmu_gap = GMU_THRESHOLD - cum_gpa_uw
            if gmu_gap <= 0:
                st.success(f"✅ **Cumulative GPA (UW): {cum_gpa_uw:.3f}** — Meets GMU {GMU_THRESHOLD} guaranteed admission threshold!")
            else:
                st.warning(
                    f"⚠️ **Cumulative GPA (UW): {cum_gpa_uw:.3f}** — "
                    f"**{gmu_gap:.3f} pts below GMU {GMU_THRESHOLD} threshold.** Senior year is critical."
                )
        st.info(f"Weighted GPA (Honors/AP boost): **{cum_gpa_w:.3f}** across {total_credits:.1f} credits")

    st.markdown("---")

# ── GMU + VCCS sections (HS students only) ────────────────────────────────────
if GMU_THRESHOLD and history:
    st.header("\U0001f3eb GMU Guaranteed Admission — Direct Freshman Path")
    st.markdown(
        f"**GMU guarantees freshman admission to VA HS students with cumulative GPA ≥ {GMU_THRESHOLD} "
        f"by end of junior year.** Ben just finished junior year — this is the evaluation point. "
        f"Official LCPS transcript GPA as of Feb 12, 2026 (mid-junior year): **3.18 / 16.50 credits.**"
    )

    if cum_gpa_uw:
        gap = GMU_THRESHOLD - cum_gpa_uw
        if gap <= 0:
            st.success(f"✅ **Qualifies: {cum_gpa_uw:.3f} ≥ {GMU_THRESHOLD}**")
        else:
            est_senior_credits = 6.5
            pts_needed = GMU_THRESHOLD * (total_credits + est_senior_credits) - (cum_gpa_uw * total_credits)
            needed_senior_gpa = pts_needed / est_senior_credits
            st.error(
                f"❌ **Does not qualify: {cum_gpa_uw:.3f} vs. {GMU_THRESHOLD} needed "
                f"(gap: {gap:.3f} pts)**"
            )
            st.info(
                f"To reach {GMU_THRESHOLD} cumulative after senior year (~{est_senior_credits} credits): "
                f"needs **{needed_senior_gpa:.2f} GPA senior year** — essentially straight A's. "
                f"NOVA → GMU transfer (3.0 at NOVA) is the more realistic path."
            )

    st.markdown("---")

    st.header("\U0001f4cb VCCS Guaranteed Admission — Fallback via NOVA")
    st.caption(
        "Enroll at NOVA → complete AA/AS → transfer to a 4-year VA school with guaranteed admission. "
        "The GPA below applies to credits earned AT NOVA, not HS GPA."
    )

    gaa_rows = []
    for s in VCCS_SCHOOLS:
        if s["min_gpa"] is None:
            req, status = "N/A", "❌ Not available"
        else:
            req    = f"{s['min_gpa']:.1f}"
            status = "✅ Achievable" if s["min_gpa"] <= 3.2 else "⚠️ Competitive"
        gaa_rows.append({"School": s["school"], "Min GPA at NOVA": req,
                         "Status": status, "Notes": s["notes"]})
    st.dataframe(pd.DataFrame(gaa_rows), hide_index=True, use_container_width=True)
    st.caption(
        "GMU via VCCS needs only 3.0 at NOVA — easier bar than the 3.25 direct HS admission threshold."
    )

    st.markdown("---")

# ── Certification Payouts ──────────────────────────────────────────────────────
if selected_id == "ben":
    st.header("\U0001f3c6 Certification Payouts")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("CCNA Bonus")
        st.metric("Potential", "$1,000.00")
        st.progress(0.1, text="Coursework Started")
    with c2:
        st.subheader("Security+ Bonus")
        st.metric("Potential", "$1,000.00")
        st.progress(0.0, text="Queued")
