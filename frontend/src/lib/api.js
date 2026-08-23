const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";

export async function uploadMedia(file) {
  const body = new FormData();
  body.append("file", file);
  const response = await fetch(`${API_BASE_URL}/chat/upload`, { method: "POST", body });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || "Upload failed.");
  return payload;
}

export async function fetchAgents() {
  const response = await fetch(`${API_BASE_URL}/agents`);
  if (!response.ok) throw new Error("Unable to load agents.");
  return response.json();
}

function blocksToMarkdown(blocks = []) {
  return blocks
    .map((block) => {
      const title = block.title ? `### ${block.title}\n\n` : "";
      return `${title}${block.content || ""}`.trim();
    })
    .filter(Boolean)
    .join("\n\n");
}

export async function streamChat({
  agentId,
  message,
  conversationId,
  history,
  onStart,
  onToken,
  onDone,
  attachments = [],
}) {
  const response = await fetch(`${API_BASE_URL}/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify({
      agent_id: agentId,
      message,
      conversation_id: conversationId,
      history,
      attachments,
    }),
  });

  if (!response.ok || !response.body) {
    throw new Error("Streaming request failed.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let accumulatedText = "";

  function handleEvent(event) {
    const line = event
      .split(/\r?\n/)
      .find((entry) => entry.startsWith("data:"));

    if (!line) return;

    const payload = JSON.parse(line.replace(/^data:\s*/, ""));

    if (payload.type === "start") onStart?.(payload);
    if (payload.type === "thinking") {
      accumulatedText = "_Thinking..._\n\n";
      onToken?.(accumulatedText);
    }
    if (payload.type === "token") {
      if (accumulatedText === "_Thinking..._\n\n") {
        accumulatedText = "";
      }
      accumulatedText += payload.token || "";
      onToken?.(accumulatedText);
    }
    if (payload.type === "block" && payload.block) {
      if (accumulatedText === "_Thinking..._\n\n") {
        accumulatedText = "";
      }
      if (payload.block.title) {
        accumulatedText += `**${payload.block.title}**\n\n`;
      }
      accumulatedText += `${payload.block.content}\n\n`;
      onToken?.(accumulatedText);
    }
    if (payload.type === "done") {
      const hasStructuredResponse =
        typeof payload.response === "string" &&
        payload.response.toLowerCase().includes("<structured_response");
      const formattedResponse = hasStructuredResponse && payload.structured?.length
        ? blocksToMarkdown(payload.structured)
        : payload.response;
      if (formattedResponse) {
        accumulatedText = formattedResponse;
        onToken?.(accumulatedText);
      }
      onDone?.(payload);
    }
    if (payload.type === "error") throw new Error(payload.detail);
  }

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      buffer += decoder.decode();
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split(/\r?\n\r?\n/);
    buffer = events.pop() || "";

    for (const event of events) handleEvent(event);
  }

  // A valid SSE event can arrive without another read after its delimiter.
  // Process it so the final token/done event is never lost.
  if (buffer.trim()) handleEvent(buffer);
}
