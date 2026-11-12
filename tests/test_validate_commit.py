from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

import pytest

from validate_commit import (
    DIFF_SECRET_PATTERNS,
    Policy,
    Report,
    TicketPolicy,
    detect_commitlint,
    first_word,
    is_issue_only,
    language_key,
    load_policy,
    looks_like_footer,
    main,
    parse_message,
    parse_commitlint_command,
    policy_from_commitlint,
    policy_from_data,
    policy_from_ticket,
    read_diff,
    read_json,
    read_message,
    run_commitlint,
    scan_secrets,
    split_blocks,
    validate_message,
)

FIXTURES = Path(__file__).parent / "fixtures"
VALID = (FIXTURES / "valid_commit.txt").read_text(encoding="utf-8")
VALID_PT = (FIXTURES / "valid_commit_pt_br.txt").read_text(encoding="utf-8")
INVALID = (FIXTURES / "invalid_commit.txt").read_text(encoding="utf-8")


def run(text: str, policy: Policy | None = None, **kwargs) -> Report:
    report = Report()
    validate_message(text, policy or Policy(), report, **kwargs)
    return report


def error_codes(report: Report) -> set[str]:
    return {issue.code for issue in report.errors}


def warning_codes(report: Report) -> set[str]:
    return {issue.code for issue in report.warnings}


def test_valid_message_passes() -> None:
    report = run(VALID)
    assert report.ok, [issue.message for issue in report.errors]
    assert not report.warnings
    assert report.stats["type"] == "fix"
    assert report.stats["scope"] == "auth"
    assert report.stats["has_body"] is True
    assert report.stats["has_footer"] is True
    assert report.stats["ticket_found"] is True


def test_valid_pt_br_message_passes() -> None:
    report = run(VALID_PT, Policy(language="pt-BR"))
    assert report.ok, [issue.message for issue in report.errors]
    assert not report.warnings
    assert report.stats["type"] == "feat"


def test_invalid_fixture_reports_errors() -> None:
    codes = error_codes(run(INVALID))
    assert "trailing-period" in codes
    assert "not-imperative" in warning_codes(run(INVALID))


def test_empty_message() -> None:
    assert "empty-message" in error_codes(run("   \n"))


def test_missing_header_after_comments() -> None:
    assert "missing-header" in error_codes(run("# only a comment\n"))


def test_non_conventional_header() -> None:
    assert "invalid-header" in error_codes(run("Update files\n"))
    report = run("Update files\n", allow_non_conventional=True)
    assert report.ok
    assert "non-conventional" in warning_codes(report)


def test_invalid_type() -> None:
    assert "invalid-type" in error_codes(run("wip: add login\n"))


def test_scope_format_and_allowlist() -> None:
    assert "invalid-scope-format" in error_codes(run("feat(Auth): add login\n"))
    assert "invalid-scope" in error_codes(run("feat(other): add login\n", Policy(scopes=("auth",))))


def test_scope_wildcard_accepts_any_valid_scope() -> None:
    assert run("feat(api/v2): add login\n", Policy(scopes=None)).ok
    assert run("feat(my_scope): add login\n", Policy(scopes=None)).ok


def test_trailing_period() -> None:
    assert "trailing-period" in error_codes(run("feat: add login.\n"))


def test_subject_uppercase_warns() -> None:
    assert "subject-uppercase" in warning_codes(run("feat: Add login\n"))


def test_not_imperative_english() -> None:
    assert "not-imperative" in warning_codes(run("feat: added login\n"))


def test_not_imperative_portuguese() -> None:
    report = run("feat: adicionado login\n", Policy(language="pt-BR"))
    assert "not-imperative" in warning_codes(report)


def test_issue_as_description() -> None:
    assert "issue-as-description" in error_codes(run("feat: PROJ-123\n"))
    assert "issue-as-description" in error_codes(run("feat: Refs PROJ-123\n"))


def test_header_length() -> None:
    long_warning = run("feat: " + "a" * 70 + "\n")
    assert "header-long" in warning_codes(long_warning)
    too_long = run("feat: " + "a" * 80 + "\n")
    assert "header-too-long" in error_codes(too_long)


