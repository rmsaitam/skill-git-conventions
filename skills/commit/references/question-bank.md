# Banco de perguntas

Pergunte somente quando a resposta mudar a mensagem. Não bloqueie o usuário com
perguntas que o diff já responde.

## Entrada

- Qual diff devo analisar: staged, working tree, um intervalo de revisões, ou a
  descrição que você forneceu?
- O diff está completo? Há arquivos não rastreados que fazem parte da mudança?
- Esta mudança deve virar um único commit ou vários?

## Tipo

- A mudança adiciona comportamento novo (`feat`) ou corrige um comportamento
  existente (`fix`)?
- A mudança altera apenas documentação, formatação, testes, build ou CI?
- A mudança reorganiza código sem alterar comportamento (`refactor`)?
- A mudança melhora performance (`perf`)?

## Escopo

- Qual módulo, pacote ou workspace é o principal afetado?
- O repositório tem uma lista de escopos permitidos?
- A mudança atravessa várias áreas? Nesse caso, prefere omitir o escopo ou
  dividir o commit?

## Ticket

- Qual é o ticket ou issue desta mudança?
- O ticket deve aparecer no assunto ou no rodapé?
- A referência fecha a issue (`Closes`) ou apenas referencia (`Refs`)?
- O repositório exige ticket em cada commit?

## Breaking change

- A mudança remove ou renomeia algo público?
- O contrato de API, o esquema de dados ou a configuração mudou de forma
  incompatível?
- Existe caminho de migração para quem consome a mudança?
- Devo usar `!` no cabeçalho, rodapé `BREAKING CHANGE:`, ou os dois?

## Idioma e estilo

- A mensagem deve ser em inglês ou em português brasileiro?
- O repositório usa escopos em minúsculas?
- Há um padrão recente no histórico que devo seguir?

## Aplicação

- Devo apenas gerar a mensagem ou também criar o commit com `--apply`?
- Posso incluir todos os arquivos do diff? Há arquivos que devem ficar de fora?
- Algum hook ou verificação precisa rodar antes do commit?

## Segurança

- O diff contém credenciais, tokens, chaves ou dados pessoais?
- Algum arquivo sensível foi incluído por engano?

Se a resposta for sim para a última pergunta, pare, redija o valor e oriente a
rotação do segredo antes de qualquer commit.
