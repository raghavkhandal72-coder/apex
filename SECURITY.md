# Security Policy

## Reporting a vulnerability
Please report privately via GitHub: **Security → Report a vulnerability**. Do not open a public issue.
Expect an acknowledgement within 5 days.

## Scope and honest threat model
- Apex executes candidate code (LLM output or mutated code) in an **isolated subprocess**
  (`python -E -s`, scrubbed environment). This is **not** a kernel sandbox: it does not block
  file-system or network access. Run Apex inside Docker or a VM when handling untrusted code.
- API keys are read from environment variables and are never written to logs (only a masked prefix in `--verbose`).
- The PR Action needs `pull-requests: write` and nothing else. It sends no data to third parties.

## Supported versions
Only the latest release receives fixes while the project is pre-1.0.
