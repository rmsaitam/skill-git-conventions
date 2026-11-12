#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Iterable

DEFAULT_TYPES = (
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
)

TICKET_PATTERNS = {
    "generic": r"[A-Z][A-Z0-9]+-\d+",
    "jira": r"[A-Z][A-Z0-9]+-\d+",
    "linear": r"[A-Z][A-Z0-9]+-\d+",
    "github": r"#\d+",
    "gitlab": r"(?:#\d+|!\d+)",
}

HEADER_RE = re.compile(
    r"^(?P<type>[a-z][a-z0-9-]*)"
    r"(?:\((?P<scope>[^()\r\n]+)\))?"
    r"(?P<breaking>!)?: "
    r"(?P<description>.+)$"
)
SCOPE_RE = re.compile(r"^[a-z0-9][a-z0-9._/-]*$")
COMMENT_RE = re.compile(r"(?m)^#.*$")
FENCE_RE = re.compile(r"^[ \t]*(```|~~~)")
BREAKING_RE = re.compile(r"(?m)^BREAKING[ -]CHANGE:\s*(.*)$")
LOWER_BREAKING_RE = re.compile(r"(?im)^breaking[ -]change:")
UPPER_BREAKING_RE = re.compile(r"(?m)^BREAKING(?: |-)CHANGE:")
KNOWN_FOOTER_RE = re.compile(
    r"^(?:"
    r"BREAKING[ -]CHANGE:.*|"
    r"Refs?:\s*\S.*|"
    r"Closes:\s*\S.*|"
    r"Closes\s+#\d+.*|"
    r"Fixes:\s*\S.*|"
    r"Fixes\s+#\d+.*|"
    r"Resolves:\s*\S.*|"
    r"Resolves\s+#\d+.*|"
    r"Related to\s+\S.*|"
    r"Part of\s+\S.*|"
    r"See merge request\s+!\d+.*|"
    r"Co-authored-by:\s*\S.*|"
    r"Reviewed-by:\s*\S.*|"
    r"Signed-off-by:\s*\S.*|"
    r"Acked-by:\s*\S.*|"
    r"Tested-by:\s*\S.*"
    r")$",
    re.IGNORECASE,
)
PLACEHOLDER_RE = re.compile(
    r"\b(?:TODO|TBD|FIXME)\b|\[insert\b|<insert\b|\[placeholder\b|<placeholder\b|lorem ipsum",
    re.IGNORECASE,
)
SECRET_PATTERNS = (
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("GitHub fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    (
        "JSON Web Token",
        re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    ),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
)
DIFF_SECRET_PATTERNS = SECRET_PATTERNS + (
    (
        "AWS secret access key",
        re.compile(r"(?i)\baws_secret_access_key\b\s*[=:]\s*['\"]?[A-Za-z0-9/+=]{40}"),
    ),
    ("Anthropic API key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
    ("OpenAI API key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("Stripe secret key", re.compile(r"\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}\b")),
    ("GitLab token", re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b")),
    ("npm token", re.compile(r"\bnpm_[A-Za-z0-9]{36}\b")),
    ("Hugging Face token", re.compile(r"\bhf_[A-Za-z0-9]{30,}\b")),
    (
        "connection string with credentials",
        re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp)://[^\s:@/]+:[^\s@/]+@"),
    ),
    (
        "credential assignment",
        re.compile(
            r"(?i)\b(?:password|passwd|pwd|secret|token|api[_-]?key)\b\s*[=:]\s*['\"]?[A-Za-z0-9_./+=-]{8,}"
        ),
    ),
)
COMMITLINT_COMMAND_HELP = (
    "Commitlint command must be 'commitlint', 'npx --no-install commitlint', "
    "'bunx --no-install commitlint', 'pnpm exec commitlint', or "
    "'yarn exec commitlint'."
)
COMMITLINT_PREFIXES = (
    ("commitlint",),
    ("npx", "--no-install", "commitlint"),
    ("bunx", "--no-install", "commitlint"),
    ("pnpm", "exec", "commitlint"),
    ("yarn", "exec", "commitlint"),
)
SHELL_METACHARACTER_RE = re.compile(r"[;&|`$<>]")
NON_IMPERATIVE_WORDS = {
    "en": {
        "added",
        "adds",
        "adding",
        "fixed",
        "fixes",
        "fixing",
        "updated",
        "updates",
        "updating",
        "removed",
        "removes",
        "removing",
        "changed",
        "changes",
        "changing",
        "implemented",
        "implements",
        "implementing",
        "created",
        "creates",
        "creating",
        "refactored",
        "refactors",
        "refactoring",
        "improved",
        "improves",
        "improving",
        "corrected",
        "corrects",
        "correcting",
        "moved",
        "moves",
        "moving",
        "renamed",
        "renames",
        "renaming",
        "bumped",
        "bumps",
        "bumping",
        "documented",
        "documents",
        "documenting",
        "tested",
        "tests",
        "testing",
        "reverted",
        "reverts",
        "reverting",
    },
    "pt": {
        "adicionado",
        "adicionada",
        "adicionou",
        "adicionando",
        "corrigido",
        "corrigida",
        "corrigiu",
        "corrigindo",
        "implementado",
        "implementada",
        "implementou",
        "implementando",
        "removido",
        "removida",
        "removeu",
        "removendo",
        "alterado",
        "alterada",
        "alterou",
        "alterando",
        "criado",
        "criada",
        "criou",
        "criando",
        "atualizado",
        "atualizada",
        "atualizou",
        "atualizando",
        "movido",
        "moveu",
        "movendo",
        "renomeado",
        "renomeou",
        "renomeando",
        "documentado",
        "documentou",
        "documentando",
        "testado",
        "testou",
        "testando",
        "revertido",
        "reverteu",
        "revertendo",
        "melhorado",
        "melhorou",
        "melhorando",
    },
}


@dataclass(frozen=True)
class TicketPolicy:
    provider: str = "generic"
    pattern: str | None = None
    required: bool = False
    placement: str = "footer"
    keyword: str = "Refs"


@dataclass(frozen=True)
class Policy:
    language: str = "en"
    types: tuple[str, ...] = DEFAULT_TYPES
    scopes: tuple[str, ...] | None = None
    max_header: int = 72
    hard_header: int = 80
    require_body: bool = False
    ticket: TicketPolicy = field(default_factory=TicketPolicy)
    commitlint_enabled: bool = False
    commitlint_command: str = "commitlint"

    def ticket_regex(self) -> re.Pattern[str]:
        if self.ticket.pattern:
            return re.compile(self.ticket.pattern)
        provider = self.ticket.provider if self.ticket.provider in TICKET_PATTERNS else "generic"
        return re.compile(TICKET_PATTERNS[provider])


@dataclass
class Issue:
    level: str
    code: str
    message: str
    location: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "level": self.level,
            "code": self.code,
            "message": self.message,
            "location": self.location,
        }


