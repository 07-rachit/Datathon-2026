import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  listChatSessions,
  createChatSession,
  getChatMessages,
  sendChatMessage,
  confirmAgentAction,
  cancelAgentAction,
  downloadChatTranscript,
} from "../lib/api.js";


const ACTIVE_SESSION_KEY = "crime_intel_active_chat_session";

export default function Assistant() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(() => localStorage.getItem(ACTIVE_SESSION_KEY));
  const [messages, setMessages] = useState([]);
  const [focusedMessage, setFocusedMessage] = useState(null);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [language, setLanguage] = useState("en"); // "en" | "kn"
  const [listening, setListening] = useState(false);
  const [speakingId, setSpeakingId] = useState(null);
  const [exporting, setExporting] = useState(false);

  const bottomRef = useRef(null);
  const recognitionRef = useRef(null);

  const speechSupported = typeof window !== "undefined" && ("webkitSpeechRecognition" in window || "SpeechRecognition" in window);

  // Load session list & initial active session
  useEffect(() => {
    loadSessions();
  }, []);

  // Sync messages whenever activeSessionId changes
  useEffect(() => {
    if (activeSessionId) {
      localStorage.setItem(ACTIVE_SESSION_KEY, activeSessionId);
      getChatMessages(activeSessionId)
        .then((msgs) => {
          setMessages(msgs);
          // Auto-focus latest assistant message for inspector panel
          const asstMsgs = msgs.filter((m) => m.role === "assistant");
          if (asstMsgs.length > 0) {
            setFocusedMessage(asstMsgs[asstMsgs.length - 1]);
          }
        })
        .catch(() => {
          localStorage.removeItem(ACTIVE_SESSION_KEY);
          setActiveSessionId(null);
          setMessages([]);
        });
    } else {
      setMessages([]);
    }
  }, [activeSessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function loadSessions() {
    try {
      const list = await listChatSessions();
      setSessions(list);
      const storedSession = localStorage.getItem(ACTIVE_SESSION_KEY);
      if (list.length > 0) {
        if (!storedSession || !list.some((s) => s.id === storedSession)) {
          setActiveSessionId(list[0].id);
        } else {
          setActiveSessionId(storedSession);
        }
      } else {
        localStorage.removeItem(ACTIVE_SESSION_KEY);
        setActiveSessionId(null);
      }
    } catch {
      setSessions([]);
    }
  }

  async function handleCreateSession() {
    try {
      const s = await createChatSession();
      setSessions((prev) => [s, ...prev]);
      setActiveSessionId(s.id);
      setMessages([]);
      setFocusedMessage(null);
    } catch (err) {
      setError("Could not create a new chat session.");
    }
  }

  const [pendingAction, setPendingAction] = useState(null);
  const [actionExecuting, setActionExecuting] = useState(false);

  async function handleSend() {
    const text = input.trim();
    if (!text || sending) return;

    setError("");
    setSending(true);
    setInput("");

    // Temporary optimistic user message
    const tempUserMsg = {
      id: `temp-${Date.now()}`,
      role: "user",
      content: text,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      let sid = activeSessionId;
      if (!sid || (sessions.length > 0 && !sessions.some((s) => s.id === sid))) {
        const newS = await createChatSession();
        sid = newS.id;
        setActiveSessionId(sid);
        setSessions((prev) => [newS, ...prev]);
      }

      let answer;
      try {
        answer = await sendChatMessage(sid, text, language);
      } catch (sendErr) {
        if (sendErr.response && sendErr.response.status === 404) {
          const newS = await createChatSession();
          sid = newS.id;
          setActiveSessionId(sid);
          setSessions((prev) => [newS, ...prev]);
          answer = await sendChatMessage(sid, text, language);
        } else {
          throw sendErr;
        }
      }

      const asstMsg = {
        ...answer.assistant_message,
        reasoning_steps: answer.reasoning_steps || answer.assistant_message.reasoning_steps || [],
      };

      setMessages((prev) => [
        ...prev.filter((m) => !String(m.id).startsWith("temp-")),
        answer.user_message,
        asstMsg,
      ]);
      setFocusedMessage(asstMsg);
      setPendingAction(answer.pending_action || null);

      // Refresh session list to show updated titles
      loadSessions();
    } catch (err) {
      setError("Could not send message. Is the backend server online?");
    } finally {
      setSending(false);
    }
  }

  async function handleConfirmAction() {
    if (!pendingAction || actionExecuting) return;
    setActionExecuting(true);
    try {
      const res = await confirmAgentAction(pendingAction.id);
      setPendingAction(null);

      // Append AI execution confirmation message
      const confirmMsg = {
        id: `confirm-${Date.now()}`,
        role: "assistant",
        content: `✅ **Action Confirmed & Executed**\n\n${res.message}`,
        created_at: new Date().toISOString(),
        reasoning_steps: [`Confirmed & Executed tool '${pendingAction.tool_name}'`],
      };
      setMessages((prev) => [...prev, confirmMsg]);
      setFocusedMessage(confirmMsg);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to confirm action.");
    } finally {
      setActionExecuting(false);
    }
  }

  async function handleCancelAction() {
    if (!pendingAction || actionExecuting) return;
    setActionExecuting(true);
    try {
      await cancelAgentAction(pendingAction.id);
      setPendingAction(null);

      const cancelMsg = {
        id: `cancel-${Date.now()}`,
        role: "assistant",
        content: "❌ Write action cancelled by officer.",
        created_at: new Date().toISOString(),
        reasoning_steps: [`Cancelled write tool '${pendingAction.tool_name}'`],
      };
      setMessages((prev) => [...prev, cancelMsg]);
    } catch (err) {
      setError("Failed to cancel action.");
    } finally {
      setActionExecuting(false);
    }
  }


  function handleVoiceToggle() {
    if (!speechSupported) return;
    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
      return;
    }
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const rec = new SpeechRecognition();
    rec.continuous = false;
    rec.interimResults = false;
    rec.lang = language === "kn" ? "kn-IN" : "en-US";

    rec.onresult = (e) => {
      const transcript = e.results[0][0].transcript;
      setInput((prev) => (prev ? `${prev} ${transcript}` : transcript));
      setListening(false);
    };

    rec.onerror = () => setListening(false);
    rec.onend = () => setListening(false);

    recognitionRef.current = rec;
    rec.start();
    setListening(true);
  }

  function handleSpeak(msg) {
    if (speakingId === msg.id) {
      window.speechSynthesis?.cancel();
      setSpeakingId(null);
      return;
    }
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      const uttr = new SpeechSynthesisUtterance(msg.content);
      uttr.lang = language === "kn" ? "kn-IN" : "en-US";
      uttr.onend = () => setSpeakingId(null);
      uttr.onerror = () => setSpeakingId(null);
      setSpeakingId(msg.id);
      window.speechSynthesis.speak(uttr);
    }
  }

  async function handleExportPDF() {
    if (!activeSessionId) return;
    setExporting(true);
    try {
      await downloadChatTranscript(activeSessionId, "investigation_ai");
    } catch {
      setError("Failed to download PDF transcript.");
    } finally {
      setExporting(false);
    }
  }

  // Parse sources for focused message
  let focusedSources = [];
  if (focusedMessage?.sources) {
    try {
      focusedSources = JSON.parse(focusedMessage.sources);
    } catch {
      focusedSources = [];
    }
  }

  return (
    <div className="flex h-screen bg-bg text-ink overflow-hidden">
      {/* ── 1. Left Sessions Column (260px) ────────────────────────────────── */}
      <div className="w-64 border-r border-line bg-panel flex flex-col">
        <div className="p-4 border-b border-line flex items-center justify-between">
          <p className="font-mono text-xs text-muted uppercase tracking-wider">Investigative Threads</p>
          <button
            onClick={handleCreateSession}
            className="text-xs font-mono bg-teal text-bg px-2.5 py-1 rounded font-semibold hover:brightness-110 transition"
          >
            + New
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {sessions.length === 0 ? (
            <p className="text-muted text-xs font-mono p-3">No saved sessions yet.</p>
          ) : (
            sessions.map((s) => (
              <div
                key={s.id}
                onClick={() => setActiveSessionId(s.id)}
                className={`p-3 rounded text-xs font-mono cursor-pointer transition truncate border ${
                  activeSessionId === s.id
                    ? "bg-panel2 border-teal text-teal font-semibold"
                    : "border-transparent text-muted hover:text-ink hover:bg-panel2/50"
                }`}
              >
                <p className="truncate">{s.title || "Untitled Session"}</p>
                <p className="text-[10px] text-muted/60 mt-1">
                  {new Date(s.created_at).toLocaleDateString()}
                </p>
              </div>
            ))
          )}
        </div>
      </div>

      {/* ── 2. Center Column: Main Conversation Area (Flex-1) ────────────── */}
      <div className="flex-1 flex flex-col bg-bg border-r border-line relative">
        {/* Header Bar */}
        <div className="p-4 border-b border-line bg-panel flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-display text-xl text-ink">AI Case Assistant</h2>
                <span className="font-mono text-[10px] uppercase bg-teal/10 border border-teal/40 text-teal px-2 py-0.5 rounded">
                  Deep Search &middot; Investigator Mode
                </span>
              </div>
              <p className="text-muted text-xs font-mono mt-0.5">
                Full-page investigative research desk with real-time RAG context & reasoning steps
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Language Toggle */}
            <div className="bg-panel2 border border-line rounded p-0.5 flex text-xs font-mono">
              <button
                onClick={() => setLanguage("en")}
                className={`px-2.5 py-1 rounded transition ${language === "en" ? "bg-amber text-base font-bold" : "text-muted"}`}
              >
                EN
              </button>
              <button
                onClick={() => setLanguage("kn")}
                className={`px-2.5 py-1 rounded transition ${language === "kn" ? "bg-amber text-base font-bold" : "text-muted"}`}
              >
                ಕನ್ನಡ
              </button>
            </div>

            {/* Export PDF Button */}
            <button
              onClick={handleExportPDF}
              disabled={exporting || !activeSessionId}
              className="bg-amber text-base text-xs font-mono font-semibold rounded px-3 py-1.5 hover:brightness-110 transition disabled:opacity-50"
            >
              {exporting ? "Generating..." : "⬇ Export PDF Report"}
            </button>
          </div>
        </div>

        {/* Message Scroll Container */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {error && (
            <div className="border border-crit/40 bg-crit/10 text-crit text-xs font-mono p-3 rounded">
              {error}
            </div>
          )}

          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-8 text-muted font-mono">
              <div className="w-12 h-12 rounded-full bg-teal/10 border border-teal/40 flex items-center justify-center text-teal text-xl mb-3">
                🔍
              </div>
              <p className="text-ink font-display text-lg mb-1">Deep-Search AI Case Assistant</p>
              <p className="text-xs max-w-md leading-relaxed">
                Ask about specific case IDs (e.g. <code className="text-teal">CR-2026-0016</code>), suspect phone numbers, crime trends, or request investigative next steps.
              </p>
            </div>
          ) : (
            messages.map((m) => {
              const isUser = m.role === "user";
              const isFocused = focusedMessage?.id === m.id;

              return (
                <div
                  key={m.id}
                  onClick={() => !isUser && setFocusedMessage(m)}
                  className={`flex ${isUser ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg p-4 cursor-pointer transition border ${
                      isUser
                        ? "bg-amber text-base border-transparent"
                        : isFocused
                        ? "bg-panel2 border-teal ring-2 ring-teal/20"
                        : "bg-panel border-line hover:border-line/80"
                    }`}
                  >
                    <div className="flex items-center justify-between text-xs font-mono mb-2 border-b border-line/40 pb-1.5">
                      <span className={isUser ? "text-base font-bold uppercase" : "text-teal font-bold uppercase"}>
                        {isUser ? "Investigator Query" : "AI Assistant Response"}
                      </span>
                      <span className="text-muted text-[10px]">
                        {new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </div>

                    <p className="text-sm leading-relaxed whitespace-pre-wrap font-body">{m.content}</p>

                    {!isUser && (
                      <div className="flex items-center justify-between mt-3 pt-2 border-t border-line/40 text-xs font-mono">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSpeak(m);
                          }}
                          className="text-muted hover:text-teal transition flex items-center gap-1"
                        >
                          🔊 {speakingId === m.id ? "Stop Reading" : "Read Aloud"}
                        </button>

                        <span className="text-[11px] text-teal hover:underline">
                          Inspect Reasoning & Sources →
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}

          {/* Write Action Confirmation Card */}
          {pendingAction && (
            <div className="bg-panel2 border-2 border-amber/80 rounded-lg p-4 space-y-3 font-mono text-xs shadow-2xl animate-slide-up">
              <div className="flex items-center gap-2 text-amber font-bold text-sm">
                <span>⚠️ WRITE ACTION CONFIRMATION REQUIRED</span>
              </div>
              <p className="text-ink text-xs leading-relaxed font-body">
                {pendingAction.description}
              </p>
              <div className="bg-bg/60 p-2.5 rounded border border-line text-[11px] text-muted space-y-1">
                <p><span className="text-teal">Tool:</span> {pendingAction.tool_name}</p>
                <p><span className="text-teal">Target Parameters:</span> {JSON.stringify(pendingAction.arguments)}</p>
              </div>
              <div className="flex items-center gap-3 pt-1">
                <button
                  onClick={handleConfirmAction}
                  disabled={actionExecuting}
                  className="bg-amber text-base font-bold px-4 py-2 rounded text-xs hover:brightness-110 transition flex items-center gap-1.5 disabled:opacity-50"
                >
                  {actionExecuting ? "Executing..." : "✓ Confirm & Execute Action"}
                </button>
                <button
                  onClick={handleCancelAction}
                  disabled={actionExecuting}
                  className="border border-line text-muted hover:text-crit px-4 py-2 rounded text-xs transition disabled:opacity-50"
                >
                  ✕ Cancel Action
                </button>
              </div>
            </div>
          )}

          <div ref={bottomRef} />

        </div>

        {/* Multi-line Input Box */}
        <div className="p-4 border-t border-line bg-panel">
          <div className="flex items-end gap-3 bg-panel2 border border-line rounded-lg p-2 focus-within:border-teal transition">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Ask an investigative question, search case ID, phone number, or crime pattern..."
              rows={2}
              className="flex-1 bg-transparent text-ink text-sm outline-none resize-none font-body px-2"
            />

            {speechSupported && (
              <button
                onClick={handleVoiceToggle}
                className={`p-2 rounded text-sm transition ${listening ? "bg-crit text-ink animate-pulse" : "text-muted hover:text-ink"}`}
                title="Voice input mic"
              >
                🎤
              </button>
            )}

            <button
              onClick={handleSend}
              disabled={sending || !input.trim()}
              className="bg-amber text-base font-semibold px-4 py-2 rounded text-xs font-mono hover:brightness-110 transition disabled:opacity-40"
            >
              {sending ? "Analyzing..." : "Send Query ➔"}
            </button>
          </div>
        </div>
      </div>

      {/* ── 3. Right Inspector Column: Context & Reasoning (320px) ───────── */}
      <div className="w-80 border-l border-line bg-panel p-5 flex flex-col overflow-y-auto space-y-6">
        <div>
          <h3 className="font-display text-lg text-ink mb-1">Context Inspector</h3>
          <p className="text-muted text-xs font-mono">
            Click any AI response in the main thread to view its exact reasoning path and source citations.
          </p>
        </div>

        {!focusedMessage ? (
          <div className="border border-line rounded p-4 text-center text-muted text-xs font-mono bg-panel2">
            No response selected. Click an AI response to inspect citations.
          </div>
        ) : (
          <>
            {/* AI Reasoning Pipeline */}
            <div>
              <p className="font-mono text-xs text-teal uppercase font-semibold mb-2 flex items-center gap-1.5">
                ⚡ Execution Reasoning Steps
              </p>
              {!focusedMessage.reasoning_steps || focusedMessage.reasoning_steps.length === 0 ? (
                <p className="text-muted text-xs font-mono">No recorded reasoning steps.</p>
              ) : (
                <div className="space-y-2 bg-panel2 border border-line rounded p-3 text-xs font-mono">
                  {focusedMessage.reasoning_steps.map((st, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <span className="text-amber">›</span>
                      <span className="text-ink text-[11px] leading-tight">{st}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Retrieved Source Case Citations */}
            <div>
              <p className="font-mono text-xs text-amber uppercase font-semibold mb-2">
                📄 Source Case Citations ({focusedSources.length})
              </p>

              {focusedSources.length === 0 ? (
                <p className="text-muted text-xs font-mono">No direct sources cited for this reply.</p>
              ) : (
                <div className="space-y-3">
                  {focusedSources.map((src, i) => (
                    <div key={i} className="bg-panel2 border border-line rounded p-3 text-xs font-mono space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-teal font-bold">{src.case_code}</span>
                        <span className="text-amber text-[10px]">{(src.score * 100).toFixed(0)}% match</span>
                      </div>

                      <span className="inline-block text-[10px] uppercase px-1.5 py-0.5 rounded bg-panel border border-line text-muted">
                        Match: {src.match_type}
                      </span>

                      <p className="text-muted text-[11px] leading-normal line-clamp-3 bg-bg/50 p-2 rounded border border-line/40">
                        "{src.snippet}"
                      </p>

                      <Link
                        to={`/cases/${src.case_id}`}
                        target="_blank"
                        className="text-teal hover:underline text-[11px] block text-right pt-1 font-semibold"
                      >
                        Open Case File ➔
                      </Link>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
