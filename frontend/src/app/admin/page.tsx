"use client";

import { useState, useEffect, useRef } from "react";

const API_URL = "http://localhost:8000";

const C = {
  darkest: "#022c22",
  dark: "#064e3b",
  primary: "#15803d",
  teal: "#0f766e",
  greenLight: "#dcfce7",
  text: "#0f172a",
  muted: "#64748b",
  border: "#e2e8f0",
  bg: "#f1f5f4",
  white: "#ffffff",
  error: "#b91c1c",
};

const FONT = "'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif";

type User = { id: number; first_name: string; last_name: string; email: string; role: string };
type Category = { id: number; name: string; description: string };
type UploadedDoc = { id: number; title: string; filename: string };
type Section = "users" | "categories" | "documents";

const NAV: { key: Section; label: string }[] = [
  { key: "users", label: "Utilisateurs" },
  { key: "categories", label: "Catégories" },
  { key: "documents", label: "Documents" },
];

const FIELD_LABELS: Record<string, string> = {
  first_name: "Prénom",
  last_name: "Nom",
  email: "Adresse e-mail",
  password: "Mot de passe",
  role: "Rôle",
  name: "Nom de la catégorie",
  description: "Description",
  title: "Titre",
  category_id: "Catégorie",
  file: "Fichier",
};


function frenchValidationMessage(msg: string): string {
  const min = msg.match(/at least (\d+) characters?/i);
  if (min) return `doit contenir au moins ${min[1]} caractères`;
  const max = msg.match(/at most (\d+) characters?/i);
  if (max) return `doit contenir au maximum ${max[1]} caractères`;
  if (/required|missing/i.test(msg)) return "est obligatoire";
  if (/valid email/i.test(msg)) return "n'est pas une adresse e-mail valide";
  if (/valid|not a valid/i.test(msg)) return "n'est pas valide";
  return msg;
}

function frenchError(status: number, body: unknown): string {
  if (status === 401) return "Votre session a expiré, reconnectez-vous.";
  if (status === 403) return "Vous n'avez pas le droit d'effectuer cette action.";
  if (status === 404) return "Élément introuvable.";
  if (status === 409) return "Cet élément existe déjà.";

  if (status === 422 && body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (Array.isArray(detail)) {
      return detail
        .map((d: { loc?: (string | number)[]; msg?: string }) => {
          const field = String(d.loc?.[d.loc.length - 1] ?? "");
          const label = FIELD_LABELS[field] ?? field;
          return `${label} ${frenchValidationMessage(d.msg ?? "")}`;
        })
        .join(" ; ");
    }
  }

  if (status === 400) return "Le serveur a refusé la demande. Vérifiez les informations saisies.";
  return "Une erreur est survenue. Réessayez.";
}


async function apiFetch(path: string, token: string, options: RequestInit = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { Authorization: `Bearer ${token}`, ...(options.headers as Record<string, string>) },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const err = new Error(frenchError(res.status, body)) as Error & { status?: number };
    err.status = res.status;
    throw err;
  }
  return res.status === 204 ? null : res.json();
}

function isUnauthorized(e: unknown) {
  return typeof e === "object" && e !== null && (e as { status?: number }).status === 401;
}

function messageOf(e: unknown) {
  return e instanceof Error ? e.message : "Erreur inconnue";
}

type SectionProps = { token: string; onUnauthorized: () => void };


function Styles() {
  return (
    <style>{`
      @keyframes fadeUp {
        from { opacity: 0; transform: translateY(12px); }
        to   { opacity: 1; transform: translateY(0); }
      }
      .fade-up { animation: fadeUp 0.5s ease-out both; }

      button, a {
        transition: transform 0.15s ease, filter 0.15s ease, box-shadow 0.15s ease;
      }
      button:hover:not(:disabled) {
        filter: brightness(1.1);
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(21,128,61,0.35);
      }
      a:hover {
        filter: brightness(1.2);
      }
    `}</style>
  );
}

