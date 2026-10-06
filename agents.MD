# Gestor de Contratos (Omega) — instruções para o agente

Projeto acadêmico FIAP (CP2). Back-end Flask em `api/app.py` + PostgreSQL (AWS RDS). Front-end HTML/JS/CSS em `frontend/` (páginas, `js/`, `css/`), servido em 127.0.0.1:8000. Testes com pytest.

## Produto
- O usuário é o **gestor de contratos de uma empresa**. Ele cadastra seus contratos e usa a IA como **suporte** para destacar cláusulas com impacto financeiro (ex.: multa de rescisão de 20%).
- Ferramenta self-service. Não há equipe verificando contratos nem painel de funcionários.
- Cada usuário tem a própria carteira. Sem múltiplos usuários por empresa.

## Estado atual (atualizar conforme avançar)
- Existem: `POST /auth/login`, `POST /auth/registrar`, CRUD em `/contratos` e `/clausulas`.
- Faltam: isolamento por usuário (hoje qualquer usuário logado vê tudo), paginação e filtros em `GET /contratos`, `GET /dashboard/resumo`, análise com LLM (`POST /contratos/{id}/analisar`) e confirmar/corrigir/descartar cláusula.
- Se um endpoint necessário não existir: fazer tudo o que for possível sem ele, deixar a tela em estado "indisponível" e listar a lacuna. Nunca inventar endpoints nem dados.

## Papéis e autenticação
- `usuario` é o papel principal. `admin` é opcional e só gerencia usuários.
- O autocadastro (`/registrar`) cria SEMPRE `usuario`. O papel nunca vem do corpo da requisição.
- Senha com hash (bcrypt ou argon2). Login devolve token com o id do usuário.
- Após o login, redirecionar para o dashboard do usuário.

## Regras obrigatórias do backend
- **Todo endpoint de contratos, cláusulas e dashboard filtra por `usuario_id` do token.** Nunca aceitar `usuario_id` no corpo. Cláusulas checam o dono pelo contrato.
- Contrato ou cláusula de outro usuário responde **404**.
- Validação de entrada com schemas (usar a biblioteca já adotada no projeto) e limite de tamanho no texto das cláusulas.
- Erros em JSON padronizado: usar o formato já existente no projeto e o mesmo em todos os endpoints.
- Listagens com paginação e filtros.
- Swagger/OpenAPI com tags separadas (auth, contratos, dashboard) e descrições atualizadas. O Flask não gera isso sozinho: usar a biblioteca já adotada no projeto.
- Segredos (credenciais do RDS, chave da LLM) só em variáveis de ambiente. Nunca no código nem no repositório (`.env` no `.gitignore`).

## Banco
- Contratos pertencem a um usuário (`usuario_id`, FK com índice).
- Contratos têm data de término, para alertas de vencimento.
- Cláusulas ligadas ao contrato, com o resultado da análise da IA.
- Confirmar nomes de tabelas e colunas com o modelo atual antes de alterar. Mudanças de schema com migração.

## Análise de cláusulas com LLM (a implementar)
- Provedor planejado: **API do Gemini, nível gratuito**. Chave em variável de ambiente, faturamento desativado. Não usar Bedrock (a conta AWS do lab não tem permissão).
- Chamada isolada em uma função `analisar_clausulas(texto)`, para trocar de provedor em um único lugar.
- **Uma chamada única com saída estruturada.** Não usar agente nem chatbot genérico.
- Entrada: apenas o texto das cláusulas, **sem nomes, CNPJ ou dados pessoais**. No nível gratuito o conteúdo pode ser usado pelo provedor, então a demo e os testes usam só contratos fictícios.
- Saída em JSON validado por schema, lista de cláusulas com: tipo, valor ou percentual, nível de impacto (baixo, médio, alto) e `trecho_original`.
- Conferir por código que `trecho_original` existe no texto enviado. Se não existir, descartar a cláusula.
- O texto do contrato é entrada não confiável (prompt injection): instruções do sistema separadas do conteúdo, e a saída sempre validada.
- Tratar JSON inválido, timeout e limite de uso da API com retry limitado e erro claro.
- Salvar o resultado no banco e reutilizar. Reanalisar só se o texto mudar. Guardar modelo e versão do prompt usados.
- O usuário pode revisar e corrigir o resultado. Na tela, mostrar o trecho original ao lado e o aviso "Análise automática. Confira no contrato original."

