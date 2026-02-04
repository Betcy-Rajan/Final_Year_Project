import React from 'react';
import './AgentResponse.css';

function BuyerConnectResponse({ output }) {
  if (!output) return null;

  const matchedBuyers = output.matched_buyers || [];
  const priceSuggestions = output.price_suggestions || [];
  const benchmarkPrice = output.benchmark_price || null;
  const listingId = output.listing_id || null;

  return (
    <div className="agent-response buyer-connect-response">
      <div className="response-header">
        <div className="header-icon">🤝</div>
        <div>
          <h3>Buyer Connection</h3>
          <p className="header-subtitle">Find Buyers & Negotiate Fair Prices</p>
        </div>
      </div>

      <div className="response-content">
        {benchmarkPrice && (
          <div className="benchmark-info">
            <span className="info-label">📊 Market Benchmark Price:</span>
            <span className="info-value">₹{benchmarkPrice.toFixed(2)} per kg</span>
          </div>
        )}

        {matchedBuyers.length > 0 && (
          <div className="buyers-section">
            <h5 className="section-title">👥 Matching Buyers ({matchedBuyers.length}):</h5>
            <div className="buyers-list">
              {matchedBuyers.map((buyer, idx) => {
                const matchScore = buyer.match_score || 0;
                const priceSuggestion = priceSuggestions[idx] || {};
                
                return (
                  <div key={idx} className="buyer-card">
                    <div className="buyer-header">
                      <div>
                        <h6 className="buyer-name">{buyer.buyer_name || buyer.name || `Buyer ${idx + 1}`}</h6>
                        <p className="buyer-location">📍 {buyer.location || 'Location not specified'}</p>
                      </div>
                      {matchScore > 0 && (
                        <div className="match-score">
                          <span className="score-value">{Math.round(matchScore * 100)}%</span>
                          <span className="score-label">Match</span>
                        </div>
                      )}
                    </div>

                    <div className="buyer-details">
                      <div className="detail-row">
                        <span className="detail-label">Preferred Price:</span>
                        <span className="detail-value">₹{buyer.preferred_price?.toFixed(2) || 'N/A'} per kg</span>
                      </div>
                      {buyer.demand_range && (
                        <div className="detail-row">
                          <span className="detail-label">Demand Range:</span>
                          <span className="detail-value">
                            {buyer.demand_range.min_qty} - {buyer.demand_range.max_qty} kg
                          </span>
                        </div>
                      )}
                    </div>

                    {priceSuggestion.suggested_price && (
                      <div className="price-suggestion">
                        <div className="suggestion-header">
                          <span className="suggestion-icon">💡</span>
                          <strong>Suggested Fair Price</strong>
                        </div>
                        <div className="suggestion-price">
                          ₹{priceSuggestion.suggested_price.toFixed(2)} per kg
                        </div>
                        {priceSuggestion.explanation && (
                          <p className="suggestion-explanation">
                            {priceSuggestion.explanation}
                          </p>
                        )}
                        {priceSuggestion.fair_lower && priceSuggestion.fair_upper && (
                          <div className="price-range">
                            Fair Range: ₹{priceSuggestion.fair_lower.toFixed(2)} - ₹{priceSuggestion.fair_upper.toFixed(2)}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {matchedBuyers.length === 0 && (
          <div className="no-buyers">
            <p>No matching buyers found at this time. Try adjusting your crop details or check back later.</p>
          </div>
        )}

        {listingId && (
          <div className="listing-info">
            <small>Listing ID: {listingId}</small>
          </div>
        )}
      </div>
    </div>
  );
}

export default BuyerConnectResponse;

