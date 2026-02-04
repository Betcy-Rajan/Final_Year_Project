import React from 'react';
import './AgentResponse.css';

function DiseaseResponse({ output }) {
  if (!output) return null;

  const diseaseInfo = output.disease_info || {};
  const remedy = output.remedy || output.remedy_info || {};
  const identifiedDisease = diseaseInfo.identified_disease || diseaseInfo.disease || 'Unknown Disease';
  const confidence = diseaseInfo.confidence || diseaseInfo.confidence_score || null;
  const symptoms = diseaseInfo.symptoms || [];
  const description = diseaseInfo.description || '';
  const treatments = remedy.treatments || [];
  const prevention = remedy.prevention || [];
  const imageNote = output.image_processing_note || null;

  // Check if this is an error case (CNN not available)
  const isError = identifiedDisease === "Image Analysis Unavailable" || (imageNote && imageNote.cnn_unavailable);

  return (
    <div className="agent-response disease-response">
      <div className="response-header">
        <div className="header-icon">🦠</div>
        <div>
          <h3>Disease Diagnosis</h3>
          <p className="header-subtitle">Plant Health Analysis</p>
        </div>
      </div>

      <div className="response-content">
        {imageNote && imageNote.cnn_unavailable && (
          <div className="error-notice" style={{
            backgroundColor: '#fff3cd',
            border: '1px solid #ffc107',
            borderRadius: '8px',
            padding: '16px',
            marginBottom: '16px',
            color: '#856404'
          }}>
            <strong>⚠️ Image Processing Unavailable</strong>
            <p style={{ marginTop: '8px', marginBottom: 0 }}>
              {imageNote.message || 'Image-based disease detection requires TensorFlow. Please install it: pip install tensorflow>=2.13.0'}
            </p>
            {imageNote.fallback_to_text && (
              <p style={{ marginTop: '8px', marginBottom: 0, fontSize: '0.9em' }}>
                Falling back to text-based diagnosis based on your query.
              </p>
            )}
          </div>
        )}

        <div className="disease-card">
          <div className="disease-title-section">
            <h4 className="disease-name">{identifiedDisease}</h4>
            {confidence && typeof confidence === 'number' && confidence > 0 && (
              <span className="confidence-badge">
                {Math.round(confidence * 100)}% Confidence
              </span>
            )}
            {typeof confidence === 'string' && confidence !== 'low' && (
              <span className="confidence-badge">
                {confidence.charAt(0).toUpperCase() + confidence.slice(1)} Confidence
              </span>
            )}
          </div>

          {description && (
            <p className="disease-description">{description}</p>
          )}

          {symptoms.length > 0 && (
            <div className="symptoms-section">
              <h5 className="section-title">🔍 Symptoms Identified:</h5>
              <ul className="symptoms-list">
                {symptoms.map((symptom, idx) => (
                  <li key={idx}>{symptom}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {treatments.length > 0 && (
          <div className="treatments-card">
            <h5 className="section-title">💊 Recommended Treatments:</h5>
            <div className="treatments-list">
              {treatments.map((treatment, idx) => (
                <div key={idx} className="treatment-item">
                  <span className="treatment-number">{idx + 1}</span>
                  <div className="treatment-content">
                    {typeof treatment === 'string' ? (
                      <p>{treatment}</p>
                    ) : (
                      <>
                        {treatment.name && <strong>{treatment.name}</strong>}
                        {treatment.description && <p>{treatment.description}</p>}
                        {treatment.dosage && <p className="dosage">Dosage: {treatment.dosage}</p>}
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {prevention.length > 0 && (
          <div className="prevention-card">
            <h5 className="section-title">🛡️ Prevention Tips:</h5>
            <ul className="prevention-list">
              {prevention.map((tip, idx) => (
                <li key={idx}>{tip}</li>
              ))}
            </ul>
          </div>
        )}

        {output.shop_info && (
          <div className="shop-info-card">
            <h5 className="section-title">🏪 Nearby Fertilizer Shops:</h5>
            <p className="shop-info">{output.shop_info}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default DiseaseResponse;

