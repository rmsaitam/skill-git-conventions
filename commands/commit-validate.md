---
description: Validate a commit message against Conventional Commits and the repository policy.
argument-hint: "[path/to/message.txt] [--scan-diff <path>] [--config <path>] [--json] [--strict]"
---

# Validate Commit

Validate a commit message produced by the `commit` skill before it is used.

## Instructions

- Default to a message file supplied by the user. Accept `-` to read from stdin.
- Run the bundled validator. Resolve the script path from the `commit` skill
  directory:

  ```bash
  python3 <path-to-skill>/scripts/validate_commit.py <message-file> --config <path>
  ```

- Use `--config <path>` to load `.git-conventions.json` from another location.
- Use `--language en|pt-BR` to override the expected subject language.
- Use `--types` and `--scopes` to override the allowlists.
- Use `--require-ticket` to fail when no ticket reference is present.
- Use `--scan-diff <path>` to scan a diff for secrets before applying.
- Use `--commitlint` to run an allowlisted Commitlint command.
- Use `--json` for machine-readable output and `--strict` to treat warnings as
  failures.
- Do not modify the message unless the user explicitly asks for fixes. If fixes
  are requested, preserve the intent and re-run the validator.
- Never expose secrets. If the validator reports a possible secret, redact it
  and tell the user to rotate it.
