import React from "react";
import {
  ArrowRight,
  BadgeCheck,
  FileSearch,
  MessageSquareText,
  Scale,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

export default function Landing({ onStart }) {
  return (
    <main className="landing-page">
      <nav className="landing-nav">
        <a className="brand" href="/">
          <span className="brand-mark">CA</span>
          <span>Civic AI</span>
        </a>
        <div className="nav-actions">
          <a href="#agents">Agents</a>
          <a href="#trust">Trust</a>
          <button className="ghost-button" type="button" onClick={onStart}>
            Sign in
          </button>
        </div>
      </nav>

      <section className="hero-section">
        <div className="hero-copy">
          <div className="eyebrow">
            <Sparkles size={16} />
            Citizen-first legal and civic guidance
          </div>
          <h1>Civic AI</h1>
          <p>
            Ask RTI and consumer-rights questions, draft stronger applications,
            and understand next steps through a focused AI workspace built for
            Indian citizens.
          </p>
          <div className="hero-actions">
            <button className="primary-button big" type="button" onClick={onStart}>
              Start your session
              <ArrowRight size={20} />
            </button>
            <a className="secondary-link" href="#agents">
              Explore agents
            </a>
          </div>
        </div>

        <div className="hero-stage" aria-hidden="true">
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <div className="glass-console">
            <div className="console-top">
              <span />
              <span />
              <span />
            </div>
            <div className="console-message user">
              Can I ask a department for file status under RTI?
            </div>
            <div className="console-message assistant">
              Yes. I can help draft a precise RTI request and list the details
              you should include.
            </div>
            <div className="typing-row">
              <span />
              <span />
              <span />
            </div>
          </div>
          <div className="floating-card card-rti">
            <FileSearch size={22} />
            RTI drafts
          </div>
          <div className="floating-card card-consumer">
            <Scale size={22} />
            Consumer complaints
          </div>
        </div>
      </section>

      <section className="agent-band" id="agents">
        <article>
          <FileSearch />
          <h2>RTI Agent</h2>
          <p>Frame precise information requests, appeals, and follow-ups.</p>
        </article>
        <article>
          <Scale />
          <h2>Consumer Rights Agent</h2>
          <p>Plan complaint steps, collect evidence, and draft escalation text.</p>
        </article>
        <article>
          <MessageSquareText />
          <h2>Streaming Chat</h2>
          <p>Responses appear progressively for a natural typing experience.</p>
        </article>
      </section>

      <section className="trust-strip" id="trust">
        <div>
          <ShieldCheck />
          No hardcoded secrets
        </div>
        <div>
          <BadgeCheck />
          Supabase auth ready
        </div>
        <div>
          <Sparkles />
          Expandable agent system
        </div>
      </section>
    </main>
  );
}
