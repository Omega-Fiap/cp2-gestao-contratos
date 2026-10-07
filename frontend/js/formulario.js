/* Formulário público do cliente */

(function () {
  const $ = (id) => document.getElementById(id);
  const lista = $("lista-clausulas");
  const erroBox = $("erro");

  if (!Auth.token()) {
    location.replace("login.html");
    return;
  }

  function mostrarErro(msg) {
    erroBox.textContent = msg;
    erroBox.hidden = false;
    erroBox.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function renumerar() {
    lista.querySelectorAll(".clausula-item").forEach((item, i) => {
      item.querySelector(".topo strong").textContent = `Cláusula ${i + 1}`;
    });
  }

  function adicionarClausula() {
    const item = document.createElement("div");
    item.className = "clausula-item";
    item.innerHTML = `
      <div class="topo">
        <strong></strong>
        <button type="button" class="btn btn-danger-outline btn-sm" data-remover>Remover</button>
      </div>
      <div class="field">
        <label>Título</label>
        <input type="text" data-campo="titulo">
      </div>
      <div class="field" style="margin-bottom:0">
        <label>Descrição</label>
        <textarea data-campo="descricao"></textarea>
      </div>`;
    lista.appendChild(item);
    renumerar();
  }

  $("btn-add-clausula").addEventListener("click", adicionarClausula);

  lista.addEventListener("click", (e) => {
    const botao = e.target.closest("[data-remover]");
    if (botao) {
      botao.closest(".clausula-item").remove();
      renumerar();
    }
  });

  function coletar() {
    const clausulas = [...lista.querySelectorAll(".clausula-item")].map((item) => ({
      titulo: item.querySelector('[data-campo="titulo"]').value.trim(),
      descricao: item.querySelector('[data-campo="descricao"]').value.trim(),
    })).filter((c) => c.titulo || c.descricao);

    return {
      cliente: {
        nome: $("c-nome").value.trim(),
        tipo: $("c-tipo").value,
        documento: $("c-documento").value.trim(),
        email: $("c-email").value.trim(),
        telefone: $("c-telefone").value.trim(),
      },
      contrato: {
        titulo: $("t-titulo").value.trim(),
        tipo_contrato: $("t-tipo").value,
        valor_total: $("t-valor").value,
        data_inicio: $("t-inicio").value,
        data_fim: $("t-fim").value,
      },
      clausulas,
    };
  }

  $("form-contrato").addEventListener("submit", async (e) => {
    e.preventDefault();
    erroBox.hidden = true;

    const dados = coletar();
    if (!dados.cliente.nome) return mostrarErro("Informe o seu nome ou razão social.");
    if (!dados.contrato.titulo) return mostrarErro("Informe o título do contrato.");
    if (!dados.contrato.data_inicio) return mostrarErro("Informe a data de início.");
    if (dados.contrato.data_fim && dados.contrato.data_fim < dados.contrato.data_inicio) {
      return mostrarErro("A data de término não pode ser anterior ao início.");
    }

    const botao = $("btn-enviar");
    botao.disabled = true;
    botao.textContent = "Enviando…";

    try {
      const r = await api("/formulario", { metodo: "POST", corpo: dados });
      $("numero-contrato").textContent = r.contrato.numero;
      $("area-form").hidden = true;
      $("area-sucesso").hidden = false;
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      mostrarErro(err.message);
    } finally {
      botao.disabled = false;
      botao.textContent = "Enviar formulário";
    }
  });

  $("btn-outro").addEventListener("click", () => {
    $("form-contrato").reset();
    lista.innerHTML = "";
    $("area-sucesso").hidden = true;
    $("area-form").hidden = false;
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
})();
