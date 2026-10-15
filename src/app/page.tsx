"use client";

import { useEffect, useRef, useState, useCallback } from "react";

const RAW_API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const API_BASE = RAW_API_BASE.replace(/\/+$/, "");

// ── Types ──────────────────────────────────────────────────────────────────
type TurnState = "STANDBY" | "AI_SPEAKING" | "USER_TURN" | "AI_REASONING";

// Browser SpeechRecognition shim (not always in TS lib.dom)
interface ISpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onstart: (() => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
  onresult: ((e: SpeechRecognitionEvent) => void) | null;
  start(): void;
  stop(): void;
}
interface ISpeechRecognitionCtor {
  new(): ISpeechRecognition;
}
interface SpeechRecognitionEvent extends Event {
  resultIndex: number;
  results: SpeechRecognitionResultList;
}

interface TranscriptEntry {
  id: string;
  type: "agent" | "vendor" | "notice" | "whisper";
  text: string;
  act?: string;
  time: string;
  noticeStyle?: "red" | "green" | "amber";
}

interface WsPayload {
  type: string;
  vendor_speech?: string;
  agent_speech?: string;
  counter_price?: number;
  detected_price?: number;
  phase?: string;
  status?: string;
  dialogue_act?: string;
  sentiment?: string;
  round?: number;
  whisper?: string;
}

interface WarVendor {
  vendor_name: string;
  phone: string;
  initial_quote: number;
  final_price: number;
  savings: number;
  savings_pct: number;
  is_winner: boolean;
  perks: string;
  evidence_quote: string;
}

interface EvidenceRecord {
  vendor: string;
  category: string;
  initial_quote: number;
  negotiated_price: number;
  savings: number;
  savings_pct: number;
  status: string;
  perks: string;
  evidence_quote: string;
}

// ── EQ Bars ───────────────────────────────────────────────────────────────
function EqBars() {
  return (
    <div className="flex items-end space-x-1 text-[#ea580c]">
      <span className="eq-bar" />
      <span className="eq-bar" />
      <span className="eq-bar" />
      <span className="eq-bar" />
    </div>
  );
}

