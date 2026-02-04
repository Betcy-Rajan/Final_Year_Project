import React, { useState } from 'react';
import './Header.css';

function Header({ onBuyerConnectClick }) {
  return (
    <header className="header">
      <div className="header-content">
        <div className="logo">
          <span className="logo-icon">🌾</span>
          <h1>AgriMitra</h1>
        </div>
        <p className="tagline">Your Intelligent Agricultural Assistant</p>
        {onBuyerConnectClick && (
          <button 
            className="buyer-connect-button"
            onClick={onBuyerConnectClick}
            title="Buyer Connect"
          >
            🤝 Buyer Connect
          </button>
        )}
      </div>
    </header>
  );
}

export default Header;

