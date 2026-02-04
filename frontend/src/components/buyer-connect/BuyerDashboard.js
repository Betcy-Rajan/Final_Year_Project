import React, { useState, useEffect } from 'react';
import './BuyerDashboard.css';

function BuyerDashboard({ buyerId = 1, onBack }) {
  const [requirements, setRequirements] = useState([]);
  const [incomingOffers, setIncomingOffers] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    crop: '',
    required_quantity: '',
    max_price: '',
    location: '',
    valid_till: ''
  });
  const [editingRequirement, setEditingRequirement] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadRequirements();
    loadIncomingOffers();
  }, [buyerId]);

  const loadRequirements = async () => {
    try {
      const response = await fetch(`/api/buyer-connect/buyer-requirements?buyer_id=${buyerId}`);
      if (response.ok) {
        const data = await response.json();
        setRequirements(data);
      }
    } catch (error) {
      console.error('Error loading requirements:', error);
    }
  };

  const loadIncomingOffers = async () => {
    try {
      const response = await fetch(`/api/buyer-connect/negotiations/buyer/${buyerId}`);
      if (response.ok) {
        const data = await response.json();
        setIncomingOffers(data.filter(n => !n.decision || n.decision === 'pending'));
      }
    } catch (error) {
      console.error('Error loading offers:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const requirementData = {
        ...formData,
        buyer_id: buyerId,
        required_quantity: parseFloat(formData.required_quantity),
        max_price: parseFloat(formData.max_price)
      };

      if (editingRequirement) {
        requirementData.id = editingRequirement.id;
      }

      const response = await fetch('/api/buyer-connect/buyer-requirements', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requirementData)
      });

      if (response.ok) {
        await loadRequirements();
        setShowForm(false);
        setFormData({
          crop: '',
          required_quantity: '',
          max_price: '',
          location: '',
          valid_till: ''
        });
        setEditingRequirement(null);
      }
    } catch (error) {
      console.error('Error saving requirement:', error);
      alert('Error saving requirement. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (requirement) => {
    setEditingRequirement(requirement);
    setFormData({
      crop: requirement.crop,
      required_quantity: requirement.required_quantity.toString(),
      max_price: requirement.max_price.toString(),
      location: requirement.location,
      valid_till: requirement.valid_till.split('T')[0] // Extract date part
    });
    setShowForm(true);
  };

  const handleDelete = async (requirementId) => {
    if (!window.confirm('Are you sure you want to delete this requirement?')) return;
    
    try {
      const response = await fetch(`/api/buyer-connect/buyer-requirements/${requirementId}`, {
        method: 'DELETE'
      });
      if (response.ok) {
        await loadRequirements();
      }
    } catch (error) {
      console.error('Error deleting requirement:', error);
    }
  };

  const handleOfferAction = async (negotiationId, action) => {
    try {
      const response = await fetch(`/api/buyer-connect/negotiations/${negotiationId}/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision: action })
      });
      if (response.ok) {
        await loadIncomingOffers();
      }
    } catch (error) {
      console.error('Error updating offer:', error);
    }
  };

  return (
    <div className="buyer-dashboard">
      <div className="dashboard-header">
        <button className="back-button" onClick={onBack}>← Back</button>
        <h1>Buyer Dashboard</h1>
      </div>

      <div className="dashboard-content">
        <div className="section">
          <div className="section-header">
            <h2>My Requirements</h2>
            <button 
              className="add-button"
              onClick={() => {
                setShowForm(!showForm);
                setEditingRequirement(null);
                setFormData({
                  crop: '',
                  required_quantity: '',
                  max_price: '',
                  location: '',
                  valid_till: ''
                });
              }}
            >
              {showForm ? 'Cancel' : '+ Add Requirement'}
            </button>
          </div>

          {showForm && (
            <form className="requirement-form" onSubmit={handleSubmit}>
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
                  Required Quantity (kg) *
                  <input 
                    type="number" 
                    value={formData.required_quantity}
                    onChange={(e) => setFormData({...formData, required_quantity: e.target.value})}
                    required
                    min="1"
                  />
                </label>
              </div>
              <div className="form-row">
                <label>
                  Maximum Price (₹/kg) *
                  <input 
                    type="number" 
                    step="0.01"
                    value={formData.max_price}
                    onChange={(e) => setFormData({...formData, max_price: e.target.value})}
                    required
                    min="0"
                  />
                </label>
                <label>
                  Location *
                  <input 
                    type="text" 
                    value={formData.location}
                    onChange={(e) => setFormData({...formData, location: e.target.value})}
                    required
                    placeholder="City/District"
                  />
                </label>
              </div>
              <div className="form-row">
                <label>
                  Validity Period *
                  <input 
                    type="date" 
                    value={formData.valid_till}
                    onChange={(e) => setFormData({...formData, valid_till: e.target.value})}
                    required
                    min={new Date().toISOString().split('T')[0]}
                  />
                </label>
              </div>
              <button type="submit" className="submit-button" disabled={loading}>
                {loading ? 'Saving...' : editingRequirement ? 'Update Requirement' : 'Save Requirement'}
              </button>
            </form>
          )}

          <div className="requirements-list">
            {requirements.length === 0 ? (
              <p className="empty-state">No requirements yet. Add one to get started!</p>
            ) : (
              requirements.map(req => (
                <div key={req.id} className="requirement-card">
                  <div className="requirement-info">
                    <h3>{req.crop.charAt(0).toUpperCase() + req.crop.slice(1)}</h3>
                    <p><strong>Quantity:</strong> {req.required_quantity} kg</p>
                    <p><strong>Max Price:</strong> ₹{req.max_price}/kg</p>
                    <p><strong>Location:</strong> {req.location}</p>
                    <p><strong>Valid Till:</strong> {new Date(req.valid_till).toLocaleDateString()}</p>
                  </div>
                  <div className="requirement-actions">
                    <button onClick={() => handleEdit(req)}>Edit</button>
                    <button onClick={() => handleDelete(req.id)} className="delete-button">Delete</button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="section">
          <h2>Incoming Farmer Offers</h2>
          <div className="offers-list">
            {incomingOffers.length === 0 ? (
              <p className="empty-state">No incoming offers yet.</p>
            ) : (
              incomingOffers.map(offer => (
                <div key={offer.id} className="offer-card">
                  <div className="offer-info">
                    <h3>Listing #{offer.listing_id}</h3>
                    {offer.ai_suggested_price && (
                      <p className="ai-price">
                        <strong>AI Suggested Price:</strong> ₹{offer.ai_suggested_price.toFixed(2)}/kg
                      </p>
                    )}
                    <p className="explanation">{offer.explanation}</p>
                    {offer.benchmark_price && (
                      <p><strong>Market Benchmark:</strong> ₹{offer.benchmark_price.toFixed(2)}/kg</p>
                    )}
                  </div>
                  <div className="offer-actions">
                    <button 
                      onClick={() => handleOfferAction(offer.id, 'accept')}
                      className="accept-button"
                    >
                      Accept
                    </button>
                    <button 
                      onClick={() => handleOfferAction(offer.id, 'counter')}
                      className="counter-button"
                    >
                      Counter
                    </button>
                    <button 
                      onClick={() => handleOfferAction(offer.id, 'reject')}
                      className="reject-button"
                    >
                      Reject
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default BuyerDashboard;
