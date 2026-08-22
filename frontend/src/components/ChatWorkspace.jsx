import React, { useEffect, useMemo, useRef, useState, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/cjs/styles/prism";
import {
  BookOpen,
  Bot,
  Check,
  Copy,
  FileSearch,
  Library,
  Loader2,
  PanelLeft,
  Paperclip,
  Plus,
  Scale,
  Search,
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

function CodeBlock({ language, code }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    });
  }, [code]);

  return (
    <div className="code-block">
      <div className="code-header">
        <span className="code-lang">
          <span className="code-lang-dot" />
          {language.toUpperCase()}
        </span>
        <button
          className={`copy-btn ${copied ? "copied" : ""}`}
          type="button"
          onClick={handleCopy}
        >
          {copied ? <Check size={13} /> : <Copy size={13} />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <SyntaxHighlighter
        language={language}
        style={oneDark}
        customStyle={{
          margin: 0,
          borderRadius: "0 0 8px 8px",
          fontSize: "0.88rem",
          lineHeight: "1.6",
          padding: "16px",
          background: "#1e1e2e",
        }}
        showLineNumbers={false}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}

function structuredBlocksToMarkdown(blocks = []) {
  return blocks
    .map((block) => {
      const title = block.title ? `### ${block.title}\n\n` : "";
      return `${title}${block.content || ""}`.trim();
    })
    .filter(Boolean)
    .join("\n\n");
}

function normalizeAssistantMarkdown(content) {
  if (!content?.includes("<structured_response")) return content || "";

  const match = content.match(
    /<structured_response\s*>([\s\S]*?)<\/structured_response>/i,
  );
  const candidate = match?.[1]?.trim();
  if (!candidate) return content;

  try {
    const parsed = JSON.parse(candidate);
    if (Array.isArray(parsed?.blocks)) {
      return structuredBlocksToMarkdown(parsed.blocks);
    }
  } catch {
    return content;
  }

  return content;
}

function MarkdownMessage({ content }) {
  const markdown = normalizeAssistantMarkdown(content);

  return (
    <div className="markdown-message">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          pre({ children }) {
            return <>{children}</>;
          },
          code({ className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || "");
            const code = String(children).replace(/\n$/, "");
            const isBlock = Boolean(match) || code.includes("\n");

            if (isBlock) {
              return <CodeBlock language={match?.[1] || "text"} code={code} />;
            }

            return (
              <code className="inline-code" {...props}>
                {children}
              </code>
            );
          },
        }}
      >
        {markdown}
      </ReactMarkdown>
    </div>
  );
}

// Renders streamed content directly — no artificial ticker delay.
// The SSE stream delivers tokens progressively, which naturally creates
// the ChatGPT-like typing effect without any client-side word-revealing.
function StreamingMessage({ content, streaming }) {
  return (
    <>
      <MarkdownMessage content={content} />
      {streaming && <span className="live-cursor" aria-label="Streaming response" />}
    </>
  );
}