//  Utilisateurs 
function UsersSection({ token, onUnauthorized }: SectionProps) {
  const emptyForm = { first_name: "", last_name: "", email: "", password: "", role: "user" };
  const [users, setUsers] = useState<User[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function fail(e: unknown) {
    if (isUnauthorized(e)) onUnauthorized();
    else setError(messageOf(e));
  }

  async function load() {
    try {
      setUsers((await apiFetch("/users", token)) ?? []);
    } catch (e) {
      fail(e);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function reset() {
    setForm(emptyForm);
    setEditingId(null);
  }

  function edit(u: User) {
    setEditingId(u.id);
    setForm({ first_name: u.first_name, last_name: u.last_name, email: u.email, password: "", role: u.role });
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const headers = { "Content-Type": "application/json" };
      if (editingId) {
        await apiFetch(`/users/${editingId}`, token, {
          method: "PATCH",
          headers,
          body: JSON.stringify({ first_name: form.first_name, last_name: form.last_name, email: form.email }),
        });
      } else {
        await apiFetch("/users", token, { method: "POST", headers, body: JSON.stringify(form) });
      }
      reset();
      await load();
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: number) {
    if (!confirm("Supprimer cet utilisateur ?")) return;
    try {
      await apiFetch(`/users/${id}`, token, { method: "DELETE" });
      await load();
    } catch (err) {
      fail(err);
    }
  }

  return (
    <div style={{ display: "grid", gap: 20 }}>
      <section style={cardStyle}>
        <h2 style={sectionTitle}>{editingId ? "Modifier l'utilisateur" : "Ajouter un utilisateur"}</h2>
        <form onSubmit={save} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <input
            placeholder="Prénom"
            value={form.first_name}
            onChange={(e) => setForm({ ...form, first_name: e.target.value })}
            style={inputStyle}
            required
          />
          <input
            placeholder="Nom"
            value={form.last_name}
            onChange={(e) => setForm({ ...form, last_name: e.target.value })}
            style={inputStyle}
            required
          />
          <input
            type="email"
            placeholder="Prenom.Nom@entreprise.com"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            style={{ ...inputStyle, gridColumn: "1 / -1" }}
            required
          />
          {!editingId && (
            <>
              <input
                type="password"
                placeholder="Mot de passe"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                style={inputStyle}
                required
              />
              <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} style={inputStyle}>
                <option value="user">Utilisateur</option>
                <option value="admin">Administrateur</option>
              </select>
            </>
          )}
          <div style={{ gridColumn: "1 / -1", display: "flex", gap: 8 }}>
            <button type="submit" className="btn" disabled={busy} style={{ ...buttonStyle, width: "auto", padding: "0 20px" }}>
              {editingId ? "Enregistrer" : "Ajouter"}
            </button>
            {editingId && (
              <button type="button" onClick={reset} style={secondaryBtn}>
                Annuler
              </button>
            )}
          </div>
        </form>
        {error && <p style={{ color: C.error, fontSize: 14 }}>{error}</p>}
      </section>

      <section style={cardStyle}>
        <h2 style={sectionTitle}>Liste des utilisateurs</h2>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={th}>Nom</th>
              <th style={th}>Email</th>
              <th style={th}>Rôle</th>
              <th style={th}></th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td style={td}>
                  {u.first_name} {u.last_name}
                </td>
                <td style={td}>{u.email}</td>
                <td style={td}>{u.role}</td>
                <td style={{ ...td, textAlign: "right", whiteSpace: "nowrap" }}>
                  <button onClick={() => edit(u)} style={smallBtn(C.primary)}>Modifier</button>
                  <button onClick={() => remove(u.id)} style={smallBtn(C.error)}>Supprimer</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

// Catégories 
function CategoriesSection({ token, onUnauthorized }: SectionProps) {
  const emptyForm = { name: "", description: "" };
  const [categories, setCategories] = useState<Category[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function fail(e: unknown) {
    if (isUnauthorized(e)) onUnauthorized();
    else setError(messageOf(e));
  }

  async function load() {
    try {
      setCategories((await apiFetch("/categories", token)) ?? []);
    } catch (e) {
      fail(e);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function reset() {
    setForm(emptyForm);
    setEditingId(null);
  }

  function edit(c: Category) {
    setEditingId(c.id);
    setForm({ name: c.name, description: c.description ?? "" });
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const headers = { "Content-Type": "application/json" };
      if (editingId) {
        await apiFetch(`/categories/${editingId}`, token, { method: "PUT", headers, body: JSON.stringify(form) });
      } else {
        await apiFetch("/categories", token, { method: "POST", headers, body: JSON.stringify(form) });
      }
      reset();
      await load();
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: number) {
    if (!confirm("Supprimer cette catégorie ?")) return;
    try {
      await apiFetch(`/categories/${id}`, token, { method: "DELETE" });
      await load();
    } catch (err) {
      fail(err);
    }
  }

  return (
    <div style={{ display: "grid", gap: 20 }}>
      <section style={cardStyle}>
        <h2 style={sectionTitle}>{editingId ? "Modifier la catégorie" : "Ajouter une catégorie"}</h2>
        <form onSubmit={save} style={{ display: "grid", gap: 12 }}>
          <input
            placeholder="Nom de la catégorie"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            style={inputStyle}
            required
          />
          <input
            placeholder="Description"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            style={inputStyle}
          />
          <div style={{ display: "flex", gap: 8 }}>
            <button type="submit" className="btn" disabled={busy} style={{ ...buttonStyle, width: "auto", padding: "0 20px" }}>
              {editingId ? "Enregistrer" : "Ajouter"}
            </button>
            {editingId && (
              <button type="button" onClick={reset} style={secondaryBtn}>
                Annuler
              </button>
            )}
          </div>
        </form>
        {error && <p style={{ color: C.error, fontSize: 14 }}>{error}</p>}
      </section>

      <section style={cardStyle}>
        <h2 style={sectionTitle}>Liste des catégories</h2>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={th}>Nom</th>
              <th style={th}>Description</th>
              <th style={th}></th>
            </tr>
          </thead>
          <tbody>
            {categories.map((c) => (
              <tr key={c.id}>
                <td style={td}>{c.name}</td>
                <td style={td}>{c.description}</td>
                <td style={{ ...td, textAlign: "right", whiteSpace: "nowrap" }}>
                  <button onClick={() => edit(c)} style={smallBtn(C.primary)}>Modifier</button>
                  <button onClick={() => remove(c.id)} style={smallBtn(C.error)}>Supprimer</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

// Documents 
function DocumentsSection({ token, onUnauthorized }: SectionProps) {
  const [categories, setCategories] = useState<Category[]>([]);
  const [docs, setDocs] = useState<UploadedDoc[]>([]);
  const [title, setTitle] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function fail(e: unknown) {
    setSuccess("");
    if (isUnauthorized(e)) onUnauthorized();
    else setError(messageOf(e));
  }

  useEffect(() => {
    (async () => {
      try {
        setCategories((await apiFetch("/categories", token)) ?? []);
      } catch (e) {
        fail(e);
      }
    })();
  }, []);

  async function upload(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      const fd = new FormData();
      fd.append("title", title);
      fd.append("category_id", categoryId);
      fd.append("file", file);
      const data = await apiFetch("/documents/upload", token, { method: "POST", body: fd });
      setDocs((d) => [{ id: data.id, title: data.title ?? title, filename: file.name }, ...d]);
      setSuccess(`Document « ${data.title ?? title} » envoyé (n° ${data.id}).`);
      setTitle("");
      setCategoryId("");
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: number) {
    if (!confirm(`Supprimer le document n° ${id} ?`)) return;
    setError("");
    setSuccess("");
    try {
      await apiFetch(`/documents/${id}`, token, { method: "DELETE" });
      setDocs((d) => d.filter((x) => x.id !== id));
      setSuccess(`Document n° ${id} supprimé.`);
    } catch (err) {
      fail(err);
    }
  }

  return (
    <div style={{ display: "grid", gap: 20 }}>
      <section style={cardStyle}>
        <h2 style={sectionTitle}>Ajouter un document</h2>
        <form onSubmit={upload} style={{ display: "grid", gap: 12 }}>
          <input
            placeholder="Titre du document (3 caractères minimum)"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            minLength={3}
            maxLength={255}
            style={inputStyle}
            required
          />
          <select value={categoryId} onChange={(e) => setCategoryId(e.target.value)} style={inputStyle} required>
            <option value="">Choisir une catégorie</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>

          <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <button
              type="button"
              className="btn"
              onClick={() => fileInputRef.current?.click()}
              style={{ ...secondaryBtn, padding: "10px 16px" }}
            >
              Choisir un fichier
            </button>
            <span style={{ fontSize: 14, color: file ? C.text : C.muted }}>
              {file
                ? `${file.name} (${(file.size / 1024 / 1024).toFixed(2)} Mo)`
                : "Aucun fichier choisi"}
            </span>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            style={{ display: "none" }}
          />

          <div>
            <button type="submit" className="btn" disabled={busy || !file} style={{ ...buttonStyle, width: "auto", padding: "0 20px" }}>
              {busy ? "Envoi en cours..." : "Envoyer le document"}
            </button>
          </div>
        </form>
        {categories.length === 0 && (
          <p style={{ color: C.muted, fontSize: 13, marginBottom: 0 }}>
            Créez d'abord une catégorie : un document doit être rattaché à une catégorie.
          </p>
        )}
      </section>

      {(error || success) && (
        <p style={{ color: error ? C.error : C.primary, fontSize: 14, margin: 0 }}>{error || success}</p>
      )}

      <section style={cardStyle}>
        <h2 style={sectionTitle}>Documents envoyés</h2>
        <p style={{ color: C.muted, fontSize: 13, marginTop: 0 }}>Documents envoyés pendant cette session.</p>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={th}>N°</th>
              <th style={th}>Titre</th>
              <th style={th}>Fichier</th>
              <th style={th}></th>
            </tr>
          </thead>
          <tbody>
            {docs.map((d) => (
              <tr key={d.id}>
                <td style={td}>{d.id}</td>
                <td style={td}>{d.title}</td>
                <td style={td}>{d.filename}</td>
                <td style={{ ...td, textAlign: "right" }}>
                  <button onClick={() => remove(d.id)} style={smallBtn(C.error)}>Supprimer</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

// Page admin 
export default function AdminPage() {
  const [ready, setReady] = useState(false);
  const [token, setToken] = useState("");
  const [role, setRole] = useState("");
  const [userName, setUserName] = useState("");
  const [section, setSection] = useState<Section>("users");

  useEffect(() => {
    try {
      setToken(localStorage.getItem("token") ?? "");
      setRole(localStorage.getItem("role") ?? "");
      setUserName(localStorage.getItem("userName") ?? "");
    } catch {
      
    }
    setReady(true);
  }, []);

  function logout() {
    try {
      localStorage.removeItem("token");
      localStorage.removeItem("role");
      localStorage.removeItem("userName");
    } catch {
      
    }
    window.location.href = "/";
  }

  if (!ready) return null;

  const shell = (children: React.ReactNode) => (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 16,
        fontFamily: FONT,
        color: C.text,
        background: C.bg,
      }}
    >
      <Styles />
      <div className="fade-up" style={{ ...cardStyle, maxWidth: 420, textAlign: "center" }}>
        {children}
      </div>
    </main>
  );

  if (!token) {
    return shell(
      <>
        <h2 style={sectionTitle}>Connexion requise</h2>
        <p style={{ color: C.muted }}>Connectez-vous depuis la page d'accueil pour accéder à l'administration.</p>
        <a href="/" style={{ color: C.primary, fontWeight: 600 }}>Aller à la connexion</a>
      </>
    );
  }

  if (role !== "admin") {
    return shell(
      <>
        <h2 style={sectionTitle}>Accès réservé</h2>
        <p style={{ color: C.muted }}>Cette page est réservée aux administrateurs.</p>
        <a href="/" style={{ color: C.primary, fontWeight: 600 }}>Retour aux questions</a>
      </>
    );
  }

  const onUnauthorized = () => logout();

  return (
    <div className="fade-up" style={{ display: "flex", height: "100vh", fontFamily: FONT, background: C.bg, color: C.text }}>
      <Styles />

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
          <div style={{ fontSize: 12, opacity: 0.7, marginTop: 4 }}>Administration</div>
        </div>

        <div style={{ fontSize: 15, fontWeight: 600 }}>Bonjour {userName || role}</div>

        <nav style={{ display: "grid", gap: 6 }}>
          {NAV.map((n) => (
            <button
              key={n.key}
              onClick={() => setSection(n.key)}
              style={{
                textAlign: "left",
                background: section === n.key ? "rgba(255,255,255,0.15)" : "transparent",
                color: "#fff",
                border: "none",
                borderRadius: 8,
                padding: "10px 12px",
                fontSize: 14,
                fontWeight: section === n.key ? 600 : 400,
                cursor: "pointer",
              }}
            >
              {n.label}
            </button>
          ))}
        </nav>

        <div style={{ marginTop: "auto", display: "grid", gap: 8 }}>
          <a href="/" style={{ color: "#fff", fontSize: 14, textDecoration: "underline" }}>
            ← Retour aux questions
          </a>
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
          {NAV.find((n) => n.key === section)?.label}
        </header>

        <div style={{ flex: 1, overflowY: "auto", padding: 24 }}>
          {section === "users" && <UsersSection token={token} onUnauthorized={onUnauthorized} />}
          {section === "categories" && <CategoriesSection token={token} onUnauthorized={onUnauthorized} />}
          {section === "documents" && <DocumentsSection token={token} onUnauthorized={onUnauthorized} />}
        </div>
      </main>
    </div>
  );
}

const cardStyle = {
  background: C.white,
  border: `1px solid ${C.border}`,
  borderRadius: 12,
  padding: 24,
  boxShadow: "0 1px 3px rgba(15,23,42,0.06)",
};

const sectionTitle = { margin: "0 0 16px", fontSize: 17, fontWeight: 700 };

const th = {
  textAlign: "left" as const,
  padding: "10px 12px",
  fontSize: 12,
  color: C.muted,
  textTransform: "uppercase" as const,
  letterSpacing: 0.5,
  borderBottom: `1px solid ${C.border}`,
};

const td = { padding: "12px", borderBottom: `1px solid ${C.border}`, fontSize: 14 };

const smallBtn = (color: string) => ({
  padding: "6px 10px",
  borderRadius: 8,
  border: `1px solid ${color}`,
  background: "transparent",
  color,
  cursor: "pointer",
  fontSize: 13,
  marginLeft: 6,
});

const secondaryBtn = {
  padding: "11px 16px",
  borderRadius: 10,
  border: `1px solid ${C.border}`,
  background: C.white,
  color: C.text,
  cursor: "pointer",
  fontSize: 15,
};

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
  background: `linear-gradient(135deg, #15803d, #0f766e)`,
  cursor: "pointer",
};