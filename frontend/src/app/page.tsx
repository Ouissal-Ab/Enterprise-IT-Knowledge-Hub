"use client";

import { useState, useRef, useEffect } from "react";

const API_URL = "http://localhost:8000";

const C = {
  darkest: "#022c22",
  dark: "#064e3b",
  primary: "#15803d",
  teal: "#0f766e",
  tealLight: "#ccfbf1",
  greenLight: "#dcfce7",
  text: "#0f172a",
  muted: "#64748b",
  border: "#e2e8f0",
  bg: "#f1f5f4",
  white: "#ffffff",
  error: "#b91c1c",
};

const FONT = "'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif";

type Source = { document: string; page: number };
type Message = { role: "user" | "assistant"; text: string; sources?: Source[] };

const SUGGESTIONS = [
  "Quelle est la durée maximale d'une session VPN ?",
  "Quelle est la durée de validité de mon mot de passe Windows ?",
  "Que signifie le code d'erreur -14 du VPN ?",
  "Le VPN est-il obligatoire pour accéder à Outlook et Teams ?",
  "Puis-je utiliser le VPN sur mon ordinateur personnel ?",
];

// Styles partagés : animation d'apparition et effet de survol des boutons
function Styles() {
  return (
    <style>{`
      @keyframes fadeUp {
        from { opacity: 0; transform: translateY(12px); }
        to   { opacity: 1; transform: translateY(0); }
      }
      .fade-up { animation: fadeUp 0.5s ease-out both; }
      .btn {
        transition: transform 0.15s ease, filter 0.15s ease, box-shadow 0.15s ease;
      }
      .btn:hover {
        filter: brightness(1.1);
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(21,128,61,0.35);
      }
    `}</style>
  );
}

