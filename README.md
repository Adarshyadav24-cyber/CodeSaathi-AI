# CodeSaathi AI

CodeSaathi AI is a small, beginner-friendly Python debugging tutor built with Streamlit. It explains common mistakes in plain English, suggests next steps, keeps a local learning history, and includes demonstration snippets.

## Safety and what the checks mean

Submitted code is parsed with Python's `ast` module and inspected with conservative static rules. **It is never executed by the application.** This avoids running arbitrary user programs on the app server. The displayed “test results” are syntax and static-check results only. Suggested tests are ideas for you to run in your own trusted Python environment; they have not been run by CodeSaathi.

Static analysis is limited: valid syntax does not prove a program is correct, and the basic name checks can miss issues or flag a name used from an external package. Review the explanation and test your program yourself.

## Features

- Code editor and demonstration examples for common beginner mistakes.
- Syntax validation and static hints, with line numbers when available.
- Simple-English demo explanations that work without an API key.
- Optional OpenAI explanation mode using environment variables. API errors fall back to the demo tutor.
- Corrected-code panel with narrowly scoped demonstration fixes; the app does not guess broad edits.
- Suggested tests and clear results for the checks that actually ran.
- SQLite history stored locally in `codesaathi_history.db` (ignored by Git).
- Responsive Streamlit layout and input-size validation.

## Requirements

- Windows 10 or 11
- Python 3.10 or newer (the project was developed with Python 3.11)
- Internet connection only to install packages or use the optional AI API

## Install and run (Windows PowerShell)

From the project folder:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m streamlit run app.py
```

If PowerShell blocks activation, either allow scripts for this terminal with `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, then activate again, or run the environment's executable directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Streamlit prints the local address to open in your browser (normally `http://localhost:8501`). Stop the app with Ctrl+C in the terminal.

## Optional AI explanations

Demo mode works out of the box. To enable the optional OpenAI API, set the variables in the same PowerShell window before starting Streamlit. Do not commit an actual API key:

```powershell
$env:OPENAI_API_KEY = "your-key-here"
$env:OPENAI_MODEL = "gpt-4o-mini"
python -m streamlit run app.py
```

`.env.example` documents the variable names and contains no secret. The app intentionally does not load `.env` automatically; environment variables are explicit and secrets are never stored in SQLite or Git. When the API is unavailable, the app reports the failure and uses its demo explanation rules.

## Project structure

```text
app.py                    Streamlit pages and presentation
codesaathi/analyzer.py    AST syntax checks, hints, examples, safe fix demos
codesaathi/ai.py          Optional AI adapter and demo fallback
codesaathi/history.py     Local SQLite history
tests/test_core.py        Focused standard-library unit tests
requirements.txt          App dependencies
.env.example              Names of optional environment variables
```

## Run checks

```powershell
python -m unittest discover -s tests -v
```

The tests cover blank input, invalid and valid Python, static hints, API fallback, and SQLite history. They do not execute user snippets.
