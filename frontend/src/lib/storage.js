const STORAGE_KEY = "civic-ai-conversations";

export function loadConversations(userId) {
  const raw = localStorage.getItem(`${STORAGE_KEY}:${userId}`);
  if (!raw) return [];

  try {
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

export function saveConversations(userId, conversations) {
  localStorage.setItem(
    `${STORAGE_KEY}:${userId}`,
    JSON.stringify(conversations),
  );
}

export function makeConversation(agentId) {
  return {
    id: crypto.randomUUID(),
    backendId: null,
    agentId,
    title: "New civic session",
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    messages: [],
  };
}
