"use client";

import { useEffect, useState } from "react";

const RAW_API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const API_BASE = RAW_API_BASE.replace(/\/+$/, "");

interface DialogueEntry {
  speaker: string;
  text: string;
  timestamp?: string;
}

interface CallRecord {
  company_stance?: string;
  initial_offer?: number;
  final_price?: number;
  savings?: number;
  status?: string;
  timestamp?: string;
  evidence_quote?: string;
  dialogue_history?: DialogueEntry[];
}

interface GroupedData {
  [merchant: string]: CallRecord[];
}

export default function HistoryPage() {
  const [allData, setAllData] = useState<GroupedData>({});
  const [filtered, setFiltered] = useState<GroupedData>({});
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    loadMerchants();
  }, []);

  useEffect(() => {
    if (!search.trim()) {
      setFiltered(allData);
      return;
    }
    const q = search.toLowerCase();
    const result: GroupedData = {};
    Object.keys(allData).forEach(name => {
      if (name.toLowerCase().includes(q)) result[name] = allData[name];
    });
    setFiltered(result);
  }, [search, allData]);

  async function loadMerchants() {
    try {
      const res = await fetch(`${API_BASE}/api/merchants`);
      const data: GroupedData = await res.json();
      setAllData(data);
      setFiltered(data);
      setLoading(false);
    } catch (e) {
      console.error(e);
      setError(true);
      setLoading(false);
    }
  }

  async function playSnippet(text: string) {
    try {
      const res = await fetch(`${API_BASE}/api/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, voice: "en-US-JennyNeural" }),
      });
      const blob = await res.blob();
      const audio = new Audio(URL.createObjectURL(blob));
      audio.play();
    } catch (e) {
      console.error(e);
    }
  }

  const merchantNames = Object.keys(filtered);

  return (
    <div className="min-h-screen font-sans antialiased selection:bg-orange-100"
      style={{ background: "radial-gradient(circle at 85% 15%, rgba(251,146,60,0.22) 0%, transparent 60%), #FAF6F0", color: "#201815" }}>

      {/* ── HEADER ── */}
      <header className="bg-white/90 backdrop-blur-md border-b px-4 sm:px-8 py-4 sticky top-0 z-40" style={{ borderColor: "#F1E9DE" }}>
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <a href="/" className="w-9 h-9 rounded-2xl bg-orange-600 flex items-center justify-center text-white shadow-sm hover:bg-orange-700 transition">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
              </svg>
            </a>
            <div>
              <span className="font-bold text-lg sm:text-xl tracking-tight">VoiceAgent</span>
              <span className="ml-1 text-xs px-2.5 py-0.5 rounded-full bg-orange-100 text-orange-800 font-semibold">Merchant Vault</span>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <a href="/" className="px-4 py-2 rounded-full bg-orange-50 hover:bg-orange-100 border border-orange-200 text-xs font-semibold transition">
              🎙️ Live Call Studio
            </a>
            <span className="inline-flex items-center space-x-1.5 text-xs font-semibold px-3 py-1 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>MongoDB Storage Active</span>
            </span>
          </div>
        </div>
      </header>

      {/* ── MAIN ── */}
      <main className="max-w-7xl mx-auto px-4 sm:px-8 py-8 space-y-8">

        {/* Title & Search */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-orange-700 bg-orange-100 px-3 py-1 rounded-full">Database Records</span>
            <h1 className="font-serif text-3xl sm:text-4xl mt-2 font-bold">Grouped Merchant Call Histories</h1>
            <p className="text-xs sm:text-sm mt-1" style={{ color: "#7A6E65" }}>
              All multi-turn voice negotiations categorized by vendor name with company stances, savings, and full transcripts.
            </p>
          </div>
          <div className="w-full md:w-80">
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full p-3 rounded-2xl border bg-white text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/20"
              style={{ borderColor: "#F1E9DE" }}
              placeholder="Filter by merchant name…"
            />
          </div>
        </div>

        {/* Content */}
        <div className="space-y-6">
          {loading && (
            <div className="text-center py-12 text-sm animate-pulse" style={{ color: "#7A6E65" }}>
              Loading merchant records from database…
            </div>
          )}
          {error && (
            <div className="text-center py-12 text-red-600 text-sm">
              Failed to load records from server. Make sure the backend is running.
            </div>
          )}
          {!loading && !error && merchantNames.length === 0 && (
            <div className="text-center py-12 text-sm" style={{ color: "#7A6E65" }}>
              No merchant records saved yet. <a href="/" className="underline text-orange-700 font-semibold">Start a call</a> to save one!
            </div>
          )}

          {merchantNames.map(merchant => {
            const records = filtered[merchant];
            const totalSaved = records.reduce((acc, r) => acc + (r.savings || 0), 0);
            const latestStance = records[0]?.company_stance || "Strict corporate budget mandate";

            return (
              <div key={merchant} className="bg-white rounded-3xl border shadow-sm overflow-hidden p-6 sm:p-8 space-y-5" style={{ borderColor: "#F1E9DE" }}>
                {/* Merchant Header */}
                <div className="flex flex-col md:flex-row md:items-center justify-between pb-5 border-b gap-4" style={{ borderColor: "#F1E9DE" }}>
                  <div>
                    <div className="flex items-center space-x-2">
                      <h2 className="font-serif text-2xl font-bold">{merchant}</h2>
                      <span className="text-xs px-2.5 py-0.5 rounded-full bg-orange-100 text-orange-800 font-bold">
                        {records.length} {records.length === 1 ? "Call" : "Calls"} Recorded
                      </span>
                    </div>
                    <div className="text-xs mt-1" style={{ color: "#7A6E65" }}>
                      <span className="font-bold" style={{ color: "#201815" }}>Company Stance:</span> &quot;{latestStance}&quot;
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-[10px] uppercase font-bold" style={{ color: "#7A6E65" }}>Total Net Saved</div>
                    <div className="text-lg font-bold text-emerald-700">+${totalSaved.toLocaleString()}</div>
                  </div>
                </div>

                {/* Records */}
                <div className="space-y-4">
                  {records.map((r, idx) => (
                    <div key={idx} className="p-4 sm:p-5 rounded-2xl border space-y-3" style={{ background: "rgba(250,246,240,0.5)", borderColor: "#F1E9DE" }}>
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center space-x-2">
                          <span className="text-xs font-bold">Session #{idx + 1}</span>
                          <span className="text-[11px]" style={{ color: "#7A6E65" }}>{r.timestamp || "Today"}</span>
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
                            {r.status || "Deal Secured"}
                          </span>
                        </div>
                        <div className="flex items-center space-x-4 text-xs">
                          <div>Initial: <span className="line-through font-medium" style={{ color: "#7A6E65" }}>${r.initial_offer?.toLocaleString()}</span></div>
                          <div className="font-bold">Final: <span className="text-orange-700">${r.final_price?.toLocaleString()}</span></div>
                          <div className="font-bold text-emerald-700">Saved: ${r.savings?.toLocaleString()}</div>
                        </div>
                      </div>

                      {r.evidence_quote && (
                        <div className="p-3 rounded-xl bg-orange-50 border border-orange-200 text-xs text-orange-950 italic flex items-center justify-between">
                          <div>
                            <span className="font-bold uppercase text-[10px] text-orange-800 not-italic">Verbal Agreement Evidence:</span>{" "}
                            &quot;{r.evidence_quote}&quot;
                          </div>
                          <button
                            onClick={() => playSnippet(r.evidence_quote!)}
                            className="ml-3 px-3 py-1 rounded-lg bg-orange-600 hover:bg-orange-700 text-white text-[10px] font-bold flex-shrink-0 transition"
                          >
                            🔊 Play Proof
                          </button>
                        </div>
                      )}

                      {/* Transcript */}
                      {(r.dialogue_history || []).length > 0 && (
                        <div className="pt-2">
                          <div className="text-[11px] font-bold uppercase tracking-wider mb-2" style={{ color: "#7A6E65" }}>Multi-Turn Transcript:</div>
                          <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                            {(r.dialogue_history || []).map((d, di) => (
                              <div
                                key={di}
                                className={`text-xs leading-relaxed p-2 rounded-lg ${d.speaker === "Agent" ? "bg-orange-50/70 border border-orange-200/60" : "bg-white border"}`}
                                style={d.speaker !== "Agent" ? { borderColor: "#F1E9DE" } : {}}
                              >
                                <span className={`font-bold ${d.speaker === "Agent" ? "text-orange-800" : ""}`} style={d.speaker !== "Agent" ? { color: "#201815" } : {}}>{d.speaker}:</span>{" "}
                                <span>&quot;{d.text}&quot;</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </main>
    </div>
  );
}