def test_missing_blank_line() -> None:
    assert "missing-blank-line" in error_codes(run("feat: add login\nBody without blank.\n"))


def test_body_required() -> None:
    assert "missing-body" in error_codes(run("feat: add login\n", Policy(require_body=True)))


def test_body_long_warns() -> None:
    text = "feat: add login\n\n" + "a" * 120 + "\n"
    assert "body-line-too-long" in warning_codes(run(text))


def test_breaking_without_details_warns() -> None:
    assert "breaking-without-details" in warning_codes(run("feat(api)!: remove endpoint\n"))


def test_breaking_footer_is_accepted() -> None:
    text = "feat(api)!: remove endpoint\n\nBREAKING CHANGE: clients must migrate\n"
    report = run(text)
    assert report.ok
    assert "breaking-without-details" not in warning_codes(report)


def test_breaking_case_and_empty_value() -> None:
    lower = run("feat: add login\n\nbreaking change: clients must migrate\n")
    assert "breaking-change-case" in error_codes(lower)
    empty = run("feat: add login\n\nBREAKING CHANGE:\n")
    assert "empty-breaking-change" in error_codes(empty)


def test_breaking_in_body_warns() -> None:
    text = (
        "feat: add login\n\n"
        "Some body.\n\n"
        "BREAKING CHANGE: clients must migrate.\n\n"
        "More body.\n"
    )
    assert "breaking-in-body" in warning_codes(run(text))


def test_ticket_required_missing() -> None:
    policy = Policy(ticket=TicketPolicy(provider="jira", required=True))
    assert "missing-ticket" in error_codes(run("feat(auth): add login\n", policy))


def test_ticket_placement_subject() -> None:
    policy = Policy(ticket=TicketPolicy(provider="jira", required=True, placement="subject"))
    text = "feat(auth): add login\n\nRefs: PROJ-123\n"
    assert "ticket-placement" in error_codes(run(text, policy))


def test_ticket_placement_footer() -> None:
    policy = Policy(ticket=TicketPolicy(provider="jira", required=True, placement="footer"))
    text = "feat(auth): add login PROJ-123\n"
    assert "ticket-placement" in error_codes(run(text, policy))


def test_ticket_placement_both() -> None:
    policy = Policy(ticket=TicketPolicy(provider="jira", required=True, placement="both"))
    text = "feat(auth): add login\n\nRefs: PROJ-123\n"
    assert "ticket-placement" in error_codes(run(text, policy))


def test_ticket_keyword_warning() -> None:
    policy = Policy(
        ticket=TicketPolicy(provider="jira", required=True, placement="footer", keyword="Refs")
    )
    text = "feat(auth): add login\n\nReviewed-by: PROJ-123\n"
    assert "missing-ticket-keyword" in warning_codes(run(text, policy))


def test_github_ticket_is_accepted() -> None:
    policy = Policy(
        ticket=TicketPolicy(provider="github", required=True, placement="footer", keyword="Closes")
    )
    text = "fix(auth): reject expired sessions\n\nCloses #123\n"
    report = run(text, policy)
    assert report.ok
    assert not report.warnings


def test_placeholder_in_body() -> None:
    assert "placeholder" in error_codes(run("feat: add login\n\nTODO: remove this line.\n"))


def test_placeholders_in_code_are_ignored() -> None:
    text = "feat: add login\n\nUse `TODO` in the body.\n\n~~~\nTODO\n~~~\n"
    report = run(text)
    assert report.ok, [issue.message for issue in report.errors]


def test_secret_is_rejected() -> None:
    text = "feat: add login\n\nAKIAABCDEFGHIJKLMNOP\n"
    assert "secret" in error_codes(run(text))


def test_parse_message_body_and_footer() -> None:
    parsed = parse_message("feat(auth)!: add login\n\nBody line.\n\nRefs: PROJ-1\n")
    assert parsed.header == "feat(auth)!: add login"
    assert parsed.body_text == "Body line."
    assert parsed.footer_text == "Refs: PROJ-1"
    assert parsed.breaking is True


