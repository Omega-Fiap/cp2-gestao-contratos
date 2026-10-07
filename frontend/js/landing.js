(() => {
  const stack = document.querySelector(".card-stack");
  if (!stack) return;

  const cardsContainer = stack.querySelector(".stack-cards");
  const indicatorsContainer = stack.querySelector(".stack-indicators");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const examples = [
    {
      number: "08",
      topic: "Rescisão",
      quoteBefore: "Em caso de encerramento antecipado, será aplicada multa equivalente a ",
      highlight: "20% do valor restante",
      quoteAfter: " do contrato.",
      value: "Multa de rescisão:",
      detail: "20%",
      impact: "(alto impacto).",
      impactClass: "risk-label",
      due: "Vence em 30 dias.",
    },
    {
      number: "12",
      topic: "Reajuste",
      quoteBefore: "O valor mensal será reajustado a cada 12 meses pela ",
      highlight: "variação acumulada do IPCA",
      quoteAfter: ".",
      value: "Reajuste anual:",
      detail: "IPCA",
      impact: "(impacto médio).",
      impactClass: "impact-label",
      due: "Próximo reajuste em 90 dias.",
    },
    {
      number: "15",
      topic: "Renovação",
      quoteBefore: "O contrato será renovado automaticamente, salvo ",
      highlight: "aviso prévio de 60 dias",
      quoteAfter: ".",
      value: "Renovação automática",
      detail: "",
      impact: "(atenção ao prazo).",
      impactClass: "impact-label",
      due: "Aviso até 45 dias.",
    },
  ];

  const makeElement = (tag, className, text) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  };

  const cards = examples.map((example, index) => {
    const card = makeElement("article", "stack-card");
    card.dataset.pos = String(index);
    card.setAttribute("aria-hidden", String(index !== 0));

    const label = makeElement("div", "result-label", "EXEMPLO FICTÍCIO");
    label.classList.add("fiction-label");

    const clause = makeElement("div", "document-label");
    const clauseNumber = makeElement("span", "", `CLÁUSULA ${example.number} `);
    const separator = makeElement("span", "document-separator", "·");
    const topic = makeElement("span", "", ` ${example.topic.toLocaleUpperCase("pt-BR")}`);
    clause.append(clauseNumber, separator, topic);

    const quote = makeElement("blockquote");
    quote.append('“', document.createTextNode(example.quoteBefore));
    const highlight = makeElement("mark", "", example.highlight);
    quote.append(highlight, document.createTextNode(example.quoteAfter), '”');

    const clauseBlock = makeElement("div", "example-clause");
    clauseBlock.append(label, clause, quote);

    const attention = makeElement("div", "example-attention");
    attention.append(makeElement("span", "result-label", "PONTO DE ATENÇÃO FINANCEIRA"));

    const value = makeElement("p");
    value.append(document.createTextNode(example.value));
    if (example.detail) value.append(" ", makeElement("strong", "", example.detail));
    value.append(" ", makeElement("span", example.impactClass, example.impact));

    const due = makeElement("div", "example-due", example.due);
    attention.append(value, due);

    const note = makeElement("p", "example-note", "Análise automática. Confira no contrato original.");
    card.append(clauseBlock, attention, note);
    cardsContainer.append(card);

    const indicator = makeElement("button", "stack-indicator");
    indicator.type = "button";
    indicator.setAttribute("aria-label", `Mostrar exemplo ${index + 1}: cláusula ${example.number}, ${example.topic.toLocaleLowerCase("pt-BR")}`);
    indicator.setAttribute("aria-pressed", String(index === 0));
    indicator.addEventListener("click", () => selectCard(index));
    indicatorsContainer.append(indicator);

    return card;
  });

  const indicators = [...indicatorsContainer.querySelectorAll("button")];
  let order = [...cards];
  let cycleTimer = 0;
  let cycleDue = 0;
  let cycleRemaining = 6000;
  let transitionTimer = 0;
  let transitioning = false;
  let hovered = false;
  let focused = false;

  const isPaused = () => hovered || focused || document.hidden || reducedMotion.matches;

  const updateAccessibleState = () => {
    order.forEach((card, position) => {
      card.dataset.pos = String(position);
      card.setAttribute("aria-hidden", String(position !== 0));
    });
    cards.forEach((card, index) => {
      indicators[index].setAttribute("aria-pressed", String(card === order[0]));
    });
  };

  const scheduleCycle = (delay = 6000) => {
    window.clearTimeout(cycleTimer);
    cycleRemaining = delay;
    if (isPaused()) return;
    cycleDue = performance.now() + delay;
    cycleTimer = window.setTimeout(advanceCard, delay);
  };

  const pauseCycle = () => {
    if (cycleTimer) {
      cycleRemaining = Math.max(0, cycleDue - performance.now());
      window.clearTimeout(cycleTimer);
      cycleTimer = 0;
    }
  };

  const resumeCycle = () => {
    if (!isPaused() && !transitioning && !cycleTimer) scheduleCycle(cycleRemaining);
  };

  const advanceCard = () => {
    cycleTimer = 0;
    if (isPaused() || transitioning) {
      resumeCycle();
      return;
    }

    transitioning = true;
    cycleRemaining = 5300;
    const outgoing = order[0];
    outgoing.classList.add("is-exiting");
    outgoing.setAttribute("aria-hidden", "true");

    transitionTimer = window.setTimeout(() => {
      order = [...order.slice(1), outgoing];
      outgoing.classList.add("is-resetting");
      outgoing.classList.remove("is-exiting");
      updateAccessibleState();
      void outgoing.offsetWidth;

      requestAnimationFrame(() => {
        outgoing.classList.remove("is-resetting");
      });

      transitionTimer = window.setTimeout(() => {
        transitioning = false;
        resumeCycle();
      }, 400);
    }, 300);
  };

  const selectCard = (index) => {
    const selected = cards[index];
    if (selected === order[0]) return;

    window.clearTimeout(cycleTimer);
    window.clearTimeout(transitionTimer);
    cycleTimer = 0;
    transitioning = false;
    cards.forEach((card) => card.classList.remove("is-exiting", "is-resetting"));
    order = [selected, ...order.filter((card) => card !== selected)];
    updateAccessibleState();
    cycleRemaining = 6000;
    resumeCycle();
  };

  stack.addEventListener("pointerenter", () => {
    hovered = true;
    pauseCycle();
  });
  stack.addEventListener("pointerleave", () => {
    hovered = false;
    resumeCycle();
  });
  stack.addEventListener("focusin", () => {
    focused = true;
    pauseCycle();
  });
  stack.addEventListener("focusout", (event) => {
    if (!stack.contains(event.relatedTarget)) {
      focused = false;
      resumeCycle();
    }
  });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) pauseCycle();
    else resumeCycle();
  });

  const handleMotionPreference = () => {
    if (reducedMotion.matches) {
      pauseCycle();
      cycleRemaining = 6000;
    } else {
      resumeCycle();
    }
  };
  if (reducedMotion.addEventListener) reducedMotion.addEventListener("change", handleMotionPreference);
  else reducedMotion.addListener(handleMotionPreference);

  updateAccessibleState();
  resumeCycle();
})();