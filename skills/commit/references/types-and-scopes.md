# Tipos e escopos

## Tipos

Escolha o tipo que representa a mudança dominante, não o maior arquivo do diff.

| Tipo | Quando usar | Exemplos |
| --- | --- | --- |
| `feat` | Nova funcionalidade ou comportamento visível ao usuário. | Novo endpoint, nova tela, novo filtro. |
| `fix` | Correção de bug ou comportamento incorreto. | Corrigir cálculo, tratar erro, evitar condição de corrida. |
| `docs` | Somente documentação. | README, comentários de API, guias. |
| `style` | Formatação sem mudança de lógica. | Espaços, ponto e vírgula, lint de estilo. |
| `refactor` | Reestruturação sem corrigir bug nem adicionar funcionalidade. | Extrair função, renomear variável, mover módulo. |
| `perf` | Melhoria de performance. | Cache, índice, reduzir alocações. |
| `test` | Adição ou correção de testes. | Testes unitários, integração, fixtures. |
| `build` | Sistema de build ou dependências externas. | npm, pip, Maven, Gradle, Dockerfile. |
| `ci` | Arquivos e scripts de integração contínua. | GitHub Actions, GitLab CI, Jenkins. |
| `chore` | Manutenção que não altera código nem testes. | `.gitignore`, `.editorconfig`, scripts locais. |
| `revert` | Reverte um commit anterior. | Reverter deploy, reverter feature. |

## Como decidir

1. A mudança adiciona comportamento novo? `feat`.
2. A mudança corrige um comportamento errado? `fix`.
3. A mudança altera somente documentação? `docs`.
4. A mudança altera somente formatação? `style`.
5. A mudança só reorganiza código? `refactor`.
6. A mudança só melhora performance? `perf`.
7. A mudança só adiciona ou corrige testes? `test`.
8. A mudança afeta build ou dependências? `build`.
9. A mudança afeta CI? `ci`.
10. A mudança é manutenção sem código ou testes? `chore`.
11. A mudança reverte um commit? `revert`.

Quando o diff mistura categorias, divida em commits separados. Se o usuário
quiser um único commit, use o tipo dominante e explique as mudanças secundárias
no corpo.

## Escopos

O escopo é opcional. Use quando ele acrescenta informação sobre a área afetada.

Boas práticas:

- Use o nome do módulo, pacote ou workspace: `auth`, `api`, `billing`, `ui`.
- Use minúsculas e evite espaços.
- Não use o nome do arquivo como escopo.
- Não use escopo quando a mudança atravessa várias áreas sem um eixo comum.
- Em monorepos, use o nome do pacote como escopo.
- Quando o repositório tem uma lista de escopos permitidos, use um valor dela.

Exemplos:

```text
feat(auth): add OAuth2 login
fix(billing): correct invoice rounding
refactor(db): extract connection pool
docs(api): document rate limits
chore(deps): bump TailwindCSS to 4.1
```

## Escopos em monorepos

```text
feat(@app/web): add dark mode toggle
fix(@app/api): reject expired sessions
build(@app/ui): publish 2.0.0
```

Regras:

- Use o nome do pacote exatamente como aparece no manifesto.
- Se o pacote tiver escopo npm, mantenha o prefixo `@`.
- Se a mudança afetar a raiz do monorepo, omita o escopo ou use `repo`.
