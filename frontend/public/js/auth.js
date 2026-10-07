/* Login e registro */

(function () {
  const erroBox = document.getElementById("erro");

  function mostrarErro(msg) {
    erroBox.textContent = msg;
    erroBox.hidden = false;
  }

  function limparErro() {
    erroBox.hidden = true;
  }

  /* ---------- Login ---------- */
  const formLogin = document.getElementById("form-login");
  if (formLogin) {
    if (Auth.token()) {
      location.replace("dashboard.html");
      return;
    }

    if (new URLSearchParams(location.search).get("cadastro") === "ok") {
      document.getElementById("aviso").hidden = false;
    }

    formLogin.addEventListener("submit", async (e) => {
      e.preventDefault();
      limparErro();

      const email = document.getElementById("email").value.trim();
      const senha = document.getElementById("senha").value;
      if (!email || !senha) return mostrarErro("Informe e-mail e senha.");

      const botao = formLogin.querySelector("button[type=submit]");
      botao.disabled = true;
      botao.textContent = "Entrando…";

      try {
        const r = await api("/auth/login", { metodo: "POST", corpo: { email, senha } });
        Auth.salvar(r.token, r.usuario);
        location.href = "dashboard.html";
      } catch (err) {
        mostrarErro(err.message);
        botao.disabled = false;
        botao.textContent = "Entrar";
      }
    });
  }

  /* ---------- Registro ---------- */
  const formRegistrar = document.getElementById("form-registrar");
  if (formRegistrar) {
    formRegistrar.addEventListener("submit", async (e) => {
      e.preventDefault();
      limparErro();

      const nome = document.getElementById("nome").value.trim();
      const email = document.getElementById("email").value.trim();
      const senha = document.getElementById("senha").value;
      const confirmar = document.getElementById("confirmar").value;

      if (!nome || !email || !senha) return mostrarErro("Preencha todos os campos.");
      if (senha.length < 6) return mostrarErro("A senha deve ter pelo menos 6 caracteres.");
      if (senha !== confirmar) return mostrarErro("As senhas não coincidem.");

      const botao = formRegistrar.querySelector("button[type=submit]");
      botao.disabled = true;
      botao.textContent = "Criando…";

      try {
        await api("/auth/registrar", { metodo: "POST", corpo: { nome, email, senha } });
        location.href = "login.html?cadastro=ok";
      } catch (err) {
        mostrarErro(err.message);
        botao.disabled = false;
        botao.textContent = "Criar conta";
      }
    });
  }
})();
