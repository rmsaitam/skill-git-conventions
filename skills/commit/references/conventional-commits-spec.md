# Conventional Commits v1.0.0

Resumo operacional da especificação usada pelo skill `commit`.

## Estrutura

```text
<tipo>[escopo opcional][!]: <descrição>

[corpo opcional]

[rodapé(s) opcional(is)]
```

- O cabeçalho é obrigatório e ocupa uma única linha.
- O corpo e os rodapés são opcionais.
- Corpo e rodapés são separados do cabeçalho por uma linha em branco.
- Rodapés são separados do corpo por uma linha em branco.
- Não há limite rígido de tamanho no corpo, mas quebre as linhas em 72
  caracteres para facilitar a leitura.

## Cabeçalho

Formato:

```text
<tipo>(<escopo>)!: <descrição>
```

- `tipo`: um dos tipos permitidos, em minúsculas.
- `escopo`: opcional, entre parênteses, descreve o módulo ou componente.
- `!`: opcional, indica uma breaking change.
- `descrição`: resumo curto no modo imperativo, sem ponto final.

Exemplos válidos:

```text
feat: add user profile page
fix(api): reject expired sessions
refactor(parser)!: remove the legacy grammar
docs(readme): document the release process
```

## Corpo

Use o corpo para explicar o motivo da mudança e o comportamento anterior.

```text
fix(auth): reject tokens without an expiry claim

Tokens issued before v2 did not include the exp claim. The handler accepted
them until the signature check, which caused a 500 instead of a 401.
```

Regras:

- Separe o corpo do cabeçalho com uma linha em branco.
- Explique o "porquê" antes do "o quê".
- Não repita a descrição do cabeçalho.
- Não use marcadores de tarefa pendente.

## Rodapés

Formato:

```text
<token>: <valor>
```

Tokens comuns:

```text
BREAKING CHANGE: the /v1/tokens endpoint now rejects legacy tokens.
Refs: PROJ-123
Closes #123
Reviewed-by: Ana Silva
Co-authored-by: Bruno Souza <bruno@example.com>
```

- `BREAKING CHANGE` deve ser escrito exatamente assim, em maiúsculas, com um
  espaço ou hífen (`BREAKING-CHANGE`).
- Um rodapé pode ocupar várias linhas; as linhas seguintes são continuação do
  valor.
- Referências de issue usam o formato do provedor do repositório.

## Breaking changes

Uma breaking change acontece quando o commit quebra a compatibilidade com a
versão anterior. Duas formas de sinalizar:

1. `!` depois do tipo ou do escopo:

   ```text
   refactor(api)!: remove the legacy token endpoint
   ```

2. Rodapé `BREAKING CHANGE:`:

   ```text
   refactor(api): remove the legacy token endpoint

   BREAKING CHANGE: clients must migrate to /v2/tokens.
   ```

Recomendação: use `!` no cabeçalho e um rodapé `BREAKING CHANGE:` com o caminho
de migração. O `!` chama a atenção; o rodapé explica o impacto.

## Revert

Para reverter um commit anterior:

```text
revert: add token validation

This reverts commit 1a2b3c4d5e6f.

Refs: 1a2b3c4d5e6f
```

- Use o tipo `revert`.
- Mantenha o assunto original quando possível.
- Referencie o commit revertido no corpo ou no rodapé.

## Tipos permitidos

```text
feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert
```

A lista pode ser restringida por `.git-conventions.json` ou pelo Commitlint do
repositório.

## Erros comuns

| Erro | Correção |
| --- | --- |
| `Feat: add login` | `feat: add login` (tipo em minúsculas) |
| `feat: Add login.` | `feat: add login` (imperativo, sem ponto) |
| `fix: fixed the bug` | `fix: correct the bug` |
| `feat: adding login` | `feat: add login` |
| `feat: login` | `feat(auth): add login` (verbo imperativo) |
| `update files` | `chore: update dependencies` (tipo obrigatório) |
| `feat: PROJ-123` | `feat(auth): add login` + `Refs: PROJ-123` |
| `feat!: changes` | `feat(api)!: remove the legacy endpoint` |

## Idiomas

A descrição deve seguir o idioma configurado no repositório. O padrão deste
skill é inglês; use `"language": "pt-BR"` para português brasileiro.

Em pt-BR, o imperativo costuma terminar em `-a`, `-e` ou `-i`:

```text
feat(login): implementa autenticação via OAuth2
fix(carrinho): corrige cálculo de frete grátis
refactor(api): extrai o cliente HTTP
```

Evite formas no particípio (`adicionado`, `corrigido`) e no gerúndio
(`adicionando`, `corrigindo`).
