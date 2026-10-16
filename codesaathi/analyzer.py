"""Safe, static Python analysis. Submitted code is parsed, never executed."""

from __future__ import annotations

import ast
import re
from dataclasses import asdict, dataclass


@dataclass
class Finding:
    title: str
    detail: str
    line: int | None = None
    severity: str = "Tip"


@dataclass
class Analysis:
    status: str
    syntax_error: str | None
    line: int | None
    findings: list[Finding]
    tests: list[str]
    test_results: list[dict[str, str]]

    def to_dict(self) -> dict:
        data = asdict(self)
        return data


ERROR_HELP = {
    "SyntaxError": ("Python could not understand this line. Check punctuation, quotes, and indentation.", "Read the indicated line and the one just above it; add any missing colon, bracket, or quote."),
    "IndentationError": ("This line is not lined up with the block it belongs to.", "Use consistent four-space indentation inside loops, functions, and conditionals."),
    "NameError": ("A name is being used before Python knows what it means.", "Check spelling and make sure you assign the variable before using it."),
    "TypeError": ("An operation received a kind of value it cannot work with.", "Check the types of the values involved; convert a value when appropriate."),
    "IndexError": ("The code asked for a list position that does not exist.", "Check the list length before indexing, or use a valid index."),
    "KeyError": ("The requested dictionary key is missing.", "Check that the key exists or use dictionary.get() with a default."),
    "ZeroDivisionError": ("A number was divided by zero.", "Check the divisor before dividing and decide what to do when it is zero."),
    "ValueError": ("A value has the right general type but an unusable format or range.", "Validate the value before converting or using it."),
    "AttributeError": ("The value does not have the property or method used here.", "Check the value's type and spelling of the attribute."),
}

EXAMPLES = {
    "Missing colon": "for number in range(3)\n    print(number)",
    "Undefined variable": "name = \"Asha\"\nprint(nam)",
    "Wrong list index": "colors = [\"red\", \"blue\"]\nprint(colors[2])",
    "Divide by zero": "total = 12\ncount = 0\nprint(total / count)",
}


def _static_findings(tree: ast.AST, source: str) -> list[Finding]:
    findings: list[Finding] = []
    defined: set[str] = set()
    used: list[tuple[str, int]] = []
    builtins = set(dir(__builtins__)) if isinstance(__builtins__, dict) else set(dir(__builtins__))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined.add(node.name)
            defined.update(arg.arg for arg in getattr(node.args, "args", []))
        elif isinstance(node, ast.Name):
            if isinstance(node.ctx, (ast.Store, ast.Param)):
                defined.add(node.id)
            elif isinstance(node.ctx, ast.Load):
                used.append((node.id, node.lineno))
    for name, line in used:
        if name not in defined and name not in builtins:
            findings.append(Finding("Possible undefined name", f"'{name}' is used but is not assigned anywhere in this code. Check its spelling.", line, "Check"))
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div) and isinstance(node.right, ast.Constant) and node.right.value == 0:
            findings.append(Finding("Division by zero", "This expression always divides by zero, so it will raise ZeroDivisionError.", node.lineno, "Error"))
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, int) and node.slice.value < 0:
            findings.append(Finding("Negative index", "Negative indexes count from the end of a sequence. Check this is intentional.", node.lineno))
    if not findings:
        findings.append(Finding("No obvious static issues", "Python syntax is valid. Static analysis cannot guarantee the program behaves as intended."))
    return findings


def _tests_for(source: str, tree: ast.AST) -> list[str]:
    tests = ["Try the normal input and confirm the output matches what you expect."]
    if any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in ast.walk(tree)):
        tests.extend(["Call each function with a typical input.", "Try an empty, boundary, or unexpected input for each function."])
    if any(isinstance(n, (ast.For, ast.While)) for n in ast.walk(tree)):
        tests.append("Try an empty collection or a condition that is false immediately.")
    if "input(" in source:
        tests.append("Try valid input, blank input, and text that cannot be converted to the expected type.")
    return list(dict.fromkeys(tests))


def analyze_code(source: str) -> Analysis:
    """Parse code and run conservative AST checks without executing it."""
    if not source or not source.strip():
        return Analysis("empty", "Paste some Python code to get started.", None, [], [], [])
    if len(source) > 20_000:
        return Analysis("invalid", "This demo accepts up to 20,000 characters at a time.", None, [], [], [])
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError) as exc:
        line = getattr(exc, "lineno", None)
        name = "IndentationError" if isinstance(exc, IndentationError) else "SyntaxError"
        message = getattr(exc, "msg", None) or str(exc)
        simple, fix = ERROR_HELP[name]
        return Analysis("syntax_error", f"{name}: {message}", line, [Finding(f"{name} on line {line or '?'}", f"{simple} Suggested fix: {fix}", line, "Error")], [], [{"name": "Python syntax", "status": "Failed", "detail": message}])
    findings = _static_findings(tree, source)
    syntax = {"name": "Python syntax", "status": "Passed", "detail": "The code parsed successfully."}
    static_status = "Review" if any(item.severity in {"Error", "Check"} for item in findings) else "Passed"
    checks = [syntax, {"name": "Static checks", "status": static_status, "detail": f"{len(findings)} note(s); code was not executed."}]
    return Analysis("ok", None, None, findings, _tests_for(source, tree), checks)


def demo_correction(source: str, analysis: Analysis) -> tuple[str, str]:
    """Apply narrowly scoped demonstration fixes; never guess at general repairs."""
    if analysis.status == "syntax_error" and "expected ':'" in (analysis.syntax_error or ""):
        lines = source.splitlines()
        if analysis.line and 0 < analysis.line <= len(lines):
            lines[analysis.line - 1] = lines[analysis.line - 1].rstrip() + ":"
            return "\n".join(lines), "Added the missing colon. Python requires a colon after a for, if, while, class, or function header."
    if re.search(r"\bprint\(nam\)", source) and "name =" in source:
        return re.sub(r"\bprint\(nam\)", "print(name)", source), "Changed 'nam' to 'name' so the spelling matches the variable assignment."
    return source, "No automatic edit was made. Use the suggestions above to update your code, then analyze it again."


def explain_error(error_text: str) -> tuple[str, str]:
    kind = next((name for name in ERROR_HELP if name in (error_text or "")), None)
    if kind:
        return ERROR_HELP[kind]
    return ("I couldn't identify a specific Python error type from this message.", "Read the first traceback line that points to your own file, then check the value and spelling on that line.")
