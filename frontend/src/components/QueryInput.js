import React, { useState } from 'react';
import './QueryInput.css';

function QueryInput({ onQuery, loading }) {
  const [query, setQuery] = useState('');
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim() || imageFile) {
      onQuery(query.trim(), imageFile);
      setQuery('');
      setImageFile(null);
      setImagePreview(null);
    }
  };

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setImageFile(file);
      // Create preview
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const removeImage = () => {
    setImageFile(null);
    setImagePreview(null);
  };

  return (
    <div className="query-input-container">
      <form onSubmit={handleSubmit} className="query-form">
        <div className="input-wrapper">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask me anything about farming... e.g., 'My tomato leaves have yellow spots' or 'What's the price of rice?'"
            className="query-textarea"
            rows="3"
            disabled={loading}
          />
          <div className="image-upload-section">
            <label htmlFor="image-upload" className="image-upload-label">
              📷 Upload Image
            </label>
            <input
              id="image-upload"
              type="file"
              accept="image/*"
              onChange={handleImageChange}
              className="image-input"
              disabled={loading}
            />
            {imagePreview && (
              <div className="image-preview">
                <img src={imagePreview} alt="Preview" />
                <button
                  type="button"
                  onClick={removeImage}
                  className="remove-image-btn"
                >
                  ✕
                </button>
              </div>
            )}
          </div>
        </div>
        <button
          type="submit"
          className="submit-btn"
          disabled={loading || (!query.trim() && !imageFile)}
        >
          {loading ? (
            <>
              <span className="spinner"></span>
              Processing...
            </>
          ) : (
            <>
              <span>🔍</span>
              Ask AgriMitra
            </>
          )}
        </button>
      </form>
      
      <div className="example-queries">
        <p className="examples-title">Try these examples:</p>
        <div className="example-chips">
          <button
            type="button"
            className="example-chip"
            onClick={() => setQuery("My tomato leaves have yellow spots")}
            disabled={loading}
          >
            Disease Diagnosis
          </button>
          <button
            type="button"
            className="example-chip"
            onClick={() => setQuery("What's the current price of rice?")}
            disabled={loading}
          >
            Market Price
          </button>
          <button
            type="button"
            className="example-chip"
            onClick={() => setQuery("I want to sell my tomato crop")}
            disabled={loading}
          >
            Find Buyers
          </button>
          <button
            type="button"
            className="example-chip"
            onClick={() => setQuery("Show me agricultural schemes in Maharashtra")}
            disabled={loading}
          >
            Government Schemes
          </button>
        </div>
      </div>
    </div>
  );
}

export default QueryInput;

