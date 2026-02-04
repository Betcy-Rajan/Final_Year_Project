import React from 'react';
import './AgentResponse.css';

function SchemeResponse({ output }) {
  if (!output) return null;

  const schemes = output.schemes || [];
  const categories = output.categories || [];
  const subcategories = output.subcategories || [];
  const location = output.location || '';

  return (
    <div className="agent-response scheme-response">
      <div className="response-header">
        <div className="header-icon">🏛️</div>
        <div>
          <h3>Government Schemes</h3>
          <p className="header-subtitle">Agricultural Subsidies & Benefits</p>
        </div>
      </div>

      <div className="response-content">
        {location && (
          <div className="location-info">
            <span className="info-label">📍 Location:</span>
            <span className="info-value">{location}</span>
          </div>
        )}

        {schemes.length > 0 && (
          <div className="schemes-section">
            <h5 className="section-title">📋 Available Schemes ({schemes.length}):</h5>
            <div className="schemes-list">
              {schemes.map((scheme, idx) => (
                <div key={idx} className="scheme-card">
                  <div className="scheme-header">
                    <h6 className="scheme-name">{scheme.name || scheme.scheme_name || `Scheme ${idx + 1}`}</h6>
                    {scheme.category && (
                      <span className="scheme-category">{scheme.category}</span>
                    )}
                  </div>

                  {scheme.description && (
                    <p className="scheme-description">{scheme.description}</p>
                  )}

                  <div className="scheme-details">
                    {scheme.benefit && (
                      <div className="detail-item">
                        <span className="detail-icon">💰</span>
                        <span className="detail-text">{scheme.benefit}</span>
                      </div>
                    )}
                    {scheme.eligibility && (
                      <div className="detail-item">
                        <span className="detail-icon">✅</span>
                        <span className="detail-text">Eligibility: {scheme.eligibility}</span>
                      </div>
                    )}
                    {scheme.subsidy_amount && (
                      <div className="detail-item">
                        <span className="detail-icon">💵</span>
                        <span className="detail-text">Subsidy: {scheme.subsidy_amount}</span>
                      </div>
                    )}
                  </div>

                  {scheme.link && (
                    <a href={scheme.link} target="_blank" rel="noopener noreferrer" className="scheme-link">
                      Learn More →
                    </a>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {categories.length > 0 && (
          <div className="categories-section">
            <h5 className="section-title">📁 Scheme Categories:</h5>
            <div className="categories-list">
              {categories.map((category, idx) => (
                <span key={idx} className="category-chip">{category}</span>
              ))}
            </div>
          </div>
        )}

        {subcategories.length > 0 && (
          <div className="subcategories-section">
            <h5 className="section-title">📂 Subcategories:</h5>
            <div className="subcategories-list">
              {subcategories.map((subcategory, idx) => (
                <span key={idx} className="subcategory-chip">{subcategory}</span>
              ))}
            </div>
          </div>
        )}

        {schemes.length === 0 && categories.length === 0 && (
          <div className="no-schemes">
            <p>No schemes found for your criteria. Try specifying a location or category.</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default SchemeResponse;

