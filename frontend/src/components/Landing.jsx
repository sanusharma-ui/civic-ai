import React from "react";
import {
  ArrowRight,
  BookOpen,
  ChevronRight,
  FileSearch,
  Scale,
  MessageSquare,
  CheckCircle2,
  Cpu,
  Landmark,
  ShieldAlert
} from "lucide-react";

export default function Landing({ onStart }) {
  return (
    <main className="landing-page">
      <nav className="landing-nav">
        <a className="brand" href="/">
          <span className="brand-mark">CA</span>
          <span className="brand-text">Civic AI</span>
        </a>
        <div className="nav-actions">
          <a href="#agents" className="nav-link">Agents</a>
          <a href="#how-it-works" className="nav-link">How it works</a>
          <a href="#trust" className="nav-link">Trust</a>
          <div className="nav-auth">
            <button className="ghost-button" type="button" onClick={onStart}>
              Sign in
            </button>
            <button className="primary-button small-nav-btn" type="button" onClick={onStart}>
              Start session
            </button>
          </div>
        </div>
      </nav>

      <section className="hero-section">
        <div className="hero-copy">
          <div className="eyebrow">
            <div className="eyebrow-dot"></div>
            Civic Intelligence Workspace
          </div>
          <h1>AI for getting things done.</h1>
          <p>
            Understand your rights. Draft the right request. Take the next step.
            A focused workspace built for Indian civic and legal workflows.
          </p>
          <div className="hero-actions">
            <button className="primary-button big" type="button" onClick={onStart}>
              Start your session
              <ArrowRight size={20} />
            </button>
            <a className="secondary-link group" href="#agents">
              Explore agents
              <ChevronRight size={16} className="group-hover-translate" />
            </a>
          </div>
        </div>

        <div className="hero-visual-wrapper" aria-hidden="true">
          <div className="hero-workspace-mock">
            <div className="mock-sidebar">
              <div className="mock-agent active">
                <FileSearch size={16} /> RTI Agent
              </div>
              <div className="mock-agent">
                <Scale size={16} /> Consumer
              </div>
              <div className="mock-agent">
                <Landmark size={16} /> Civic
              </div>
            </div>
            <div className="mock-chat-area">
              <div className="mock-message user">
                <p>I need to find out why my passport verification is delayed for 3 months. Can I file an RTI?</p>
              </div>
              <div className="mock-message ai">
                <div className="mock-ai-header">
                  <span className="mock-avatar">CA</span>
                  <span>RTI Agent</span>
                </div>
                <p>Yes, you can file an RTI with the Regional Passport Office (RPO). Here is what you should ask:</p>
                <div className="mock-card">
                  <div className="mock-card-title">Draft Application</div>
                  <div className="mock-card-body">1. Daily progress report on file number...</div>
                </div>
              </div>
            </div>
          </div>
          <div className="bg-glow"></div>
        </div>
      </section>

      <section className="value-section">
        <div className="section-header">
          <h2>Built for real civic problems</h2>
        </div>
        <div className="value-grid">
          <div className="value-card">
            <FileSearch size={24} className="value-icon" />
            <h3>RTI</h3>
            <p>Turn questions into precise information requests and track follow-ups.</p>
          </div>
          <div className="value-card">
            <ShieldAlert size={24} className="value-icon" />
            <h3>Consumer Rights</h3>
            <p>Build stronger complaints with the right evidence and legal grounding.</p>
          </div>
          <div className="value-card">
            <BookOpen size={24} className="value-icon" />
            <h3>Civic Guidance</h3>
            <p>Understand what to do next, without the confusing legal jargon.</p>
          </div>
        </div>
      </section>

      <section className="agent-showcase" id="agents">
        <div className="showcase-header">
          <h2>One workspace. Multiple civic problems.</h2>
        </div>
        <div className="showcase-grid">
          <article className="showcase-card informational-card">
            <div className="card-icon-wrapper">
              <FileSearch size={22} />
            </div>
            <div className="card-content">
              <h3>RTI Agent</h3>
              <p>Draft precise requests, first appeals, and follow-ups based on the RTI Act 2005.</p>
            </div>
          </article>
          
          <article className="showcase-card informational-card">
            <div className="card-icon-wrapper">
              <Scale size={22} />
            </div>
            <div className="card-content">
              <h3>Consumer Rights</h3>
              <p>Structure complaints, organize evidence, and plan escalation steps effectively.</p>
            </div>
          </article>

          <article className="showcase-card informational-card">
            <div className="card-icon-wrapper">
              <MessageSquare size={22} />
            </div>
            <div className="card-content">
              <h3>Civic Assistant</h3>
              <p>Understand notices, procedural norms, and exactly what to do next.</p>
            </div>
          </article>
        </div>
      </section>

      <section className="how-it-works-section" id="how-it-works">
        <div className="section-header">
          <h2>How it works</h2>
        </div>
        <div className="steps-container">
          <div className="step-item">
            <div className="step-number">1</div>
            <h3>Choose an agent</h3>
            <p>Select the agent that matches your civic problem.</p>
          </div>
          <div className="step-item">
            <div className="step-number">2</div>
            <h3>Ask your question</h3>
            <p>Describe your issue in plain language.</p>
          </div>
          <div className="step-item">
            <div className="step-number">3</div>
            <h3>Get guidance</h3>
            <p>Draft the next step and take action.</p>
          </div>
        </div>
      </section>


      <section className="trust-section" id="trust">
        <div className="trust-grid">
          <div className="trust-item">
            <CheckCircle2 size={20} className="trust-icon" />
            <span>Clear by design.</span>
          </div>
          <div className="trust-item">
            <CheckCircle2 size={20} className="trust-icon" />
            <span>Grounded in your question.</span>
          </div>
          <div className="trust-item">
            <CheckCircle2 size={20} className="trust-icon" />
            <span>Built for Indian civic workflows.</span>
          </div>
        </div>
      </section>
    </main>
  );
}
