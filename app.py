"""Streamlit interface for CodeSaathi AI."""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from codesaathi.ai import get_explanation
from codesaathi.analyzer import EXAMPLES, analyze_code
from codesaathi.history import list_recent, save


ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("CODESAATHI_DB", str(ROOT / "codesaathi_history.db")))

st.set_page_config(page_title="CodeSaathi AI · Python tutor", page_icon="🌱", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root { --ink:#18252b; --muted:#64747b; --green:#087e68; --soft:#e9f5f0; }
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
h1,h2,h3 {font-family:'Space Grotesk',sans-serif; color:var(--ink);}
.hero { background:linear-gradient(120deg,#e9f5f0,#f3f7e9); border:1px solid #d9e9e1; border-radius:22px; padding:28px 32px; margin-bottom:20px; }
.eyebrow { color:#087e68; font-size:.75rem; letter-spacing:.12em; text-transform:uppercase; font-weight:700; }
.hero h1 {font-size:2.1rem; margin:.25rem 0;}
.hero p {color:#52656c; margin:0;}
.card {border:1px solid #e2e9e6; background:white; border-radius:16px; padding:18px 20px; margin:.5rem 0;}
.small {color:#64747b; font-size:.9rem;}
div.stButton > button[kind="primary"] {background:#087e68;border-color:#087e68;}
@media(max-width:700px){.hero{padding:20px}.hero h1{font-size:1.7rem}}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## 🌱 CodeSaathi AI")
    page = st.radio("Navigate", ["Analyze code", "History", "Examples"], label_visibility="collapsed")
    st.divider()
    st.caption("A patient Python learning companion")
    st.caption("🔒 Your code is parsed, never executed here.")


def load_selected_example() -> None:
    selected = st.session_state.get("sample_choice")
    if selected in EXAMPLES:
        st.session_state["editor_code"] = EXAMPLES[selected]


def show_header(title: str, sub: str) -> None:
    st.markdown(f'<section class="hero"><div class="eyebrow">Your friendly Python tutor</div><h1>{title}</h1><p>{sub}</p></section>', unsafe_allow_html=True)


if page == "Analyze code":
    show_header("Let’s debug together.", "Paste your Python, and we’ll make the next step easier to understand.")
    left, right = st.columns([1.35, 1], gap="large")
    with left:
        st.session_state.setdefault("editor_code", "")
        sample_name = st.selectbox("Start with an example", ["Choose an example…", *EXAMPLES.keys()], key="sample_choice", on_change=load_selected_example)
        code = st.text_area("Your Python code", height=350, placeholder="# Paste a short Python program here\nprint('Hello, world!')", key="editor_code", help="Maximum 20,000 characters. Code is only parsed and statically checked; it is not run.")
        submitted = st.button("Analyze my code →", type="primary", use_container_width=True)
        if submitted:
            if not code.strip():
                st.warning("Paste some Python code first, or choose an example above.")
            else:
                with st.spinner("Reading your code…"):  # analysis stays local and quick
                    analysis = analyze_code(code)
                    explanation = get_explanation(code, analysis)
                result = {"analysis": analysis.to_dict(), "explanation": explanation}
                save(DB_PATH, f"Analysis · {sample_name if sample_name != 'Choose an example…' else 'Python code'}", code, result)
                st.session_state["latest_result"] = result
                st.session_state["latest_code"] = code
    with right:
        st.markdown("### Your results")
        result = st.session_state.get("latest_result")
        if not result:
            st.markdown('<div class="card"><strong>Ready when you are</strong><p class="small">Your explanation, possible fix, and safe checks will appear here.</p></div>', unsafe_allow_html=True)
            st.markdown("**What happens to your code?**\n\nWe check its Python syntax and look for a few common issues. The code is never executed on this server.")
        else:
            details = result["analysis"]
            explanation = result["explanation"]
            st.caption(f"Explanation mode: {explanation['mode']}")
            if explanation.get("notice"):
                st.info(explanation["notice"])
            st.markdown(explanation["text"])
            st.markdown("#### Suggested corrected code")
            st.code(explanation["corrected_code"], language="python")
            st.caption(explanation["changes"])
            st.markdown("#### Safe check results")
            for check in details["test_results"]:
                icon = "✅" if check["status"] == "Passed" else "⚠️"
                st.markdown(f"{icon} **{check['name']} · {check['status']}** — {check['detail']}")
            for finding in details["findings"]:
                where = f" · line {finding['line']}" if finding.get("line") else ""
                st.markdown(f"**{finding['severity']}: {finding['title']}{where}**\n\n{finding['detail']}")
            if details["tests"]:
                st.markdown("#### Tests to try next")
                for test in details["tests"]:
                    st.markdown(f"- {test}")
                st.caption("These are suggestions. Your code was not executed, so these tests have not been run.")
            if explanation.get("mode") == "AI":
                st.caption("AI explanations may be imperfect. Review suggestions before using them.")
elif page == "History":
    show_header("Your learning trail.", "Revisit previous snippets and the notes you received.")
    entries = list_recent(DB_PATH)
    if not entries:
        st.info("No analyses saved yet. Head to Analyze code to start your first one.")
    for item in entries:
        with st.expander(f"{item['title']}  ·  {item['created_at']}"):
            st.code(item["code"], language="python")
            st.markdown(item["result"].get("explanation", {}).get("text", ""))
            st.caption("Saved locally in the SQLite database on this computer.")
elif page == "Examples":
    show_header("Learn by exploring.", "Choose a small example to see a common beginner mistake and how to think about it.")
    for name, sample in EXAMPLES.items():
        with st.expander(name):
            st.code(sample, language="python")
            st.caption("Open Analyze code and choose this example from the dropdown to see its explanation.")
