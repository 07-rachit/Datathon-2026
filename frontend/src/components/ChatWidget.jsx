import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  createChatSession, getChatMessages, sendChatMessage, confirmAgentAction, cancelAgentAction, downloadChatTranscript,
} from "../lib/api.js";


const ACTIVE_SESSION_KEY = "ci_active_chat_session";

const MATCH_LABEL = {
  direct_case_id: "exact case ID",
  phone_match: "phone match",
  similarity: "similar",
};

function ChatIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M4 5.5C4 4.67 4.67 4 5.5 4h13c.83 0 1.5.67 1.5 1.5v10c0 .83-.67 1.5-1.5 1.5H9l-4 4v-4H5.5A1.5 1.5 0 0 1 4 15.5v-10Z"
        stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round"
      />
      <circle cx="8.5" cy="10.5" r="1" fill="currentColor" />
      <circle cx="12" cy="10.5" r="1" fill="currentColor" />
      <circle cx="15.5" cy="10.5" r="1" fill="currentColor" />
    </svg>
  );
}
function CloseIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}
function MicIcon({ active }) {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="9" y="2" width="6" height="12" rx="3" stroke="currentColor" strokeWidth="1.7" fill={active ? "currentColor" : "none"} />
      <path d="M5 11a7 7 0 0 0 14 0M12 18v3" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}
function SpeakerIcon({ speaking }) {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M4 9v6h4l5 4V5L8 9H4Z" fill="currentColor" opacity={speaking ? 1 : 0.85} />
      <path d="M17 8.5a5 5 0 0 1 0 7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}
function DownloadIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 3v12m0 0-4-4m4 4 4-4M5 19h14" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function SourceChip({ source }) {
  return (
    <Link
      to={`/cases/${source.case_id}`}
      className="inline-flex items-center gap-1 border border-line rounded px-2 py-0.5 text-[11px] font-mono text-teal hover:bg-panel2 transition"
      title={source.snippet}
    >
      {source.case_code}
      <span className="text-muted">
        · {MATCH_LABEL[source.match_type] || "similar"} · {(source.score * 100).toFixed(0)}%
      </span>
    </Link>
  );
}

