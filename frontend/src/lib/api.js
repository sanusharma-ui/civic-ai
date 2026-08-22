const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";

export async function fetchAgents() {
  const response = await fetch(`${API_BASE_URL}/agents`);
  if (!response.ok) throw new Error("Unable to load agents.");
  return response.json();
}

export async function streamChat({
  agentId,
  message,
  conversationId,
  history,
  onStart,
  onToken,
  onDone,
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
    }),
  });

  if (!response.ok || !response.body) {
    throw new Error("Streaming request failed.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let accumulatedText = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";

    for (const event of events) {
      const line = event
        .split("\n")
        .find((entry) => entry.startsWith("data:"));

      if (!line) continue;

      const payload = JSON.parse(line.replace(/^data:\s*/, ""));

      if (payload.type === "start") onStart?.(payload);
      if (payload.type === "thinking") {
        accumulatedText = "_Thinking..._\n\n";
        onToken?.(accumulatedText);
      }
      if (payload.type === "token") {
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
        onToken?.(accumulatedText); // Passing full accumulated text
      }
      if (payload.type === "done") onDone?.(payload);
      if (payload.type === "error") throw new Error(payload.detail);
    }
  }
}
