# app.py
#
# Web interface for the report generator, built with Streamlit.
# This doesn't change the underlying logic - analysis.py,
# report_generator.py, and report_config.py all stay the same.
#
# This deployed version runs on a small SYNTHETIC demo dataset
# (synthetic_data.py) instead of a file upload. The real Bisoprolol
# dataset from the assessment can't be redistributed publicly, and a
# generic "upload any file" option would break since analysis.py
# expects specific ICSR-style column names - so this demo shows the
# real pipeline working end to end on clearly-fake sample data instead.

import streamlit as st

from analysis import run_full_analysis
from report_generator import build_section
from report_config import PADER_SECTIONS
from synthetic_data import generate_demo_dataframe

st.set_page_config(page_title="PADER Report Generator", page_icon="📋", layout="wide")

st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: 700; margin-bottom: 0.2rem; }
    .sub-header { color: #6b7280; font-size: 1rem; margin-bottom: 1rem; }
    .stat-card { background: #f8f9fb; border: 1px solid #e5e7eb; border-radius: 10px; padding: 1rem 1.2rem; text-align: center; }
    .stat-number { font-size: 1.8rem; font-weight: 700; color: #111827; }
    .stat-label { color: #6b7280; font-size: 0.85rem; }
    .grounding-note { background: #eef2ff; border-left: 4px solid #6366f1; padding: 0.8rem 1rem; border-radius: 6px; font-size: 0.9rem; margin: 1rem 0; }
    .demo-note { background: #fff7ed; border-left: 4px solid #f97316; padding: 0.8rem 1rem; border-radius: 6px; font-size: 0.9rem; margin: 1rem 0; }
    div[data-testid="stExpander"] { border: 1px solid #e5e7eb; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">📋 PADER Report Generator</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Turns an adverse event dataset into a structured, evidence-based '
    'safety report — every number is calculated in plain Python, the AI only writes narrative '
    'text from numbers it\'s already been given.</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="grounding-note">🔒 <b>Grounding guarantee:</b> the AI never sees the raw dataset '
    '— only small, pre-calculated numbers for the specific section it\'s writing.</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="demo-note">🧪 <b>This demo runs on a small synthetic sample dataset</b> (made up by me, '
    'not real data) — the original assessment dataset can\'t be redistributed publicly. The pipeline '
    'itself is exactly the same one used on the real dataset.</div>',
    unsafe_allow_html=True,
)

for key, default in [("results", None), ("sections", {}), ("approvals", {}), ("final_report", None)]:
    if key not in st.session_state:
        st.session_state[key] = default

# ------------------------------------------------------------------
# Step 1: Run on the built-in demo dataset
# ------------------------------------------------------------------
st.markdown("### 1️⃣ Run the pipeline")

if st.button("▶️ Generate demo report from synthetic sample data", type="primary"):
    with st.spinner("Cleaning data and calculating numbers..."):
        df = generate_demo_dataframe()
        tmp_path = "demo_data_temp.xlsx"
        df.to_excel(tmp_path, index=False)
        try:
            st.session_state.results = run_full_analysis(tmp_path)
            st.session_state.sections = {}
            st.session_state.approvals = {}
            st.session_state.final_report = None
        finally:
            import os
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

# ------------------------------------------------------------------
# Step 2: Quick stats overview
# ------------------------------------------------------------------
if st.session_state.results:
    results = st.session_state.results
    cc = results["case_counts"]

    st.markdown("### 📊 At a glance")
    c1, c2, c3, c4 = st.columns(4)
    stats = [
        (cc["total_cases"], "Total Cases"),
        (f"{cc['serious_cases']} ({cc['serious_pct']}%)", "Serious"),
        (results["reactions"]["unique_reaction_terms"], "Unique Reactions"),
        (results["alerts_15day"]["alert_case_count"], "15-Day Alerts"),
    ]
    for col, (num, label) in zip([c1, c2, c3, c4], stats):
        with col:
            st.markdown(
                f'<div class="stat-card"><div class="stat-number">{num}</div>'
                f'<div class="stat-label">{label}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("### 2️⃣ Generate & review each section")
    st.caption("Nothing is added to the final report until you approve it.")

    total_sections = len(PADER_SECTIONS)
    done_sections = len(st.session_state.sections)
    st.progress(done_sections / total_sections, text=f"{done_sections} of {total_sections} sections generated")

    for section_def in PADER_SECTIONS:
        key = section_def["key"]

        if key not in st.session_state.sections:
            left, right = st.columns([4, 1])
            with left:
                st.markdown(f"**{section_def['title']}** — not generated yet")
            with right:
                if st.button("Generate", key=f"gen_{key}", use_container_width=True):
                    with st.spinner("Writing..."):
                        st.session_state.sections[key] = build_section(section_def, results)
                    st.rerun()
        else:
            status = st.session_state.approvals.get(key, "pending")
            icon = {"approved": "✅", "flagged": "🚩", "pending": "🕒"}[status]

            with st.expander(f"{icon} {section_def['title']}", expanded=(status == "pending")):
                st.markdown(st.session_state.sections[key])
                b1, b2, b3 = st.columns([1, 1, 3])
                with b1:
                    if st.button("✅ Approve", key=f"approve_{key}", use_container_width=True):
                        st.session_state.approvals[key] = "approved"
                        st.rerun()
                with b2:
                    if st.button("🚩 Flag", key=f"flag_{key}", use_container_width=True):
                        st.session_state.approvals[key] = "flagged"
                        st.rerun()

    all_generated = all(s["key"] in st.session_state.sections for s in PADER_SECTIONS)

    if all_generated:
        st.markdown("### 3️⃣ Finalize")
        if st.button("📄 Assemble final report", type="primary"):
            title = f"# Periodic Adverse Drug Experience Report (PADER)\n## {results['reporting_period']['product']}\n\n"
            parts = []
            for section_def in PADER_SECTIONS:
                key = section_def["key"]
                content = st.session_state.sections[key]
                if st.session_state.approvals.get(key) == "flagged":
                    content = f"[FLAGGED FOR REVIEW]\n\n{content}"
                parts.append(content)
            st.session_state.final_report = title + "\n".join(parts)

        if st.session_state.final_report:
            st.success("Report assembled.")
            st.download_button(
                "⬇️ Download report_output.md",
                data=st.session_state.final_report,
                file_name="report_output.md",
                mime="text/markdown",
                type="primary",
            )
            with st.expander("Preview final report", expanded=False):
                st.markdown(st.session_state.final_report)
else:
    st.info("Click the button above to generate a demo report from synthetic sample data.")