function MessageBubble({ msg, onSpeak, speakingId }) {
  const isUser = msg.role === "user";
  const [showReasoning, setShowReasoning] = useState(false);
  let sources = [];
  try {
    sources = msg.sources ? JSON.parse(msg.sources) : [];
  } catch {
    sources = [];
  }
  const steps = msg.reasoning_steps || [];

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div className={`max-w-[85%] ${isUser ? "bg-amber text-base" : "bg-panel2 border border-line text-ink"} rounded-md px-3 py-2`}>
        <p className="text-[13px] whitespace-pre-wrap leading-relaxed">{msg.content}</p>
        <div className="flex items-center justify-between mt-1.5">
          {!isUser && (
            <div className="flex items-center gap-3">
              <button
                onClick={() => onSpeak(msg)}
                className="text-muted hover:text-teal transition flex items-center gap-1"
                title="Read aloud"
              >
                <SpeakerIcon speaking={speakingId === msg.id} />
              </button>
              {steps.length > 0 && (
                <button
                  onClick={() => setShowReasoning(!showReasoning)}
                  className="text-[11px] font-mono text-teal hover:underline flex items-center gap-1"
                >
                  ⚡ {showReasoning ? "Hide Reasoning" : "Show Reasoning"}
                </button>
              )}
            </div>
          )}
        </div>

        {/* Reasoning Steps Panel */}
        {!isUser && showReasoning && steps.length > 0 && (
          <div className="mt-2 pt-2 border-t border-line/40 space-y-1.5 text-[11px] font-mono text-muted bg-panel p-2 rounded">
            <p className="text-teal font-semibold uppercase text-[10px] tracking-wider">AI Reasoning Pipeline</p>
            {steps.map((st, i) => (
              <div key={i} className="flex items-start gap-1.5">
                <span className="text-amber">›</span>
                <span>{st}</span>
              </div>
            ))}
          </div>
        )}

        {sources.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2 pt-2 border-t border-line/40">
            {sources.map((s, i) => (
              <SourceChip key={i} source={s} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function ChatWidget() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [sessionId, setSessionId] = useState(() => localStorage.getItem(ACTIVE_SESSION_KEY));
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [language, setLanguage] = useState("en"); // "en" | "kn"
  const [listening, setListening] = useState(false);
  const [speakingId, setSpeakingId] = useState(null);
  const bottomRef = useRef(null);
  const recognitionRef = useRef(null);

  const speechSupported = typeof window !== "undefined" && ("webkitSpeechRecognition" in window || "SpeechRecognition" in window);

  useEffect(() => {
    if (open && sessionId) {
      getChatMessages(sessionId).then(setMessages).catch(() => {
        localStorage.removeItem(ACTIVE_SESSION_KEY);
        setSessionId(null);
      });
    }
  }, [open, sessionId]);

  useEffect(() => {
    if (open) bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, open]);

  async function ensureSession() {
    if (sessionId) return sessionId;
    const session = await createChatSession();
    setSessionId(session.id);
    localStorage.setItem(ACTIVE_SESSION_KEY, session.id);
    return session.id;
  }

  async function handleNewChat() {
    const session = await createChatSession();
    setSessionId(session.id);
    localStorage.setItem(ACTIVE_SESSION_KEY, session.id);
    setMessages([]);
  }

  async function handleExportPdf() {
    if (!sessionId) return;
    try {
      await downloadChatTranscript(sessionId, "case_assistant_chat");
    } catch {
      setError("Could not export the conversation as PDF.");
    }
  }

  function handleVoiceInput() {
    if (!speechSupported) {
      setError("Voice input isn't supported in this browser. Try Chrome.");
      return;
    }
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.lang = language === "kn" ? "kn-IN" : "en-IN";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => setListening(true);
    recognition.onend = () => setListening(false);
    recognition.onerror = () => setListening(false);
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setInput((prev) => (prev ? `${prev} ${transcript}` : transcript));
    };

    recognitionRef.current = recognition;
    recognition.start();
  }

  function handleSpeak(msg) {
    if (!("speechSynthesis" in window)) return;
    if (speakingId === msg.id) {
      window.speechSynthesis.cancel();
      setSpeakingId(null);
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(msg.content);
    utterance.lang = language === "kn" ? "kn-IN" : "en-IN";
    utterance.onend = () => setSpeakingId(null);
    utterance.onerror = () => setSpeakingId(null);
    setSpeakingId(msg.id);
    window.speechSynthesis.speak(utterance);
  }

  const [pendingAction, setPendingAction] = useState(null);
  const [actionExecuting, setActionExecuting] = useState(false);

  async function handleSend(e) {
    e.preventDefault();
    if (!input.trim()) return;

    const question = input;
    setInput("");
    setSending(true);
    setError("");
    setMessages((prev) => [
      ...prev,
      { id: `temp-${Date.now()}`, role: "user", content: question, sources: null },
    ]);

    try {
      const sid = await ensureSession();
      const answer = await sendChatMessage(sid, question, language);
      const asstMsg = {
        ...answer.assistant_message,
        reasoning_steps: answer.reasoning_steps || answer.assistant_message.reasoning_steps || [],
      };
      setMessages((prev) => [
        ...prev.filter((m) => !String(m.id).startsWith("temp-")),
        answer.user_message,
        asstMsg,
      ]);
      setPendingAction(answer.pending_action || null);
    } catch (err) {
      setError("Could not reach the assistant. Is the API running?");
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
      setMessages((prev) => [
        ...prev,
        {
          id: `confirm-${Date.now()}`,
          role: "assistant",
          content: `✅ **Action Confirmed & Executed**\n\n${res.message}`,
          reasoning_steps: [`Confirmed & Executed tool '${pendingAction.tool_name}'`],
        },
      ]);
    } catch (err) {
      setError("Failed to confirm write action.");
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
      setMessages((prev) => [
        ...prev,
        {
          id: `cancel-${Date.now()}`,
          role: "assistant",
          content: "❌ Write action cancelled by officer.",
          reasoning_steps: [`Cancelled write tool '${pendingAction.tool_name}'`],
        },
      ]);
    } catch (err) {
      setError("Failed to cancel action.");
    } finally {
      setActionExecuting(false);
    }
  }


  return (
    <>
      {open && (
        <div className="fixed bottom-24 right-6 w-[400px] h-[580px] bg-panel border border-line rounded-lg shadow-2xl flex flex-col z-50 overflow-hidden">
          <div className="px-4 py-3 border-b border-line bg-panel2">
            <div className="flex items-center justify-between mb-2">
              <div>
                <p className="font-mono text-teal text-[10px] tracking-[0.2em]">DEEP SEARCH · INVESTIGATOR MODE</p>
                <p className="text-ink font-display text-lg leading-tight">Case Assistant</p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    setOpen(false);
                    navigate("/assistant");
                  }}
                  className="text-muted hover:text-teal text-xs font-mono transition border border-line px-1.5 py-0.5 rounded flex items-center gap-1"
                  title="Expand to Full Page"
                >
                  Full Page ↗
                </button>
                <button onClick={() => setOpen(false)} className="text-muted hover:text-crit transition">
                  <CloseIcon />
                </button>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1 bg-panel rounded border border-line p-0.5">
                <button
                  onClick={() => setLanguage("en")}
                  className={`px-2 py-0.5 text-[11px] font-mono rounded transition ${language === "en" ? "bg-amber text-base" : "text-muted hover:text-ink"}`}
                >
                  EN
                </button>
                <button
                  onClick={() => setLanguage("kn")}
                  className={`px-2 py-0.5 text-[11px] font-mono rounded transition ${language === "kn" ? "bg-amber text-base" : "text-muted hover:text-ink"}`}
                >
                  ಕನ್ನಡ
                </button>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={handleExportPdf}
                  disabled={!sessionId || messages.length === 0}
                  className="text-muted hover:text-teal text-xs font-mono transition disabled:opacity-30 flex items-center gap-1"
                  title="Export conversation as PDF"
                >
                  <DownloadIcon /> PDF
                </button>
                <button
                  onClick={handleNewChat}
                  className="text-muted hover:text-teal text-xs font-mono transition"
                  title="Start a new conversation"
                >
                  + NEW
                </button>
              </div>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto px-3 py-3">
            {messages.length === 0 && (
              <p className="text-muted text-xs leading-relaxed">
                Ask about a case ID, a phone number, a district, or a pattern across cases &mdash;
                e.g. <span className="text-ink">"What connects CR-2026-0016 to other open cases?"</span>
                {" "}Tap the mic to ask by voice, in English or Kannada.
              </p>
            )}
            {messages.map((m) => (
              <MessageBubble key={m.id} msg={m} onSpeak={handleSpeak} speakingId={speakingId} />
            ))}

            {pendingAction && (
              <div className="bg-panel2 border-2 border-amber/80 rounded-lg p-3 space-y-2 font-mono text-xs shadow-xl my-2 animate-slide-up">
                <div className="flex items-center gap-1.5 text-amber font-bold text-[11px]">
                  <span>⚠️ ACTION CONFIRMATION REQUIRED</span>
                </div>
                <p className="text-ink text-[11px] leading-snug font-body">
                  {pendingAction.description}
                </p>
                <div className="flex items-center gap-2 pt-1">
                  <button
                    type="button"
                    onClick={handleConfirmAction}
                    disabled={actionExecuting}
                    className="bg-amber text-base font-bold px-3 py-1.5 rounded text-[11px] hover:brightness-110 transition disabled:opacity-50"
                  >
                    {actionExecuting ? "Executing..." : "✓ Confirm & Execute"}
                  </button>
                  <button
                    type="button"
                    onClick={handleCancelAction}
                    disabled={actionExecuting}
                    className="border border-line text-muted hover:text-crit px-3 py-1.5 rounded text-[11px] transition disabled:opacity-50"
                  >
                    ✕ Cancel
                  </button>
                </div>
              </div>
            )}

            <div ref={bottomRef} />

          </div>

          {error && (
            <p className="text-crit text-xs font-mono border-t border-crit/40 bg-crit/10 px-4 py-1.5">{error}</p>
          )}

          <form onSubmit={handleSend} className="border-t border-line p-3 flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={language === "kn" ? "ಪ್ರಶ್ನೆ ಕೇಳಿ..." : "Ask the case assistant..."}
              className="flex-1 bg-panel2 border border-line rounded px-3 py-2 text-ink text-sm focus:outline-none focus:ring-1 focus:ring-teal"
            />
            <button
              type="button"
              onClick={handleVoiceInput}
              className={`rounded px-3 py-2 border transition ${listening ? "bg-crit/20 border-crit text-crit animate-pulse" : "border-line text-muted hover:text-teal"}`}
              title="Voice input"
            >
              <MicIcon active={listening} />
            </button>
            <button
              type="submit"
              disabled={sending}
              className="bg-amber text-base font-semibold rounded px-4 py-2 text-sm hover:brightness-110 transition disabled:opacity-50"
            >
              {sending ? "..." : "Send"}
            </button>
          </form>
        </div>
      )}

      <button
        onClick={() => setOpen((v) => !v)}
        className="fixed bottom-6 right-6 w-14 h-14 rounded-full bg-amber text-base flex items-center justify-center shadow-2xl hover:brightness-110 transition z-50"
        title="Case Assistant"
      >
        {open ? <CloseIcon /> : <ChatIcon />}
      </button>
    </>
  );
}