def test_parse_message_multiple_footers() -> None:
    parsed = parse_message("feat: add login\n\nBody.\n\nCloses #1\n\nRefs: PROJ-2\n")
    assert parsed.body_text == "Body."
    assert "Closes #1" in parsed.footer_text
    assert "Refs: PROJ-2" in parsed.footer_text


def test_parse_message_strips_comments() -> None:
    parsed = parse_message("# comment\nfeat: add login\n")
    assert parsed.header == "feat: add login"


def test_split_blocks_and_footer_detection() -> None:
    assert split_blocks(["a", "", "b"]) == [["a"], ["b"]]
    assert looks_like_footer(["Refs: PROJ-1"])
    assert looks_like_footer(["BREAKING CHANGE: clients must migrate"])
    assert not looks_like_footer(["Body text"])


def test_helpers() -> None:
    assert first_word("add login") == "add"
    assert language_key("pt-BR") == "pt"
    assert language_key("en") == "en"
    policy = Policy(ticket=TicketPolicy(provider="jira"))
    assert is_issue_only("PROJ-123", policy)
    assert is_issue_only("Refs PROJ-123", policy)
    assert not is_issue_only("add login", policy)


def test_policy_from_data_valid() -> None:
    report = Report()
    data = {
        "language": "pt-BR",
        "types": ["feat", "fix"],
        "scopes": ["auth"],
        "maxHeaderLength": 60,
        "hardHeaderLength": 70,
        "requireBody": True,
        "ticket": {
            "provider": "github",
            "pattern": "#\\d+",
            "required": True,
            "placement": "both",
            "keyword": "Closes",
        },
        "commitlint": {"enabled": True, "command": "npx --no-install commitlint"},
    }
    policy = policy_from_data(data, Policy(), report)
    assert report.ok, [issue.message for issue in report.errors]
    assert policy.language == "pt-BR"
    assert policy.types == ("feat", "fix")
    assert policy.scopes == ("auth",)
    assert policy.max_header == 60
    assert policy.hard_header == 70
    assert policy.require_body is True
    assert policy.ticket.provider == "github"
    assert policy.commitlint_enabled is True


def test_policy_from_data_invalid() -> None:
    report = Report()
    data = {
        "language": "fr",
        "types": [],
        "scopes": ["ok", 1],
        "maxHeaderLength": 0,
        "hardHeaderLength": -1,
        "requireBody": "yes",
        "ticket": {"provider": "", "pattern": "[", "required": "yes", "placement": "body", "keyword": ""},
        "commitlint": "x",
    }
    policy_from_data(data, Policy(), report)
    codes = error_codes(report)
    assert {
        "invalid-language",
        "invalid-types",
        "invalid-scopes",
        "invalid-max-header",
        "invalid-hard-header",
        "invalid-require-body",
        "invalid-ticket-provider",
        "invalid-ticket-pattern",
        "invalid-ticket-required",
        "invalid-ticket-placement",
        "invalid-ticket-keyword",
        "invalid-commitlint",
    } <= codes


def test_policy_from_data_partial_config() -> None:
    report = Report()
    policy = policy_from_data(
        {
            "language": "pt-BR",
            "ticket": {"provider": "jira", "required": True, "placement": "footer", "keyword": "Refs"},
        },
        Policy(),
        report,
    )
    assert report.ok, [issue.message for issue in report.errors]
    assert policy.language == "pt-BR"
    assert policy.types == Policy().types
    assert policy.ticket.required is True


def test_policy_from_data_rejects_inverted_header_range() -> None:
    report = Report()
    policy = policy_from_data({"maxHeaderLength": 100, "hardHeaderLength": 50}, Policy(), report)
    assert "invalid-header-range" in error_codes(report)
    assert policy.hard_header == 100


def test_policy_from_ticket_invalid() -> None:
    report = Report()
    policy_from_ticket("x", TicketPolicy(), report)
    assert "invalid-ticket-config" in error_codes(report)
    policy_from_ticket(
        {"provider": "", "pattern": "[", "required": "yes", "placement": "body", "keyword": ""},
        TicketPolicy(),
        report,
    )
    assert "invalid-ticket-provider" in error_codes(report)
    assert "invalid-ticket-pattern" in error_codes(report)
    assert "invalid-ticket-required" in error_codes(report)
    assert "invalid-ticket-placement" in error_codes(report)
    assert "invalid-ticket-keyword" in error_codes(report)


