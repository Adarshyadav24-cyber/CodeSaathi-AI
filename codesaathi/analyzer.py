"""Safe, static Python analysis. Submitted code is parsed, never executed."""

from __future__ import annotations

import ast
import difflib
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
    numeric_values: dict[str, tuple[int | float, int]] = {}
    list_values: dict[str, int] = {}
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
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, (int, float)):
                numeric_values[node.targets[0].id] = (node.value.value, node.lineno)
            elif isinstance(node.value, ast.List):
                list_values[node.targets[0].id] = len(node.value.elts)
    for name, line in used:
        if name not in defined and name not in builtins:
            suggestions = difflib.get_close_matches(name, defined, n=1, cutoff=0.78)
            hint = f" Did you mean '{suggestions[0]}'?" if suggestions else ""
            findings.append(Finding("Possible undefined name", f"Line {line} uses '{name}', but this name is not assigned in the code.{hint}", line, "Check"))
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            is_zero = isinstance(node.right, ast.Constant) and node.right.value == 0
            assigned = numeric_values.get(node.right.id) if isinstance(node.right, ast.Name) else None
            if assigned and assigned[0] == 0:
                is_zero = True
                detail = f"Line {node.lineno} divides by '{node.right.id}', which is assigned the value 0 on line {assigned[1]}."
            else:
                detail = f"Line {node.lineno} divides by zero, which raises ZeroDivisionError."
            if is_zero:
                findings.append(Finding("Division by zero", detail, node.lineno, "Error"))
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, int) and node.slice.value >= 0:
            length = list_values.get(node.value.id) if isinstance(node.value, ast.Name) else len(node.value.elts) if isinstance(node.value, ast.List) else None
            if length is not None and node.slice.value >= length:
                findings.append(Finding("List index is out of range", f"Line {node.lineno} asks for item {node.slice.value}, but this list has only {length} item(s). Valid indexes are 0 to {length - 1}.", node.lineno, "Error"))
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
    """Apply conservative beginner-example fixes without executing submitted code."""
    if analysis.status == "syntax_error" and "expected ':'" in (analysis.syntax_error or ""):
        lines = source.splitlines()
        if analysis.line and 0 < analysis.line <= len(lines):
            lines[analysis.line - 1] = lines[analysis.line - 1].rstrip() + ":"
            return "\n".join(lines), f"Line {analysis.line}: added the missing colon after the loop or block header."
    if analysis.status != "ok":
        return source, "No safe automatic correction was available for this input."

    tree = ast.parse(source)
    for finding in analysis.findings:
        if finding.title == "Possible undefined name" and finding.line:
            suggestion = re.search(r"Did you mean '([A-Za-z_]\w*)'\?", finding.detail)
            typo = re.search(r"uses '([A-Za-z_]\w*)'", finding.detail)
            if suggestion and typo:
                target = next((node for node in ast.walk(tree) if isinstance(node, ast.Name) and node.id == typo.group(1) and isinstance(node.ctx, ast.Load) and node.lineno == finding.line), None)
                if target:
                    return _replace_node(source, target, suggestion.group(1)), f"Line {finding.line}: changed '{typo.group(1)}' to '{suggestion.group(1)}' to match the variable assignment."
        if finding.title == "List index is out of range" and finding.line:
            node = next((item for item in ast.walk(tree) if isinstance(item, ast.Subscript) and item.lineno == finding.line and isinstance(item.slice, ast.Constant) and isinstance(item.slice.value, int)), None)
            if node and isinstance(node.value, ast.Name):
                list_name, index = node.value.id, node.slice.value
                line = source.splitlines()[finding.line - 1]
                indent = line[:len(line) - len(line.lstrip())]
                replacement = f"{indent}if len({list_name}) > {index}:\n{indent}    {line.lstrip()}\n{indent}else:\n{indent}    print('Index {index} is out of range')"
                return _replace_line(source, finding.line, replacement), f"Line {finding.line}: added a length check before reading index {index}, preventing an IndexError when the list is too short."
        if finding.title == "Division by zero" and finding.line:
            node = next((item for item in ast.walk(tree) if isinstance(item, ast.BinOp) and isinstance(item.op, ast.Div) and item.lineno == finding.line), None)
            if node and isinstance(node.right, ast.Name):
                divisor = node.right.id
                line = source.splitlines()[finding.line - 1]
                indent = line[:len(line) - len(line.lstrip())]
                replacement = f"{indent}if {divisor} == 0:\n{indent}    print('Cannot divide by zero')\n{indent}else:\n{indent}    {line.lstrip()}"
                return _replace_line(source, finding.line, replacement), f"Line {finding.line}: added a check for '{divisor}' before division; it is zero because it was assigned 0 on an earlier line."
    return source, "No safe automatic correction was available. The explanation identifies the relevant line and what to change."


def _replace_node(source: str, node: ast.AST, replacement: str) -> str:
    lines = source.splitlines(keepends=True)
    line_index = node.lineno - 1
    raw = lines[line_index].encode("utf-8")
    lines[line_index] = (raw[:node.col_offset] + replacement.encode("utf-8") + raw[node.end_col_offset:]).decode("utf-8")
    return "".join(lines)


def _replace_line(source: str, line_number: int, replacement: str) -> str:
    lines = source.splitlines()
    lines[line_number - 1:line_number] = replacement.splitlines()
    return "\n".join(lines)


def explain_error(error_text: str) -> tuple[str, str]:
    kind = next((name for name in ERROR_HELP if name in (error_text or "")), None)
    if kind:
        return ERROR_HELP[kind]
    return ("I couldn't identify a specific Python error type from this message.", "Read the first traceback line that points to your own file, then check the value and spelling on that line.")
