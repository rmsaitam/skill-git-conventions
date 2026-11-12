# Regras da empresa

Este documento mostra como adaptar o skill `commit` às regras de Jira, Linear,
GitHub, GitLab e Commitlint. A configuração fica em `.git-conventions.json` na
raiz do repositório.

## Precedência

1. Flags de linha de comando.
2. `.git-conventions.json`.
3. Configuração do Commitlint detectada no repositório.
4. Padrões internos do skill.

## Formato da configuração

```json
{
  "language": "en",
  "types": ["feat", "fix", "docs", "style", "refactor", "perf", "test", "build", "ci", "chore", "revert"],
  "scopes": ["auth", "api", "ui", "db", "ci", "deps"],
  "maxHeaderLength": 72,
  "hardHeaderLength": 80,
  "ticket": {
    "provider": "jira",
    "pattern": "[A-Z][A-Z0-9]+-\\d+",
    "required": true,
    "placement": "footer",
    "keyword": "Refs"
  },
  "commitlint": {
    "enabled": false,
    "command": "npx --no-install commitlint"
  }
}
```

Campos:

| Campo | Valores | Efeito |
| --- | --- | --- |
| `language` | `en`, `pt-BR` | Idioma esperado na descrição. |
| `types` | lista | Tipos permitidos. |
| `scopes` | lista ou `null` | Escopos permitidos; `null` aceita qualquer escopo válido. |
| `maxHeaderLength` | inteiro | Limite preferido do cabeçalho. Acima disso, aviso. |
| `hardHeaderLength` | inteiro | Limite máximo do cabeçalho. Acima disso, erro. |
| `ticket.provider` | `jira`, `linear`, `github`, `gitlab`, `generic` | Padrão de referência. |
| `ticket.pattern` | regex | Sobrescreve o padrão do provedor. |
| `ticket.required` | booleano | Exige a referência no commit. |
| `ticket.placement` | `subject`, `footer`, `both` | Onde a referência deve aparecer. |
| `ticket.keyword` | texto | Palavra usada no rodapé. |
| `commitlint.enabled` | booleano | Executa o Commitlint; exige opt-in explícito. |
| `commitlint.command` | texto | Comando allowlisted; padrão `commitlint`. |

## Jira

Referência no formato `PROJ-123`.

Rodapé (recomendado):

```text
feat(auth): add OAuth2 login

Refs: PROJ-123
```

No assunto:

```text
feat(auth): PROJ-123 add OAuth2 login
```

Configuração:

```json
{
  "ticket": {
    "provider": "jira",
    "pattern": "[A-Z][A-Z0-9]+-\\d+",
    "required": true,
    "placement": "footer",
    "keyword": "Refs"
  }
}
```

Encontre o ticket no nome da branch:

```bash
git branch --show-current
```

Exemplo de branch: `feature/PROJ-123-login`. O ticket é `PROJ-123`.

## Linear

Referência no formato `ENG-456`.

```text
fix(api): ENG-456 correct the rate limit window

Refs: ENG-456
```

Configuração:

```json
{
  "ticket": {
    "provider": "linear",
    "pattern": "[A-Z][A-Z0-9]+-\\d+",
    "required": true,
    "placement": "footer",
    "keyword": "Refs"
  }
}
```

## GitHub

Referência no formato `#123`.

```text
fix(auth): reject expired sessions

Closes #123
```

Regras:

- Use `Closes`, `Fixes` ou `Resolves` somente quando o commit realmente fecha a
  issue.
- Use `Refs #123` ou `Related to #123` quando a issue deve continuar aberta.

Configuração:

```json
{
  "ticket": {
    "provider": "github",
    "pattern": "#\\d+",
    "required": false,
    "placement": "footer",
    "keyword": "Refs"
  }
}
```

## GitLab

Referências:

- Issue: `#123`.
- Merge request: `!45`.

```text
feat(ui): add dark mode

Closes #123
See merge request !45
```

Configuração:

```json
{
  "ticket": {
    "provider": "gitlab",
    "pattern": "(?:#\\d+|!\\d+)",
    "required": false,
    "placement": "footer",
    "keyword": "Refs"
  }
}
```

## Commitlint

Quando o repositório usa Commitlint, o skill deve respeitar as regras do
projeto. A detecção automática lê `type-enum`, `scope-enum` e
`header-max-length` de arquivos JSON, mas **não executa** o Commitlint. A
execução exige `--commitlint` ou `"enabled": true`. Quando a configuração é
JavaScript ou TypeScript, use `--commitlint` para delegar a checagem final.

Comandos aceitos: `commitlint`, `npx --no-install commitlint`,
`bunx --no-install commitlint`, `pnpm exec commitlint` e
`yarn exec commitlint`. O padrão é o binário local `commitlint`; evite `npx`
sem `--no-install` para não baixar um pacote não fixado.

Exemplo de `commitlint.config.js`:

```js
module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [2, 'always', ['feat', 'fix', 'docs', 'refactor', 'test', 'chore']],
    'scope-enum': [2, 'always', ['auth', 'api', 'ui', 'db', 'ci', 'deps']],
    'header-max-length': [2, 'always', 72],
    'subject-case': [2, 'never', ['sentence-case', 'start-case', 'pascal-case', 'upper-case']],
    'subject-full-stop': [2, 'never', '.'],
    'body-max-line-length': [1, 'always', 100]
  }
};
```

Exemplo de `package.json`:

```json
{
  "commitlint": {
    "extends": ["@commitlint/config-conventional"]
  }
}
```

Hook local com Husky:

```bash
npx husky add .husky/commit-msg 'npx --no-install commitlint --edit "$1"'
```

Validação manual:

```bash
npx --no-install commitlint --edit .git/COMMIT_EDITMSG
```

## Validação combinada

O validador interno cobre o formato e as regras de ticket. O Commitlint cobre as
regras específicas do projeto. Use os dois:

```bash
python3 <path-to-skill>/scripts/validate_commit.py <message-file> --config .git-conventions.json --commitlint
```

## Exemplo completo

`.git-conventions.json` para um time que usa Jira, inglês e escopos fechados:

```json
{
  "language": "en",
  "types": ["feat", "fix", "refactor", "perf", "test", "docs", "build", "ci", "chore", "revert"],
  "scopes": ["auth", "billing", "api", "ui", "db", "ci", "deps"],
  "maxHeaderLength": 72,
  "hardHeaderLength": 80,
  "ticket": {
    "provider": "jira",
    "pattern": "[A-Z][A-Z0-9]+-\\d+",
    "required": true,
    "placement": "footer",
    "keyword": "Refs"
  },
  "commitlint": {
    "enabled": true,
    "command": "npx --no-install commitlint"
  }
}
```

Resultado:

```text
feat(billing): add proration for plan upgrades

Refs: BILL-482
```