@dataclass
class Report:
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)
    stats: dict[str, object] = field(default_factory=dict)

    def error(self, code: str, message: str, location: str = "") -> None:
        self.errors.append(Issue("error", code, message, location))

    def warning(self, code: str, message: str, location: str = "") -> None:
        self.warnings.append(Issue("warning", code, message, location))

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, object]:
        return {
            "status": "pass" if self.ok else "fail",
            "stats": self.stats,
            "errors": [issue.to_dict() for issue in self.errors],
            "warnings": [issue.to_dict() for issue in self.warnings],
        }


@dataclass
class ParsedMessage:
    lines: list[str]
    header: str
    body_text: str
    footer_text: str
    breaking: bool = False


def strip_fenced_code(text: str) -> str:
    result: list[str] = []
    in_fence = False
    for line in text.splitlines(keepends=True):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            result.append("\n" if line.endswith("\n") else "")
        elif in_fence:
            result.append("\n" if line.endswith("\n") else "")
        else:
            result.append(line)
    return "".join(result)


def strip_inline_code(text: str) -> str:
    return re.sub(r"`[^`\n]+`", "", text)


def strip_comments(text: str) -> str:
    return COMMENT_RE.sub("", text)


def split_blocks(lines: Iterable[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if not line.strip():
            if current:
                blocks.append(current)
                current = []
            continue
        current.append(line)
    if current:
        blocks.append(current)
    return blocks


def looks_like_footer(block: list[str]) -> bool:
    return bool(block and KNOWN_FOOTER_RE.match(block[0].strip()))


def parse_message(text: str) -> ParsedMessage:
    cleaned = strip_comments(text).strip("\n")
    lines = cleaned.splitlines()
    header = lines[0].strip() if lines else ""
    blocks = split_blocks(lines[1:])
    footer_blocks: list[list[str]] = []
    while blocks and looks_like_footer(blocks[-1]):
        footer_blocks.insert(0, blocks.pop())
    body_text = "\n\n".join("\n".join(block) for block in blocks)
    footer_text = "\n\n".join("\n".join(block) for block in footer_blocks)
    breaking = False
    match = HEADER_RE.match(header)
    if match:
        breaking = bool(match.group("breaking"))
    return ParsedMessage(
        lines=lines,
        header=header,
        body_text=body_text,
        footer_text=footer_text,
        breaking=breaking,
    )


def language_key(language: str) -> str:
    return "pt" if language.lower().startswith("pt") else "en"


def first_word(description: str) -> str:
    return re.split(r"[\s:(\[]", description.strip(), maxsplit=1)[0].lower()


def is_issue_only(description: str, policy: Policy) -> bool:
    text = description.strip()
    if policy.ticket_regex().fullmatch(text):
        return True
    return bool(
        re.fullmatch(
            r"(?:closes|fixes|resolves|refs?|related to|part of)\s+\S+",
            text,
            re.IGNORECASE,
        )
    )


def validate_header(
    header: str,
    policy: Policy,
    report: Report,
    allow_non_conventional: bool,
) -> dict[str, str] | None:
    if not header:
        report.error("missing-header", "The message needs a header.", "header")
        return None
    match = HEADER_RE.match(header)
    if not match:
        if allow_non_conventional:
            report.warning(
                "non-conventional",
                "The header does not follow Conventional Commits.",
                "header",
            )
            return None
        report.error(
            "invalid-header",
            "The header must follow type(scope)!: description.",
            "header",
        )
        return None
    type_ = match.group("type")
    scope = match.group("scope")
    description = match.group("description").strip()
    result = {"type": type_, "scope": scope or "", "description": description}

    if type_ not in policy.types:
        report.error(
            "invalid-type",
            f"The type {type_!r} is not allowed. Use one of: {', '.join(policy.types)}.",
            "header",
        )
    if scope is not None:
        if not SCOPE_RE.match(scope):
            report.error(
                "invalid-scope-format",
                "The scope must be lowercase and free of spaces.",
                "header",
            )
        elif policy.scopes is not None and scope not in policy.scopes:
            report.error(
                "invalid-scope",
                f"The scope {scope!r} is not allowed. Use one of: {', '.join(policy.scopes)}.",
                "header",
            )
    if not description:
        report.error("empty-description", "The description is empty.", "header")
    else:
        if description.endswith("."):
            report.error("trailing-period", "The description must not end with a period.", "header")
        if description[0].isupper():
            report.warning(
                "subject-uppercase",
                "Start the description with a lowercase letter unless it is a proper noun.",
                "header",
            )
        if PLACEHOLDER_RE.search(description):
            report.error("placeholder-description", "The description contains a placeholder.", "header")
        if is_issue_only(description, policy):
            report.error(
                "issue-as-description",
                "The description must explain the change, not only reference a ticket.",
                "header",
            )
        if first_word(description) in NON_IMPERATIVE_WORDS[language_key(policy.language)]:
            report.warning(
                "not-imperative",
                "Use the imperative mood in the description.",
                "header",
            )
    if len(header) > policy.hard_header:
        report.error(
            "header-too-long",
            f"The header has {len(header)} characters; the maximum is {policy.hard_header}.",
            "header",
        )
    elif len(header) > policy.max_header:
        report.warning(
            "header-long",
            f"The header has {len(header)} characters; prefer {policy.max_header} or fewer.",
            "header",
        )
    return result


def validate_structure(parsed: ParsedMessage, report: Report) -> None:
    if len(parsed.lines) > 1 and parsed.lines[1].strip():
        report.error(
            "missing-blank-line",
            "Add a blank line after the header.",
            "body:2",
        )


def validate_body(parsed: ParsedMessage, policy: Policy, report: Report) -> None:
    if not parsed.body_text.strip():
        if policy.require_body:
            report.error("missing-body", "The body is required by the policy.", "body")
        return
    for index, line in enumerate(parsed.body_text.splitlines(), start=2):
        if len(line) > 100:
            report.warning(
                "body-line-too-long",
                f"The body line has {len(line)} characters; wrap at 72.",
                f"body:{index}",
            )
    if BREAKING_RE.search(parsed.body_text):
        report.warning(
            "breaking-in-body",
            "Put BREAKING CHANGE in the footer, after a blank line.",
            "body",
        )


def validate_footer(parsed: ParsedMessage, report: Report) -> None:
    text = parsed.footer_text
    if not text.strip():
        if parsed.breaking:
            report.warning(
                "breaking-without-details",
                "Add a BREAKING CHANGE footer explaining the impact and migration.",
                "footer",
            )
        return
    if LOWER_BREAKING_RE.search(text) and not UPPER_BREAKING_RE.search(text):
        report.error(
            "breaking-change-case",
            "Write BREAKING CHANGE in uppercase.",
            "footer",
        )
    for value in BREAKING_RE.findall(text):
        if not value.strip():
            report.error(
                "empty-breaking-change",
                "The BREAKING CHANGE footer needs a description.",
                "footer",
            )


def validate_ticket(parsed: ParsedMessage, policy: Policy, report: Report) -> None:
    pattern = policy.ticket_regex()
    in_subject = bool(pattern.search(parsed.header))
    in_footer = bool(pattern.search(parsed.footer_text))
    in_body = bool(pattern.search(parsed.body_text))
    found = in_subject or in_footer or in_body
    report.stats["ticket_found"] = found
    if not found:
        if policy.ticket.required:
            report.error(
                "missing-ticket",
                f"No ticket matching {pattern.pattern!r} was found.",
                "message",
            )
        return
    placement = policy.ticket.placement
    if placement == "subject" and not in_subject:
        report.error("ticket-placement", "The ticket must appear in the subject.", "message")
    elif placement == "footer" and not in_footer:
        report.error("ticket-placement", "The ticket must appear in the footer.", "message")
    elif placement == "both" and not (in_subject and in_footer):
        report.error("ticket-placement", "The ticket must appear in the subject and the footer.", "message")
    if in_footer and policy.ticket.keyword:
        keyword = re.escape(policy.ticket.keyword)
        has_keyword = re.search(rf"(?im)^{keyword}\s*:", parsed.footer_text)
        has_closing = re.search(
            r"(?im)^(?:closes|fixes|resolves|refs?|related to|part of)\b",
            parsed.footer_text,
        )
        if not has_keyword and not has_closing:
            report.warning(
                "missing-ticket-keyword",
                f"Add a keyword such as '{policy.ticket.keyword}:' before the ticket.",
                "footer",
            )


def scan_placeholders(text: str, report: Report) -> None:
    cleaned = strip_inline_code(strip_fenced_code(strip_comments(text)))
    for match in PLACEHOLDER_RE.finditer(cleaned):
        line = cleaned.count("\n", 0, match.start()) + 1
        report.error(
            "placeholder",
            f"The message contains a placeholder {match.group(0)!r}.",
            f"message:{line}",
        )


def scan_secrets(
    text: str,
    report: Report,
    patterns: Iterable[tuple[str, re.Pattern[str]]] = SECRET_PATTERNS,
    source: str = "message",
) -> None:
    for name, pattern in patterns:
        for match in pattern.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            label = "The message" if source == "message" else f"The {source}"
            report.error(
                "secret",
                f"{label} contains a possible {name}. Redact and rotate it.",
                f"{source}:{line}",
            )


def validate_message(
    text: str,
    policy: Policy,
    report: Report,
    allow_non_conventional: bool = False,
) -> None:
    if not text.strip():
        report.error("empty-message", "The message is empty.", "message")
        return
    parsed = parse_message(text)
    header_info = validate_header(parsed.header, policy, report, allow_non_conventional)
    validate_structure(parsed, report)
    validate_body(parsed, policy, report)
    validate_footer(parsed, report)
    validate_ticket(parsed, policy, report)
    scan_placeholders(text, report)
    scan_secrets(text, report)
    report.stats["header_length"] = len(parsed.header)
    report.stats["type"] = header_info["type"] if header_info else ""
    report.stats["scope"] = header_info["scope"] if header_info else ""
    report.stats["breaking"] = parsed.breaking
    report.stats["has_body"] = bool(parsed.body_text.strip())
    report.stats["has_footer"] = bool(parsed.footer_text.strip())


def read_json(path: Path, report: Report, code: str = "invalid-config") -> dict[str, object] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        report.error("missing-config", f"Missing config file: {path}.", str(path))
        return None
    except json.JSONDecodeError as error:
        report.error(code, f"Invalid JSON in {path}: {error}.", str(path))
        return None
    except OSError as error:
        report.error("unreadable-config", f"Cannot read {path}: {error}.", str(path))
        return None
    if not isinstance(data, dict):
        report.error("invalid-config-root", f"{path} must contain a JSON object.", str(path))
        return None
    return data


def policy_from_ticket(data: object, base: TicketPolicy, report: Report) -> TicketPolicy:
    if not isinstance(data, dict):
        report.error("invalid-ticket-config", "ticket must be an object.", "config:ticket")
        return base
    provider = data.get("provider", base.provider)
    if not isinstance(provider, str) or not provider.strip():
        report.error("invalid-ticket-provider", "ticket.provider must be a string.", "config:ticket.provider")
        provider = base.provider
    pattern = data.get("pattern", base.pattern)
    if pattern is not None:
        if not isinstance(pattern, str) or not pattern.strip():
            report.error("invalid-ticket-pattern", "ticket.pattern must be a string.", "config:ticket.pattern")
            pattern = base.pattern
        else:
            try:
                re.compile(pattern)
            except re.error as error:
                report.error(
                    "invalid-ticket-pattern",
                    f"ticket.pattern is not a valid regex: {error}.",
                    "config:ticket.pattern",
                )
                pattern = base.pattern
    required = data.get("required", base.required)
    if not isinstance(required, bool):
        report.error("invalid-ticket-required", "ticket.required must be a boolean.", "config:ticket.required")
        required = base.required
    placement = data.get("placement", base.placement)
    if placement not in {"subject", "footer", "both"}:
        report.error(
            "invalid-ticket-placement",
            "ticket.placement must be subject, footer, or both.",
            "config:ticket.placement",
        )
        placement = base.placement
    keyword = data.get("keyword", base.keyword)
    if not isinstance(keyword, str) or not keyword.strip():
        report.error("invalid-ticket-keyword", "ticket.keyword must be a string.", "config:ticket.keyword")
        keyword = base.keyword
    return TicketPolicy(
        provider=provider.strip().lower(),
        pattern=pattern,
        required=required,
        placement=placement,
        keyword=keyword.strip(),
    )


def parse_commitlint_command(command: str) -> list[str] | None:
    try:
        args = shlex.split(command)
    except ValueError:
        return None
    if not args:
        return None
    if any(SHELL_METACHARACTER_RE.search(arg) for arg in args):
        return None
    for prefix in COMMITLINT_PREFIXES:
        if tuple(args[: len(prefix)]) == prefix:
            return args
    return None


def policy_from_data(data: dict[str, object], base: Policy, report: Report) -> Policy:
    language = base.language
    if "language" in data:
        language = data["language"]
        if language not in {"en", "pt-BR"}:
            report.error("invalid-language", "language must be en or pt-BR.", "config:language")
            language = base.language
    types = base.types
    if "types" in data:
        types = data["types"]
        if not isinstance(types, list) or not types or not all(
            isinstance(item, str) and item.strip() for item in types
        ):
            report.error("invalid-types", "types must be a non-empty list of strings.", "config:types")
            types = base.types
        else:
            types = tuple(item.strip() for item in types)
    scopes = base.scopes
    if "scopes" in data:
        scopes = data["scopes"]
        if scopes is not None:
            if not isinstance(scopes, list) or not all(
                isinstance(item, str) and item.strip() for item in scopes
            ):
                report.error("invalid-scopes", "scopes must be a list of strings or null.", "config:scopes")
                scopes = base.scopes
            else:
                scopes = tuple(item.strip() for item in scopes)
    max_header = base.max_header
    if "maxHeaderLength" in data:
        max_header = data["maxHeaderLength"]
        if not isinstance(max_header, int) or max_header <= 0:
            report.error(
                "invalid-max-header",
                "maxHeaderLength must be a positive integer.",
                "config:maxHeaderLength",
            )
            max_header = base.max_header
    hard_header = base.hard_header
    if "hardHeaderLength" in data:
        hard_header = data["hardHeaderLength"]
        if not isinstance(hard_header, int) or hard_header <= 0:
            report.error(
                "invalid-hard-header",
                "hardHeaderLength must be a positive integer.",
                "config:hardHeaderLength",
            )
            hard_header = base.hard_header
    if hard_header < max_header:
        report.error(
            "invalid-header-range",
            "hardHeaderLength must be greater than or equal to maxHeaderLength.",
            "config",
        )
        hard_header = max_header
    require_body = base.require_body
    if "requireBody" in data:
        require_body = data["requireBody"]
        if not isinstance(require_body, bool):
            report.error("invalid-require-body", "requireBody must be a boolean.", "config:requireBody")
            require_body = base.require_body
    ticket = base.ticket
    ticket_data = data.get("ticket")
    if ticket_data is not None:
        ticket = policy_from_ticket(ticket_data, base.ticket, report)
    commitlint_enabled = base.commitlint_enabled
    commitlint_command = base.commitlint_command
    if "commitlint" in data:
        commitlint_data = data["commitlint"]
        if isinstance(commitlint_data, bool):
            commitlint_enabled = commitlint_data
        elif isinstance(commitlint_data, dict):
            enabled = commitlint_data.get("enabled", commitlint_enabled)
            if not isinstance(enabled, bool):
                report.error(
                    "invalid-commitlint",
                    "commitlint.enabled must be a boolean.",
                    "config:commitlint.enabled",
                )
            else:
                commitlint_enabled = enabled
            command = commitlint_data.get("command", commitlint_command)
            if not isinstance(command, str) or not command.strip():
                report.error(
                    "invalid-commitlint",
                    "commitlint.command must be a string.",
                    "config:commitlint.command",
                )
                commitlint_enabled = False
            else:
                parsed = parse_commitlint_command(command)
                if parsed is None:
                    report.error(
                        "invalid-commitlint",
                        COMMITLINT_COMMAND_HELP,
                        "config:commitlint.command",
                    )
                    commitlint_enabled = False
                else:
                    commitlint_command = " ".join(parsed)
        else:
            report.error("invalid-commitlint", "commitlint must be a boolean or an object.", "config:commitlint")
    return Policy(
        language=language,
        types=tuple(types),
        scopes=scopes,
        max_header=max_header,
        hard_header=hard_header,
        require_body=require_body,
        ticket=ticket,
        commitlint_enabled=commitlint_enabled,
        commitlint_command=commitlint_command,
    )


def rule_value(rules: dict[str, object], name: str, index: int = 2) -> object:
    entry = rules.get(name)
    if isinstance(entry, list) and len(entry) > index:
        return entry[index]
    return None


def policy_from_commitlint(data: dict[str, object], base: Policy) -> Policy:
    rules = data.get("rules")
    if not isinstance(rules, dict):
        return base
    overrides: dict[str, object] = {}
    types = rule_value(rules, "type-enum")
    if isinstance(types, list) and types and all(isinstance(item, str) for item in types):
        overrides["types"] = tuple(types)
    scopes = rule_value(rules, "scope-enum")
    if isinstance(scopes, list) and scopes and all(isinstance(item, str) for item in scopes):
        overrides["scopes"] = tuple(scopes)
    max_header = rule_value(rules, "header-max-length")
    if isinstance(max_header, int) and max_header > 0:
        overrides["max_header"] = max_header
        overrides["hard_header"] = max_header
    return replace(base, **overrides)


def detect_commitlint(root: Path, report: Report) -> Policy | None:
    for name in ("commitlint.config.json", ".commitlintrc.json", ".commitlintrc"):
        path = root / name
        if path.is_file():
            data = read_json(path, report)
            if data is not None:
                return policy_from_commitlint(data, Policy())
    package = root / "package.json"
    if package.is_file():
        try:
            data = json.loads(package.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = None
        if isinstance(data, dict) and isinstance(data.get("commitlint"), dict):
            return policy_from_commitlint(data["commitlint"], Policy())
    for name in (
        "commitlint.config.js",
        "commitlint.config.cjs",
        "commitlint.config.mjs",
        "commitlint.config.ts",
        ".commitlintrc.yaml",
        ".commitlintrc.yml",
    ):
        if (root / name).is_file():
            return Policy()
    return None


def load_policy(config_path: Path | None, root: Path, report: Report) -> Policy:
    base = Policy()
    if config_path is not None:
        data = read_json(config_path, report)
        if data is None:
            return base
        return policy_from_data(data, base, report)
    default_path = root / ".git-conventions.json"
    if default_path.is_file():
        data = read_json(default_path, report)
        if data is None:
            return base
        return policy_from_data(data, base, report)
    detected = detect_commitlint(root, report)
    if detected is not None:
        return detected
    return base


def run_commitlint(text: str, policy: Policy, report: Report) -> None:
    args = parse_commitlint_command(policy.commitlint_command)
    if args is None:
        report.error("commitlint-command", COMMITLINT_COMMAND_HELP, "commitlint")
        return
    try:
        result = subprocess.run(
            args,
            input=text,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        report.error(
            "commitlint-unavailable",
            f"Commitlint command not found: {args[0]}.",
            "commitlint",
        )
        return
    except OSError as error:
        report.error("commitlint-error", f"Cannot run Commitlint: {error}.", "commitlint")
        return
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        message = detail[-1] if detail else "Commitlint rejected the message."
        report.error("commitlint", message, "commitlint")


def read_source(path: str, report: Report, label: str) -> str | None:
    if path == "-":
        return sys.stdin.read()
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        report.error("missing-file", f"Missing {label} file: {path}.", path)
    except OSError as error:
        report.error("unreadable-file", f"Cannot read {path}: {error}.", path)
    return None


def read_message(path: str, report: Report) -> str | None:
    return read_source(path, report, "message")


def read_diff(path: str, report: Report) -> str | None:
    return read_source(path, report, "diff")


def format_issue(issue: Issue) -> str:
    location = f" ({issue.location})" if issue.location else ""
    return f"[{issue.level.upper()}] {issue.code}: {issue.message}{location}"


def print_report(report: Report, as_json: bool) -> None:
    if as_json:
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        return
    for issue in report.errors:
        print(format_issue(issue), file=sys.stderr)
    for issue in report.warnings:
        print(format_issue(issue), file=sys.stderr)
    status = "PASS" if report.ok else "FAIL"
    print(
        f"{status}: type {report.stats.get('type') or 'unknown'}, "
        f"header {report.stats.get('header_length', 0)} char(s); "
        f"{len(report.errors)} error(s), {len(report.warnings)} warning(s)."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a commit message against Conventional Commits and the repository policy."
    )
    parser.add_argument(
        "message",
        nargs="?",
        default=None,
        help="Path to the message file, or - to read from stdin",
    )
    parser.add_argument(
        "--scan-diff",
        nargs="?",
        const="-",
        default=None,
        metavar="PATH",
        help="Scan a diff for secrets, or - to read from stdin",
    )
    parser.add_argument("--config", help="Path to .git-conventions.json")
    parser.add_argument("--root", default=".", help="Repository root for config discovery")
    parser.add_argument("--language", choices=("en", "pt-BR"), help="Subject language")
    parser.add_argument("--types", help="Comma-separated allowed types")
    parser.add_argument("--scopes", help="Comma-separated allowed scopes")
    parser.add_argument("--max-header", type=int, help="Preferred header length")
    parser.add_argument("--require-ticket", action="store_true", help="Fail when no ticket is present")
    parser.add_argument("--require-body", action="store_true", help="Fail when the body is empty")
    parser.add_argument("--commitlint", action="store_true", help="Run Commitlint")
    parser.add_argument(
        "--commitlint-command",
        help="Commitlint command to run; only allowlisted forms are accepted",
    )
    parser.add_argument(
        "--allow-non-conventional",
        action="store_true",
        help="Allow a header that is not Conventional Commits",
    )
    parser.add_argument("--json", action="store_true", help="Emit a JSON report")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    report = Report()
    policy = load_policy(
        Path(args.config) if args.config else None,
        Path(args.root),
        report,
    )
    overrides: dict[str, object] = {}
    if args.language:
        overrides["language"] = args.language
    if args.types is not None:
        overrides["types"] = tuple(item.strip() for item in args.types.split(",") if item.strip())
    if args.scopes is not None:
        overrides["scopes"] = tuple(item.strip() for item in args.scopes.split(",") if item.strip())
    if args.max_header is not None:
        overrides["max_header"] = args.max_header
        if args.max_header > policy.hard_header:
            overrides["hard_header"] = args.max_header
    if args.require_ticket:
        overrides["ticket"] = replace(policy.ticket, required=True)
    if args.require_body:
        overrides["require_body"] = True
    if args.commitlint:
        overrides["commitlint_enabled"] = True
    if args.commitlint_command:
        parsed = parse_commitlint_command(args.commitlint_command)
        if parsed is None:
            report.error("commitlint-command", COMMITLINT_COMMAND_HELP, "commitlint")
            overrides["commitlint_enabled"] = False
        else:
            overrides["commitlint_command"] = " ".join(parsed)
    if overrides:
        policy = replace(policy, **overrides)
    if args.scan_diff is not None:
        diff_text = read_diff(args.scan_diff, report)
        if diff_text is not None:
            scan_secrets(diff_text, report, DIFF_SECRET_PATTERNS, "diff")
    message_path = args.message
    if message_path is None and args.scan_diff is None:
        message_path = "-"
    if message_path is not None:
        text = read_message(message_path, report)
        if text is not None:
            validate_message(
                text,
                policy,
                report,
                allow_non_conventional=args.allow_non_conventional,
            )
            if policy.commitlint_enabled:
                run_commitlint(text, policy, report)
    print_report(report, args.json)
    if report.errors:
        return 1
    if args.strict and report.warnings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