// ── Master Turn Banner ────────────────────────────────────────────────────
function TurnBanner({ state, customMsg }: { state: TurnState; customMsg?: string }) {
  const configs: Record<TurnState, { banner: string; iconBox: string; icon: string; title: string; badge: string; badgeText: string; sub: string; showEq: boolean }> = {
    AI_SPEAKING: {
      banner: "w-full mb-6 p-4 rounded-3xl transition-all duration-500 shadow-lg border-2 border-[#f97316] bg-gradient-to-r from-[#fff7ed] via-amber-50 to-orange-50 flex flex-col sm:flex-row items-center justify-between gap-3 ring-4 ring-[#fdba74]/30",
      iconBox: "w-12 h-12 rounded-2xl bg-[#ea580c] text-white flex items-center justify-center flex-shrink-0 shadow-md animate-pulse",
      icon: "🤖", title: "AI Agent is Speaking (Please Listen)",
      badge: "text-[10px] px-2.5 py-0.5 rounded-full bg-[#ea580c] text-white font-bold uppercase tracking-wider animate-pulse",
      badgeText: "AI Speaking",
      sub: customMsg || "The Negotiator is speaking in Jenny Neural Voice. Mic will listen once she completes.",
      showEq: true,
    },
    USER_TURN: {
      banner: "w-full mb-6 p-4 rounded-3xl transition-all duration-500 shadow-xl border-2 border-emerald-500 bg-gradient-to-r from-emerald-50 via-teal-50 to-white flex flex-col sm:flex-row items-center justify-between gap-3 ring-4 ring-emerald-300/40",
      iconBox: "w-12 h-12 rounded-2xl bg-emerald-600 text-white flex items-center justify-center flex-shrink-0 shadow-md animate-bounce",
      icon: "🎙️", title: "YOUR TURN TO SPEAK (Vendor)",
      badge: "text-[10px] px-2.5 py-0.5 rounded-full bg-emerald-600 text-white font-bold uppercase tracking-wider animate-pulse",
      badgeText: "Speak Now",
      sub: "Speak into your microphone now, or click any sample quote chip below!",
      showEq: false,
    },
    AI_REASONING: {
      banner: "w-full mb-6 p-4 rounded-3xl transition-all duration-500 shadow-md border-2 border-amber-400 bg-gradient-to-r from-amber-50 to-yellow-50 flex flex-col sm:flex-row items-center justify-between gap-3",
      iconBox: "w-12 h-12 rounded-2xl bg-amber-500 text-white flex items-center justify-center flex-shrink-0 shadow-md animate-spin",
      icon: "⚡", title: "AI Reasoning (Groq Qwen 27B)",
      badge: "text-[10px] px-2.5 py-0.5 rounded-full bg-amber-500 text-white font-bold uppercase",
      badgeText: "Thinking…",
      sub: "Evaluating vendor offer against company stance and calculating concession step…",
      showEq: false,
    },
    STANDBY: {
      banner: "w-full mb-6 p-4 rounded-3xl transition-all duration-500 shadow-md border glass-card flex flex-col sm:flex-row items-center justify-between gap-3 bg-gradient-to-r from-amber-50/80 via-white/80 to-[#fff7ed]/80 border-amber-200/80",
      iconBox: "w-12 h-12 rounded-2xl bg-[#ffedd5] text-[#9a3412] flex items-center justify-center flex-shrink-0 shadow-sm",
      icon: "📞", title: "Ready to Dial Vendor",
      badge: "text-[10px] px-2 py-0.5 rounded-full bg-[#ffedd5] text-[#9a3412] font-bold uppercase",
      badgeText: "Standby",
      sub: 'Click "📞 Start Live Call" below to connect with the merchant.',
      showEq: false,
    },
  };

  const c = configs[state];
  return (
    <div className={c.banner}>
      <div className="flex items-center space-x-3.5">
        <div className={c.iconBox}>
          <span className="text-2xl">{c.icon}</span>
        </div>
        <div>
          <div className="font-bold text-sm sm:text-base tracking-tight text-[#1C1512] flex items-center space-x-2">
            <span>{c.title}</span>
            <span className={c.badge}>{c.badgeText}</span>
          </div>
          <div className="text-xs text-[#766860] mt-0.5">{c.sub}</div>
        </div>
      </div>
      {c.showEq && (
        <div className="flex items-center space-x-2 text-[#ea580c] bg-[#ffedd5]/70 px-4 py-2 rounded-2xl border border-[#fed7aa]">
          <EqBars />
          <span className="text-xs font-bold tracking-wider uppercase ml-1">AI Speaking</span>
        </div>
      )}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────
export default function HomePage() {
  // ── State ──
  const [turnState, setTurnState] = useState<TurnState>("STANDBY");
  const [isCallActive, setIsCallActive] = useState(false);
  const [callSeconds, setCallSeconds] = useState(0);
  const [merchantName, setMerchantName] = useState("Apex Grand Hotel & Suites");
  const [companyStance, setCompanyStance] = useState("Our company policy limits conference accommodations to $1,500 and requires breakfast vouchers with zero deposit penalty.");
  const [targetCap, setTargetCap] = useState(1500);
  const [batna, setBatna] = useState(1680);
  const [audioEnabled, setAudioEnabled] = useState(true);
  const [handsFree, setHandsFree] = useState(true);
  const [vendorText, setVendorText] = useState("No, $1,950 is my bottom line, take it or leave it.");
  const [whisperText, setWhisperText] = useState("");
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [vendorQuote, setVendorQuote] = useState(1950);
  const [aiCounter, setAiCounter] = useState(1500);
  const [savings, setSavings] = useState({ amount: 450, pct: "23.1" });
  const [liveBadge, setLiveBadge] = useState("Ready to Dial");
  const [phaseBadge, setPhaseBadge] = useState({ text: "🛑 Phase 1: Firm Rejection (Above $1,500 Cap)", cls: "bg-red-50 text-red-900 border-red-300" });
  const [warVendors, setWarVendors] = useState<WarVendor[]>([]);
  const [evidenceRecords, setEvidenceRecords] = useState<EvidenceRecord[]>([]);
  const [isListening, setIsListening] = useState(false);
  const [sttLabel, setSttLabel] = useState("● Ready");
  const [customBannerMsg, setCustomBannerMsg] = useState<string>();

  // ── Refs ──
  const socketRef = useRef<WebSocket | null>(null);
  const recognitionRef = useRef<ISpeechRecognition | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const speechPlayerRef = useRef<HTMLAudioElement | null>(null);
  const callTimerRef = useRef<NodeJS.Timeout | null>(null);
  const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const transcriptEndRef = useRef<HTMLDivElement>(null);
  const lastOfferRef = useRef(1950);
  const initialOfferRef = useRef(1950);
  const roundRef = useRef(1);
  const targetPriceRef = useRef(1500);
  const batnaPriceRef = useRef(1680);
  const activeWhisperRef = useRef("");
  const dialogueHistoryRef = useRef<{ speaker: string; text: string; timestamp: string }[]>([]);
  const lastEvidenceRef = useRef("");
  const isCallActiveRef = useRef(false);
  const handsFreeRef = useRef(true);
  const audioEnabledRef = useRef(true);

  // Keep refs in sync
  useEffect(() => { handsFreeRef.current = handsFree; }, [handsFree]);
  useEffect(() => { audioEnabledRef.current = audioEnabled; }, [audioEnabled]);

  // ── Auto-scroll transcript ──
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcript]);

  // ── Load evidence & war room on mount ──
  useEffect(() => {
    loadEvidenceRecords();
    launchWarRoom();
    connectWebSocket();
    return () => { socketRef.current?.close(); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── AudioContext ──
  function getAudioContext() {
    if (!audioCtxRef.current) {
      const AC = (window as unknown as { AudioContext?: typeof AudioContext; webkitAudioContext?: typeof AudioContext }).AudioContext ||
                 (window as unknown as { AudioContext?: typeof AudioContext; webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (AC) audioCtxRef.current = new AC();
    }
    if (audioCtxRef.current?.state === "suspended") audioCtxRef.current.resume();
    return audioCtxRef.current;
  }

  function playTone(f1: number, f2: number, dur: number) {
    try {
      const ctx = getAudioContext();
      if (!ctx) return;
      const osc1 = ctx.createOscillator();
      const osc2 = ctx.createOscillator();
      const gain = ctx.createGain();
      osc1.frequency.value = f1; osc2.frequency.value = f2;
      gain.gain.setValueAtTime(0.08, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + dur);
      osc1.connect(gain); osc2.connect(gain); gain.connect(ctx.destination);
      osc1.start(); osc2.start();
      osc1.stop(ctx.currentTime + dur); osc2.stop(ctx.currentTime + dur);
    } catch (_) {}
  }

  async function playRingback() {
    const seq = [[697, 1209], [770, 1336], [852, 1477]];
    for (const [f1, f2] of seq) {
      playTone(f1, f2, 0.12);
      await delay(140);
    }
    playTone(440, 480, 1.2);
    await delay(1400);
  }

  function delay(ms: number) { return new Promise<void>(r => setTimeout(r, ms)); }

  // ── WebSocket ──
  function connectWebSocket() {
    try {
      let wsUrl: string;
      if (API_BASE) {
        const isHttps = API_BASE.startsWith("https://");
        const wsProto = isHttps ? "wss:" : "ws:";
        const host = API_BASE.replace(/^https?:\/\//, "");
        wsUrl = `${wsProto}//${host}/ws/call`;
      } else {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        wsUrl = `${protocol}//${window.location.host}/ws/call`;
      }

      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;
      ws.onmessage = (ev) => {
        try {
          const data: WsPayload = JSON.parse(ev.data);
          if (data.type === "turn_update") handleTurnUpdate(data);
          else if (data.type === "whisper_alert") addEntry({ type: "whisper", text: `🤫 Human Whisper: "${data.whisper}"`, time: now() });
        } catch (_) {}
      };
      ws.onclose = () => setTimeout(connectWebSocket, 3000);
    } catch (_) {}
  }

  function now() { return new Date().toLocaleTimeString(); }

  function addEntry(entry: Omit<TranscriptEntry, "id">) {
    setTranscript(prev => [...prev, { ...entry, id: Math.random().toString(36).slice(2) }]);
  }

  // ── Turn Update ──
  const handleTurnUpdate = useCallback(async (data: WsPayload) => {
    const detected = Number(data.detected_price) || lastOfferRef.current;
    const counter = Number(data.counter_price) || targetPriceRef.current;
    lastOfferRef.current = detected;
    roundRef.current = data.round || roundRef.current + 1;

    // Vendor bubble
    if (data.vendor_speech) {
      addEntry({ type: "vendor", text: data.vendor_speech, time: now() });
      dialogueHistoryRef.current.push({ speaker: "Vendor", text: data.vendor_speech, timestamp: now() });
    }

    // Agent bubble
    if (data.agent_speech) {
      addEntry({ type: "agent", text: data.agent_speech, act: data.dialogue_act || "Bargaining", time: now() });
      dialogueHistoryRef.current.push({ speaker: "Agent", text: data.agent_speech, timestamp: now() });
      lastEvidenceRef.current = data.agent_speech;
    }

    // Phase badge
    if (data.phase === "DEAL_FINALIZED" || data.status === "deal_closed") {
      setPhaseBadge({ text: "✅ Phase 3: Deal Locked & Finalized!", cls: "bg-emerald-50 text-emerald-900 border-emerald-300" });
    } else if (data.phase === "ASKING_CONFIRMATION" || data.status === "deal_pending" || detected <= targetPriceRef.current) {
      setPhaseBadge({ text: "🤝 Phase 2: Stance Met — Asking Deal Confirmation", cls: "bg-blue-50 text-blue-900 border-blue-300" });
    } else {
      setPhaseBadge({ text: `🛑 Phase 1: Firm Rejection (Above $${targetPriceRef.current.toLocaleString()} Cap)`, cls: "bg-red-50 text-red-900 border-red-300" });
    }

    // Stats
    setVendorQuote(detected);
    setAiCounter(counter);
    const saved = Math.max(0, detected - counter);
    setSavings({ amount: saved, pct: ((saved / Math.max(1, detected)) * 100).toFixed(1) });
    setLiveBadge(data.sentiment || "Negotiating");

    // TTS
    if (audioEnabledRef.current && data.agent_speech) {
      await playNeuralVoice(data.agent_speech);
    } else {
      setTurnState("USER_TURN");
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── TTS ──
  async function playNeuralVoice(text: string) {
    try {
      setCustomBannerMsg(`Speaking: "${text.substring(0, 70)}…"`);
      setTurnState("AI_SPEAKING");
      const res = await fetch(`${API_BASE}/api/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, voice: "en-US-JennyNeural" }),
      });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      if (!speechPlayerRef.current) {
        speechPlayerRef.current = new Audio();
      }
      speechPlayerRef.current.src = url;
      speechPlayerRef.current.onended = () => {
        setTurnState("USER_TURN");
        if (handsFreeRef.current && isCallActiveRef.current) resumeListening();
      };
      speechPlayerRef.current.play().catch(() => setTurnState("USER_TURN"));
    } catch (_) {
      setTurnState("USER_TURN");
    }
  }

  // ── Start Call ──
  async function startCall() {
    if (isCallActive) return;
    getAudioContext();
    targetPriceRef.current = targetCap;
    batnaPriceRef.current = batna;
    lastOfferRef.current = 1950;
    initialOfferRef.current = 1950;
    roundRef.current = 1;
    dialogueHistoryRef.current = [];
    isCallActiveRef.current = true;
    setIsCallActive(true);
    setCallSeconds(0);
    setTranscript([]);
    setPhaseBadge({ text: `🛑 Phase 1: Firm Rejection (Above $${targetCap.toLocaleString()} Cap)`, cls: "bg-red-50 text-red-900 border-red-300" });
    setTurnState("AI_REASONING");

    clearInterval(callTimerRef.current!);
    callTimerRef.current = setInterval(() => setCallSeconds(s => s + 1), 1000);

    await playRingback();

    const greeting = `Hello! I am calling from Procurement regarding your corporate group rate. ${companyStance}. What is your standard quote?`;
    addEntry({ type: "agent", text: greeting, act: "Opening Inquiry (Company Stance)", time: now() });
    dialogueHistoryRef.current.push({ speaker: "Agent", text: greeting, timestamp: now() });
    await playNeuralVoice(greeting);
  }

  // ── Cut Call ──
  async function cutCall() {
    if (!isCallActive) return;
    isCallActiveRef.current = false;
    setIsCallActive(false);
    clearInterval(callTimerRef.current!);
    speechPlayerRef.current?.pause();
    try { recognitionRef.current?.stop(); } catch (_) {}
    setIsListening(false);
    playTone(425, 425, 0.4);
    setTurnState("STANDBY");
    setPhaseBadge({ text: "📞 Call Disconnected by User", cls: "bg-gray-100 text-gray-800 border-gray-300" });

    const finalSavings = Math.max(0, initialOfferRef.current - lastOfferRef.current);
    await saveRecord({
      merchant_name: merchantName,
      company_stance: companyStance,
      target_price: targetCap,
      initial_offer: initialOfferRef.current,
      final_price: lastOfferRef.current,
      savings: finalSavings,
      status: lastOfferRef.current <= targetCap ? "Deal Secured" : "Call Ended / Archived",
      dialogue_history: dialogueHistoryRef.current,
      evidence_quote: lastEvidenceRef.current || `Call ended at $${lastOfferRef.current.toFixed(2)}`,
    });

    addEntry({
      type: "notice",
      noticeStyle: "red",
      text: `🔴 Call Cut & Saved! Final Offer: $${lastOfferRef.current.toLocaleString()} | Saved: $${finalSavings.toLocaleString()}`,
      time: now(),
    });
  }

  // ── Microphone STT ──
  function toggleMic() {
    const win = window as unknown as { SpeechRecognition?: ISpeechRecognitionCtor; webkitSpeechRecognition?: ISpeechRecognitionCtor };
    const SR: ISpeechRecognitionCtor | undefined = win.SpeechRecognition || win.webkitSpeechRecognition;
    if (!SR) return alert("Speech Recognition not supported in this browser.");

    if (!recognitionRef.current) {
      const rec = new SR();
      rec.continuous = true;
      rec.interimResults = true;
      rec.lang = "en-US";
      rec.onstart = () => { setIsListening(true); setSttLabel("● Listening…"); setTurnState("USER_TURN"); };
      rec.onresult = (e: SpeechRecognitionEvent) => {
        let text = "";
        for (let i = e.resultIndex; i < e.results.length; i++) text += e.results[i][0].transcript;
        if (text.trim()) setVendorText(text);
        if (handsFreeRef.current && text.trim().length > 3) {
          clearTimeout(silenceTimerRef.current!);
          silenceTimerRef.current = setTimeout(() => {
            if (isListening) { try { recognitionRef.current?.stop(); } catch (_) {} sendVendorTurn(text); }
          }, 1200);
        }
      };
      rec.onerror = () => { setIsListening(false); setSttLabel("● Ready"); };
      rec.onend = () => { setIsListening(false); setSttLabel("● Ready"); };
      recognitionRef.current = rec;
    }

    if (isListening) {
      recognitionRef.current.stop();
    } else {
      try { recognitionRef.current.start(); } catch (_) {}
    }
  }

  function resumeListening() {
    if (!isListening && recognitionRef.current) {
      try { recognitionRef.current.start(); } catch (_) {}
    }
  }

  // ── Send Vendor Turn ──
  function sendVendorTurn(overrideText?: string) {
    const text = overrideText ?? vendorText;
    if (!text.trim()) return;
    setTurnState("AI_REASONING");

    const payload = {
      type: "vendor_speech",
      merchant_name: merchantName,
      company_stance: companyStance,
      text,
      target_price: targetPriceRef.current,
      last_offer: lastOfferRef.current,
      batna_price: batnaPriceRef.current,
      whisper: activeWhisperRef.current,
      round: roundRef.current,
    };

    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(payload));
      activeWhisperRef.current = "";
    } else {
      fetch(`${API_BASE}/api/roleplay`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_speech: text,
          target_price: targetPriceRef.current,
          last_offer: lastOfferRef.current,
          batna_price: batnaPriceRef.current,
          whisper_instruction: activeWhisperRef.current,
          company_stance: companyStance,
          round: roundRef.current,
        }),
      })
        .then(r => r.json())
        .then(data => handleTurnUpdate({ type: "turn_update", ...data, vendor_speech: text }))
        .catch(() => setTurnState("USER_TURN"));
      activeWhisperRef.current = "";
    }
  }

  function setSample(quote: string) {
    setVendorText(quote);
    setTimeout(() => sendVendorTurn(quote), 50);
  }

  // ── Whisper ──
  function sendWhisper() {
    if (!whisperText.trim()) return;
    activeWhisperRef.current = whisperText;
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: "whisper", whisper: whisperText }));
    }
    addEntry({ type: "whisper", text: `🤫 Whisper Injected: "${whisperText}"`, time: now() });
    setWhisperText("");
  }

  // ── Save Record ──
  async function saveRecord(record: object) {
    try {
      await fetch(`${API_BASE}/api/records/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(record),
      });
    } catch (_) {}
  }

  // ── War Room ──
  async function launchWarRoom() {
    setWarVendors([]);
    try {
      const res = await fetch(`${API_BASE}/api/war-room`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category: "Logistics & Supplies", target_budget: 1500 }),
      });
      const data: WarVendor[] = await res.json();
      setWarVendors(data);
    } catch (_) {}
  }

  // ── Evidence Records ──
  async function loadEvidenceRecords() {
    try {
      const res = await fetch(`${API_BASE}/api/records`);
      const data: EvidenceRecord[] = await res.json();
      setEvidenceRecords(data);
    } catch (_) {}
  }

  async function playProof(text: string) {
    try {
      const res = await fetch(`${API_BASE}/api/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, voice: "en-US-JennyNeural" }),
      });
      const blob = await res.blob();
      if (!speechPlayerRef.current) speechPlayerRef.current = new Audio();
      speechPlayerRef.current.src = URL.createObjectURL(blob);
      speechPlayerRef.current.play().catch(() => {});
    } catch (_) {}
  }

  // ── Helpers ──
  const fmtTimer = (s: number) =>
    `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

  const micBtnClass = isListening
    ? "w-24 h-24 sm:w-28 sm:h-28 rounded-full bg-gradient-to-tr from-emerald-600 to-teal-500 text-white flex flex-col items-center justify-center shadow-xl shadow-emerald-600/40 transition transform active:scale-95 focus:outline-none pulse-ring-green cursor-pointer"
    : turnState === "AI_SPEAKING"
      ? "w-24 h-24 sm:w-28 sm:h-28 rounded-full bg-gradient-to-tr from-[#c2410c] to-amber-600 text-white flex flex-col items-center justify-center shadow-md transition opacity-80"
      : "w-24 h-24 sm:w-28 sm:h-28 rounded-full bg-gradient-to-tr from-amber-600 via-[#ea580c] to-[#f97316] text-white flex flex-col items-center justify-center shadow-xl shadow-[#ea580c]/35 transition transform active:scale-95 focus:outline-none pulse-ring";

  // ── JSX ──────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen crystal-glow font-sans antialiased pb-28 md:pb-16 selection:bg-[#fed7aa]">

      {/* ── HEADER ── */}
      <header className="sticky top-0 z-40 bg-[#FAF4EE]/85 backdrop-blur-md border-b border-white/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <a href="/" className="w-9 h-9 sm:w-10 sm:h-10 rounded-2xl bg-gradient-to-tr from-[#ea580c] to-amber-500 flex items-center justify-center shadow-md shadow-[#f97316]/25 text-white flex-shrink-0">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 100-6 3 3 0 000 6z"/>
              </svg>
            </a>
            <div>
              <span className="font-bold text-lg sm:text-xl tracking-tight text-[#1C1512]">VoiceAgent</span>
              <span className="ml-1 text-[11px] px-2.5 py-0.5 rounded-full bg-[#ffedd5]/80 text-[#9a3412] border border-[#fed7aa]/60 font-semibold">The Negotiator</span>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <a href="/history" className="text-xs sm:text-sm font-semibold px-4 py-2 rounded-full glass-inner hover:bg-white text-[#9a3412] shadow-sm transition flex items-center space-x-1.5 border border-white/80">
              <span>📂 Merchant Vault</span>
            </a>
            <button onClick={() => document.getElementById("call-studio")?.scrollIntoView({ behavior: "smooth" })} className="px-4 sm:px-5 py-2 sm:py-2.5 rounded-full bg-[#ea580c] hover:bg-[#c2410c] text-white font-medium text-xs sm:text-sm shadow-md shadow-[#ea580c]/20 transition active:scale-95 flex items-center space-x-1.5">
              <span>📞 Live Call Studio</span>
            </button>
          </div>
        </div>
      </header>

      {/* ── MAIN CONTENT ── */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 pt-6 sm:pt-10 space-y-16 sm:space-y-24">

        {/* ── HERO ── */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-center">
          <div className="lg:col-span-7 space-y-4 sm:space-y-6">
            <div className="inline-flex items-center space-x-2 text-[11px] sm:text-xs uppercase tracking-widest font-semibold text-[#9a3412] px-3 py-1 rounded-full bg-[#ffedd5]/70 border border-[#fed7aa]/50">
              <span>EACL 2024 Negotiation Framework • Powered by Groq Qwen 27B</span>
            </div>
            <h1 className="font-serif text-4xl sm:text-5xl lg:text-6xl text-[#1C1512] leading-[1.12] tracking-tight">
              AI Voice Agents That <br />
              <span className="italic font-normal">Sound Human</span> &{" "}
              <span className="text-[#ea580c]">Solve Real Problems</span>
            </h1>
            <p className="text-[#766860] text-base sm:text-lg max-w-xl font-normal leading-relaxed">
              Handle calls, negotiate merchant quotes, and demonstrate verified ROI with natural, intelligent conversations and phased bargaining in Jenny female neural voice.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 pt-2">
              <button onClick={() => document.getElementById("call-studio")?.scrollIntoView({ behavior: "smooth" })} className="w-full sm:w-auto px-7 py-3.5 rounded-full bg-[#ea580c] hover:bg-[#c2410c] text-white font-semibold text-sm shadow-xl shadow-[#ea580c]/25 transition flex items-center justify-center space-x-2">
                <span>Book a Demo / Live Call</span>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
              </button>
              <button onClick={() => document.getElementById("war-room")?.scrollIntoView({ behavior: "smooth" })} className="w-full sm:w-auto px-6 py-3.5 rounded-full glass-card hover:bg-white text-[#1C1512] font-medium text-sm transition flex items-center justify-center space-x-2">
                <span>3-Vendor War Room</span>
              </button>
            </div>
            {/* Metrics */}
            <div className="pt-4 grid grid-cols-3 gap-3 sm:gap-6 border-t border-[#fed7aa]/50">
              {[["24.2%", "Avg. Won Discount"], ["ZOPA & BATNA", "EACL 2024 Logic"], ["< 320ms", "Spoken Cadence"]].map(([val, label]) => (
                <div key={label}>
                  <div className="text-xl sm:text-2xl font-bold text-[#1C1512]">{val}</div>
                  <div className="text-[11px] sm:text-xs text-[#766860] font-medium">{label}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Hero Image */}
          <div className="lg:col-span-5 flex flex-col items-center justify-center relative py-4">
            <a href="#call-studio" className="group block relative cursor-pointer transform hover:scale-[1.02] transition duration-300 w-full max-w-md">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/static/hero-wave.png" alt="AI Voice Agents Acoustic Resonance" className="w-full rounded-3xl shadow-2xl border border-white/80 object-cover" />
              <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent rounded-3xl opacity-0 group-hover:opacity-100 transition flex items-end justify-center p-5">
                <span className="text-white text-xs font-bold bg-[#ea580c] px-5 py-2.5 rounded-full shadow-lg flex items-center space-x-2">
                  <span>🎙️ Start Live Voice Call</span>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
                </span>
              </div>
            </a>
            <div className="mt-3 text-xs font-semibold text-[#766860] text-center">Click waveform to launch live demo • Jenny Female Neural Voice</div>
          </div>
        </div>

        {/* ── LIVE CALL STUDIO ── */}
        <section id="call-studio" className="pt-4 scroll-mt-20">
          {/* Studio Header */}
          <div className="flex flex-col sm:flex-row sm:items-end justify-between mb-4 gap-2">
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#9a3412] bg-[#ffedd5]/70 border border-[#fed7aa]/50 px-3 py-1 rounded-full">Interactive Pitch Studio</span>
              <h2 className="font-serif text-2xl sm:text-3xl text-[#1C1512] mt-2 font-bold">The Negotiator • Dual-Device Live Studio</h2>
              <p className="text-[#766860] text-xs sm:text-sm mt-0.5">Enforces company policy: Rejects offers above cap till matched, then explicitly asks to finalize!</p>
            </div>
            <span className={`inline-flex items-center space-x-1.5 text-xs font-bold px-3.5 py-1.5 rounded-full border shadow-sm ${phaseBadge.cls}`}>
              <span>{phaseBadge.text}</span>
            </span>
          </div>

          {/* Turn Banner */}
          <TurnBanner state={turnState} customMsg={customBannerMsg} />

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 sm:gap-8 items-start">

            {/* ── LEFT: DEVICE 1 PHONE HANDSET ── */}
            <div className="lg:col-span-5 glass-card rounded-3xl p-6 sm:p-8 flex flex-col items-center text-center space-y-4">
              <div className="w-full text-center">
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#9a3412] bg-[#ffedd5]/70 border border-[#fed7aa]/50 px-3 py-1 rounded-full">DEVICE 1: PHONE HANDSET</span>
                <h3 className="font-serif text-2xl sm:text-3xl text-[#1C1512] mt-2 font-bold">Talk as the Vendor</h3>
                <p className="text-xs text-[#766860] mt-1 max-w-sm mx-auto">Speak into phone or test preset quotes. AI rejects above cap till stance is met.</p>
              </div>

              {/* Inputs */}
              <div className="w-full text-left space-y-2.5 p-3.5 rounded-2xl glass-inner">
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-wider text-[#766860] mb-1">🏢 Target Merchant / Business Name</label>
                  <input type="text" value={merchantName} onChange={e => setMerchantName(e.target.value)} className="w-full p-2.5 rounded-xl border border-white/90 text-xs font-bold bg-white/90 focus:outline-none focus:ring-1 focus:ring-[#f97316]" placeholder="e.g. Apex Grand Hotel" />
                </div>
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-wider text-[#766860] mb-1">🛡️ Company Policy / Procurement Stance</label>
                  <input type="text" value={companyStance} onChange={e => setCompanyStance(e.target.value)} className="w-full p-2.5 rounded-xl border border-white/90 text-xs font-medium bg-white/90 focus:outline-none focus:ring-1 focus:ring-[#f97316]" placeholder="State what the company mandates..." />
                </div>
                <div className="grid grid-cols-2 gap-2 pt-1">
                  <div>
                    <label className="block text-[10px] font-bold uppercase tracking-wider text-[#766860] mb-1">Target Cap ($)</label>
                    <input type="number" value={targetCap} onChange={e => setTargetCap(Number(e.target.value))} className="w-full p-2 rounded-xl border border-white/90 text-xs font-bold bg-white/90" />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold uppercase tracking-wider text-[#766860] mb-1">BATNA Benchmark ($)</label>
                    <input type="number" value={batna} onChange={e => setBatna(Number(e.target.value))} className="w-full p-2 rounded-xl border border-white/90 text-xs font-bold bg-white/90" />
                  </div>
                </div>
              </div>

              {/* Call Controls */}
              <div className="w-full grid grid-cols-2 gap-2 pt-1">
                <button onClick={startCall} className="py-3 px-3 rounded-2xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-lg shadow-emerald-600/30 transition transform active:scale-95 flex items-center justify-center space-x-1.5">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"/></svg>
                  <span>📞 Start Live Call</span>
                </button>
                <button onClick={cutCall} className="py-3 px-3 rounded-2xl bg-red-600 hover:bg-red-700 text-white font-bold text-xs shadow-lg shadow-red-600/30 transition transform active:scale-95 flex items-center justify-center space-x-1.5">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.2} d="M16 8l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2M5 3a2 2 0 00-2 2v1c0 8.284 6.716 15 15 15h1a2 2 0 002-2v-3.28a1 1 0 00-.684-.948l-4.493-1.498a1 1 0 00-1.21.502l-1.13 2.257a11.042 11.042 0 01-5.516-5.517l2.257-1.128a1 1 0 00.502-1.21L9.228 3.683A1 1 0 008.28 3H5z"/></svg>
                  <span>🔴 Cut / End Call</span>
                </button>
              </div>

              {isCallActive && (
                <div className="text-xs font-mono font-bold text-emerald-800 bg-emerald-50 py-1.5 px-4 rounded-full border border-emerald-200">
                  In Call: {fmtTimer(callSeconds)} • Jenny Neural Voice
                </div>
              )}

              {/* Hands-Free Toggle */}
              <div className="w-full p-2.5 rounded-2xl bg-amber-50/70 border border-amber-200/70 flex items-center justify-between text-left">
                <div>
                  <div className="text-[11px] font-bold text-amber-900 flex items-center space-x-1">
                    <span className="w-2 h-2 rounded-full bg-amber-500 animate-ping" />
                    <span>Hands-Free Auto-Call Mode</span>
                  </div>
                  <div className="text-[9px] text-amber-800/90">Auto-detects silence ➔ Replies automatically!</div>
                </div>
                <label className="relative inline-flex items-center cursor-pointer ml-2">
                  <input type="checkbox" checked={handsFree} onChange={e => setHandsFree(e.target.checked)} className="sr-only peer" />
                  <div className="w-10 h-5 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-[#ea580c]" />
                </label>
              </div>

              {/* Mic Button */}
              <div className="pt-1">
                <button onClick={toggleMic} className={micBtnClass}>
                  <svg className="w-8 h-8 mb-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 100-6 3 3 0 000 6z"/>
                  </svg>
                  <span className="text-[9px] font-bold uppercase tracking-wider">
                    {isListening ? "🎙️ YOUR TURN" : turnState === "AI_SPEAKING" ? "AI SPEAKING…" : "Vendor Mic"}
                  </span>
                </button>
              </div>

              {/* Speech Input & Presets */}
              <div className="w-full glass-inner rounded-2xl p-4 text-left space-y-2.5">
                <div className="flex items-center justify-between text-[11px] font-bold text-[#766860] uppercase tracking-wider">
                  <span>WHAT YOU SPEAK (VENDOR):</span>
                  <span className="text-[#c2410c] font-bold">{sttLabel}</span>
                </div>
                <textarea rows={2} value={vendorText} onChange={e => setVendorText(e.target.value)} className="w-full bg-white/90 p-3 rounded-xl border border-white/90 text-xs font-medium focus:outline-none focus:ring-1 focus:ring-[#f97316] shadow-inner" placeholder="Your speech will appear here automatically..." />

                {/* Phase Chips */}
                <div className="space-y-1">
                  <div className="text-[10px] font-bold text-[#766860] uppercase tracking-wider">Test Negotiation Phases:</div>
                  <div className="grid grid-cols-2 gap-1.5">
                    {[
                      ["No, $1,950 is our bottom line, take it or leave it.", "1. Rejection:", '"$1,950 bottom line"', "bg-red-50 hover:bg-red-100 border-red-200 text-red-900"],
                      ["If you pay today, I can drop to $1,700.", "2. Bargain:", '"Drop to $1,700"', "bg-amber-50 hover:bg-amber-100 border-amber-200 text-amber-900"],
                      ["Alright, we can match your $1,500 budget with breakfast vouchers.", "3. Match Stance:", '"Match $1,500"', "bg-blue-50 hover:bg-blue-100 border-blue-200 text-blue-900"],
                      ["Yes, we have a confirmed deal at $1,500. Send the contract!", "4. Finalize:", '"Yes, confirmed deal!"', "bg-emerald-50 hover:bg-emerald-100 border-emerald-200 text-emerald-900"],
                    ].map(([quote, label, sub, cls]) => (
                      <button key={label} onClick={() => setSample(quote)} className={`text-[10px] p-1.5 rounded-xl border font-medium text-left transition ${cls}`}>
                        <span className="font-bold">{label}</span> {sub}
                      </button>
                    ))}
                  </div>
                </div>

                <button onClick={() => sendVendorTurn()} className="w-full py-3 px-4 rounded-2xl bg-[#832f17] hover:bg-[#722712] text-white font-bold text-xs sm:text-sm shadow-md transition transform active:scale-98 flex items-center justify-center space-x-2">
                  <span>Send Spoken Turn (Manual)</span>
                  <span className="text-sm">➔</span>
                </button>
              </div>

              {/* Audio Toggle */}
              <div className="w-full pt-1 flex items-center justify-between text-xs text-[#766860]">
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input type="checkbox" checked={audioEnabled} onChange={e => setAudioEnabled(e.target.checked)} className="w-4 h-4 rounded accent-[#ea580c]" />
                  <span className="text-[11px] font-medium">Play AI Voice on this device</span>
                </label>
                <span className="text-[10px] font-semibold text-[#9a3412]">Groq Qwen 27B + Jenny TTS</span>
              </div>
            </div>

            {/* ── RIGHT: DEVICE 2 LIVE TERMINAL ── */}
            <div className="lg:col-span-7 glass-card rounded-3xl p-5 sm:p-7 flex flex-col h-[700px]">
              <div className="flex items-center justify-between pb-3.5 border-b border-[#fed7aa]/40">
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#9a3412] bg-[#ffedd5]/70 border border-[#fed7aa]/50 px-3 py-1 rounded-full">DEVICE 2: LIVE CALL TERMINAL</span>
                  <h3 className="font-serif text-xl sm:text-2xl font-bold text-[#1C1512] mt-1.5">Real-Time Call Transcript</h3>
                </div>
                <div className="text-right">
                  <div className="text-xs font-bold text-emerald-700">{liveBadge}</div>
                  <div className="text-[10px] text-[#766860] font-mono">Target Cap: ${targetCap.toLocaleString()}</div>
                </div>
              </div>

              {/* Stats Row */}
              <div className="grid grid-cols-3 gap-2 my-3.5 p-3 rounded-2xl glass-inner text-center text-xs">
                {[
                  ["VENDOR QUOTE", `$${vendorQuote.toLocaleString()}`, "text-[#766860]", "text-[#1C1512]"],
                  ["AI COUNTER", `$${aiCounter.toLocaleString()}`, "text-[#9a3412]", "text-[#9a3412]"],
                  ["NET SAVED", `$${savings.amount.toLocaleString()} (${savings.pct}%)`, "text-emerald-700", "text-emerald-700"],
                ].map(([label, val, labelCls, valCls]) => (
                  <div key={label}>
                    <div className={`text-[10px] uppercase font-bold tracking-wider ${labelCls}`}>{label}</div>
                    <div className={`font-bold text-sm sm:text-base mt-0.5 ${valCls}`}>{val}</div>
                  </div>
                ))}
              </div>

              {/* Transcript Feed */}
              <div className="flex-1 overflow-y-auto space-y-3 p-3.5 rounded-2xl glass-inner">
                {transcript.length === 0 ? (
                  <div className="text-center py-20 text-[#766860] text-xs">
                    Click <span className="font-bold text-emerald-700">{"📞 Start Live Call"}</span> to begin dialing and hear the phased negotiation!
                  </div>
                ) : (
                  transcript.map(entry => {
                    if (entry.type === "agent") return (
                      <div key={entry.id} className="flex flex-col items-start mr-8 mt-2">
                        <div className="flex items-center space-x-2 text-[10px] text-[#766860] mb-1 font-semibold">
                          <span>🤖 The Negotiator (Jenny Voice)</span>
                          <span>{entry.time}</span>
                          <span className="text-[9px] px-2 py-0.5 rounded-full bg-[#ffedd5] text-[#9a3412] font-bold">{entry.act}</span>
                        </div>
                        <div className="p-3.5 rounded-2xl rounded-tl-sm bg-[#fff7ed]/85 border border-[#fed7aa]/70 text-xs text-[--color-brand-950] leading-relaxed shadow-sm">
                          &quot;{entry.text}&quot;
                        </div>
                      </div>
                    );
                    if (entry.type === "vendor") return (
                      <div key={entry.id} className="flex flex-col items-end ml-8">
                        <div className="flex items-center space-x-2 text-[10px] text-[#766860] mb-1 font-semibold">
                          <span>{entry.time}</span>
                          <span>👤 Vendor (Phone)</span>
                        </div>
                        <div className="p-3.5 rounded-2xl rounded-tr-sm bg-white/95 border border-[#F1E8DF] text-xs text-[#1C1512] leading-relaxed shadow-sm">
                          &quot;{entry.text}&quot;
                        </div>
                      </div>
                    );
                    if (entry.type === "notice") {
                      const nc = entry.noticeStyle === "red" ? "bg-red-50 border-red-300 text-red-950" : entry.noticeStyle === "green" ? "bg-emerald-50 border-emerald-300 text-emerald-950" : "bg-amber-50 border-amber-300 text-amber-950";
                      return (
                        <div key={entry.id} className={`p-3.5 rounded-2xl border text-xs font-medium my-3 space-y-1 shadow-sm ${nc}`}>
                          {entry.text}{" "}
                          <a href="/history" className="underline font-bold hover:opacity-80">👉 View in Merchant Vault</a>
                        </div>
                      );
                    }
                    return (
                      <div key={entry.id} className="p-2 rounded-xl bg-amber-50 border border-amber-300 text-[11px] font-semibold text-amber-900 text-center my-2">
                        {entry.text}
                      </div>
                    );
                  })
                )}
                <div ref={transcriptEndRef} />
              </div>

              {/* Whisper Bar */}
              <div className="pt-3 border-t border-[#fed7aa]/40 mt-3">
                <label className="block text-[10px] font-bold uppercase tracking-wider text-[#9a3412] mb-1.5">
                  🤫 HUMAN WHISPER BAR (INJECT TIPS TO AGENT MID-CALL)
                </label>
                <div className="flex gap-2">
                  <input type="text" value={whisperText} onChange={e => setWhisperText(e.target.value)} onKeyDown={e => e.key === "Enter" && sendWhisper()} className="flex-1 p-2.5 rounded-xl border border-white/90 bg-white/90 text-xs focus:outline-none focus:ring-1 focus:ring-[#f97316] shadow-inner" placeholder="Type private advice (e.g. 'Demand free parking before agreeing')..." />
                  <button onClick={sendWhisper} className="px-5 py-2.5 rounded-xl bg-[#ea580c] hover:bg-[#c2410c] text-white text-xs font-semibold shadow-sm transition">Whisper</button>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ── EACL STRATEGY ── */}
        <section id="strategy" className="pt-4 scroll-mt-20">
          <div className="mb-6">
            <span className="text-[10px] font-bold uppercase tracking-wider text-[#9a3412] bg-[#ffedd5]/70 border border-[#fed7aa]/50 px-3 py-1 rounded-full">Academic Foundation</span>
            <h2 className="font-serif text-2xl sm:text-3xl text-[#1C1512] mt-2 font-bold">EACL 2024 Negotiation Framework</h2>
            <p className="text-[#766860] text-xs sm:text-sm mt-0.5">Based on <span className="font-semibold text-[#1C1512]">&quot;Let&apos;s Negotiate! A Survey of Negotiation Dialogue Systems&quot;</span> (EACL 2024).</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6">
            {[
              { num: "01", sub: "ZOPA Estimation", title: "Zone of Possible Agreement", desc: "The agent dynamically calculates the overlap between your maximum budget and the vendor's reservation cost, preventing premature concessions.", badge: "Estimated ZOPA: $1,500 ⇄ $1,720", badgeCls: "text-emerald-800 bg-emerald-50/80 border-emerald-200" },
              { num: "02", sub: "BATNA Benchmarking", title: "Best Alternative Fallback", desc: "When a vendor resists concessions, the agent cites verified quotes from rival vendors as objective leverage without hostile threats.", badge: "Active BATNA Anchor: $1,680 (Metro Logistics)", badgeCls: "text-[#9a3412] bg-[#fff7ed]/80 border-[#fed7aa]" },
              { num: "03", sub: "Dialogue Acts", title: "Taxonomy of Concessions", desc: "Classifies every phrase into Anchor, Concession, Inquiry, Information Disclosure, and Package Bargaining.", badge: "Strategy: Tit-for-Tat Concession Curve", badgeCls: "text-[#1C1512] bg-white/70 border-[#F1E8DF]" },
            ].map(card => (
              <div key={card.num} className="glass-card p-6 rounded-3xl space-y-2.5">
                <div className="text-[11px] font-bold uppercase text-[#c2410c]">{card.num}. {card.sub}</div>
                <h3 className="font-serif font-bold text-lg text-[#1C1512]">{card.title}</h3>
                <p className="text-xs text-[#766860] leading-relaxed">{card.desc}</p>
                <div className={`text-[11px] font-semibold p-2.5 rounded-xl border ${card.badgeCls}`}>{card.badge}</div>
              </div>
            ))}
          </div>
        </section>

        {/* ── WAR ROOM ── */}
        <section id="war-room" className="pt-4 scroll-mt-20">
          <div className="flex flex-col sm:flex-row sm:items-end justify-between mb-6 gap-3">
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#9a3412] bg-[#ffedd5]/70 border border-[#fed7aa]/50 px-3 py-1 rounded-full">Autonomous Parallel Calling</span>
              <h2 className="font-serif text-2xl sm:text-3xl text-[#1C1512] mt-2 font-bold">Autonomous 3-Vendor War Room</h2>
              <p className="text-[#766860] text-xs sm:text-sm mt-0.5">Calls 3 vendors simultaneously, applies cross-quote leverage, and secures the best deal.</p>
            </div>
            <button onClick={launchWarRoom} className="w-full sm:w-auto px-6 py-3 rounded-full bg-[#ea580c] hover:bg-[#c2410c] text-white font-semibold text-xs sm:text-sm shadow-md transition flex items-center justify-center space-x-2">
              <span>🚀 Run 3-Vendor Negotiation</span>
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6">
            {warVendors.length === 0 ? (
              <div className="col-span-3 text-center py-8 text-[#766860] text-sm animate-pulse">Dialing 3 competing vendors simultaneously…</div>
            ) : warVendors.map((v, idx) => (
              <div key={v.vendor_name} className={`p-6 rounded-3xl border transition ${v.is_winner ? "bg-amber-50/80 border-amber-300 ring-2 ring-amber-400/40 shadow-xl" : "glass-card"}`}>
                <div className="flex items-center justify-between mb-3">
                  <span className={`text-[11px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full ${v.is_winner ? "text-amber-800 bg-amber-100" : "text-[#766860] bg-white/70"}`}>
                    {v.is_winner ? "🏆 Recommended (Best ZOPA)" : `Bidder #${idx + 1}`}
                  </span>
                  <span className="text-xs font-semibold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                    Saved ${v.savings.toLocaleString()} ({v.savings_pct}%)
                  </span>
                </div>
                <h3 className="font-bold text-base sm:text-lg text-[#1C1512]">{v.vendor_name}</h3>
                <div className="text-xs text-[#766860] mb-3">{v.phone}</div>
                <div className="grid grid-cols-2 gap-2 mb-3 p-3 rounded-2xl glass-inner text-center">
                  <div>
                    <div className="text-[10px] uppercase font-bold text-[#766860]">Initial Quote</div>
                    <div className="text-xs sm:text-sm font-semibold text-[#766860] line-through">${v.initial_quote.toLocaleString()}</div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase font-bold text-[#c2410c]">Final Agreed</div>
                    <div className="text-sm sm:text-base font-bold text-[#1C1512]">${v.final_price.toLocaleString()}</div>
                  </div>
                </div>
                <div className="text-xs text-[#766860] mb-4">
                  <span className="font-semibold text-[#1C1512]">Perks Won:</span> {v.perks}
                </div>
                <button onClick={() => playProof(v.evidence_quote)} className="w-full py-2.5 rounded-xl bg-white/80 hover:bg-[#ea580c] hover:text-white border border-[#F1E8DF] text-xs font-semibold transition flex items-center justify-center space-x-1.5 shadow-sm">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/></svg>
                  <span>Play Audio Proof (Jenny Voice)</span>
                </button>
              </div>
            ))}
          </div>
        </section>

        {/* ── EVIDENCE LOCKER ── */}
        <section id="evidence" className="pt-4 scroll-mt-20">
          <div className="flex flex-col sm:flex-row sm:items-end justify-between mb-6 gap-3">
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#9a3412] bg-[#ffedd5]/70 border border-[#fed7aa]/50 px-3 py-1 rounded-full">Verifiable Proof</span>
              <h2 className="font-serif text-2xl sm:text-3xl text-[#1C1512] mt-2 font-bold">Evidence-Backed Call Records</h2>
              <p className="text-[#766860] text-xs sm:text-sm mt-0.5">Every verbal discount is backed by exact timestamped transcripts and verifiable verbal audio signatures.</p>
            </div>
            <button onClick={() => window.print()} className="w-full sm:w-auto px-5 py-2.5 rounded-full glass-card hover:bg-white text-[#1C1512] text-xs font-semibold shadow-sm transition flex items-center justify-center space-x-1.5">
              <svg className="w-4 h-4 text-[#766860]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/></svg>
              <span>Print Executive Deal Memo</span>
            </button>
          </div>
          <div className="glass-card rounded-3xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse min-w-[620px]">
                <thead>
                  <tr className="border-b border-[#fed7aa]/50 bg-white/40 text-[11px] font-bold uppercase tracking-wider text-[#766860]">
                    {["Vendor / Business", "Initial Quote", "Negotiated Price", "Net Savings", "Perks", "Verifiable Audio Proof"].map((h, i) => (
                      <th key={h} className={`py-4 px-5 ${i === 5 ? "text-right" : ""}`}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#fed7aa]/30 text-xs sm:text-sm">
                  {evidenceRecords.length === 0 ? (
                    <tr><td colSpan={6} className="py-10 px-5 text-center text-[#766860] text-xs">Start a call to generate evidence records…</td></tr>
                  ) : evidenceRecords.map((r, i) => (
                    <tr key={i} className="hover:bg-white/40 transition">
                      <td className="py-4 px-5">
                        <div className="font-semibold text-[#1C1512]">{r.vendor}</div>
                        <div className="text-xs text-[#766860]">{r.category}</div>
                      </td>
                      <td className="py-4 px-5 font-medium text-[#766860] line-through">${r.initial_quote.toLocaleString()}</td>
                      <td className="py-4 px-5 font-bold text-[#1C1512]">${r.negotiated_price.toLocaleString()}</td>
                      <td className="py-4 px-5">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold text-emerald-800 bg-emerald-50 border border-emerald-200">
                          -${r.savings.toLocaleString()} ({r.savings_pct}%)
                        </span>
                      </td>
                      <td className="py-4 px-5">
                        <div className="text-xs font-semibold text-[#1C1512]">{r.status}</div>
                        <div className="text-[11px] text-[#766860]">{r.perks}</div>
                      </td>
                      <td className="py-4 px-5 text-right">
                        <button onClick={() => playProof(r.evidence_quote)} className="px-3.5 py-1.5 rounded-xl glass-inner hover:bg-[#ea580c] hover:text-white border border-[#F1E8DF] text-xs font-semibold transition flex items-center space-x-1 ml-auto shadow-sm">
                          <span>Proof (Jenny)</span>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </main>

      {/* ── FOOTER ── */}
      <footer className="max-w-7xl mx-auto px-4 sm:px-6 py-8 border-t border-[#fed7aa]/40 text-center text-xs text-[#766860] mt-16">
        <p>VoiceAgent — The Negotiator • All Spoken in Jenny Female Neural Voice • Powered by Groq Qwen 27B &amp; MongoDB</p>
      </footer>
    </div>
  );
}
