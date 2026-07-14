import React from 'react';
import { useSelector } from 'react-redux';
import { RootState } from '../store';
import { User, Phone, Mail, MapPin, Award, CheckCircle } from 'lucide-react';

export const HCPContextPanel: React.FC = () => {
  const { hcpContext } = useSelector((state: RootState) => state.interaction);

  if (!hcpContext) {
    return (
      <div className="hcp-context-panel card empty">
        <User size={24} className="panel-icon" />
        <p>Select a Healthcare Professional or ask about a doctor to load their historical CRM profile context.</p>
      </div>
    );
  }

  return (
    <div className="hcp-context-panel card">
      <div className="panel-header-sub">
        <User size={18} className="header-icon" />
        <h3>HCP Profile Context: {hcpContext.name}</h3>
      </div>

      <div className="profile-details-grid">
        <div className="detail-item">
          <Award size={14} />
          <span><strong>Specialty:</strong> {hcpContext.specialty}</span>
        </div>
        <div className="detail-item">
          <MapPin size={14} />
          <span><strong>Clinic:</strong> {hcpContext.clinic_name || 'N/A'}</span>
        </div>
        <div className="detail-item">
          <Mail size={14} />
          <span><strong>Email:</strong> {hcpContext.email || 'N/A'}</span>
        </div>
        <div className="detail-item">
          <Phone size={14} />
          <span><strong>Phone:</strong> {hcpContext.phone || 'N/A'}</span>
        </div>
      </div>

      {hcpContext.preferred_products.length > 0 && (
        <div className="profile-section">
          <h4>Preferred Products Discussed</h4>
          <div className="preferred-products-list">
            {hcpContext.preferred_products.map((p, idx) => (
              <span key={idx} className="product-badge">
                {p}
              </span>
            ))}
          </div>
        </div>
      )}

      {hcpContext.recent_interactions.length > 0 && (
        <div className="profile-section">
          <h4>Last Interactions</h4>
          <div className="interactions-mini-list">
            {hcpContext.recent_interactions.map((inter, idx) => (
              <div key={idx} className="interaction-mini-card">
                <div className="mini-card-header">
                  <span className="mini-card-date">{inter.date}</span>
                  <span className="mini-card-type">{inter.type}</span>
                  <span className={`mini-card-sentiment ${inter.sentiment}`}>
                    {inter.sentiment === 'Positive' ? '😊' : inter.sentiment === 'Negative' ? '😟' : '😐'} {inter.sentiment}
                  </span>
                </div>
                <div className="mini-card-topics">{inter.topics}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
