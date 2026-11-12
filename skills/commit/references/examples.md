# Exemplos

## Inglês

### Válidos

```text
feat(auth): add OAuth2 login
fix(cart): correct free shipping for discounted items
docs(readme): document the commit policy
style(api): apply the formatter
refactor(db): extract the connection pool
perf(search): cache prefix queries
test(auth): cover expired session handling
build(deps): bump TailwindCSS to 4.1
ci(github): cache Python dependencies
chore(git): ignore coverage output
revert: add token validation
```

Com corpo e rodapé:

```text
fix(auth): reject tokens without an expiry claim

Tokens issued before v2 did not include the exp claim. The handler accepted
them until the signature check, which returned a 500 instead of a 401.

Closes #482
```

Breaking change:

```text
refactor(api)!: remove the legacy token endpoint

BREAKING CHANGE: clients must migrate to /v2/tokens before the next release.
```

### Inválidos

| Mensagem | Problema |
| --- | --- |
| `Feat: add login` | Tipo em maiúsculas. |
| `feat: Add login.` | Descrição em maiúscula e com ponto final. |
| `feat: added login` | Particípio, não imperativo. |
| `feat: adding login` | Gerúndio, não imperativo. |
| `feat: login` | Falta o verbo imperativo. |
| `fix: fixed the bug` | Particípio e descrição vaga. |
| `update files` | Falta o tipo. |
| `feat: update files` | Descrição vaga. |
| `feat: PROJ-123` | Ticket usado como descrição. |
| `feat(auth): add login.` | Ponto final. |

## Português brasileiro

Ative com `"language": "pt-BR"` em `.git-conventions.json`.

### Válidos

```text
feat(login): implementa autenticação via OAuth2
fix(carrinho): corrige cálculo de frete grátis para produtos em promoção
docs(readme): documenta a política de commits
style(api): aplica o formatador
refactor(db): extrai o pool de conexões
perf(busca): adiciona cache para consultas por prefixo
test(login): cobre sessões expiradas
build(deps): atualiza o TailwindCSS para 4.1
ci(github): adiciona cache de dependências Python
chore(git): ignora a saída de cobertura
revert: adiciona validação de token
```

Com corpo e rodapé:

```text
fix(login): rejeita tokens sem claim de expiração

Tokens emitidos antes da v2 não incluíam a claim exp. O handler os aceitava até
a checagem de assinatura, retornando 500 em vez de 401.

Closes #482
```

Breaking change:

```text
refactor(api)!: remove o endpoint legado de tokens

BREAKING CHANGE: os clientes devem migrar para /v2/tokens antes da próxima versão.
```

### Inválidos

| Mensagem | Problema |
| --- | --- |
| `Feat: adiciona login` | Tipo em maiúsculas. |
| `feat: adiciona login.` | Ponto final. |
| `feat: adicionado login` | Particípio, não imperativo. |
| `feat: adicionando login` | Gerúndio, não imperativo. |
| `feat: login` | Falta o verbo imperativo. |
| `fix: corrigiu o bug` | Pretérito e descrição vaga. |
| `atualiza arquivos` | Falta o tipo. |
| `feat: atualiza arquivos` | Descrição vaga. |
| `feat: PROJ-123` | Ticket usado como descrição. |

## Comparações

| Fraco | Melhor |
| --- | --- |
| `feat: updates` | `feat(auth): add token validation` |
| `fix: bug` | `fix(cart): correct free shipping for discounted items` |
| `docs: docs` | `docs(api): document the rate limit headers` |
| `refactor: changes` | `refactor(db): extract the connection pool` |
| `test: tests` | `test(auth): cover expired session handling` |
| `chore: stuff` | `chore(deps): bump TailwindCSS to 4.1` |
| `feat: PROJ-123 login` | `feat(auth): add login` + `Refs: PROJ-123` |

## Ticket no assunto vs rodapé

Assunto:

```text
feat(auth): PROJ-123 add OAuth2 login
```

Rodapé:

```text
feat(auth): add OAuth2 login

Refs: PROJ-123
```

Prefira o rodapé. O assunto fica legível e o ticket continua rastreável.

## Múltiplas mudanças

Diff com feature e correção não relacionadas:

```text
feat(profile): add avatar upload
fix(cart): correct free shipping for discounted items
```

Não use:

```text
feat: add avatar upload and fix cart
```
