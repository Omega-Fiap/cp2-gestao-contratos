/* ============================================================
   Gestor de Contratos - utilitários compartilhados
   ============================================================ */

// A ponte local encaminha /api/... para a API Flask configurada no servidor.
const API_URL = "/api";

/* ---------------- Tema claro / escuro ---------------- */

const ICONE_TEMA = `
<button type="button" class="icon-btn" data-toggle-tema
        aria-label="Alternar entre modo claro e escuro" title="Alternar tema">
  <svg class="i-sun" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>
  <svg class="i-moon" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>
</button>`;

function aplicarTema(tema) {
  document.documentElement.dataset.theme = tema;
  try { localStorage.setItem("tema", tema); } catch (_) { /* ignora */ }
  document.dispatchEvent(new CustomEvent("temachange", { detail: tema }));
}

document.addEventListener("click", (e) => {
  if (e.target.closest("[data-toggle-tema]")) {
    aplicarTema(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
  }
});

document.querySelectorAll(".theme-slot").forEach((el) => { el.innerHTML = ICONE_TEMA; });

/* ---------------- Autenticação ---------------- */

const Auth = {
  token: () => localStorage.getItem("token"),
  usuario() {
    try { return JSON.parse(localStorage.getItem("usuario")); } catch (_) { return null; }
  },
  salvar(token, usuario) {
    localStorage.setItem("token", token);
    localStorage.setItem("usuario", JSON.stringify(usuario));
  },
  sair() {
    localStorage.removeItem("token");
    localStorage.removeItem("usuario");
    location.href = "login.html";
  },
};

/* ---------------- Chamadas à API ---------------- */

async function api(rota, { metodo = "GET", corpo } = {}) {
  const headers = {};
  if (corpo !== undefined) headers["Content-Type"] = "application/json";
  const token = Auth.token();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let resposta;
  try {
    resposta = await fetch(API_URL + rota, {
      method: metodo,
      headers,
      body: corpo !== undefined ? JSON.stringify(corpo) : undefined,
    });
  } catch (_) {
    throw new Error(`Não foi possível conectar à API em ${API_URL}. Ela está rodando?`);
  }

  let dados = null;
  try { dados = await resposta.json(); } catch (_) { /* sem corpo JSON */ }

  if (!resposta.ok) {
    const err = new Error((dados && dados.erro) || `Erro ${resposta.status}`);
    err.status = resposta.status;
    if (resposta.status === 401 && token) Auth.sair();
    throw err;
  }
  return dados;
}

/* ---------------- Formatação ---------------- */

const _fmtMoeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

function moeda(v) {
  return v === null || v === undefined || v === "" ? "—" : _fmtMoeda.format(Number(v));
}

function dataBR(s) {
  if (!s) return "—";
  const [a, m, d] = String(s).slice(0, 10).split("-");
  return `${d}/${m}/${a}`;
}

// O servidor guarda datas/horas em UTC sem fuso; converte para o horário local.
function dataHoraBR(s) {
  if (!s) return "—";
  const iso = /[zZ]|[+-]\d\d:\d\d$/.test(s) ? s : s + "Z";
  return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

function esc(v) {
  return String(v ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

function iniciais(nome) {
  return String(nome || "?").trim().split(/\s+/).slice(0, 2).map((p) => p[0]).join("").toUpperCase();
}

/* ---------------- Avisos (toast) ---------------- */

function toast(msg, tipo = "info") {
  let box = document.getElementById("toasts");
  if (!box) {
    box = document.createElement("div");
    box.id = "toasts";
    document.body.appendChild(box);
  }
  const t = document.createElement("div");
  t.className = `toast ${tipo}`;
  t.textContent = msg;
  box.appendChild(t);
  setTimeout(() => {
    t.classList.add("saindo");
    setTimeout(() => t.remove(), 300);
  }, 4200);
}
