import React from 'react';
import './AgentResponse.css';

function PriceResponse({ output }) {
  if (!output) return null;

  const priceInfo = output.price_info || {};
  const currentPrice = priceInfo.current_price || priceInfo.price || null;
  const unit = priceInfo.unit || 'per kg';
  const trend = priceInfo.trend || priceInfo.price_trend || 'stable';
  const marketLocation = priceInfo.market || priceInfo.location || '';
  const priceChange = priceInfo.price_change || null;
  const recommendation = priceInfo.recommendation || priceInfo.suggestion || null;
  const crop = priceInfo.crop || '';

  // Format price
  const formattedPrice = currentPrice ? `₹${currentPrice.toFixed(2)}` : 'N/A';

  // Determine trend icon and color
  const getTrendInfo = () => {
    if (trend.toLowerCase().includes('up') || trend.toLowerCase().includes('rising') || trend.toLowerCase().includes('increase')) {
      return { icon: '📈', color: '#e74c3c', text: 'Rising' };
    } else if (trend.toLowerCase().includes('down') || trend.toLowerCase().includes('falling') || trend.toLowerCase().includes('decrease')) {
      return { icon: '📉', color: '#3498db', text: 'Falling' };
    }
    return { icon: '➡️', color: '#95a5a6', text: 'Stable' };
  };

  const trendInfo = getTrendInfo();

  return (
    <div className="agent-response price-response">
      <div className="response-header">
        <div className="header-icon">💰</div>
        <div>
          <h3>Market Price Information</h3>
          <p className="header-subtitle">Current Market Rates & Trends</p>
        </div>
      </div>

      <div className="response-content">
        <div className="price-card-main">
          <div className="price-display">
            <div className="price-label">Current Price</div>
            <div className="price-value">{formattedPrice}</div>
            <div className="price-unit">{unit}</div>
          </div>

          <div className="trend-display">
            <span className="trend-icon" style={{ color: trendInfo.color }}>
              {trendInfo.icon}
            </span>
            <span className="trend-text" style={{ color: trendInfo.color }}>
              {trendInfo.text}
            </span>
            {priceChange && (
              <span className="price-change" style={{ color: trendInfo.color }}>
                ({priceChange > 0 ? '+' : ''}{priceChange}%)
              </span>
            )}
          </div>
        </div>

        {marketLocation && (
          <div className="market-info">
            <span className="info-label">📍 Market:</span>
            <span className="info-value">{marketLocation}</span>
          </div>
        )}

        {recommendation && (
          <div className="recommendation-card">
            <h5 className="section-title">💡 Trading Recommendation:</h5>
            <p className="recommendation-text">{recommendation}</p>
          </div>
        )}

        {priceInfo.historical_data && (
          <div className="historical-card">
            <h5 className="section-title">📊 Price History:</h5>
            <div className="historical-data">
              {Array.isArray(priceInfo.historical_data) ? (
                <ul className="historical-list">
                  {priceInfo.historical_data.slice(0, 5).map((item, idx) => (
                    <li key={idx}>
                      {item.date || item.day}: ₹{item.price}
                    </li>
                  ))}
                </ul>
              ) : (
                <p>{JSON.stringify(priceInfo.historical_data)}</p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default PriceResponse;

