import React from "react";
import { LogOut, Mail, Shield, User } from "lucide-react";

export default function ProfilePanel({ user, onClose, onSignOut }) {
  const name = user.user_metadata?.full_name || "Civic AI user";

  return (
    <div className="profile-overlay" onClick={onClose}>
      <aside className="profile-panel" onClick={(event) => event.stopPropagation()}>
        <div className="profile-avatar">
          {name
            .split(" ")
            .map((part) => part[0])
            .slice(0, 2)
            .join("")
            .toUpperCase()}
        </div>
        <h2>{name}</h2>
        <p>{user.email}</p>

        <form className="profile-form" onSubmit={(e) => { e.preventDefault(); onClose(); }}>
          <label>
            Full Name
            <input type="text" defaultValue={name} />
          </label>
          <label>
            Email
            <input type="email" defaultValue={user.email} disabled />
          </label>
          <button className="primary-button full" type="submit" style={{ marginTop: '10px' }}>
            Update Profile
          </button>
        </form>

        <div className="profile-list">
          <div>
            <User size={18} />
            Profile synced with Supabase Auth
          </div>
          <div>
            <Shield size={18} />
            Chat history saved locally for this user
          </div>
        </div>

        <button className="danger-button" type="button" onClick={onSignOut}>
          <LogOut size={18} />
          Sign out
        </button>
      </aside>
    </div>
  );
}
