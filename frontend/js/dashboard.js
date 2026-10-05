/* Dashboard de gestão de contratos */

(function () {
  const VERIFICADO = "verificado";
  const S = { contratos: [], clientes: new Map(), aditivos: [], busca: "" };
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

  async function carregar() {
    try {
      const [contratos, clientes, aditivos] = await Promise.all([
        api("/contratos"), api("/clientes"), api("/aditivos"),
      ]);
      S.contratos = contratos;
      S.clientes = new Map(clientes.map((c) => [c.id, c]));
      S.aditivos = aditivos;
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
    const total = S.contratos.length;
    const ver = S.contratos.filter(verificado).length;
    const pend = total - ver;
    const valor = S.contratos.reduce((soma, c) => soma + (Number(c.valor_total) || 0), 0);

    const hoje = new Date();
    hoje.setHours(0, 0, 0, 0);
    const limite = new Date(hoje);
    limite.setDate(limite.getDate() + 30);
    const vencendo = S.contratos.filter((c) => {
      if (!c.data_fim) return false;
      const d = new Date(c.data_fim + "T00:00:00");
      return d >= hoje && d <= limite;
    }).length;

    const pct = total ? Math.round((ver / total) * 100) : 0;
    const itens = [
      { rotulo: "Total de contratos", valor: total, sub: `${S.aditivos.length} aditivo(s) registrados`, cls: "" },
      { rotulo: "Aguardando verificação", valor: pend, sub: "Precisam de análise", cls: "warning" },
      { rotulo: "Verificados", valor: ver, sub: `${pct}% do total`, cls: "success" },
      { rotulo: "Valor total", valor: moeda(valor), sub: "Soma de todos os contratos", cls: "" },
      { rotulo: "Vencem em 30 dias", valor: vencendo, sub: "Pelo término do contrato", cls: "danger" },
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
    const ver = S.contratos.filter(verificado).length;
    const pend = S.contratos.length - ver;
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
    const porTipo = agrupar(S.contratos, (c) => c.tipo_contrato || "Não informado", () => 1);
    montarGrafico("g-tipo", {
      type: "bar",
      data: {
        labels: [...porTipo.keys()],
        datasets: [{ label: "Contratos", data: [...porTipo.values()], backgroundColor: primaria, borderRadius: 6 }],
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
        datasets: [{ label: "Valor", data: top.map((t) => t[1]), backgroundColor: cor("--success"), borderRadius: 6 }],
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

    $("#cont-pend").textContent = S.contratos.filter((c) => !verificado(c)).length;
    $("#cont-ver").textContent = S.contratos.filter(verificado).length;

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
    if (acao === "excluir") excluir(id);
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
    } catch (err) {
      $("#detalhe-corpo").innerHTML = `<div class="alert alert-erro">${esc(err.message)}</div>`;
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

    return `
      <h3 style="margin-bottom:.2rem">${esc(c.titulo)}</h3>
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
