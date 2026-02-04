import React, { useState } from 'react';
import './FarmerInterface.css';
import BuyerMatchDisplay from './BuyerMatchDisplay';

function FarmerInterface({ farmerId = 1, onBack }) {
  const [activeTab, setActiveTab] = useState('nl'); // 'nl' or 'form'
  const [nlQuery, setNlQuery] = useState('');
  const [formData, setFormData] = useState({
    crop: '',
    quantity: '',
    minimum_price: '',
    location: ''
  });
  const [matchedBuyers, setMatchedBuyers] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleNLSubmit = async (e) => {
    e.preventDefault();
    if (!nlQuery.trim()) return;

    setLoading(true);
    setError(null);
    setMatchedBuyers(null);

    try {
      const response = await fetch('/api/buyer-connect/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: nlQuery, farmer_id: farmerId })
      });

      if (!response.ok) {
        throw new Error('Failed to process query');
      }

      const data = await response.json();
      console.log('NL Query Response:', data);
      console.log('Matched Buyers:', data.matched_buyers);
      
      if (data.matched_buyers && data.matched_buyers.length > 0) {
        setMatchedBuyers(data);
      } else {
        setError('No matching buyers found. Try adjusting your quantity or price, or create a buyer requirement first.');
        setMatchedBuyers(null);
      }
    } catch (err) {
      console.error('NL Query Error:', err);
      setError(err.message || 'An error occurred. Please try again.');
      setMatchedBuyers(null);
    } finally {
      setLoading(false);
    }
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setMatchedBuyers(null);

    try {
      // Create listing first
      const listingResponse = await fetch('/api/buyer-connect/listings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          farmer_id: farmerId,
          crop: formData.crop,
          quantity: parseFloat(formData.quantity),
          unit: 'kg',
          farmer_threshold_price: parseFloat(formData.minimum_price)
        })
      });

      if (!listingResponse.ok) {
        throw new Error('Failed to create listing');
      }

      const listing = await listingResponse.json();

      // Get matched buyers
      const matchResponse = await fetch(`/api/buyer-connect/buyers/match/${listing.id}`);
      if (!matchResponse.ok) {
        throw new Error('Failed to find matches');
      }

      const matched = await matchResponse.json();
      
      // Get price suggestions for each match
      const matchesWithSuggestions = await Promise.all(
        matched.map(async (buyer) => {
          try {
            const negResponse = await fetch(
              `/api/buyer-connect/negotiate/${listing.id}/${buyer.buyer_id}/enhanced`
            );
            if (negResponse.ok) {
              const negotiation = await negResponse.json();
              return {
                ...buyer,
                negotiation: negotiation,
                ai_suggested_price: negotiation.ai_suggested_price,
                explanation: negotiation.explanation,
                benchmark_price: negotiation.benchmark_price,
                buyer_offer: negotiation.buyer_offer,
                farmer_min_price: negotiation.farmer_min_price
              };
            }
          } catch (err) {
            console.error('Error getting negotiation:', err);
          }
          return buyer;
        })
      );

      setMatchedBuyers({
        listing_id: listing.id,
        matched_buyers: matchesWithSuggestions
      });
    } catch (err) {
      setError(err.message || 'An error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="farmer-interface">
      <div className="interface-header">
        <button className="back-button" onClick={onBack}>← Back</button>
        <h1>Farmer Interface</h1>
      </div>

      {!matchedBuyers ? (
        <div className="interface-content">
          <div className="tab-selector">
            <button 
              className={activeTab === 'nl' ? 'active' : ''}
              onClick={() => setActiveTab('nl')}
            >
              Natural Language
            </button>
            <button 
              className={activeTab === 'form' ? 'active' : ''}
              onClick={() => setActiveTab('form')}
            >
              Manual Form
            </button>
          </div>

          {activeTab === 'nl' ? (
            <form className="nl-form" onSubmit={handleNLSubmit}>
              <div className="form-group">
                <label>
                  Describe what you want to sell
                  <textarea
                    value={nlQuery}
                    onChange={(e) => setNlQuery(e.target.value)}
                    placeholder="Example: I want to sell 500 kg tomato, minimum price 30 rupees"
                    rows={4}
                    required
                  />
                </label>
              </div>
              <button type="submit" className="submit-button" disabled={loading}>
                {loading ? 'Finding Buyers...' : 'Find Buyers'}
              </button>
            </form>
          ) : (
            <form className="manual-form" onSubmit={handleFormSubmit}>
              <div className="form-row">
                <label>
                  Crop *
                  <select 
                    value={formData.crop} 
                    onChange={(e) => setFormData({...formData, crop: e.target.value})}
                    required
                  >
                    <option value="">Select crop</option>
                    <option value="tomato">Tomato</option>
                    <option value="potato">Potato</option>
                    <option value="onion">Onion</option>
                    <option value="rice">Rice</option>
                    <option value="wheat">Wheat</option>
                    <option value="corn">Corn</option>
                  </select>
                </label>
                <label>
                  Quantity (kg) *
                  <input 
                    type="number" 
                    value={formData.quantity}
                    onChange={(e) => setFormData({...formData, quantity: e.target.value})}
                    required
                    min="1"
                    placeholder="e.g., 500"
                  />
                </label>
              </div>
              <div className="form-row">
                <label>
                  Minimum Price (₹/kg) *
                  <input 
                    type="number" 
                    step="0.01"
                    value={formData.minimum_price}
                    onChange={(e) => setFormData({...formData, minimum_price: e.target.value})}
                    required
                    min="0"
                    placeholder="e.g., 30"
                  />
                </label>
                <label>
                  Location
                  <input 
                    type="text" 
                    value={formData.location}
                    onChange={(e) => setFormData({...formData, location: e.target.value})}
                    placeholder="Auto-filled from profile"
                  />
                </label>
              </div>
              <button type="submit" className="submit-button" disabled={loading}>
                {loading ? 'Finding Buyers...' : 'Find Buyers'}
              </button>
            </form>
          )}

          {error && (
            <div className="error-message">
              <span className="error-icon">⚠️</span>
              {error}
            </div>
          )}
        </div>
      ) : (
        <BuyerMatchDisplay 
          matchedBuyers={matchedBuyers}
          onBack={() => setMatchedBuyers(null)}
        />
      )}
    </div>
  );
}

export default FarmerInterface;
