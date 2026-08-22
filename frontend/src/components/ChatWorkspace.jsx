import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  Bot,
  FileSearch,
  Loader2,
  Menu,
  PanelLeft,
  Plus,
  Scale,
  Send,
  Sparkles,
  User,
  X,
} from "lucide-react";
import { fetchAgents, streamChat } from "../lib/api";
import {
  loadConversations,
  makeConversation,
  saveConversations,
} from "../lib/storage";
import ProfilePanel from "./ProfilePanel.jsx";

const fallbackAgents = [
  {
    id: "rti",
    name: "RTI Agent",
    description: "Prepare information requests and appeals.",
    knowledge_domain: "rti",
    version: "1.0",
  },
  {
    id: "consumer",
    name: "Consumer Rights Agent",
    description: "Plan consumer complaint and escalation steps.",
    knowledge_domain: "consumer",
    version: "1.0",
  },
];

const quickPrompts = {
  rti: [
    "Draft an RTI for delay in passport police verification.",
    "What details should I include before filing an RTI?",
    "Help me prepare a first appeal format.",
  ],
  consumer: [
    "Draft a complaint for a defective phone replacement.",
    "What evidence should I collect before a consumer complaint?",
    "Help me write to an e-commerce seller about refund delay.",
  ],
};

export default function ChatWorkspace({ user, onSignOut }) {
  const [agents, setAgents] = useState(fallbackAgents);
  const [selectedAgent, setSelectedAgent] = useState("rti");
  const [conversations, setConversations] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    fetchAgents()
      .then(setAgents)
      .catch(() => setAgents(fallbackAgents));
  }, []);

  useEffect(() => {
    const saved = loadConversations(user.id);
    if (saved.length) {
      setConversations(saved);
      setActiveId(saved[0].id);
      setSelectedAgent(saved[0].agentId);
      return;
    }

    const first = makeConversation("rti");
    setConversations([first]);
    setActiveId(first.id);
  }, [user.id]);

  useEffect(() => {
    if (conversations.length) saveConversations(user.id, conversations);
  }, [conversations, user.id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [conversations, activeId, busy]);

  const activeConversation = useMemo(
    () => conversations.find((conversation) => conversation.id === activeId),
    [conversations, activeId],
  );

  const activeAgent = useMemo(
    () => agents.find((agent) => agent.id === selectedAgent) || agents[0],
    [agents, selectedAgent],
  );

  function updateActive(mutator) {
    setConversations((current) =>
      current.map((conversation) =>
        conversation.id === activeId ? mutator(conversation) : conversation,
      ),
    );
  }

  function createNewChat(agentId = selectedAgent) {
    const next = makeConversation(agentId);
    setConversations((current) => [next, ...current]);
    setActiveId(next.id);
    setSelectedAgent(agentId);
    setSidebarOpen(false);
  }

  function selectConversation(conversation) {
    setActiveId(conversation.id);
    setSelectedAgent(conversation.agentId);
    setSidebarOpen(false);
  }

  async function sendMessage(text = input) {
    const message = text.trim();
    if (!message || busy || !activeConversation) return;

    setInput("");
    setBusy(true);
    setError("");

    const userMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: message,
      createdAt: new Date().toISOString(),
    };
    const assistantMessage = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
      createdAt: new Date().toISOString(),
      streaming: true,
    };

    updateActive((conversation) => ({
      ...conversation,
      title:
        conversation.messages.length === 0
          ? message.slice(0, 54)
          : conversation.title,
      updatedAt: new Date().toISOString(),
      messages: [...conversation.messages, userMessage, assistantMessage],
    }));

    try {
      await streamChat({
        agentId: selectedAgent,
        message,
        conversationId: activeConversation.backendId,
        history: activeConversation.messages
          .filter((entry) => entry.role === "user" || entry.role === "assistant")
          .slice(-10)
          .map((entry) => ({ role: entry.role, content: entry.content })),
        onStart: (payload) => {
          updateActive((conversation) => ({
            ...conversation,
            backendId: payload.conversation_id || conversation.backendId,
          }));
        },
        onToken: (token) => {
          updateActive((conversation) => ({
            ...conversation,
            messages: conversation.messages.map((entry) =>
              entry.id === assistantMessage.id
                ? { ...entry, content: entry.content + token }
                : entry,
            ),
          }));
        },
        onDone: () => {
          updateActive((conversation) => ({
            ...conversation,
            updatedAt: new Date().toISOString(),
            messages: conversation.messages.map((entry) =>
              entry.id === assistantMessage.id
                ? { ...entry, streaming: false }
                : entry,
            ),
          }));
        },
      });
    } catch (streamError) {
      setError(streamError.message || "Something went wrong.");
      updateActive((conversation) => ({
        ...conversation,
        messages: conversation.messages.map((entry) =>
          entry.id === assistantMessage.id
            ? {
                ...entry,
                streaming: false,
                content:
                  entry.content ||
                  "I could not reach the backend. Check API URL, backend server, and Groq key.",
              }
            : entry,
        ),
      }));
    } finally {
      setBusy(false);
    }
  }

  function onComposerKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  }

  return (
    <main className="workspace">
      <aside className={`sidebar ${sidebarOpen ? "open" : ""}`}>
        <div className="sidebar-head">
          <a className="brand compact" href="/">
            <span className="brand-mark">CA</span>
            <span>Civic AI</span>
          </a>
          <button
            className="icon-button mobile-only"
            type="button"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close sidebar"
          >
            <X size={20} />
          </button>
        </div>

        <button className="new-chat-button" type="button" onClick={() => createNewChat()}>
          <Plus size={18} />
          New session
        </button>

        <div className="agent-picker">
          {agents.map((agent) => (
            <button
              key={agent.id}
              className={selectedAgent === agent.id ? "agent-tab active" : "agent-tab"}
              type="button"
              onClick={() => {
                setSelectedAgent(agent.id);
                if (activeConversation?.messages.length === 0) {
                  updateActive((conversation) => ({
                    ...conversation,
                    agentId: agent.id,
                  }));
                } else {
                  createNewChat(agent.id);
                }
              }}
            >
              {agent.id === "rti" ? <FileSearch size={18} /> : <Scale size={18} />}
              <span>{agent.name}</span>
            </button>
          ))}
        </div>

        <div className="conversation-list">
          <div className="section-label">Saved chats</div>
          {conversations.map((conversation) => (
            <button
              key={conversation.id}
              className={
                conversation.id === activeId
                  ? "conversation-item active"
                  : "conversation-item"
              }
              type="button"
              onClick={() => selectConversation(conversation)}
            >
              <span>{conversation.title}</span>
              <small>{conversation.agentId.toUpperCase()}</small>
            </button>
          ))}
        </div>
      </aside>

      {sidebarOpen && <div className="scrim" onClick={() => setSidebarOpen(false)} />}

      <section className="chat-shell">
        <header className="chat-topbar">
          <button
            className="icon-button"
            type="button"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open sidebar"
          >
            <Menu size={20} />
          </button>

          <div className="agent-status">
            <span className="agent-icon">
              {activeAgent?.id === "rti" ? <FileSearch size={19} /> : <Scale size={19} />}
            </span>
            <div>
              <strong>{activeAgent?.name}</strong>
              <small>{activeAgent?.description}</small>
            </div>
          </div>

          <div className="topbar-actions">
            <button className="icon-button desktop-only" type="button" aria-label="Layout">
              <PanelLeft size={20} />
            </button>
            <button
              className="profile-chip"
              type="button"
              onClick={() => setProfileOpen(true)}
            >
              <User size={17} />
              <span>{user.user_metadata?.full_name || user.email}</span>
            </button>
          </div>
        </header>

        <div className="messages-panel">
          {activeConversation?.messages.length ? (
            activeConversation.messages.map((message) => (
              <article key={message.id} className={`message ${message.role}`}>
                <div className="message-avatar">
                  {message.role === "assistant" ? <Bot size={18} /> : <User size={18} />}
                </div>
                <div className="message-bubble">
                  <p>{message.content}</p>
                  {message.streaming && (
                    <span className="live-cursor" aria-label="Streaming response" />
                  )}
                </div>
              </article>
            ))
          ) : (
            <section className="empty-chat">
              <div className="spark-card">
                <Sparkles size={30} />
              </div>
              <h1>Start a focused civic session</h1>
              <p>
                Choose a prompt or ask directly. Your session will be saved on
                this device under your profile.
              </p>
              <div className="prompt-grid">
                {(quickPrompts[selectedAgent] || quickPrompts.rti).map((prompt) => (
                  <button key={prompt} type="button" onClick={() => sendMessage(prompt)}>
                    {prompt}
                  </button>
                ))}
              </div>
            </section>
          )}
          <div ref={messagesEndRef} />
        </div>

        {error && <div className="error-toast">{error}</div>}

        <form
          className="composer"
          onSubmit={(event) => {
            event.preventDefault();
            sendMessage();
          }}
        >
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={onComposerKeyDown}
            placeholder={`Ask the ${activeAgent?.name || "agent"}...`}
            rows={1}
          />
          <button className="send-button" type="submit" disabled={busy || !input.trim()}>
            {busy ? <Loader2 className="spin" size={20} /> : <Send size={20} />}
          </button>
        </form>
      </section>

      {profileOpen && (
        <ProfilePanel
          user={user}
          onClose={() => setProfileOpen(false)}
          onSignOut={onSignOut}
        />
      )}
    </main>
  );
}