function Bubble({ m }: { m: Message }) {
  const isUser = m.role === "user";
  return (
    <div className="fade-up" style={{ display: "flex", justifyContent: isUser ? "flex-end" : "flex-start" }}>
      <div style={{ maxWidth: "75%", display: "flex", flexDirection: "column", gap: 8 }}>
        <div
          style={{
            background: isUser ? `linear-gradient(135deg, ${C.primary}, ${C.teal})` : C.white,
            color: isUser ? "#fff" : C.text,
            border: isUser ? "none" : `1px solid ${C.border}`,
            borderRadius: 14,
            padding: "12px 16px",
            lineHeight: 1.6,
            fontSize: 15,
            boxShadow: "0 1px 3px rgba(15,23,42,0.06)",
          }}
        >
          {m.text}
        </div>
        {m.sources && m.sources.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {m.sources.map((s, i) => (
              <span
                key={i}
                style={{
                  background: C.tealLight,
                  color: C.teal,
                  borderRadius: 999,
                  padding: "4px 10px",
                  fontSize: 12,
                  fontWeight: 600,
                }}
              >
                {s.document} · page {s.page}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function Home() {
 
  const [token, setToken] = useState("");
  const [role, setRole] = useState("");
  const [userName, setUserName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);

  // Chat
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  
  useEffect(() => {
    try {
      const saved = localStorage.getItem("token");
      if (saved) {
        setToken(saved);
        setRole(localStorage.getItem("role") ?? "");
        setUserName(localStorage.getItem("userName") ?? "");
      }
    } catch {
     
    }
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function login(e: React.FormEvent) {
    e.preventDefault();
    setLoginError("");
    setLoginLoading(true);
    try {
      const res = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ username: email, password }),
      });
      if (!res.ok) throw new Error("Email ou mot de passe incorrect");
      const data = await res.json();

      
      let name = "";
      const meRes = await fetch(`${API_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${data.access_token}` },
      });
      if (meRes.ok) {
        const me = await meRes.json();
        name = `${me.first_name} ${me.last_name}`;
      }

      setToken(data.access_token);
      setRole(data.role);
      setUserName(name);
      setPassword("");

      try {
        localStorage.setItem("token", data.access_token);
        localStorage.setItem("role", data.role);
        localStorage.setItem("userName", name);
      } catch {
        // Stockage indisponible : la session ne sera pas conservée
      }
    } catch (err) {
      setLoginError(err instanceof Error ? err.message : "Erreur de connexion");
    } finally {
      setLoginLoading(false);
    }
  }

  function logout() {
    setToken("");
    setRole("");
    setUserName("");
    setMessages([]);
    setQuestion("");
    try {
      localStorage.removeItem("token");
      localStorage.removeItem("role");
      localStorage.removeItem("userName");
    } catch {
      // Rien à effacer
    }
  }

  async function ask(text: string) {
    const q = text.trim();
    if (!q || loading) return;
    setMessages((m) => [...m, { role: "user", text: q }]);
    setQuestion("");
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/chat?q=${encodeURIComponent(q)}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 401) {
        logout();
        setLoginError("Votre session a expiré, reconnectez-vous.");
        return;
      }
      if (!res.ok) throw new Error(`Erreur ${res.status}`);
      const data = await res.json();
      setMessages((m) => [...m, { role: "assistant", text: data.answer, sources: data.sources }]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: "assistant", text: err instanceof Error ? err.message : "Erreur inconnue" },
      ]);
    } finally {
      setLoading(false);
    }
  }

  // Page de connexion
  if (!token) {
    const disabled = !email || !password || loginLoading;
    return (
      <main
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: 16,
          fontFamily: FONT,
          color: C.text,
          background: `linear-gradient(135deg, ${C.darkest} 0%, ${C.dark} 45%, ${C.teal} 100%)`,
        }}
      >
        <Styles />
        <div
          className="fade-up"
          style={{
            width: "100%",
            maxWidth: 420,
            background: C.white,
            borderRadius: 18,
            padding: 36,
            boxShadow: "0 25px 60px rgba(0,0,0,0.35)",
          }}
        >
                    <h1 style={{ margin: "0 0 28px", fontSize: 23, fontWeight: 700 }}>Enterprise IT Knowledge Hub</h1>
          

          <form onSubmit={login} style={{ display: "grid", gap: 16 }}>
            <label style={{ fontSize: 13, fontWeight: 600, color: C.text }}>
              Adresse e-mail
              <input
                type="email"
                placeholder="Prenom.Nom@entreprise.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={inputStyle}
              />
            </label>
            <label style={{ fontSize: 13, fontWeight: 600, color: C.text }}>
              Mot de passe
              <input
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={inputStyle}
              />
            </label>
            <button
              type="submit"
              className="btn"
              disabled={disabled}
              style={{
                ...buttonStyle,
                background: disabled ? "#94a3b8" : `linear-gradient(135deg, ${C.primary}, ${C.teal})`,
                cursor: disabled ? "not-allowed" : "pointer",
                marginTop: 4,
              }}
            >
              {loginLoading ? "Connexion en cours..." : "Se connecter"}
            </button>
          </form>

          {loginError && (
            <p style={{ color: C.error, fontSize: 14, marginTop: 16, marginBottom: 0 }}>{loginError}</p>
          )}
        </div>
      </main>
    );
  }

  // Interface de chat (utilisateur connecté)
  return (
    <div style={{ display: "flex", height: "100vh", fontFamily: FONT, background: C.bg, color: C.text }}>
      <Styles />

      {/* Barre latérale */}
      <aside
        style={{
          width: 280,
          background: `linear-gradient(180deg, ${C.darkest}, ${C.dark})`,
          color: "#fff",
          padding: 20,
          display: "flex",
          flexDirection: "column",
          gap: 24,
          flexShrink: 0,
        }}
      >
        <div>
          <div style={{ fontWeight: 700, lineHeight: 1.3 }}>Enterprise IT Knowledge Hub</div>
          <div style={{ fontSize: 12, opacity: 0.7, marginTop: 4 }}>Entreprise A</div>
        </div>

        <div style={{ fontSize: 15, fontWeight: 600 }}>
          Bonjour {userName || role}
        </div>
                {role === "admin" && (
          <a href="/admin" style={{ color: "#fff", fontSize: 14, textDecoration: "underline" }}>
            Administration
          </a>
        )}

        <div>
          <div style={{ fontSize: 11, opacity: 0.6, letterSpacing: 1, marginBottom: 8 }}>
            QUESTIONS SUGGÉRÉES
          </div>
          <div style={{ display: "grid", gap: 8 }}>
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                className="btn"
                onClick={() => ask(s)}
                disabled={loading}
                style={{
                  textAlign: "left",
                  background: "rgba(255,255,255,0.07)",
                  color: "#fff",
                  border: "1px solid rgba(134,239,172,0.25)",
                  borderRadius: 8,
                  padding: "8px 10px",
                  fontSize: 13,
                  lineHeight: 1.4,
                  cursor: loading ? "not-allowed" : "pointer",
                }}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        <div style={{ marginTop: "auto" }}>
          <button
            onClick={logout}
            style={{
              width: "100%",
              background: "transparent",
              color: "#fff",
              border: "1px solid rgba(255,255,255,0.3)",
              borderRadius: 8,
              padding: "8px 10px",
              cursor: "pointer",
              fontSize: 14,
            }}
          >
            Se déconnecter
          </button>
        </div>
      </aside>

      {/* Zone de conversation */}
      <main style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <header
          style={{
            background: C.white,
            borderBottom: `1px solid ${C.border}`,
            padding: "16px 24px",
            fontWeight: 700,
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: C.primary,
              boxShadow: `0 0 0 4px ${C.greenLight}`,
            }}
          />
          Assistant IT
        </header>

        <div style={{ flex: 1, overflowY: "auto", padding: 24, display: "flex", flexDirection: "column", gap: 16 }}>
          {messages.length === 0 && (
            <div className="fade-up" style={{ margin: "auto", textAlign: "center", color: C.muted, maxWidth: 440 }}>
              <h2 style={{ color: C.text, fontSize: 20, margin: "0 0 8px" }}>Comment puis-je vous aider ?</h2>
              <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6 }}>
                Posez une question sur les procédures IT. Chaque réponse indique son document source.
              </p>
            </div>
          )}

          {messages.map((m, i) => (
            <Bubble key={i} m={m} />
          ))}

          {loading && (
            <div style={{ display: "flex" }}>
              <div
                style={{
                  background: C.white,
                  border: `1px solid ${C.border}`,
                  borderRadius: 14,
                  padding: "12px 16px",
                  color: C.muted,
                  fontSize: 14,
                }}
              >
                Recherche dans la base de connaissances...
              </div>
            </div>
          )}
          <div ref={endRef} />
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            ask(question);
          }}
          style={{
            background: C.white,
            borderTop: `1px solid ${C.border}`,
            padding: 16,
            display: "flex",
            gap: 12,
          }}
        >
          <input
            type="text"
            placeholder="Posez votre question..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            style={{ ...inputStyle, flex: 1, marginTop: 0 }}
          />
          <button
            type="submit"
            className="btn"
            disabled={loading || !question.trim()}
            style={{
              ...buttonStyle,
              width: "auto",
              padding: "0 22px",
              background:
                loading || !question.trim() ? "#94a3b8" : `linear-gradient(135deg, ${C.primary}, ${C.teal})`,
              cursor: loading || !question.trim() ? "not-allowed" : "pointer",
            }}
          >
            Envoyer
          </button>
        </form>
      </main>
    </div>
  );
}

const inputStyle = {
  width: "100%",
  marginTop: 6,
  padding: "11px 14px",
  border: `1px solid ${C.border}`,
  borderRadius: 10,
  fontSize: 15,
  boxSizing: "border-box" as const,
  outline: "none",
  fontWeight: 400,
  color: C.text,
  background: "#f8fafc",
};

const buttonStyle = {
  width: "100%",
  padding: "11px 16px",
  color: "#fff",
  border: "none",
  borderRadius: 10,
  fontSize: 15,
  fontWeight: 600,
};