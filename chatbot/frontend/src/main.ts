import "./styles.css";

type ChatResponse = {
  conversation_id: string;
  client_id: string;
  answer: string;
  needs_clarification: boolean;
};

const app = document.querySelector<HTMLDivElement>("#app");
let conversationId: string | null = null;
let clientId: string = crypto.randomUUID();

if (!app) throw new Error("App root not found");

app.innerHTML = `
  <section class="chat-shell" aria-label="Chatbot Ro-DOU">
    <header class="chat-header">
      <div>
        <span class="eyebrow">Diário Oficial da União</span>
        <h1>Ro-DOU Chatbot</h1>
        <p>Consulte publicações usando linguagem natural.</p>
        <p>Disponívels apenas as publicações do dia</p>
        <p>Disponível apenas para fonte INLABS</p>
      </div>
      <span class="status" data-status>Pronto</span>
    </header>
    <ol class="messages" data-messages aria-live="polite">
      <li class="message assistant">
        <div class="message-content"><p>Olá! Informe um assunto, órgão ou período para começar.</p></div>
      </li>
    </ol>
    <form class="composer" data-form>
      <textarea name="message" rows="3" maxlength="4000" placeholder="Ex.: Mostre publicações do Ministério da Saúde sobre dengue hoje" required></textarea>
      <button type="submit">Enviar</button>
    </form>
  </section>
`;

const form = app.querySelector<HTMLFormElement>("[data-form]");
const messages = app.querySelector<HTMLOListElement>("[data-messages]");
const status = app.querySelector<HTMLSpanElement>("[data-status]");

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderMarkdown(value: string): string {
  const escaped = escapeHtml(value);
  const links = escaped.replace(
    /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>',
  );

  const renderBlock = (block: string): string => {
    const lines = block.split("\n");
    const contentIndex = lines.findIndex((line) =>
      /^\s*(Ementa|Recorte):\s*(.*)$/.test(line),
    );

    if (contentIndex < 0) {
      return `<p>${lines.join("<br>")}</p>`;
    }

    const publicationContent = lines[contentIndex].match(
      /^\s*(Ementa|Recorte):\s*(.*)$/,
    );
    if (!publicationContent) return `<p>${lines.join("<br>")}</p>`;

    const [, label, content] = publicationContent;
    const kind = label === "Ementa" ? "summary" : "excerpt";
    const headingLines = lines.slice(0, contentIndex);
    const title = headingLines.shift() ?? "Publicação";
    const metadata = headingLines.join(" ").trim();
    const metadataItems = metadata
      .split(" • ")
      .filter(Boolean)
      .map((item) => `<span>${item}</span>`)
      .join("");

    return `
      <article class="publication-item">
        <p class="publication-item__title">${title}</p>
        ${metadataItems ? `<p class="publication-item__meta">${metadataItems}</p>` : ""}
        <div class="publication-content publication-content--${kind}" role="note" aria-label="${label} da publicação">
          <span class="publication-content__label">${label}</span>
          <p>${content}</p>
        </div>
      </article>
    `;
  };

  return links
    .split(/\n{2,}/)
    .map(renderBlock)
    .join("");
}

function addMessage(role: "user" | "assistant", text: string): void {
  if (!messages) return;
  const item = document.createElement("li");
  item.className = `message ${role}`;
  item.innerHTML = `<div class="message-content">${
    role === "assistant" ? renderMarkdown(text) : `<p>${escapeHtml(text)}</p>`
  }</div>`;
  if (item.querySelector(".publication-item")) {
    item.classList.add("message--results");
  }
  messages.appendChild(item);
  item.scrollIntoView({ block: "end", behavior: "smooth" });
}

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(form);
  const message = String(data.get("message") ?? "").trim();
  if (!message) return;

  addMessage("user", message);
  const messageField = form.elements.namedItem("message") as HTMLTextAreaElement;
  messageField.value = "";
  if (status) status.textContent = "Consultando";

  try {
    const response = await fetch("/api/v1/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
        client_id: clientId,
      }),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = (await response.json()) as ChatResponse;
    conversationId = payload.conversation_id;
    clientId = payload.client_id;
    addMessage("assistant", payload.answer);
    if (status) status.textContent = payload.needs_clarification ? "Aguardando detalhe" : "Pronto";
  } catch (error) {
    addMessage("assistant", "Não foi possível consultar o backend agora.");
    if (status) status.textContent = "Erro";
    console.error(error);
  }
});