## Dashboard
- Dados reais do banco, filtrados pelo dono. Nada fixo no front.
- Indicadores: valor total da carteira, contratos por tipo, cláusulas de alto impacto, contratos vencendo em 30 dias (consulta SQL, sem LLM).

## Front-end
- Todo dado vem da API. Estados de carregando, vazio e erro. Feedback em toda ação e botões desabilitados durante requisições.
- Sem token: redirecionar para o login. Resposta 401: fazer logout.
- Texto de contrato e texto gerado pela IA são entrada não confiável: renderizar com `textContent` ou escape, nunca com `innerHTML`.
- Visual sóbrio e editorial, de empresa séria de contratos e finanças. A landing tem tema único claro, sem modo escuro, e CSS próprio (`css/landing.css`).
- Tokens: papel `#FAF8F3`, branco `#FFFFFF`, tinta `#14181F`, apoio `#5B6470`, linhas `#E4DFD3`, verde `#1F4D3A`, marca-texto `#FFE58A` (só em trechos destacados de contrato), risco `#B42318` (só em impacto alto). Fontes: Newsreader (títulos) e DM Sans (texto). Raio máximo de 6px, bordas de 1px.
- Evitar: gradientes, glassmorphism, brilho, emojis, ícones dentro de círculos, grades de cards iguais com ícone, blocos de estatísticas, tudo centralizado.
- Ao refazer as telas internas, reaproveitar esses tokens.

## Ícones
- Biblioteca única: Lucide (https://lucide.dev). Não usar glifos de texto (→ ↗ ■ ✓), emojis nem outras bibliotecas.
- Como usar: SVG inline via sprite em img/icons.svg (<symbol> + <use>), sem CDN e sem dependência nova. Copiar o path do ícone no lucide.dev.
- Estilo: stroke currentColor, stroke-width 1.5, 16px (14px dentro de texto corrido), fill none. Cor herdada do texto.
- Acessibilidade: ícone decorativo com aria-hidden="true". Ícone sozinho em botão precisa de aria-label.
- Restrições da spec continuam valendo: sem ícone dentro de círculo ou quadrado com fundo e sem grade de cards iguais com ícone. Ícone entra só onde carrega significado (ação, status, data).

## Espaçamento
- Escala fixa em variáveis CSS: 4, 8, 12, 16, 24, 32, 48, 64, 96px. Não usar valores fora dela.
- Seções: 96px de padding vertical no desktop, 64px no mobile.
- Linhas de lista: padding vertical simétrico (24px) e coluna de número com largura fixa, igual em todas as listas.

## Testes (pytest)
- Usuário A não vê, lista, altera nem exclui contrato ou cláusula do usuário B (404).
- Autocadastro nunca cria admin, mesmo com `papel` no corpo.
- Sem token: 401.
- Paginação e filtros.
- Validação do JSON da LLM, com a LLM simulada (mock). Trecho inexistente é descartado.

## Como trabalhar
- Alterar só o que foi pedido: se a tarefa é o front, não mexer no backend, e vice-versa.
- Antes de editar, mostrar um plano curto dos arquivos que serão alterados.
- Uma tarefa por vez. Não adicionar dependências sem avisar. Não mudar o comportamento de endpoints existentes sem dizer.

## Fora do escopo
Assinatura digital de contrato, pagamento e planos, múltiplos usuários por empresa, agentes, chatbot genérico.