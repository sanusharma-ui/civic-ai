import React, { useState } from "react";
import { LogOut, Mail, Shield, User, Phone, MapPin, Briefcase } from "lucide-react";

export default function ProfilePanel({ user, onClose, onSignOut }) {
  const name = user.user_metadata?.full_name || "Civic AI user";
  const [formData, setFormData] = useState({
    name,
    email: user.email,
    phone: "",
    occupation: "",
    location: "",
  });

  const handleChange = (e) => {
    setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  return (
    <div className="profile-overlay" onClick={onClose}>
      <aside className="profile-panel" onClick={(event) => event.stopPropagation()}>
        <div className="profile-header">
          <div className="profile-avatar-container">
            <div className="profile-avatar large">
              {name
                .split(" ")
                .map((part) => part[0])
                .slice(0, 2)
                .join("")
                .toUpperCase()}
            </div>
            <div className="online-badge"></div>
          </div>
          <div className="profile-title">
            <h2>{name}</h2>
            <p className="profile-email">{user.email}</p>
          </div>
        </div>

        <form className="profile-form" onSubmit={(e) => { e.preventDefault(); onClose(); }}>
          <div className="form-group">
            <label>Full Name</label>
            <div className="input-with-icon">
              <User size={16} className="input-icon" />
              <input type="text" name="name" value={formData.name} onChange={handleChange} placeholder="John Doe" />
            </div>
          </div>
          
          <div className="form-group">
            <label>Email Address</label>
            <div className="input-with-icon">
              <Mail size={16} className="input-icon" />
              <input type="email" name="email" value={formData.email} disabled />
            </div>
          </div>

          <div className="form-group">
            <label>Phone Number</label>
            <div className="input-with-icon">
              <Phone size={16} className="input-icon" />
              <input type="tel" name="phone" value={formData.phone} onChange={handleChange} placeholder="+91 9876543210" />
            </div>
          </div>

          <div className="form-group">
            <label>Occupation</label>
            <div className="input-with-icon">
              <Briefcase size={16} className="input-icon" />
              <input type="text" name="occupation" value={formData.occupation} onChange={handleChange} placeholder="Legal Advisor" />
            </div>
          </div>

          <button className="primary-button full update-btn" type="submit">
            Save Changes
          </button>
        </form>

        <div className="profile-list">
          <div className="list-item">
            <Shield size={18} className="list-icon text-accent" />
            <div>
              <strong>Privacy Secured</strong>
              <small>Chat history saved locally on device</small>
            </div>
          </div>
        </div>

        <button className="danger-button full" type="button" onClick={onSignOut}>
          <LogOut size={18} />
          Sign out securely
        </button>
      </aside>
    </div>
  );
}
