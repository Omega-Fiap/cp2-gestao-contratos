/* Dashboard de gestão de contratos */

(function () {
  const VERIFICADO = "verificado";
  const S = { contratos: [], clientes: new Map(), aditivos: [], resumo: null, busca: "" };
  const charts = {};
  const $ = (s) => document.querySelector(s);

  const verificado = (c) => c.status === VERIFICADO;
  const nomeCliente = (c) => (S.clientes.get(c.cliente_id) || {}).nome || "—";
  const cor = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();

  /* ---------------- Início ---------------- */

  async function iniciar() {
    if (!Auth.token()) {
      location.replace("login.html");
      return;
    }

    try {
      const eu = await api("/auth/me");
      Auth.salvar(Auth.token(), eu);
    } catch (err) {
      if (err.status === 401) return Auth.sair();
      toast(err.message, "erro");
    }

    const u = Auth.usuario();
    $("#user-chip").textContent = u ? u.nome : "";
    await carregar();
  }

  // Uma única página (mais recentes): totais e gráfico por tipo vêm de /dashboard/resumo.
  async function carregarContratosRecentes() {
    const pagina = await api("/contratos?page=1&per_page=100");
    return pagina.items;
  }

  async function carregar() {
    try {
      const [contratos, clientes, aditivos, resumo] = await Promise.all([
        carregarContratosRecentes(), api("/clientes"), api("/aditivos"), api("/dashboard/resumo"),
      ]);
      S.contratos = contratos;
      S.clientes = new Map(clientes.map((c) => [c.id, c]));
      S.aditivos = aditivos;
      S.resumo = resumo;
      renderizar();
    } catch (err) {
      toast(err.message, "erro");
    }
  }

  function renderizar() {
    renderKpis();
    renderGraficos();
    renderTabelas();
  }

  /* ---------------- KPIs ---------------- */

  function renderKpis() {
    const resumo = S.resumo;
    if (!resumo) return;
    const pct = resumo.total_contratos
      ? Math.round((resumo.contratos_verificados / resumo.total_contratos) * 100)
      : 0;
    const itens = [
      { rotulo: "Total de contratos", valor: resumo.total_contratos, sub: `${resumo.total_aditivos} aditivo(s) registrados`, cls: "" },
      { rotulo: "Aguardando verificação", valor: resumo.contratos_pendentes, sub: "Precisam de análise", cls: "warning" },
      { rotulo: "Verificados", valor: resumo.contratos_verificados, sub: `${pct}% do total`, cls: "success" },
      { rotulo: "Valor total", valor: moeda(resumo.valor_total), sub: "Soma de todos os contratos", cls: "" },
      { rotulo: "Vencem em 30 dias", valor: resumo.vencendo_em_30_dias, sub: "Pelo término do contrato", cls: "danger" },
      { rotulo: "Cláusulas de alto impacto", valor: resumo.clausulas_alto_impacto, sub: "Nas análises de IA (sem descartadas)", cls: "danger" },
    ];

    $("#kpis").innerHTML = itens.map((i) => `
      <div class="kpi ${i.cls}">
        <span class="kpi-label">${esc(i.rotulo)}</span>
        <strong class="kpi-valor">${esc(i.valor)}</strong>
        <span class="kpi-sub">${esc(i.sub)}</span>
      </div>`).join("");
  }

  /* ---------------- Gráficos ---------------- */

  function montarGrafico(id, config) {
    if (charts[id]) charts[id].destroy();
    charts[id] = new Chart(document.getElementById(id), config);
  }

  function agrupar(lista, chave, valor) {
    const mapa = new Map();
    lista.forEach((item) => {
      const k = chave(item);
      mapa.set(k, (mapa.get(k) || 0) + valor(item));
    });
    return mapa;
  }

  function renderGraficos() {
    if (typeof Chart === "undefined") {
      document.querySelectorAll(".chart-box").forEach((b) => {
        b.innerHTML = '<p class="muted">Não foi possível carregar a biblioteca de gráficos.</p>';
      });
      return;
    }

    Chart.defaults.color = cor("--muted");
    Chart.defaults.borderColor = cor("--border");
    Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;

    const primaria = cor("--primary");
    const ver = S.resumo.contratos_verificados;
    const pend = S.resumo.contratos_pendentes;
    const opcoesBase = { responsive: true, maintainAspectRatio: false };
    const compacto = new Intl.NumberFormat("pt-BR", { notation: "compact" });

    // 1) Verificados x pendentes
    montarGrafico("g-verificacao", {
      type: "doughnut",
      data: {
        labels: ["Verificados", "Aguardando verificação"],
        datasets: [{
          data: [ver, pend],
          backgroundColor: [cor("--success"), cor("--warning")],
          borderColor: cor("--surface"),
          borderWidth: 3,
        }],
      },
      options: { ...opcoesBase, cutout: "62%", plugins: { legend: { position: "bottom" } } },
    });

    // 2) Contratos por tipo
    const porTipo = new Map(S.resumo.contratos_por_tipo.map((t) => [t.tipo, t.total]));
    montarGrafico("g-tipo", {
      type: "bar",
      data: {
        labels: [...porTipo.keys()],
        datasets: [{ label: "Contratos", data: [...porTipo.values()], backgroundColor: primaria, borderRadius: 2 }],
      },
      options: {
        ...opcoesBase,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
      },
    });

    // 3) Valor por mês de início (últimos 12 meses com contratos)
    const porMes = agrupar(
      S.contratos.filter((c) => c.data_inicio),
      (c) => c.data_inicio.slice(0, 7),
      (c) => Number(c.valor_total) || 0,
    );
    const meses = [...porMes.keys()].sort().slice(-12);
    montarGrafico("g-valor-mes", {
      type: "line",
      data: {
        labels: meses.map((m) => `${m.slice(5)}/${m.slice(0, 4)}`),
        datasets: [{
          label: "Valor",
          data: meses.map((m) => porMes.get(m)),
          borderColor: primaria,
          backgroundColor: primaria + "33",
          fill: true,
          tension: 0.3,
          pointRadius: 4,
        }],
      },
      options: {
        ...opcoesBase,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: (ctx) => moeda(ctx.parsed.y) } },
        },
        scales: { y: { beginAtZero: true, ticks: { callback: (v) => compacto.format(v) } } },
      },
    });

    // 4) Top 5 clientes por valor
    const porCliente = agrupar(S.contratos, (c) => nomeCliente(c), (c) => Number(c.valor_total) || 0);
    const top = [...porCliente.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5);
    montarGrafico("g-clientes", {
      type: "bar",
      data: {
        labels: top.map((t) => t[0]),
        datasets: [{ label: "Valor", data: top.map((t) => t[1]), backgroundColor: cor("--success"), borderRadius: 2 }],
      },
      options: {
        ...opcoesBase,
        indexAxis: "y",
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: (ctx) => moeda(ctx.parsed.x) } },
        },
        scales: { x: { beginAtZero: true, ticks: { callback: (v) => compacto.format(v) } } },
      },
    });
  }

  document.addEventListener("temachange", () => {
    if (S.contratos.length || Object.keys(charts).length) renderGraficos();
  });

  /* ---------------- Tabelas ---------------- */

  function filtrados() {
    const q = S.busca.trim().toLowerCase();
    if (!q) return S.contratos;
    return S.contratos.filter((c) =>
      [c.numero, c.titulo, nomeCliente(c), c.tipo_contrato, c.verificado_por]
        .some((v) => String(v || "").toLowerCase().includes(q)));
  }

  function renderTabelas() {
    const lista = filtrados();
    const pendentes = lista.filter((c) => !verificado(c)).sort((a, b) => b.id - a.id);
    const verificados = lista
      .filter(verificado)
      .sort((a, b) => String(b.verificado_em || "").localeCompare(String(a.verificado_em || "")));

    $("#cont-pend").textContent = S.resumo.contratos_pendentes;
    $("#cont-ver").textContent = S.resumo.contratos_verificados;

    $("#tb-pendentes").innerHTML = pendentes.length
      ? pendentes.map(linhaPendente).join("")
      : '<tr><td colspan="9" class="vazio">Nenhum contrato aguardando verificação.</td></tr>';

    $("#tb-verificados").innerHTML = verificados.length
      ? verificados.map(linhaVerificado).join("")
      : '<tr><td colspan="9" class="vazio">Nenhum contrato verificado ainda.</td></tr>';
  }

  function linhaPendente(c) {
    return `
      <tr>
        <td><strong>${esc(c.numero)}</strong></td>
        <td class="titulo-col">${esc(c.titulo)}</td>
        <td>${esc(nomeCliente(c))}</td>
        <td>${esc(c.tipo_contrato || "—")}</td>
        <td class="num">${moeda(c.valor_total)}</td>
        <td>${dataBR(c.data_inicio)}</td>
        <td>${dataBR(c.data_fim)}</td>
        <td><span class="badge pendente">${esc(c.status || "pendente")}</span></td>
        <td class="acoes">
          <button class="btn btn-outline btn-sm" data-acao="ver" data-id="${c.id}">Ver</button>
          <button class="btn btn-success btn-sm" data-acao="verificar" data-id="${c.id}">Verificar</button>
          <button class="btn btn-danger-outline btn-sm" data-acao="excluir" data-id="${c.id}">Excluir</button>
        </td>
      </tr>`;
  }

  function linhaVerificado(c) {
    const quem = c.verificado_por
      ? `<span class="quem"><span class="avatar">${esc(iniciais(c.verificado_por))}</span>${esc(c.verificado_por)}</span>`
      : '<span class="muted">Não identificado</span>';
    return `
      <tr>
        <td><strong>${esc(c.numero)}</strong></td>
        <td class="titulo-col">${esc(c.titulo)}</td>
        <td>${esc(nomeCliente(c))}</td>
        <td>${esc(c.tipo_contrato || "—")}</td>
        <td class="num">${moeda(c.valor_total)}</td>
        <td>${dataBR(c.data_fim)}</td>
        <td>${quem}</td>
        <td>${dataHoraBR(c.verificado_em)}</td>
        <td class="acoes">
          <button class="btn btn-outline btn-sm" data-acao="ver" data-id="${c.id}">Ver</button>
          <button class="btn btn-danger-outline btn-sm" data-acao="excluir" data-id="${c.id}">Excluir</button>
        </td>
      </tr>`;
  }

  /* ---------------- Ações ---------------- */

  document.addEventListener("click", (e) => {
    const botao = e.target.closest("[data-acao]");
    if (!botao) return;
    const id = Number(botao.dataset.id);
    const acao = botao.dataset.acao;
    if (acao === "ver") abrirDetalhe(id);
    if (acao === "verificar") verificar(id, botao);
    if (acao === "analisar") analisar(id, botao);
    if (acao === "excluir") excluir(id);
    if (acao === "editar") editar(id);
  });

  document.addEventListener("click", (e) => {
    const botao = e.target.closest("[data-review-action]");
    if (!botao) return;
    if (botao.dataset.reviewAction === "corrigir-toggle") {
      const form = botao.closest("li").querySelector(".review-form");
      form.hidden = !form.hidden;
      return;
    }
    revisarAnalise(botao);
  });

  async function verificar(id, botao) {
    if (botao) botao.disabled = true;
    try {
      const c = await api(`/contratos/${id}/verificar`, { metodo: "POST" });
      toast(`Contrato ${c.numero} verificado por ${c.verificado_por || "você"}.`, "sucesso");
      fecharDetalhe();
      await carregar();
    } catch (err) {
      if (err.status === 401) {
        toast("Sessão expirada. Faça login novamente.", "erro");
        setTimeout(Auth.sair, 1500);
        return;
      }
      toast(err.message, "erro");
      if (botao) botao.disabled = false;
    }
  }

  async function excluir(id) {
    const c = S.contratos.find((x) => x.id === id);
    if (!c) return;
    const ok = await confirmar(
      `Excluir o contrato ${c.numero}? As cláusulas, aditivos e o histórico dele também serão removidos. Esta ação não pode ser desfeita.`,
    );
    if (!ok) return;

    try {
      await api(`/contratos/${id}`, { metodo: "DELETE" });
      toast(`Contrato ${c.numero} excluído.`, "sucesso");
      fecharDetalhe();
      await carregar();
    } catch (err) {
      toast(err.message, "erro");
    }
  }

  function confirmar(mensagem) {
    return new Promise((resolve) => {
      const d = $("#dlg-confirmar");
      $("#confirmar-msg").textContent = mensagem;
      const fim = (valor) => { d.close(); resolve(valor); };
      $("#confirmar-ok").onclick = () => fim(true);
      $("#confirmar-cancel").onclick = () => fim(false);
      d.oncancel = () => resolve(false);
      d.showModal();
    });
  }

  /* ---------------- Detalhe do contrato ---------------- */

  function fecharDetalhe() {
    const d = $("#dlg-detalhe");
    if (d.open) d.close();
  }

  async function abrirDetalhe(id) {
    const c = S.contratos.find((x) => x.id === id);
    if (!c) return;

    $("#detalhe-titulo").textContent = c.numero;
    $("#detalhe-corpo").innerHTML = '<p class="muted">Carregando…</p>';
    $("#dlg-detalhe").showModal();

    try {
      const [clausulas, aditivos, historico] = await Promise.all([
        api(`/clausulas?contrato_id=${id}`),
        api(`/aditivos?contrato_id=${id}`),
        api(`/historico-status?contrato_id=${id}`),
      ]);
      $("#detalhe-corpo").innerHTML = htmlDetalhe(c, clausulas, aditivos, historico);
      try {
        renderizarAnalise(await api(`/contratos/${id}/analise`), id);
      } catch (err) {
        if (err.status !== 404) throw err;
      }
    } catch (err) {
      $("#detalhe-corpo").innerHTML = `<div class="alert alert-erro">${esc(err.message)}</div>`;
    }
  }

  /* ---------------- Edição do contrato ---------------- */

  function editar(id) {
    const c = S.contratos.find((x) => x.id === id);
    if (!c) return;
    $("#detalhe-corpo").innerHTML = `
      <h3 class="detalhe-titulo">Editar ${esc(c.numero)}</h3>
      <form id="form-edicao" novalidate>
        <div class="alert alert-erro" id="edicao-erro" hidden></div>
        <div class="field"><label for="ed-titulo">Título</label>
          <input id="ed-titulo" value="${esc(c.titulo)}" maxlength="200" required></div>
        <div class="field"><label for="ed-tipo">Tipo de contrato</label>
          <input id="ed-tipo" value="${esc(c.tipo_contrato || "")}" maxlength="80"></div>
        <div class="field"><label for="ed-valor">Valor total (R$)</label>
          <input id="ed-valor" type="number" min="0" step="0.01" value="${c.valor_total ?? ""}"></div>
        <div class="field"><label for="ed-inicio">Início</label>
          <input id="ed-inicio" type="date" value="${esc(c.data_inicio || "")}" required></div>
        <div class="field"><label for="ed-fim">Término</label>
          <input id="ed-fim" type="date" value="${esc(c.data_fim || "")}"></div>
        <div class="dlg-foot">
          <button type="button" class="btn btn-outline" id="ed-cancelar">Cancelar</button>
          <button type="submit" class="btn btn-primary" id="ed-salvar">Salvar alterações</button>
        </div>
      </form>`;
    $("#ed-cancelar").onclick = () => { fecharDetalhe(); abrirDetalhe(id); };
    $("#form-edicao").onsubmit = (e) => { e.preventDefault(); salvarEdicao(c); };
  }

  function erroEdicao(msg) {
    const caixa = $("#edicao-erro");
    caixa.textContent = msg;
    caixa.hidden = false;
  }

  async function salvarEdicao(c) {
    const titulo = $("#ed-titulo").value.trim();
    const inicio = $("#ed-inicio").value;
    const fim = $("#ed-fim").value;
    const valor = $("#ed-valor").value;

    if (!titulo) return erroEdicao("Informe o título do contrato.");
    if (!inicio) return erroEdicao("Informe a data de início.");
    if (fim && fim < inicio) return erroEdicao("A data de término não pode ser anterior ao início.");
    if (valor !== "" && Number(valor) < 0) return erroEdicao("O valor total não pode ser negativo.");

    const botao = $("#ed-salvar");
    botao.disabled = true;
    try {
      await api(`/contratos/${c.id}`, {
        metodo: "PUT",
        corpo: {
          titulo,
          tipo_contrato: $("#ed-tipo").value.trim() || null,
          valor_total: valor === "" ? null : Number(valor),
          data_inicio: inicio,
          data_fim: fim || null,
        },
      });
      toast(`Contrato ${c.numero} atualizado.`, "sucesso");
      fecharDetalhe();
      await carregar();
      abrirDetalhe(c.id);
    } catch (err) {
      erroEdicao(err.message);
      botao.disabled = false;
    }
  }

  async function analisar(id, botao) {
    botao.disabled = true;
    const textoOriginal = botao.textContent;
    botao.textContent = "Analisando…";
    try {
      const resultado = await api(`/contratos/${id}/analisar`, { metodo: "POST" });
      renderizarAnalise(resultado, id);
      toast(resultado.reutilizada ? "Análise salva reutilizada." : "Análise concluída.", "sucesso");
    } catch (err) {
      if (err.status === 401) {
        toast("Sessão expirada. Faça login novamente.", "erro");
        setTimeout(Auth.sair, 1500);
        return;
      }
      toast(err.message, "erro");
    } finally {
      botao.disabled = false;
      botao.textContent = textoOriginal;
    }
  }

  /* ---------------- Análise com IA ---------------- */

  const ROTULO_REVISAO = {
    pendente: "Aguardando revisão",
    confirmada: "Confirmada",
    corrigida: "Corrigida",
    descartada: "Descartada",
  };

  const semAcento = (texto) => String(texto || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "");

  // Mostra o trecho do contrato e destaca o valor encontrado. Só usa nós de texto (nunca innerHTML).
  function preencherTrecho(elemento, trecho, valor) {
    const texto = String(trecho || "");
    const termo = valor ? String(valor).trim() : "";
    const posicao = termo ? texto.indexOf(termo) : -1;
    if (posicao === -1) {
      elemento.textContent = `“${texto}”`;
      return;
    }
    const marca = document.createElement("mark");
    marca.textContent = termo;
    elemento.append(
      `“${texto.slice(0, posicao)}`,
      marca,
      `${texto.slice(posicao + termo.length)}”`,
    );
  }

  function renderizarAnalise(resultado, contratoId) {
    const corpo = $("#detalhe-corpo");
    corpo.querySelector("[data-analise]")?.remove();

    const secao = document.createElement("section");
    secao.className = "dlg-sec analise";
    secao.dataset.analise = "";

    const titulo = document.createElement("h4");
    titulo.textContent = "Análise de cláusulas com IA";
    const aviso = document.createElement("p");
    aviso.className = "analise-aviso";
    aviso.textContent = "Análise automática. Confira no contrato original.";
    const metadados = document.createElement("p");
    metadados.className = "analise-meta";
    metadados.textContent = `Modelo ${resultado.modelo} · Prompt ${resultado.versao_prompt}`;
    secao.append(titulo, aviso, metadados);

    if (!resultado.clausulas.length) {
      const vazio = document.createElement("p");
      vazio.className = "muted";
      vazio.textContent = "Nenhum ponto de impacto financeiro foi identificado.";
      secao.appendChild(vazio);
    } else {
      const lista = document.createElement("ul");
      lista.className = "lista-simples";

      resultado.clausulas.forEach((clausula) => {
        const tipoAtual = clausula.tipo_corrigido || clausula.tipo;
        const impactoAtual = clausula.impacto_corrigido || clausula.impacto;
        const valorAtual = clausula.valor_corrigido ?? clausula.valor_ou_percentual;

        const item = document.createElement("li");
        item.className = "analise-item";
        item.dataset.resultadoId = clausula.id;
        item.dataset.status = clausula.status_revisao;

        const topo = document.createElement("div");
        topo.className = "analise-topo";
        const tipo = document.createElement("strong");
        tipo.textContent = tipoAtual;
        const impacto = document.createElement("span");
        impacto.className = `badge impacto-${semAcento(impactoAtual)}`;
        impacto.textContent = `Impacto ${impactoAtual}`;
        const estado = document.createElement("span");
        estado.className = "badge estado-revisao";
        estado.textContent = ROTULO_REVISAO[clausula.status_revisao] || clausula.status_revisao;
        topo.append(tipo, impacto, estado);
        item.appendChild(topo);

        if (valorAtual) {
          const valor = document.createElement("div");
          valor.className = "analise-valor";
          valor.textContent = `Valor ou percentual: ${valorAtual}`;
          item.appendChild(valor);
        }

        const trecho = document.createElement("blockquote");
        trecho.className = "analise-trecho";
        preencherTrecho(trecho, clausula.trecho_original, valorAtual);
        item.appendChild(trecho);

        const controles = document.createElement("div");
        controles.className = "acoes";
        controles.append(
          botaoRevisao("Confirmar", "confirmar", contratoId, clausula.id),
          botaoRevisao("Descartar", "descartar", contratoId, clausula.id),
          botaoRevisao("Corrigir", "corrigir-toggle", contratoId, clausula.id),
        );

        const formulario = document.createElement("div");
        formulario.className = "review-form";
        formulario.hidden = true;
        formulario.append(
          campoRevisao("Tipo", "tipo", tipoAtual),
          campoRevisao("Valor ou percentual", "valor_ou_percentual", valorAtual),
          campoImpacto(impactoAtual),
          botaoRevisao("Salvar correção", "corrigir", contratoId, clausula.id),
        );

        item.append(controles, formulario);
        lista.appendChild(item);
      });
      secao.appendChild(lista);
    }

    // A análise entra antes dos botões de ação do contrato, não depois.
    const rodape = corpo.querySelector(".dlg-foot");
    if (rodape) corpo.insertBefore(secao, rodape);
    else corpo.appendChild(secao);
  }

  function botaoRevisao(rotulo, acao, contratoId, resultadoId) {
    const botao = document.createElement("button");
    botao.type = "button";
    botao.className = "btn btn-outline btn-sm";
    botao.dataset.reviewAction = acao;
    botao.dataset.contractId = contratoId;
    botao.dataset.resultId = resultadoId;
    botao.textContent = rotulo;
    return botao;
  }

  function campoRevisao(rotulo, nome, valor) {
    const label = document.createElement("label");
    label.className = "field";
    label.textContent = rotulo;
    const input = document.createElement("input");
    input.type = "text";
    input.dataset.reviewField = nome;
    input.value = valor || "";
    label.appendChild(input);
    return label;
  }

  function campoImpacto(valor) {
    const label = document.createElement("label");
    label.className = "field";
    label.textContent = "Impacto";
    const select = document.createElement("select");
    select.dataset.reviewField = "impacto";
    ["baixo", "médio", "alto"].forEach((opcao) => {
      const option = document.createElement("option");
      option.value = opcao;
      option.textContent = opcao;
      select.appendChild(option);
    });
    select.value = valor;
    label.appendChild(select);
    return label;
  }

  async function revisarAnalise(botao) {
    const contratoId = Number(botao.dataset.contractId);
    const resultadoId = Number(botao.dataset.resultId);
    const acaoBotao = botao.dataset.reviewAction;
    const corpo = { acao: acaoBotao };
    if (acaoBotao === "corrigir") {
      const formulario = botao.closest(".review-form");
      formulario.querySelectorAll("[data-review-field]").forEach((campo) => {
        corpo[campo.dataset.reviewField] = campo.value.trim();
      });
    }

    botao.disabled = true;
    try {
      await api(`/contratos/${contratoId}/analise/${resultadoId}`, {
        metodo: "PUT",
        corpo,
      });
      renderizarAnalise(await api(`/contratos/${contratoId}/analise`), contratoId);
      toast("Revisão salva.", "sucesso");
    } catch (err) {
      if (err.status === 401) {
        toast("Sessão expirada. Faça login novamente.", "erro");
        setTimeout(Auth.sair, 1500);
        return;
      }
      toast(err.message, "erro");
      botao.disabled = false;
    }
  }

  function htmlDetalhe(c, clausulas, aditivos, historico) {
    const banner = verificado(c)
      ? `<div class="banner-verificado">✓ Verificado por ${esc(c.verificado_por || "usuário não identificado")} em ${dataHoraBR(c.verificado_em)}</div>`
      : '<div class="banner-pendente">Este contrato ainda não foi verificado.</div>';

    const listaClausulas = clausulas.length
      ? `<ul class="lista-simples">${clausulas.map((x) => `
          <li><strong>${esc(x.ordem ? x.ordem + ". " : "")}${esc(x.titulo || "Sem título")}</strong>
          <span>${esc(x.descricao || "")}</span></li>`).join("")}</ul>`
      : '<p class="muted">Nenhuma cláusula cadastrada.</p>';

    const listaAditivos = aditivos.length
      ? `<ul class="lista-simples">${aditivos.map((x) => `
          <li><strong>${esc(x.descricao)}</strong>
          <span>Assinado em ${dataBR(x.data_assinatura)}
          ${x.novo_valor != null ? " · Novo valor: " + moeda(x.novo_valor) : ""}
          ${x.nova_data_fim ? " · Novo término: " + dataBR(x.nova_data_fim) : ""}</span></li>`).join("")}</ul>`
      : '<p class="muted">Nenhum aditivo registrado.</p>';

    const listaHistorico = historico.length
      ? `<ul class="lista-simples">${historico.map((x) => `
          <li><strong>${esc(x.status_anterior || "—")} → ${esc(x.status_novo || "—")}</strong>
          <span>${dataHoraBR(x.alterado_em)}${x.alterado_por_nome ? " · por " + esc(x.alterado_por_nome) : ""}</span></li>`).join("")}</ul>`
      : '<p class="muted">Sem alterações de status.</p>';

    const acaoVerificar = verificado(c) ? "" :
      `<button class="btn btn-success" data-acao="verificar" data-id="${c.id}">Verificar contrato</button>`;
    const acaoAnalisar = clausulas.length
      ? `<button class="btn btn-outline" data-acao="analisar" data-id="${c.id}">Analisar com IA</button>`
      : "";

    return `
      <h3 class="detalhe-titulo">${esc(c.titulo)}</h3>
      ${banner}
      <dl class="dl-grid">
        <div><dt>Cliente</dt><dd>${esc(nomeCliente(c))}</dd></div>
        <div><dt>Tipo</dt><dd>${esc(c.tipo_contrato || "—")}</dd></div>
        <div><dt>Valor total</dt><dd>${moeda(c.valor_total)}</dd></div>
        <div><dt>Início</dt><dd>${dataBR(c.data_inicio)}</dd></div>
        <div><dt>Término</dt><dd>${dataBR(c.data_fim)}</dd></div>
        <div><dt>Recebido em</dt><dd>${dataHoraBR(c.created_at)}</dd></div>
      </dl>
      <div class="dlg-sec"><h4>Cláusulas</h4>${listaClausulas}</div>
      <div class="dlg-sec"><h4>Aditivos</h4>${listaAditivos}</div>
      <div class="dlg-sec"><h4>Histórico de status</h4>${listaHistorico}</div>
      <div class="dlg-foot">
        <button class="btn btn-danger-outline" data-acao="excluir" data-id="${c.id}">Excluir</button>
        <button class="btn btn-outline" data-acao="editar" data-id="${c.id}">Editar</button>
        ${acaoAnalisar}
        ${acaoVerificar}
      </div>`;
  }

  /* ---------------- Eventos gerais ---------------- */

  $("#detalhe-fechar").addEventListener("click", fecharDetalhe);
  $("#dlg-detalhe").addEventListener("click", (e) => {
    if (e.target.id === "dlg-detalhe") fecharDetalhe(); // clique no fundo
  });
  $("#btn-sair").addEventListener("click", Auth.sair);
  $("#btn-atualizar").addEventListener("click", carregar);
  $("#busca").addEventListener("input", (e) => {
    S.busca = e.target.value;
    renderTabelas();
  });

  iniciar();
})();