import React, { useState } from 'react';
import './BuyerMatchDisplay.css';

function BuyerMatchDisplay({ matchedBuyers, onBack }) {
  const [processing, setProcessing] = useState({});
  const [negotiations, setNegotiations] = useState({}); // Store negotiations by buyer_id

  const handleNegotiate = async (buyerId, listingId) => {
    const key = `${buyerId}-negotiate`;
    setProcessing({ ...processing, [key]: true });

    try {
      const response = await fetch(`/api/buyer-connect/negotiate/${listingId}/${buyerId}/enhanced`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to initiate negotiation' }));
        throw new Error(errorData.detail || 'Failed to initiate negotiation');
      }

      const negotiation = await response.json();
      console.log('Negotiation response:', negotiation);
      console.log('Buyer ID:', buyerId, 'Type:', typeof buyerId);
      
      // Ensure we use the buyerId as the key (handle both string and number)
      const buyerKey = String(buyerId);
      setNegotiations(prev => {
        const updated = {
          ...prev,
          [buyerKey]: negotiation
        };
        console.log('Updated negotiations state:', updated);
        return updated;
      });
    } catch (error) {
      console.error('Error initiating negotiation:', error);
      alert(`Error initiating negotiation: ${error.message || 'Please try again.'}`);
    } finally {
      setProcessing({ ...processing, [key]: false });
    }
  };

  const handleAction = async (buyerId, listingId, negotiationId, action) => {
    const key = `${buyerId}-${action}`;
    setProcessing({ ...processing, [key]: true });

    try {
      if (action === 'accept') {
        // Accept the negotiation
        if (!negotiationId || negotiationId === 'undefined') {
          alert('Please negotiate first to get a fair price suggestion.');
          return;
        }
        
        const response = await fetch(`/api/buyer-connect/negotiations/${negotiationId}/decision`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ decision: 'accept' })
        });
        if (response.ok) {
          const updatedNegotiation = await response.json();
          // Update local state
          setNegotiations({
            ...negotiations,
            [buyerId]: updatedNegotiation
          });
          alert(`✅ Offer accepted! Fair price of ₹${updatedNegotiation.ai_suggested_price?.toFixed(2) || 'N/A'}/kg has been sent to ${buyerId === buyerId ? 'the buyer' : 'buyer'}.`);
        } else {
          const error = await response.json().catch(() => ({ detail: 'Failed to accept offer' }));
          alert(`Error: ${error.detail || 'Failed to accept offer'}`);
        }
      } else if (action === 'counter') {
        // For counter offer, we could show a modal to enter new price
        const newPrice = prompt('Enter your counter offer price (₹/kg):');
        if (newPrice && !isNaN(newPrice)) {
          // In a real implementation, this would create a new negotiation with counter price
          alert(`Counter offer of ₹${newPrice}/kg sent to buyer.`);
        }
      } else if (action === 'reject') {
        if (!negotiationId || negotiationId === 'undefined') {
          alert('Please negotiate first.');
          return;
        }
        
        const response = await fetch(`/api/buyer-connect/negotiations/${negotiationId}/decision`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ decision: 'reject' })
        });
        if (response.ok) {
          const updatedNegotiation = await response.json();
          setNegotiations({
            ...negotiations,
            [buyerId]: updatedNegotiation
          });
          alert('Offer rejected.');
        } else {
          const error = await response.json().catch(() => ({ detail: 'Failed to reject offer' }));
          alert(`Error: ${error.detail || 'Failed to reject offer'}`);
        }
      }
    } catch (error) {
      console.error('Error processing action:', error);
      alert('Error processing action. Please try again.');
    } finally {
      setProcessing({ ...processing, [key]: false });
    }
  };

  if (!matchedBuyers || !matchedBuyers.matched_buyers || matchedBuyers.matched_buyers.length === 0) {
    return (
      <div className="buyer-match-display">
        <button className="back-button" onClick={onBack}>← Back</button>
        <div className="no-matches">
          <p>No matching buyers found. Try adjusting your requirements.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="buyer-match-display">
      <div className="match-header">
        <button className="back-button" onClick={onBack}>← Back</button>
        <h2>Matched Buyers</h2>
        <p className="match-count">{matchedBuyers.matched_buyers.length} buyer(s) found</p>
      </div>

      <div className="buyer-cards">
        {matchedBuyers.matched_buyers.map((buyer) => {
          // Use negotiation from state if available, otherwise from buyer object
          // Handle both string and number buyer_id
          const buyerKey = String(buyer.buyer_id);
          const negotiation = negotiations[buyerKey] || negotiations[buyer.buyer_id] || buyer.negotiation || {};
          // Check if negotiation exists (has ID and explanation) - show even if no fair match
          const hasNegotiation = negotiation.id && negotiation.explanation;
          const key = `${buyer.buyer_id}-accept`;
          const isProcessing = processing[key] || processing[`${buyer.buyer_id}-counter`] || processing[`${buyer.buyer_id}-reject`] || processing[`${buyer.buyer_id}-negotiate`];
          
          // Debug log
          if (negotiation.id) {
            console.log(`Buyer ${buyer.buyer_id} negotiation:`, negotiation);
          }

          return (
            <div key={buyer.buyer_id} className="buyer-card">
              <div className="buyer-header">
                <h3>{buyer.buyer_name}</h3>
                <span className="location">📍 {buyer.location}</span>
              </div>

              <div className="buyer-details">
                <div className="detail-row">
                  <span className="label">Needs:</span>
                  <span className="value">{buyer.demand_range?.min_qty || 'N/A'} - {buyer.demand_range?.max_qty || 'N/A'} kg</span>
                </div>
                <div className="detail-row">
                  <span className="label">Buyer Max Price:</span>
                  <span className="value">₹{buyer.preferred_price || negotiation.buyer_offer || 'N/A'}/kg</span>
                </div>
                
                {hasNegotiation ? (
                  <div className="ai-suggestion">
                    {negotiation.ai_suggested_price !== null && negotiation.ai_suggested_price !== undefined ? (
                      <div className="ai-price">
                        <strong>🤖 AgriMitra Suggested Fair Price:</strong> ₹{negotiation.ai_suggested_price.toFixed(2)}/kg
                      </div>
                    ) : (
                      <div className="ai-price no-match">
                        <strong>⚠️ No Fair Price Match Available</strong>
                      </div>
                    )}
                    <div className="explanation-box">
                      <strong>📝 Explanation:</strong>
                      <p>{negotiation.explanation || 'No explanation available'}</p>
                      {(negotiation.benchmark_price || negotiation.fair_lower || negotiation.fair_upper || negotiation.farmer_min_price || negotiation.buyer_offer) && (
                        <div className="breakdown">
                          <strong>Price Breakdown:</strong>
                          <ul style={{ margin: '0.5rem 0', paddingLeft: '1.5rem' }}>
                            {negotiation.benchmark_price && (
                              <li>Market Benchmark: ₹{negotiation.benchmark_price.toFixed(2)}/kg</li>
                            )}
                            {negotiation.farmer_min_price && (
                              <li>Your Minimum: ₹{negotiation.farmer_min_price.toFixed(2)}/kg</li>
                            )}
                            {negotiation.buyer_offer && (
                              <li>Buyer Offer: ₹{negotiation.buyer_offer.toFixed(2)}/kg</li>
                            )}
                            {(negotiation.fair_lower && negotiation.fair_upper && negotiation.fair_lower <= negotiation.fair_upper) && (
                              <li>Fair Price Range: ₹{negotiation.fair_lower.toFixed(2)} - ₹{negotiation.fair_upper.toFixed(2)}/kg</li>
                            )}
                          </ul>
                        </div>
                      )}
                    </div>
                    {negotiation.decision === 'accept' && (
                      <div className="accepted-badge">
                        ✅ Accepted - Fair price sent to buyer
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="negotiate-prompt">
                    <p>Click "Negotiate" to get AgriMitra's fair price suggestion</p>
                  </div>
                )}
              </div>

              <div className="buyer-actions">
                {!hasNegotiation ? (
                  <button
                    className="action-button negotiate"
                    onClick={() => handleNegotiate(buyer.buyer_id, matchedBuyers.listing_id)}
                    disabled={isProcessing}
                  >
                    {processing[`${buyer.buyer_id}-negotiate`] ? 'Negotiating...' : '🤝 Negotiate'}
                  </button>
                ) : (
                  <>
                    {negotiation.ai_suggested_price !== null && negotiation.ai_suggested_price !== undefined ? (
                      <button
                        className="action-button accept"
                        onClick={() => handleAction(
                          buyer.buyer_id,
                          matchedBuyers.listing_id,
                          negotiation.id,
                          'accept'
                        )}
                        disabled={isProcessing || negotiation.decision === 'accept'}
                      >
                        {processing[`${buyer.buyer_id}-accept`] ? 'Processing...' : '✅ Accept'}
                      </button>
                    ) : null}
                    <button
                      className="action-button counter"
                      onClick={() => handleAction(
                        buyer.buyer_id,
                        matchedBuyers.listing_id,
                        negotiation.id,
                        'counter'
                      )}
                      disabled={isProcessing || negotiation.decision === 'accept'}
                    >
                      💬 Counter Offer
                    </button>
                    <button
                      className="action-button reject"
                      onClick={() => handleAction(
                        buyer.buyer_id,
                        matchedBuyers.listing_id,
                        negotiation.id,
                        'reject'
                      )}
                      disabled={isProcessing || negotiation.decision === 'accept'}
                    >
                      ❌ Reject
                    </button>
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default BuyerMatchDisplay;
