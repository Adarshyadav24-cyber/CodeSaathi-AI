"""Optional AI explanations with a safe built-in fallback."""

from __future__ import annotations

import os

from .analyzer import Analysis, demo_correction, explain_error


def get_explanation(source: str, analysis: Analysis) -> dict[str, str]:
    """Return a simple explanation. API failures gracefully fall back to demo mode."""
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=key, timeout=20.0, max_retries=1)
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                temperature=0.2,
                messages=[
                    {"role": "system", "content": "You are CodeSaathi, a patient Python tutor. Explain in simple English. Point to the exact line number and expression when the analysis provides them. Describe what Python is trying to do, why it fails, and show a corrected example. Do not claim code was run. Do not invent a line number. Return short labeled sections: Where the error is, Why it happens, How to fix it."},
                    {"role": "user", "content": f"Analysis: {analysis.to_dict()}\nPython code:\n{source[:12000]}"},
                ],
            )
            text = response.choices[0].message.content
            if text:
                corrected, changes = demo_correction(source, analysis)
                return {"mode": "AI", "text": text, "corrected_code": corrected, "changes": changes}
        except Exception as exc:
            fallback = _demo(source, analysis)
            fallback["mode"] = "Demo fallback"
            fallback["notice"] = f"The AI service was unavailable, so built-in explanations are shown ({type(exc).__name__})."
            return fallback
    return _demo(source, analysis)


def _demo(source: str, analysis: Analysis) -> dict[str, str]:
    corrected, changes = demo_correction(source, analysis)
    if analysis.syntax_error:
        cause, fix = explain_error(analysis.syntax_error)
        where = f"Line {analysis.line}" if analysis.line else "Python syntax"
    else:
        issue = next((f for f in analysis.findings if f.severity in {"Error", "Check"}), None)
        if issue:
            cause = issue.detail
            where = f"Line {issue.line}" if issue.line else "No specific line identified"
            if issue.title == "List index is out of range":
                fix = "Check the list length before using this index, or choose an index that exists."
            elif issue.title == "Division by zero":
                fix = "Check that the divisor is not zero before performing the division."
            elif issue.title == "Possible undefined name":
                fix = "Compare the spelling here with the variable assignment above; Python treats different spellings as different names."
            else:
                fix = "Check the name or value on this line and compare it with its definition."
        else:
            where = "No specific error found"
            cause, fix = ("The code has valid Python syntax and no obvious issue was found by the basic checks.", "Try the suggested test cases in your own trusted Python environment and compare the results with your goal.")
    return {"mode": "Demo", "text": f"**Where the error is:** {where}\n\n**Why it happens:** {cause}\n\n**How to fix it:** {fix}", "corrected_code": corrected, "changes": changes}
