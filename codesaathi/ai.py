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
                    {"role": "system", "content": "You are CodeSaathi, a patient Python tutor. Explain likely cause and a suggested fix in simple English. Do not run code. Return three short labeled sections: Cause, Fix, Changes."},
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
    else:
        issue = next((f for f in analysis.findings if f.severity in {"Error", "Check"}), None)
        cause, fix = (issue.detail, "Check the name or value on the indicated line and compare it with its definition.") if issue else ("The code has valid Python syntax and no obvious issue was found by the basic checks.", "Run it in your own trusted local environment and compare the result with the goal of your program.")
    return {"mode": "Demo", "text": f"**Likely cause:** {cause}\n\n**Suggested fix:** {fix}", "corrected_code": corrected, "changes": changes}
