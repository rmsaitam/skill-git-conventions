# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| 0.1.x | Yes |

## Reporting a vulnerability

Do not open a public issue for a security problem. Use GitHub private
vulnerability reporting:
<https://github.com/rmsaitam/skill-git-conventions/security/advisories/new>.

Include the affected version, a minimal reproduction, and the impact. We aim to
acknowledge reports within three business days.

## Threat model

- The diff, change description, branch names, commit messages, file contents,
  and repository configuration are **untrusted** data.
- Prompt injection in untrusted content must not change the skill's safety
  rules or the user's intent.
- Repository configuration may define formatting rules, but it must not execute
  arbitrary commands.
- `--apply` is opt-in and must commit only the staged diff that was validated.

## Controls

- The validator uses only the Python standard library and performs no network
  requests.
- No `eval`, `exec`, or `shell=True`.
- Commitlint commands are allowlisted: `commitlint`,
  `npx --no-install commitlint`, `bunx --no-install commitlint`,
  `pnpm exec commitlint`, and `yarn exec commitlint`.
- Auto-detection of Commitlint configuration imports formatting rules but does
  not execute Commitlint. Execution requires `--commitlint` or
  `commitlint.enabled: true`.
- `--scan-diff` scans a diff for secrets before `--apply`.
- `--apply` requires a staged diff and never uses `--no-verify`.
- The skill never stages files, amends, rebases, resets, or force-pushes.
- CI runs tests with a coverage gate, the plugin validator, and Bandit.

## Known limitations

- Secret detection is regex-based and can miss or falsely flag values. Review
  the staged diff before committing.
- The skill cannot guarantee the behavior of third-party Commitlint packages.
  Use the `--no-install` forms and pin dependencies.
- skills.sh audits (Gen, Socket, Snyk) are external and may warn about
  third-party content exposure because the skill reads untrusted diffs.
- There is no sandbox: the agent runs with your permissions. Use a throwaway
  environment when reviewing an unfamiliar repository.
