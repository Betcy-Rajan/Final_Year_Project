import React, { useState } from 'react';
import './App.css';
import QueryInput from './components/QueryInput';
import ResponseDisplay from './components/ResponseDisplay';
import Header from './components/Header';
import RoleSelectionModal from './components/buyer-connect/RoleSelectionModal';
import BuyerDashboard from './components/buyer-connect/BuyerDashboard';
import FarmerInterface from './components/buyer-connect/FarmerInterface';

function App() {
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showBuyerConnect, setShowBuyerConnect] = useState(false);
  const [selectedRole, setSelectedRole] = useState(null);

  const handleQuery = async (query, imageFile) => {
    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      let result;

      if (imageFile) {
        // Handle query with image
        const formData = new FormData();
        formData.append('image', imageFile);
        formData.append('query', query);

        const response = await fetch('/api/query/upload', {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        result = await response.json();
      } else {
        // Handle text-only query
        const response = await fetch('/api/query', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ query }),
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        result = await response.json();
      }

      // Debug: Log the response structure
      console.log('📦 Full API Response:', result);
      console.log('🔍 Disease Output:', result.disease_agent_output);
      console.log('🔍 Price Output:', result.price_agent_output);
      console.log('🔍 Scheme Output:', result.scheme_agent_output);
      console.log('🔍 Buyer Connect Output:', result.buyer_connect_agent_output);

      setResponse(result);
    } catch (err) {
      console.error('Error processing query:', err);
      setError(err.message || 'An error occurred while processing your query. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleBuyerConnectClick = () => {
    setShowBuyerConnect(true);
    setSelectedRole(null);
  };

  const handleRoleSelect = (role) => {
    setSelectedRole(role);
    setShowBuyerConnect(false);
  };

  const handleBackToMain = () => {
    setSelectedRole(null);
    setShowBuyerConnect(false);
  };

  // If Buyer Connect is active, show the appropriate interface
  if (selectedRole) {
    return (
      <div className="App">
        <Header />
        {selectedRole === 'buyer' ? (
          <BuyerDashboard buyerId={1} onBack={handleBackToMain} />
        ) : (
          <FarmerInterface farmerId={1} onBack={handleBackToMain} />
        )}
      </div>
    );
  }

  return (
    <div className="App">
      <Header onBuyerConnectClick={handleBuyerConnectClick} />
      {showBuyerConnect && (
        <RoleSelectionModal
          onSelectRole={handleRoleSelect}
          onClose={() => setShowBuyerConnect(false)}
        />
      )}
      <div className="container">
        <QueryInput onQuery={handleQuery} loading={loading} />
        {error && (
          <div className="error-message">
            <span className="error-icon">⚠️</span>
            {error}
          </div>
        )}
        {response && <ResponseDisplay response={response} onQuery={handleQuery} />}
      </div>
    </div>
  );
}

export default App;

