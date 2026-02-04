import React from 'react';
import './RoleSelectionModal.css';

function RoleSelectionModal({ onSelectRole, onClose }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>×</button>
        <h2>Select Your Role</h2>
        <div className="role-options">
          <button 
            className="role-button farmer"
            onClick={() => onSelectRole('farmer')}
          >
            <span className="role-icon">👨‍🌾</span>
            <span className="role-label">Farmer</span>
            <span className="role-description">Sell your crops and find buyers</span>
          </button>
          <button 
            className="role-button buyer"
            onClick={() => onSelectRole('buyer')}
          >
            <span className="role-icon">🏢</span>
            <span className="role-label">Buyer</span>
            <span className="role-description">Post requirements and find farmers</span>
          </button>
        </div>
      </div>
    </div>
  );
}

export default RoleSelectionModal;
