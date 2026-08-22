import React, { useState } from "react";
import { ArrowLeft, Loader2, LogIn, Mail, UserPlus } from "lucide-react";
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
        Back
      </button>

      <section className="auth-card">
        <div className="auth-visual">
          <div className="brand-mark large">CA</div>
          <h1>{mode === "signin" ? "Welcome back" : "Create your Civic AI account"}</h1>
          <p>
            Secure your sessions, keep chat history close, and continue civic
            work from any device once Supabase is connected.
          </p>
        </div>

        <form className="auth-form" onSubmit={submit}>
          <div className="mode-switch">
            <button
              className={mode === "signin" ? "active" : ""}
              type="button"
              onClick={() => setMode("signin")}
            >
              <LogIn size={16} />
              Login
            </button>
            <button
              className={mode === "signup" ? "active" : ""}
              type="button"
              onClick={() => setMode("signup")}
            >
              <UserPlus size={16} />
              Signup
            </button>
          </div>

          {mode === "signup" && (
            <label>
              Full name
              <input
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                placeholder="Your name"
              />
            </label>
          )}

          <label>
            Email
            <input
              required
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
            />
          </label>

          <label>
            Password
            <input
              required
              minLength={6}
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Minimum 6 characters"
            />
          </label>

          {message && <p className="form-message">{message}</p>}

          <button className="primary-button full" type="submit" disabled={busy}>
            {busy ? <Loader2 className="spin" size={18} /> : <Mail size={18} />}
            {mode === "signin" ? "Login and continue" : "Create account"}
          </button>

          <button className="demo-button" type="button" onClick={onDemo}>
            Continue in demo mode
          </button>
        </form>
      </section>
    </main>
  );
}