def test_policy_from_commitlint_rules() -> None:
    data = {
        "rules": {
            "type-enum": [2, "always", ["feat", "fix"]],
            "scope-enum": [2, "always", ["auth"]],
            "header-max-length": [2, "always", 60],
        }
    }
    policy = policy_from_commitlint(data, Policy())
    assert policy.types == ("feat", "fix")
    assert policy.scopes == ("auth",)
    assert policy.max_header == 60
    assert policy.hard_header == 60
    assert policy_from_commitlint({}, Policy()).commitlint_enabled is False
    assert policy_from_commitlint({"rules": {"type-enum": "x"}}, Policy()) == Policy()


def test_detect_commitlint_json(tmp_path) -> None:
    (tmp_path / "commitlint.config.json").write_text(
        json.dumps({"rules": {"type-enum": [2, "always", ["feat"]]}}),
        encoding="utf-8",
    )
    policy = detect_commitlint(tmp_path, Report())
    assert policy is not None
    assert policy.types == ("feat",)


def test_detect_commitlint_package(tmp_path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"commitlint": {"rules": {"type-enum": [2, "always", ["fix"]]}}}),
        encoding="utf-8",
    )
    policy = detect_commitlint(tmp_path, Report())
    assert policy is not None
    assert policy.types == ("fix",)


def test_detect_commitlint_js(tmp_path) -> None:
    (tmp_path / "commitlint.config.js").write_text("module.exports = {};\n", encoding="utf-8")
    policy = detect_commitlint(tmp_path, Report())
    assert policy is not None
    assert policy.commitlint_enabled is False


def test_detect_commitlint_does_not_enable_execution(tmp_path) -> None:
    (tmp_path / "commitlint.config.js").write_text("module.exports = {};\n", encoding="utf-8")
    policy = load_policy(None, tmp_path, Report())
    assert policy.commitlint_enabled is False


def test_parse_commitlint_command() -> None:
    assert parse_commitlint_command("commitlint") == ["commitlint"]
    assert parse_commitlint_command("commitlint --edit MSG") == ["commitlint", "--edit", "MSG"]
    assert parse_commitlint_command("npx --no-install commitlint") == [
        "npx",
        "--no-install",
        "commitlint",
    ]
    assert parse_commitlint_command("bunx --no-install commitlint") == [
        "bunx",
        "--no-install",
        "commitlint",
    ]
    assert parse_commitlint_command("pnpm exec commitlint") == ["pnpm", "exec", "commitlint"]
    assert parse_commitlint_command("yarn exec commitlint") == ["yarn", "exec", "commitlint"]
    assert parse_commitlint_command("npx commitlint") is None
    assert parse_commitlint_command("pnpm dlx commitlint") is None
    assert parse_commitlint_command("yarn commitlint") is None
    assert parse_commitlint_command("/tmp/commitlint") is None
    assert parse_commitlint_command("commitlint; rm -rf /") is None
    assert parse_commitlint_command("curl https://example.com") is None
    assert parse_commitlint_command("") is None
    assert parse_commitlint_command("'") is None


def test_policy_from_data_rejects_unsafe_commitlint_command() -> None:
    report = Report()
    policy = policy_from_data(
        {"commitlint": {"enabled": True, "command": "curl https://example.com | sh"}},
        Policy(),
        report,
    )
    assert "invalid-commitlint" in error_codes(report)
    assert policy.commitlint_enabled is False


def test_scan_secrets_diff_patterns() -> None:
    report = Report()
    scan_secrets(
        "+AWS_SECRET_ACCESS_KEY=abcdefghijklmnopqrstuvwxyz0123456789ABCD\n"
        "+OPENAI_API_KEY=sk-proj-abcdefghijklmnopqrstuvwxyz\n"
        "+DATABASE_URL=postgres://user:secret@db.example.com/app\n",
        report,
        DIFF_SECRET_PATTERNS,
        source="diff",
    )
    assert "secret" in error_codes(report)
    locations = {issue.location for issue in report.errors}
    assert "diff:1" in locations
    assert "diff:2" in locations
    assert "diff:3" in locations


