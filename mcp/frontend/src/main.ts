import "./styles.css";

type Source = {
  id: string;
  id_materia?: string;
  title?: string;
  pubdate?: string;
  pubname?: string;
  url?: string;
};

type ChatResponse = {
  answer: string;
  sources: Source[];
};

const apiBaseUrl = import.meta.env.VITE_RO_DOU_API_URL ?? "http://localhost:8000";
const app = document.querySelector<HTMLDivElement>("#app");

if (!app) {
  throw new Error("App root not found");
}

app.innerHTML = `
  <section class="chat-shell" aria-label="Chat Ro-DOU">
    <header class="chat-header">
      <div>
        <h1>Ro-DOU Chat</h1>
        <p>Consulta interativa as publicacoes processadas do Diario Oficial da Uniao.</p>
      </div>
      <span class="status" data-status>Pronto</span>
    </header>
    <ol class="messages" data-messages></ol>
    <form class="composer" data-form>
      <textarea name="message" rows="3" placeholder="Pergunte sobre publicacoes do DOU" required></textarea>
      <button type="submit">Enviar</button>
    </form>
  </section>
`;

const form = app.querySelector<HTMLFormElement>("[data-form]");
const messages = app.querySelector<HTMLOListElement>("[data-messages]");
const status = app.querySelector<HTMLSpanElement>("[data-status]");

function addMessage(role: "user" | "assistant", text: string, sources: Source[] = []): void {
  if (!messages) return;
  const item = document.createElement("li");
  item.className = `message ${role}`;
  const sourceMarkup = sources
    .slice(0, 5)
    .map((source) => {
      const title = source.title ?? "Publicacao sem titulo";
      const meta = [source.pubdate, source.pubname].filter(Boolean).join(" - ");
      const label = `<strong>${escapeHtml(source.id)}</strong> ${escapeHtml(title)}`;
      const linkedLabel = source.url
        ? `<a href="${escapeHtml(source.url)}" target="_blank" rel="noopener noreferrer">${label}</a>`
        : label;
      return `<li>${linkedLabel}<small>${escapeHtml(meta)}</small></li>`;
    })
    .join("");
  const content = role === "assistant" ? renderMarkdown(text) : `<p>${escapeHtml(text)}</p>`;
  item.innerHTML = `
    <div class="message-content">${content}</div>
    ${sourceMarkup ? `<ul class="sources">${sourceMarkup}</ul>` : ""}
  `;
  messages.appendChild(item);
  item.scrollIntoView({ block: "end", behavior: "smooth" });
}

function renderMarkdown(value: string): string {
  const escaped = escapeHtml(value);
  const withLinks = escaped.replace(
    /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>',
  );
  const withBold = withLinks.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  return withBold
    .split(/\n{2,}/)
    .map((block) => {
      const lines = block.split("\n");
      if (lines.every((line) => line.trim().startsWith("- "))) {
        const items = lines
          .map((line) => `<li>${line.trim().slice(2)}</li>`)
          .join("");
        return `<ul>${items}</ul>`;
      }
      return `<p>${lines.join("<br>")}</p>`;
    })
    .join("");
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(form);
  const message = String(data.get("message") ?? "").trim();
  if (!message) return;

  addMessage("user", message);
  form.reset();
  if (status) status.textContent = "Consultando";

  try {
    const response = await fetch(`${apiBaseUrl}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, size: 5 }),
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = (await response.json()) as ChatResponse;
    addMessage("assistant", payload.answer, payload.sources);
    if (status) status.textContent = "Pronto";
  } catch (error) {
    addMessage("assistant", "Nao foi possivel consultar o backend agora.");
    if (status) status.textContent = "Erro";
    console.error(error);
  }
});
