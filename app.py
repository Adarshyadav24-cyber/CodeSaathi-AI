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

st.set_page_config(page_title="CodeSaathi AI | Python learning studio", page_icon="🌱", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
:root {
  --ink: #172b2b; --muted: #667b79; --green: #087e68; --green-dark: #066553;
  --mint: #eaf5f0; --line: #dfe9e5; --canvas: #f7f9f8; --white: #ffffff;
}
html, body, [class*="css"] { font-family: Inter, "Segoe UI", sans-serif; color: var(--ink); }
.stApp { background: var(--canvas); color: var(--ink); }
[data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"] { color: var(--ink) !important; }
[data-testid="stCaptionContainer"] { color: var(--muted) !important; }
h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { color: var(--ink) !important; letter-spacing: -.035em; }
h1 { font-size: 2.15rem !important; font-weight: 700 !important; }
h2 { font-size: 1.4rem !important; }
h3 { font-size: 1.05rem !important; }
[data-testid="stSidebar"] { background: #f0f5f2; border-right: 1px solid var(--line); }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: var(--muted); }
.brand { display:flex; align-items:center; gap:11px; padding: 4px 0 18px; }
.brand-mark { display:grid; place-items:center; width:40px; height:40px; border-radius:13px; background:var(--green); color:white; font-size:21px; }
.brand-name { font-size:1.13rem; font-weight:750; color:var(--ink); line-height:1.1; }
.brand-sub { color:var(--muted); font-size:.75rem; margin-top:4px; }
.hero { background:linear-gradient(118deg,#e8f4ee 0%,#f2f6e9 100%); border:1px solid #dceae2; border-radius:20px; padding:25px 30px; margin:0 0 22px; }
.eyebrow { color:var(--green); font-size:.72rem; letter-spacing:.13em; text-transform:uppercase; font-weight:750; }
.hero h1 { color:var(--ink) !important; margin:.28rem 0 .3rem; }
.hero p { color:#536a66; font-size:.98rem; margin:0; }
.surface { border:1px solid var(--line); background:var(--white); border-radius:16px; padding:18px 20px; }
.surface-title { color:var(--ink); font-weight:700; font-size:1rem; margin-bottom:4px; }
.muted { color:var(--muted); font-size:.88rem; line-height:1.55; }
.metric { border:1px solid var(--line); border-radius:14px; background:#fff; padding:13px 15px; min-height:82px; }
.metric-label { font-size:.75rem; color:var(--muted); text-transform:uppercase; letter-spacing:.08em; font-weight:700; }
.metric-value { color:var(--ink); font-size:1.1rem; font-weight:700; margin-top:5px; }
.safe-note { border-left:3px solid var(--green); background:#eff7f3; padding:11px 13px; border-radius:0 10px 10px 0; color:#41615a; font-size:.83rem; line-height:1.45; }
div.stButton > button[kind="primary"] { background:var(--green); border-color:var(--green); border-radius:10px; font-weight:650; }
div.stButton > button[kind="primary"]:hover { background:var(--green-dark); border-color:var(--green-dark); }
div.stButton > button { border-radius:10px; }
div[data-baseweb="input"] > div, div[data-baseweb="select"] > div { border-radius:9px; }
[data-testid="stExpander"] { background:#ffffff !important; color:#172b2b !important; border:1px solid var(--line); border-radius:12px; }
[data-testid="stExpander"] summary { color:#172b2b !important; }
[data-testid="stExpander"] [data-testid="stMarkdownContainer"],
[data-testid="stExpander"] [data-testid="stMarkdownContainer"] p,
[data-testid="stExpander"] [data-testid="stMarkdownContainer"] li,
[data-testid="stExpander"] [data-testid="stMarkdownContainer"] strong,
[data-testid="stExpander"] [data-testid="stCaptionContainer"] { color:#263b39 !important; }
@media(max-width:700px) { .hero { padding:20px; } h1 { font-size:1.75rem !important; } }
</style>
""", unsafe_allow_html=True)


def navigate_to_example(example_name: str) -> None:
    st.session_state["editor_code"] = EXAMPLES[example_name]
    st.session_state["sample_choice"] = example_name
    st.session_state["nav_page"] = "Analyze code"


def show_header(eyebrow: str, title: str, subtitle: str) -> None:
    st.markdown(f'<section class="hero"><div class="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{subtitle}</p></section>', unsafe_allow_html=True)


def show_metric(label: str, value: str) -> None:
    st.markdown(f'<div class="metric"><div class="metric-label">{label}</div><div class="metric-value">{value}</div></div>', unsafe_allow_html=True)


with st.sidebar:
    st.markdown('<div class="brand"><div class="brand-mark">✳</div><div><div class="brand-name">CodeSaathi AI</div><div class="brand-sub">Python learning studio</div></div></div>', unsafe_allow_html=True)
    st.markdown("#### WORKSPACE")
    page = st.radio("Workspace", ["Analyze code", "History", "Examples"], key="nav_page", label_visibility="collapsed")
    st.divider()
    st.markdown('<div class="safe-note"><strong>Safe by design</strong><br>Code is parsed and checked. It is never executed on this server.</div>', unsafe_allow_html=True)
    st.caption("Made for learning Python, one fix at a time.")


if page == "Analyze code":
    show_header("PYTHON DEBUGGING · YOUR LEARNING SPACE", "Understand the error. Learn the fix.", "Paste a Python snippet to get a clear explanation, safe checks, and a practical next step.")
    editor, results = st.columns([1.2, 1], gap="large")
    with editor:
        st.markdown("### Code editor")
        st.caption("Paste code or start with a guided example.")
        st.session_state.setdefault("editor_code", "")
        sample_name = st.selectbox("Quick start", ["Choose an example…", *EXAMPLES.keys()], key="sample_choice", on_change=lambda: st.session_state.update(editor_code=EXAMPLES.get(st.session_state.get("sample_choice"), st.session_state.get("editor_code", ""))))
        code = st.text_area("Python code", height=330, placeholder="# Start with a small program\nprint('Hello, world!')", key="editor_code", help="Up to 20,000 characters. Code is parsed and inspected, never run here.", label_visibility="collapsed")
        st.caption(f"{len(code):,} / 20,000 characters")
        submitted = st.button("Review my code  →", type="primary", use_container_width=True)
        if submitted:
            if not code.strip():
                st.warning("Add a few lines of Python or choose an example to begin.")
            else:
                with st.spinner("Reviewing your code…"):
                    analysis = analyze_code(code)
                    explanation = get_explanation(code, analysis)
                result = {"analysis": analysis.to_dict(), "explanation": explanation}
                title = sample_name if sample_name != "Choose an example…" else "Python code review"
                save(DB_PATH, title, code, result)
                st.session_state["latest_result"] = result
                st.session_state["latest_code"] = code
    with results:
        st.markdown("### Review summary")
        result = st.session_state.get("latest_result")
        if not result:
            st.markdown('<div class="surface"><div class="surface-title">Your review will appear here</div><div class="muted">We’ll explain the likely cause, show a correction when we can make one safely, and list a few checks.</div></div>', unsafe_allow_html=True)
            st.markdown("")
            st.markdown('<div class="safe-note">Your program is not run here. “Passed” means a static check passed; suggested test cases are not executed.</div>', unsafe_allow_html=True)
        else:
            details = result["analysis"]
            explanation = result["explanation"]
            syntax_check = next((check for check in details["test_results"] if check["name"] == "Python syntax"), None)
            status = syntax_check["status"] if syntax_check else "Review"
            metric_a, metric_b, metric_c = st.columns(3)
            with metric_a:
                show_metric("Syntax", status)
            with metric_b:
                show_metric("Findings", str(len(details["findings"])))
            with metric_c:
                show_metric("Tutor", explanation["mode"])
            st.markdown("")
            if explanation.get("notice"):
                st.info(explanation["notice"])
            with st.container(border=True):
                st.markdown("#### What may be happening")
                st.markdown(explanation["text"])
            with st.expander("Suggested code and changes", expanded=True):
                st.code(explanation["corrected_code"], language="python")
                st.caption(explanation["changes"])
            with st.expander("Static check details", expanded=True):
                for check in details["test_results"]:
                    icon = "✅" if check["status"] == "Passed" else "⚠️"
                    st.markdown(f"{icon} **{check['name']} · {check['status']}** — {check['detail']}")
                for finding in details["findings"]:
                    where = f" · line {finding['line']}" if finding.get("line") else ""
                    st.markdown(f"**{finding['severity']}: {finding['title']}{where}**  \n{finding['detail']}")
            if details["tests"]:
                with st.expander("Test ideas to try next"):
                    for test in details["tests"]:
                        st.markdown(f"- {test}")
                    st.caption("These are suggestions only; CodeSaathi did not run your program or these tests.")
            if explanation.get("mode") == "AI":
                st.caption("AI suggestions can be imperfect. Review changes before using them.")
elif page == "History":
    entries = list_recent(DB_PATH)
    show_header("YOUR WORKSPACE · SAVED LOCALLY", "A record of what you’ve learned.", "Review earlier snippets and revisit the explanation whenever you need it.")
    query = st.text_input("Search history", placeholder="Search by example title or code…")
    visible = [item for item in entries if query.casefold() in (item["title"] + " " + item["code"]).casefold()]
    st.caption(f"{len(visible)} saved review{'s' if len(visible) != 1 else ''}")
    if not visible:
        st.info("No matching reviews yet. Analyze a snippet to add it to your history.")
    for item in visible:
        with st.expander(f"{item['title']}  ·  {item['created_at']}"):
            st.code(item["code"], language="python")
            st.markdown(item["result"].get("explanation", {}).get("text", ""))
            st.caption("Saved in the local SQLite database on this computer.")
elif page == "Examples":
    show_header("GUIDED PRACTICE · BEGINNER FRIENDLY", "Small examples. Useful lessons.", "Explore a common Python mistake, then open it in the editor and work through the fix.")
    cards = st.columns(2, gap="medium")
    for index, (name, sample) in enumerate(EXAMPLES.items()):
        with cards[index % 2]:
            with st.container(border=True):
                st.markdown(f"#### {name}")
                st.code(sample, language="python")
                st.button("Open in code editor  →", key=f"open_example_{index}", on_click=navigate_to_example, args=(name,), use_container_width=True)