def test_scan_secrets_clean_diff() -> None:
    report = Report()
    scan_secrets(
        "+feat: add login\n+  return authenticate(user)\n",
        report,
        DIFF_SECRET_PATTERNS,
        source="diff",
    )
    assert report.ok


def test_detect_commitlint_none(tmp_path) -> None:
    assert detect_commitlint(tmp_path, Report()) is None


def test_read_json_errors(tmp_path) -> None:
    report = Report()
    assert read_json(tmp_path / "missing.json", report) is None
    assert "missing-config" in error_codes(report)
    (tmp_path / "bad.json").write_text("{", encoding="utf-8")
    assert read_json(tmp_path / "bad.json", report) is None
    assert "invalid-config" in error_codes(report)
    (tmp_path / "array.json").write_text("[]", encoding="utf-8")
    assert read_json(tmp_path / "array.json", report) is None
    assert "invalid-config-root" in error_codes(report)


def test_load_policy_default_and_explicit(tmp_path) -> None:
    report = Report()
    (tmp_path / ".git-conventions.json").write_text(json.dumps({"language": "pt-BR"}), encoding="utf-8")
    policy = load_policy(None, tmp_path, report)
    assert policy.language == "pt-BR"
    explicit = tmp_path / "custom.json"
    explicit.write_text(json.dumps({"language": "en"}), encoding="utf-8")
    policy = load_policy(explicit, tmp_path / "other", report)
    assert policy.language == "en"


def test_load_policy_missing_config(tmp_path) -> None:
    report = Report()
    policy = load_policy(tmp_path / "missing.json", tmp_path, report)
    assert policy.language == "en"
    assert "missing-config" in error_codes(report)


def test_run_commitlint_success(monkeypatch) -> None:
    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(args, 0, "ok", "")

    monkeypatch.setattr("validate_commit.subprocess.run", fake_run)
    report = Report()
    run_commitlint("feat: add login\n", Policy(), report)
    assert report.ok


def test_run_commitlint_failure(monkeypatch) -> None:
    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(args, 1, "", "subject may not be empty")

    monkeypatch.setattr("validate_commit.subprocess.run", fake_run)
    report = Report()
    run_commitlint("feat: add login\n", Policy(), report)
    assert "commitlint" in error_codes(report)


