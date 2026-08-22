import React, { useEffect, useMemo, useState } from "react";
import { hasSupabaseConfig, supabase } from "./lib/supabase";
import Landing from "./components/Landing.jsx";
import AuthPage from "./components/AuthPage.jsx";
import ChatWorkspace from "./components/ChatWorkspace.jsx";

const demoUser = {
  id: "demo-user",
  email: "demo@civicai.local",
  user_metadata: { full_name: "Demo Citizen" },
};

export default function App() {
  const [route, setRoute] = useState("landing");
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let subscription;

    async function init() {
      if (!hasSupabaseConfig) {
        setLoading(false);
        return;
      }

      const { data } = await supabase.auth.getSession();
      setSession(data.session);
      if (data.session) setRoute("app");

      const result = supabase.auth.onAuthStateChange((_event, nextSession) => {
        setSession(nextSession);
        if (nextSession) setRoute("app");
      });

      subscription = result.data.subscription;
      setLoading(false);
    }

    init();
    return () => subscription?.unsubscribe();
  }, []);

  const user = useMemo(() => {
    if (session?.user) return session.user;
    return null;
  }, [session]);

  async function signOut() {
    if (hasSupabaseConfig) await supabase.auth.signOut();
    setSession(null);
    setRoute("landing");
  }

  function continueInDemoMode() {
    setSession({ user: demoUser });
    setRoute("app");
  }

  if (loading) {
    return (
      <main className="loading-screen">
        <div className="pulse-mark">Civic AI</div>
      </main>
    );
  }

  if (route === "landing") {
    return <Landing onStart={() => setRoute("auth")} />;
  }

  if (route === "auth" && !user) {
    return (
      <AuthPage
        onBack={() => setRoute("landing")}
        onDemo={continueInDemoMode}
      />
    );
  }

  return <ChatWorkspace user={user || demoUser} onSignOut={signOut} />;
}
