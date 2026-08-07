# Prompt for Antigravity — CrimeIntel: Full-Page AI Case Assistant

Copy everything below the line into Antigravity as your first message in a fresh session (or continuation, if it has prior context on this repo).

---

I'm continuing work on **CrimeIntel**. Right now the AI chatbot ("Case Assistant" — deep-search investigator mode, bilingual EN/Kannada, voice, PDF export, reasoning/source citations) only exists as a small floating bottom-right widget (`ChatWidget.jsx`). It's too cramped for serious investigative work — long answers, source lists, and reasoning steps all scroll inside a tiny fixed-size panel.

## What I want
Add a **full dedicated page** for the AI Case Assistant, accessible as its own item in the left sidebar (like Dashboard, Cases, Map, Network, Offenders, Insights, Admin currently are) — not just the small popup. This should be a first-class page with room to actually work, not a cramped panel.

**Keep the floating widget too** — for quick lookups while on other pages (e.g. glancing at a case detail and asking a quick question without leaving that page). Both should point at the **same backend session/conversation state**, so a conversation started in the widget can be continued on the full page and vice versa (don't fork into two separate chat histories).

## Before writing code
Review the existing `ChatWidget.jsx`, `chat.py` router, and how sessions/conversation history currently work, so the new page reuses that logic instead of duplicating it.

## New full-page AI Assistant (`/assistant` or similar route, sidebar item e.g. "04 · AI Assistant")

**Layout — three-column, desktop-first:**
1. **Left:** conversation/session list sidebar (session titles, "+ New" button, delete/rename) — this already exists in some form for the widget's session switching; promote it to a real persistent left panel here.
2. **Center:** the actual chat thread — full-height, full-width message area (not a scrollable mini-box). Larger font for readability during investigation work. User messages and AI messages clearly distinguished, same ops-room dark theme.
3. **Right (collapsible):** context panel — for the currently-focused answer, show the **reasoning steps** (from Sprint 4's `reasoning_steps`) and **source case citations with similarity scores** as a proper readable list (not tiny chips), each source clickable to open that case in a new context/tab. This is the same data the widget shows cramped — give it room here.

**Top bar of the page:**
- EN / ಕನ್ನಡ language toggle (existing)
- Voice input mic + text-to-speech toggle (existing)
- "Export conversation as PDF" button (existing, make it more prominent)
- Investigator-mode indicator (badge showing "Deep Search · Investigator Mode" as in the current widget)

**Input area:**
- Larger multi-line input box at the bottom of the center column (not fighting for space next to a small send button) with mic + send.

## Floating widget changes
- Add a small "Open full page" / expand icon in the widget's header that navigates to the new `/assistant` page carrying over the current session ID, so users can "pop out" a conversation started in the widget.
- Keep the widget itself otherwise as-is (still useful for quick questions without leaving the current page).

## Backend
- No new endpoints should be needed if sessions are already keyed by session ID and persisted — confirm this is true. If the widget currently keeps any state client-side only (not persisted per session properly), fix that first so both surfaces can share state reliably.

## Cross-cutting
- Keep the dark "ops-room" theme (slate, amber/teal accents, monospace case IDs) consistent with the rest of the app.
- Role visibility: same roles that currently see the chat widget should see this page (investigator/analyst/admin — confirm against existing RBAC, not viewer if that's the current rule).
- Test: start a conversation in the widget, confirm it appears correctly in the full page and vice versa, before considering this done. Report results back to me.

Start by reviewing the existing chat widget/session code, then build the full page, then wire the "pop out" link from the widget.
