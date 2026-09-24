"use client";

import { useState } from "react";
import { AskResponse, ChatMessage, Filters } from "@/lib/types";

// The "Ask a question" sidebar. Calls this app's own /api/ask route
// (relative, same-origin) -- that Route Handler proxies server-side to
// the FastAPI backend's URL (see app/api/ask/route.ts), so no
// NEXT_PUBLIC_* backend URL or CORS setup is needed here at all, unlike
// the Databricks build's frontend.
//
// Same Phase 6 MVP simplification the backend names: no conversation-
// level memory sent yet (`history` is always null).

const SUGGESTED_QUESTIONS = [
  "How did North America e-commerce revenue in 2026 YTD compare to the same period in 2025, and what drove the change?",
  "Which five products have the highest return rate this year, and is that concentrated in any region or size?",
  "Who are our top 10 customers by lifetime spend, and how many are repeat vs. one-time buyers?",
];

function activeFilterEntries(filters: Filters): [string, string][] {
  return (Object.entries(filters) as [string, string][]).filter(([, v]) => v);
}

// Every gold/authorized-view column in this project follows one of two
// suffix conventions (see context/schema_reference.yaml): a dollar
// amount always ends "_usd" (revenue_usd, aov_usd, margin_usd, ...) and
// a percentage always ends "_pct" (return_rate_pct, margin_pct, ...).
// The SQL agent drafts its SELECT against those same columns (or
// aliases derived from them), so formatting by column-name suffix is
// reliable here, not a guess -- a plain count/volume column (order_count,
// lines_sold, stockout_count) has neither suffix and is left as a
// compact, comma-grouped number instead.
function formatCell(column: string, value: unknown): string {
  if (value === null || value === undefined || value === "") return "";

  const num = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(num)) return String(value);

  const col = column.toLowerCase();

  if (col.endsWith("_usd")) {
    return `$${num.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }
  if (col.endsWith("_pct") || col.includes("percent")) {
    return `${num.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
  }
  // Plain numbers (counts, volumes, days, etc.): compact, comma-
  // separated, and only as many decimals as the value actually has
  // (capped at 2) -- an integer like order_count stays a clean "4,735"
  // rather than "4,735.00".
  return num.toLocaleString("en-US", { maximumFractionDigits: 2 });
}

function ResultTable({ response }: { response: AskResponse }) {
  if (response.rejected || response.rows.length === 0) return null;
  const previewRows = response.rows.slice(0, 10);
  return (
    <div className="result-table-wrap">
      <table className="result-table">
        <thead>
          <tr>
            {response.columns.map((c) => (
              <th key={c}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {previewRows.map((row, i) => (
            <tr key={i}>
              {response.columns.map((c) => (
                <td key={c}>{formatCell(c, row[c])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {response.rows.length > previewRows.length && (
        <p className="result-table-note">
          Showing {previewRows.length} of {response.rows.length} rows.
        </p>
      )}
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  return (
    <div className="chat-message">
      <div className="chat-question">{message.question}</div>

      {message.status === "pending" && (
        <div className="chat-pending">Thinking through SQL Agent -&gt; guardrails -&gt; Insight Agent...</div>
      )}

      {message.status === "error" && (
        <div className="chat-error">Request failed: {message.errorMessage}</div>
      )}

      {message.status === "done" && message.response && (
        <div className="chat-answer">
          {message.response.rejected ? (
            <div className="chat-rejected">
              Rejected by the guardrail layer: {message.response.rejection_reason}
            </div>
          ) : null}

          {!message.response.rejected && (
            <p className="chat-answer-heading">Analysis</p>
          )}
          <p className="chat-answer-text">{message.response.answer}</p>

          <ResultTable response={message.response} />

          {message.response.sql && (
            <details className="chat-sql-disclosure">
              <summary>SQL used</summary>
              <p className="chat-rationale">{message.response.sql_rationale}</p>
              <pre>{message.response.sql}</pre>
            </details>
          )}
        </div>
      )}
    </div>
  );
}

interface ChatSidebarProps {
  filters: Filters;
}

export default function ChatSidebar({ filters }: ChatSidebarProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  async function ask(question: string) {
    const trimmed = question.trim();
    if (!trimmed || busy) return;

    const id = `${Date.now()}`;
    setMessages((prev) => [...prev, { id, question: trimmed, status: "pending" }]);
    setInput("");
    setBusy(true);

    try {
      const res = await fetch(`/api/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: trimmed, filters, history: null }),
      });

      if (!res.ok) {
        const detail = await res.text();
        throw new Error(`${res.status} ${detail}`);
      }

      const data: AskResponse = await res.json();
      setMessages((prev) =>
        prev.map((m) => (m.id === id ? { ...m, status: "done", response: data } : m))
      );
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === id
            ? { ...m, status: "error", errorMessage: err instanceof Error ? err.message : String(err) }
            : m
        )
      );
    } finally {
      setBusy(false);
    }
  }

  const activeFilters = activeFilterEntries(filters);

  function clearChat() {
    if (busy) return;
    setMessages([]);
    setInput("");
  }

  return (
    <div className="chat-sidebar">
      <div className="chat-header">
        <div className="chat-header-row">
          <h2><span className="chat-header-icon">✦</span> Ask a question</h2>
          {messages.length > 0 && (
            <button
              type="button"
              className="chat-clear-btn"
              onClick={clearChat}
              disabled={busy}
              title="Clear chat"
            >
              Clear chat
            </button>
          )}
        </div>
        {activeFilters.length > 0 && (
          <div className="chat-active-filters">
            Filtered to:{" "}
            {activeFilters.map(([k, v]) => (
              <span key={k} className="chat-filter-chip">
                {k}: {v}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-suggestions">
            <p>Try one of the demo questions:</p>
            {SUGGESTED_QUESTIONS.map((q) => (
              <button key={q} className="chat-suggestion" onClick={() => ask(q)}>
                {q}
              </button>
            ))}
          </div>
        )}
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
      </div>

      <form
        className="chat-input-row"
        onSubmit={(e) => {
          e.preventDefault();
          ask(input);
        }}
      >
        <input
          type="text"
          value={input}
          placeholder="Ask about revenue, returns, customers, suppliers..."
          onChange={(e) => setInput(e.target.value)}
          disabled={busy}
        />
        <button type="submit" disabled={busy || !input.trim()}>
          Ask
        </button>
      </form>
    </div>
  );
}