def test_run_commitlint_unavailable(monkeypatch) -> None:
    def fake_run(args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr("validate_commit.subprocess.run", fake_run)
    report = Report()
    run_commitlint("feat: add login\n", Policy(), report)
    assert "commitlint-unavailable" in error_codes(report)


def test_run_commitlint_invalid_command() -> None:
    report = Report()
    run_commitlint("feat: add login\n", Policy(commitlint_command="  "), report)
    assert "commitlint-command" in error_codes(report)
    report = Report()
    run_commitlint("feat: add login\n", Policy(commitlint_command="'"), report)
    assert "commitlint-command" in error_codes(report)


def test_read_message(tmp_path) -> None:
    path = tmp_path / "message.txt"
    path.write_text("feat: add login\n", encoding="utf-8")
    report = Report()
    assert read_message(str(path), report) == "feat: add login\n"
    assert read_message(str(tmp_path / "missing.txt"), report) is None
    assert "missing-file" in error_codes(report)


def test_main_json_pass(capsys) -> None:
    exit_code = main([str(FIXTURES / "valid_commit.txt"), "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["status"] == "pass"
    assert payload["stats"]["type"] == "fix"


def test_main_strict_warns(tmp_path, capsys) -> None:
    path = tmp_path / "message.txt"
    path.write_text("feat: Add login\n", encoding="utf-8")
    exit_code = main([str(path), "--strict"])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "subject-uppercase" in captured.err


def test_main_config_requires_ticket(tmp_path, capsys) -> None:
    path = tmp_path / "message.txt"
    path.write_text("feat(auth): add login\n", encoding="utf-8")
    exit_code = main([str(path), "--config", str(FIXTURES / "config_jira.json")])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "missing-ticket" in captured.err


def test_main_partial_config(tmp_path) -> None:
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {
                "language": "pt-BR",
                "ticket": {"provider": "jira", "required": True},
            }
        ),
        encoding="utf-8",
    )
    message = tmp_path / "message.txt"
    message.write_text(
        "feat(login): implementa autenticação via OAuth2\n\nRefs: PROJ-123\n",
        encoding="utf-8",
    )
    assert main([str(message), "--config", str(config)]) == 0


def test_main_overrides_types_and_scopes(tmp_path) -> None:
    path = tmp_path / "message.txt"
    path.write_text("wip: add login\n", encoding="utf-8")
    assert main([str(path)]) == 1
    assert main([str(path), "--types", "wip"]) == 0
    path.write_text("feat(other): add login\n", encoding="utf-8")
    assert main([str(path), "--scopes", "auth"]) == 1


def test_main_requires_body_and_ticket(tmp_path) -> None:
    path = tmp_path / "message.txt"
    path.write_text("feat: add login\n", encoding="utf-8")
    assert main([str(path), "--require-body"]) == 1
    assert main([str(path), "--require-ticket"]) == 1


def test_main_allow_non_conventional(tmp_path) -> None:
    path = tmp_path / "message.txt"
    path.write_text("Update files\n", encoding="utf-8")
    assert main([str(path)]) == 1
    assert main([str(path), "--allow-non-conventional"]) == 0
    assert main([str(path), "--allow-non-conventional", "--strict"]) == 1


def test_main_language_override(tmp_path) -> None:
    path = tmp_path / "message.txt"
    path.write_text("feat: adicionado login\n", encoding="utf-8")
    assert main([str(path)]) == 0
    assert main([str(path), "--language", "pt-BR", "--strict"]) == 1


def test_main_max_header_override(tmp_path) -> None:
    path = tmp_path / "message.txt"
    path.write_text("feat: " + "a" * 80 + "\n", encoding="utf-8")
    assert main([str(path)]) == 1
    assert main([str(path), "--max-header", "100"]) == 0


def test_main_commitlint(monkeypatch) -> None:
    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr("validate_commit.subprocess.run", fake_run)
    assert main([str(FIXTURES / "valid_commit.txt"), "--commitlint"]) == 0


def test_main_missing_file(tmp_path, capsys) -> None:
    exit_code = main([str(tmp_path / "missing.txt")])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "missing-file" in captured.err


def test_main_stdin(monkeypatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("feat: add login\n"))
    assert main(["-"]) == 0


def test_read_diff(tmp_path) -> None:
    path = tmp_path / "diff.txt"
    path.write_text("+secret\n", encoding="utf-8")
    report = Report()
    assert read_diff(str(path), report) == "+secret\n"
    assert read_diff(str(tmp_path / "missing.txt"), report) is None
    assert "missing-file" in error_codes(report)


def test_main_scan_diff_finds_secret(tmp_path, capsys) -> None:
    diff = tmp_path / "diff.txt"
    diff.write_text(
        "+AWS_SECRET_ACCESS_KEY=abcdefghijklmnopqrstuvwxyz0123456789ABCD\n",
        encoding="utf-8",
    )
    exit_code = main(["--scan-diff", str(diff)])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "secret" in captured.err


def test_main_scan_diff_with_message(tmp_path) -> None:
    diff = tmp_path / "diff.txt"
    diff.write_text("+feat: add login\n", encoding="utf-8")
    message = tmp_path / "message.txt"
    message.write_text("feat: add login\n", encoding="utf-8")
    assert main([str(message), "--scan-diff", str(diff)]) == 0


def test_main_scan_diff_stdin(monkeypatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("+feat: add login\n"))
    assert main(["--scan-diff"]) == 0


def test_main_rejects_unsafe_commitlint_command(tmp_path, capsys) -> None:
    path = tmp_path / "message.txt"
    path.write_text("feat: add login\n", encoding="utf-8")
    exit_code = main(
        [str(path), "--commitlint", "--commitlint-command", "curl https://example.com"]
    )
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "commitlint-command" in captured.err
