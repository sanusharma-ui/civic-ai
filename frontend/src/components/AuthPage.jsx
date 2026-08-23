import React, { useState } from "react";
import {
  ArrowLeft,
  Loader2,
  Fingerprint,
} from "lucide-react";

import {
  hasSupabaseConfig,
  supabase,
} from "../lib/supabase";

export default function AuthPage({ onBack, onDemo }) {
  const [mode, setMode] = useState("signin");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");

  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState("");

  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();

    setMessage("");
    setMessageType("");

    if (!hasSupabaseConfig) {
      setMessage(
        "Supabase configuration is missing. Please configure your environment variables."
      );

      setMessageType("error");

      return;
    }

    if (!email.trim()) {
      setMessage("Please enter your email.");
      setMessageType("error");
      return;
    }

    if (!password) {
      setMessage("Please enter your password.");
      setMessageType("error");
      return;
    }

    if (password.length < 6) {
      setMessage("Password must be at least 6 characters.");
      setMessageType("error");
      return;
    }

    if (mode === "signup" && !fullName.trim()) {
      setMessage("Please enter your full name.");
      setMessageType("error");
      return;
    }

    setBusy(true);

    try {
      /*
        IMPORTANT:

        Tera React app React Router use nahi kar raha.

        Isliye:

        ❌ window.location.origin + "/auth"

        nahi use karna.

        Supabase confirmation ke baad seedha
        application ke root URL par aayega.

        Production:
        https://civic-ai-theta-one.vercel.app

        Local:
        http://localhost:5173
      */

      const redirectTo = window.location.origin;

      /*
        =========================
        SIGN UP
        =========================
      */

      if (mode === "signup") {
        const { data, error } = await supabase.auth.signUp({
          email: email.trim(),
          password,

          options: {
            emailRedirectTo: redirectTo,

            data: {
              full_name: fullName.trim(),
            },
          },
        });

        if (error) {
          throw error;
        }

        /*
          Agar Supabase Email Confirmation ON hai
          toh normally session null hoga jab tak
          user email verify nahi karta.
        */

        if (!data.session) {
          setMessage(
            "Account created successfully. Check your email and confirm your account."
          );

          setMessageType("success");

          return;
        }

        /*
          Agar Email Confirmation disabled hai
          toh session immediately mil sakta hai.
        */

        setMessage("Account created successfully.");

        setMessageType("success");

        return;
      }

      /*
        =========================
        SIGN IN
        =========================
      */

      const { error } =
        await supabase.auth.signInWithPassword({
          email: email.trim(),
          password,
        });

      if (error) {
        throw error;
      }

      /*
        Login successful hone ke baad
        App.jsx ka onAuthStateChange trigger hoga
        aur automatically ChatWorkspace khul jayega.
      */

      setMessage("Signed in successfully.");

      setMessageType("success");
    } catch (error) {
      console.error("Authentication error:", error);

      /*
        Thode common Supabase errors ko
        human-readable bana dete hain.
      */

      if (
        error?.message
          ?.toLowerCase()
          .includes("invalid login credentials")
      ) {
        setMessage("Invalid email or password.");
      } else if (
        error?.message
          ?.toLowerCase()
          .includes("email not confirmed")
      ) {
        setMessage(
          "Please confirm your email before signing in."
        );
      } else if (
        error?.message
          ?.toLowerCase()
          .includes("user already registered")
      ) {
        setMessage(
          "An account with this email already exists."
        );
      } else {
        setMessage(
          error?.message || "Authentication failed."
        );
      }

      setMessageType("error");
    } finally {
      setBusy(false);
    }
  }

  function switchMode(nextMode) {
    setMode(nextMode);

    setMessage("");
    setMessageType("");
  }

  return (
    <main className="auth-page">
      {/* BACK BUTTON */}

      <button
        className="back-button"
        type="button"
        onClick={onBack}
      >
        <ArrowLeft size={18} />

        <span>Back</span>
      </button>

      {/* AUTH CARD */}

      <section className="auth-card-premium">
        {/* LEFT SIDE */}

        <div className="auth-brand-side">
          <div className="auth-brand-content">
            <div className="brand-mark-wrapper">
              <div className="brand-mark large">
                CA
              </div>

              <span className="brand-name">
                Civic AI
              </span>
            </div>

            <h2>
              {mode === "signin"
                ? "Your workspace for smarter civic action."
                : "Empower your civic workflows."}
            </h2>

            <div className="abstract-motif">
              <Fingerprint
                size={120}
                strokeWidth={0.5}
                className="motif-icon"
              />
            </div>
          </div>
        </div>

        {/* RIGHT SIDE */}

        <div className="auth-form-side">
          <div className="form-header">
            <h1>
              {mode === "signin"
                ? "Welcome back"
                : "Create your Civic AI account"}
            </h1>

            <p className="subtitle">
              {mode === "signin"
                ? "Continue where you left off."
                : "Your workspace for smarter civic action."}
            </p>
          </div>

          <form
            className="premium-form"
            onSubmit={submit}
          >
            {/* MODE SWITCH */}

            <div className="mode-toggle-pill">
              <button
                className={`toggle-btn ${
                  mode === "signin"
                    ? "active"
                    : ""
                }`}
                type="button"
                onClick={() =>
                  switchMode("signin")
                }
              >
                Login
              </button>

              <button
                className={`toggle-btn ${
                  mode === "signup"
                    ? "active"
                    : ""
                }`}
                type="button"
                onClick={() =>
                  switchMode("signup")
                }
              >
                Sign up
              </button>
            </div>

            {/* FULL NAME */}

            {mode === "signup" && (
              <div className="input-group">
                <label htmlFor="fullName">
                  Full name
                </label>

                <input
                  id="fullName"
                  type="text"
                  required
                  autoComplete="name"
                  value={fullName}
                  onChange={(event) =>
                    setFullName(
                      event.target.value
                    )
                  }
                  placeholder="Jane Doe"
                />
              </div>
            )}

            {/* EMAIL */}

            <div className="input-group">
              <label htmlFor="email">
                Email address
              </label>

              <input
                id="email"
                required
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) =>
                  setEmail(event.target.value)
                }
                placeholder="you@example.com"
              />
            </div>

            {/* PASSWORD */}

            <div className="input-group">
              <label htmlFor="password">
                Password
              </label>

              <input
                id="password"
                required
                minLength={6}
                type="password"
                autoComplete={
                  mode === "signin"
                    ? "current-password"
                    : "new-password"
                }
                value={password}
                onChange={(event) =>
                  setPassword(
                    event.target.value
                  )
                }
                placeholder="••••••••"
              />
            </div>

            {/* MESSAGE */}

            {message && (
              <div
                className={`status-message ${
                  messageType === "error"
                    ? "error"
                    : "success"
                }`}
              >
                {message}
              </div>
            )}

            {/* SUBMIT */}

            <button
              className="primary-button submit-btn"
              type="submit"
              disabled={busy}
            >
              {busy && (
                <Loader2
                  className="spin"
                  size={18}
                />
              )}

              <span>
                {busy
                  ? mode === "signin"
                    ? "Signing In..."
                    : "Creating Account..."
                  : mode === "signin"
                  ? "Sign In"
                  : "Create Account"}
              </span>
            </button>

            {/* DIVIDER */}

            <div className="divider">
              <span>or</span>
            </div>

            {/* DEMO */}

            <button
              className="demo-button premium-demo-btn"
              type="button"
              onClick={onDemo}
              disabled={busy}
            >
              Continue in Demo Mode
            </button>
          </form>
        </div>
      </section>
    </main>
  );
}