// Small badge that shows how many knowledge-base sources were used.
// Clicking it opens a compact popup listing each source.
function SourcesCitation({ sources }) {
  const [open, setOpen] = useState(false);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="sources-row">
      <button
        className="sources-badge"
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-label={`${sources.length} source${sources.length > 1 ? "s" : ""} used`}
      >
        <BookOpen size={13} />
        {sources.length} source{sources.length > 1 ? "s" : ""}
      </button>

      {open && (
        <>
          <div
            className="sources-popup-overlay"
            onClick={() => setOpen(false)}
            onKeyDown={(e) => e.key === "Escape" && setOpen(false)}
          />
          <div className="sources-popup">
            <p className="sources-popup-title">Knowledge sources used</p>
            {sources.map((src, idx) => (
              <div key={src.id || idx} className="source-item">
                <span className="source-item-title">{src.title}</span>
                <span className="source-item-meta">
                  {src.domain?.toUpperCase()} · {src.source}
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

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
  const messagesPanelRef = useRef(null);
  const stickToBottomRef = useRef(true);
  const heroTextareaRef = useRef(null);
  const composerTextareaRef = useRef(null);

  useEffect(() => {
    fetchAgents()
      .then(setAgents)
      .catch(() => setAgents(fallbackAgents));
  }, []);

  useEffect(() => {
    const saved = loadConversations(user.id);
    if (saved.length) {
      setConversations(saved);
      // Do not auto-select a conversation on login/refresh to start with a fresh view.
      setActiveId(null);
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

  // Close the sidebar overlay with Escape, from anywhere.
  useEffect(() => {
    if (!sidebarOpen) return undefined;
    const onKeyDown = (event) => {
      if (event.key === "Escape") setSidebarOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [sidebarOpen]);

  // Track whether the user is scrolled near the bottom, so we only auto-scroll
  // when they haven't intentionally scrolled up to read earlier messages.
  const handlePanelScroll = useCallback(() => {
    const panel = messagesPanelRef.current;
    if (!panel) return;
    const distanceFromBottom =
      panel.scrollHeight - panel.scrollTop - panel.clientHeight;
    stickToBottomRef.current = distanceFromBottom < 120;
  }, []);

  const scrollToBottom = useCallback((smooth = true) => {
    const panel = messagesPanelRef.current;
    if (!panel) return;
    panel.scrollTo({
      top: panel.scrollHeight,
      behavior: smooth ? "smooth" : "auto",
    });
  }, []);

  useEffect(() => {
    if (stickToBottomRef.current) {
      scrollToBottom(false);
    }
  }, [activeId, scrollToBottom]);

  useEffect(() => {
    if (stickToBottomRef.current) {
      scrollToBottom(true);
    }
  }, [conversations, busy, scrollToBottom]);

  const activeConversation = useMemo(
    () => conversations.find((conversation) => conversation.id === activeId),
    [conversations, activeId],
  );

  const activeAgent = useMemo(
    () => agents.find((agent) => agent.id === selectedAgent) || agents[0],
    [agents, selectedAgent],
  );

  const hasMessages = Boolean(activeConversation?.messages.length);

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
    stickToBottomRef.current = true;
  }

  function selectConversation(conversation) {
    setActiveId(conversation.id);
    setSelectedAgent(conversation.agentId);
    setSidebarOpen(false);
    stickToBottomRef.current = true;
  }

  function pickAgent(agentId) {
    setSelectedAgent(agentId);
    if (!hasMessages && activeConversation) {
      updateActive((conversation) => ({ ...conversation, agentId }));
    } else {
      createNewChat(agentId);
    }
  }

  async function sendMessage(text = input) {
    const message = text.trim();
    if (!message || busy) return;

    let targetConversation = activeConversation;
    if (!targetConversation) {
      targetConversation = makeConversation(selectedAgent);
      setConversations((current) => [targetConversation, ...current]);
      setActiveId(targetConversation.id);
    }

    setInput("");
    setBusy(true);
    setError("");
    stickToBottomRef.current = true;

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

    setConversations((current) =>
      current.map((conversation) =>
        conversation.id === targetConversation.id
          ? {
              ...conversation,
              title:
                conversation.messages.length === 0
                  ? message.slice(0, 54)
                  : conversation.title,
              updatedAt: new Date().toISOString(),
              messages: [...conversation.messages, userMessage, assistantMessage],
            }
          : conversation
      )
    );

    try {
      await streamChat({
        agentId: selectedAgent,
        message,
        conversationId: targetConversation.backendId,
        history: targetConversation.messages
          .filter((entry) => entry.role === "user" || entry.role === "assistant")
          .slice(-10)
          .map((entry) => ({ role: entry.role, content: entry.content })),
        onStart: (payload) => {
          setConversations((current) => current.map((c) =>
            c.id === targetConversation.id ? {
              ...c,
              backendId: payload.conversation_id || c.backendId,
            } : c
          ));
        },
        onToken: (fullText) => {
          setConversations((current) => current.map((c) =>
            c.id === targetConversation.id ? {
              ...c,
              messages: c.messages.map((entry) =>
                entry.id === assistantMessage.id
                  ? { ...entry, content: fullText }
                  : entry,
              ),
            } : c
          ));
        },
        onDone: (payload) => {
          setConversations((current) => current.map((c) =>
            c.id === targetConversation.id ? {
              ...c,
              updatedAt: new Date().toISOString(),
              messages: c.messages.map((entry) =>
                entry.id === assistantMessage.id
                  ? {
                      ...entry,
                      streaming: false,
                      sources: payload.retrieved_context || [],
                    }
                  : entry,
              ),
            } : c
          ));
        },
      });
    } catch (streamError) {
      setError(streamError.message || "Something went wrong.");
      setConversations((current) => current.map((c) =>
        c.id === targetConversation.id ? {
          ...c,
          messages: c.messages.map((entry) =>
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
        } : c
      ));
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

  function autoGrow(el) {
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 200) + "px";
  }

  const initials = (user.user_metadata?.full_name || user.email || "?")
    .trim()
    .charAt(0)
    .toUpperCase();

  // Shared composer markup used both for the centered "hero" state (no
  // messages yet) and the docked state at the bottom once a chat exists.
  function renderComposer(textareaRef, variant) {
    return (
      <form
        className={`composer composer-${variant}`}
        onSubmit={(event) => {
          event.preventDefault();
          sendMessage();
        }}
      >
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onInput={(e) => autoGrow(e.target)}
          onKeyDown={onComposerKeyDown}
          placeholder="Ask anything"
          rows={1}
        />
        <div className="composer-toolbar">
          <div className="composer-toolbar-left">
            <button
              type="button"
              className="tool-chip icon-only"
              aria-label="Attach a file"
              title="Attach a file"
            >
              <Paperclip size={15} />
            </button>
            {agents.map((agent) => (
              <button
                key={agent.id}
                type="button"
                className={`tool-chip ${selectedAgent === agent.id ? "active" : ""}`}
                onClick={() => pickAgent(agent.id)}
              >
                {agent.id === "rti" ? <FileSearch size={14} /> : <Scale size={14} />}
                <span className="tool-chip-label">
                  {agent.name.replace(" Agent", "").replace(" Rights", "")}
                </span>
              </button>
            ))}
          </div>
          <button className="send-button" type="submit" disabled={busy || !input.trim()}>
            {busy ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
          </button>
        </div>
      </form>
    );
  }

  return (
    <main className="workspace">
      <nav className="icon-rail" aria-label="Primary">
        <button
          className="rail-btn"
          type="button"
          onClick={() => setSidebarOpen((open) => !open)}
          aria-label={sidebarOpen ? "Close sidebar" : "Open sidebar"}
          aria-expanded={sidebarOpen}
        >
          <PanelLeft size={19} />
        </button>
        <button
          className="rail-btn accent"
          type="button"
          onClick={() => createNewChat()}
          aria-label="New session"
          title="New session"
        >
          <Plus size={19} />
        </button>
        <button
          className="rail-btn"
          type="button"
          onClick={() => setSidebarOpen(true)}
          aria-label="Search chats"
          title="Search chats"
        >
          <Search size={18} />
        </button>
        <button
          className="rail-btn"
          type="button"
          onClick={() => setSidebarOpen(true)}
          aria-label="Saved chats"
          title="Saved chats"
        >
          <Library size={18} />
        </button>
      </nav>

      {sidebarOpen && <div className="scrim" onClick={() => setSidebarOpen(false)} />}

      <aside className={`sidebar ${sidebarOpen ? "open" : ""}`}>
        <div className="sidebar-head">
          <a className="brand compact" href="/">
            <span className="brand-mark">CA</span>
            <span>Civic AI</span>
          </a>
          <button
            className="icon-button"
            type="button"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close sidebar"
          >
            <X size={18} />
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
              onClick={() => pickAgent(agent.id)}
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

      <section className="chat-shell">
        <header className="chat-topbar">
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
            <button
              className="profile-chip"
              type="button"
              onClick={() => setProfileOpen(true)}
              aria-label="Open profile"
            >
              <span className="profile-avatar-sm">{initials}</span>
            </button>
          </div>
        </header>

        <div className="messages-panel" ref={messagesPanelRef} onScroll={handlePanelScroll}>
          {hasMessages ? (
            <div className="messages-inner">
              {activeConversation.messages.map((message) => (
                <article key={message.id} className={`message ${message.role}`}>
                  <div className="message-avatar">
                    {message.role === "assistant" ? <Bot size={18} /> : <User size={18} />}
                  </div>
                  <div className="message-bubble">
                    {message.role === "assistant" ? (
                      <>
                        <StreamingMessage
                          content={message.content}
                          streaming={!!message.streaming}
                        />
                        {!message.streaming && (
                          <SourcesCitation sources={message.sources} />
                        )}
                      </>
                    ) : (
                      <p>{message.content}</p>
                    )}
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <section className="empty-chat">
              <div className="spark-card">
                <Sparkles size={26} />
              </div>
              <h1 className="gradient-text">What can I help with?</h1>

              <div className="hero-composer">
                {renderComposer(heroTextareaRef, "hero")}
              </div>

              <div className="prompt-row">
                {(quickPrompts[selectedAgent] || quickPrompts.rti).map((prompt) => (
                  <button key={prompt} type="button" onClick={() => sendMessage(prompt)}>
                    {prompt}
                  </button>
                ))}
              </div>
            </section>
          )}
        </div>

        {error && <div className="error-toast">{error}</div>}

        {hasMessages && renderComposer(composerTextareaRef, "dock")}

        {hasMessages && <p className="disclaimer">AI can make mistakes. Please double-check responses.</p>}
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