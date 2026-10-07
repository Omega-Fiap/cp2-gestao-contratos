# Auditoria do CP2 – Gestor de Contratos

Verificação do projeto contra os critérios do Checkpoint 2 (06/10).

## Problema grave: os testes apagam o banco real

Os testes não usam SQLite como o README diz. O `api/app.py:31` cria o `SQLAlchemy(app)` com a URL do PostgreSQL do `.env`. Os testes só trocam `SQLALCHEMY_DATABASE_URI` depois disso, e no Flask-SQLAlchemy 3.1 essa troca não muda a conexão. Testado: mesmo depois da troca, `db.engine` continua apontando para o host do RDS. Cada fixture termina com `db.drop_all()`, então **rodar `pytest -q` apaga as tabelas do banco real**.

- Uma execução de `pytest -q` foi feita durante a auditoria e travou por mais de 2 minutos (foi interrompida).
- Depois, a listagem de tabelas do RDS (somente leitura) retornou `[]`: **o banco está vazio**.
- O cache do pytest mostra execuções hoje às 17:35, então as tabelas podem ter sido apagadas antes. Não dá para descartar que a execução da auditoria também tenha apagado.

**O que fazer antes da apresentação:**
- Recriar o schema (`python -m api.app` executa o `create_all`) e cadastrar de novo os dados de demonstração.
- Corrigir os testes: ler `DATABASE_URL` do ambiente e usar `sqlite://` em teste, ou criar o app com uma factory que recebe a configuração.
- Enquanto isso não for corrigido, **não rodar `pytest` com o `.env` preenchido**.

Rodando com um plugin temporário (fora do repositório) que força SQLite: **29 testes passaram**, com 100 avisos de depreciação de `datetime.utcnow()`.

## Situação por critério

| Critério (pts) | Situação | Observações |
|---|---|---|
| Backend (0,5) | Parcial | Autenticação por token, isolamento por usuário (dados de outro usuário respondem 404) e erros em JSON padronizado. **Problemas:** `PUT /contratos` não valida valor negativo nem término antes do início (o `/formulario` valida); sem `SECRET_KEY` usa chave padrão fixa; `debug=True` em `0.0.0.0`; CORS `*` por padrão; `POST /usuarios` responde 405 |
| Frontend + API (2,0) | Atende | Login, registro, formulário de cadastro, dashboard, verificação, exclusão, análise com IA e revisão. Feedback das operações, tratamento do 401 e botões desabilitados durante requisições. Não há tela para editar contrato (o `PUT /contratos` não é usado no front) |
| Dashboard (2,0) | Atende, com lacuna | Indicadores e gráficos (Chart.js) com dados reais de `/dashboard/resumo`, tabelas e detalhe do contrato. Falta a **contagem de cláusulas de alto impacto** (o README já reconhece) |
| Otimização (0,5) | Parcial | Paginação e filtros (`status`, `tipo_contrato`, `q`), agregações em SQL e reaproveitamento da análise pelo hash do texto. **Porém** o dashboard baixa todas as páginas de contratos (`dashboard.js:33`), anulando a paginação. `GET /clausulas` e `/clientes` não têm paginação |
| Banco (1,0) | Parcial | 4 migrações com índices, chave única `(usuario_id, documento)` e tabelas da análise separadas. **Inconsistências:** no model, `Contrato.usuario_id` aceita nulo e não tem índice, mas a migração 004 define NOT NULL. FKs de cláusula, aditivo e histórico sem `ondelete` (só o cascade do ORM). Falta texto justificando a modelagem |
| Documentação/Swagger (0,5) | Parcial | Swagger em OpenAPI 3 com tags. **Faltam** `/aditivos`, `/historico-status`, `/usuarios`, `/clientes/{id}` e PUT/DELETE de `/clausulas/{id}`. O README tem seção nova do CP2 no topo, mas o restante está desatualizado (AWS Lambda, `python app.py`, tabela de endpoints sem `/auth`, `/dashboard` e `/analisar`, variáveis sem `SECRET_KEY`, `GEMINI_*` e `CORS_ORIGIN`) |
| Testes (1,0) | Atende o escopo, mas perigoso | 29 testes: isolamento A/B, autocadastro sem papel de admin, 401, paginação, LLM simulada e descarte de trecho inexistente. Corrigir o problema do banco antes de demonstrar. `pytest` não está no `requirements.txt` |
| LLM (1,0) | Atende | Gemini com saída JSON validada por schema, conferência de `trecho_original` no texto, bloqueio de dados pessoais, retry, reaproveitamento por hash, modelo e versão do prompt salvos e revisão confirmar/corrigir/descartar. Confirmar se o modelo `gemini-3.8-flash` do `.env.example` existe |
| Trello (0,5) | Não verificável | Link no README; confirmar se o quadro está atualizado |
| Apresentação (1,0) | Não se aplica | — |

## Outras pendências

- **Nada do CP2 foi commitado.** Testes, migrações, Swagger, CSS novo e as mudanças no `app.py` estão pendentes. O entregável 1 ("repositório atualizado") não atende até haver commit e push.
- Remover `api/tempCodeRunnerFile.py` (sobra do VS Code) antes do commit.
- O dashboard carrega o Chart.js por CDN; sem internet os gráficos não aparecem (há mensagem de fallback).

## Prioridades

1. Corrigir o banco dos testes e recriar o RDS.
2. Fazer commit e push.
3. Completar Swagger e README.
4. Adicionar o indicador de cláusulas de alto impacto e a validação no `PUT /contratos`.
