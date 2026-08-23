import React, { useState } from "react";
import { ArrowLeft, Loader2, LogIn, Mail, UserPlus, Fingerprint } from "lucide-react";
import { hasSupabaseConfig, supabase } from "../lib/supabase";

export default function AuthPage({ onBack, onDemo }) {
  const [mode, setMode] = useState("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setMessage("");

    if (!hasSupabaseConfig) {
      setMessage("Supabase env missing. Use demo mode or configure .env.");
      return;
    }

    setBusy(true);
    try {
      const redirectTo = `${window.location.origin}/auth`;

      if (mode === "signup") {
        const { error } = await supabase.auth.signUp({
          email,
          password,
          options: {
            emailRedirectTo: redirectTo,
            data: { full_name: fullName },
          },
        });
        if (error) throw error;
        setMessage("Account created. Check your email if confirmation is on.");
      } else {
        const { error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (error) throw error;
      }
    } catch (error) {
      setMessage(error.message || "Authentication failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <button className="back-button" type="button" onClick={onBack}>
        <ArrowLeft size={18} />
        <span>Back</span>
      </button>

      <section className="auth-card-premium">
        <div className="auth-brand-side">
          <div className="auth-brand-content">
            <div className="brand-mark-wrapper">
              <div className="brand-mark large">CA</div>
              <span className="brand-name">Civic AI</span>
            </div>
            <h2>
              {mode === "signin" 
                ? "Your workspace for smarter civic action."
                : "Empower your civic workflows."}
            </h2>
            <div className="abstract-motif">
              <Fingerprint size={120} strokeWidth={0.5} className="motif-icon" />
            </div>
          </div>
        </div>

        <div className="auth-form-side">
          <div className="form-header">
            <h1>{mode === "signin" ? "Welcome back" : "Create your Civic AI account"}</h1>
            <p className="subtitle">
              {mode === "signin" ? "Continue where you left off." : "Your workspace for smarter civic action."}
            </p>
          </div>

          <form className="premium-form" onSubmit={submit}>
            <div className="mode-toggle-pill">
              <button
                className={`toggle-btn ${mode === "signin" ? "active" : ""}`}
                type="button"
                onClick={() => {
                  setMode("signin");
                  setMessage("");
                }}
              >
                Login
              </button>
              <button
                className={`toggle-btn ${mode === "signup" ? "active" : ""}`}
                type="button"
                onClick={() => {
                  setMode("signup");
                  setMessage("");
                }}
              >
                Sign up
              </button>
            </div>

            {mode === "signup" && (
              <div className="input-group">
                <label htmlFor="fullName">Full name</label>
                <input
                  id="fullName"
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  placeholder="Jane Doe"
                />
              </div>
            )}

            <div className="input-group">
              <label htmlFor="email">Email address</label>
              <input
                id="email"
                required
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@example.com"
              />
            </div>

            <div className="input-group">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                required
                minLength={6}
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="••••••••"
              />
            </div>

            {message && (
              <div className={`status-message ${message.includes("missing") || message.includes("failed") || message.includes("Invalid") ? "error" : "success"}`}>
                {message}
              </div>
            )}

            <button className="primary-button submit-btn" type="submit" disabled={busy}>
              {busy ? <Loader2 className="spin" size={18} /> : null}
              <span>{mode === "signin" ? "Sign In" : "Create Account"}</span>
            </button>

            <div className="divider">
              <span>or</span>
            </div>

            <button className="demo-button premium-demo-btn" type="button" onClick={onDemo}>
              Continue in Demo Mode
            </button>
          </form>
        </div>
      </section>
    </main>
  );
}
