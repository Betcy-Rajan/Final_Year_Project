import React from 'react';
import './ResponseDisplay.css';
import DiseaseResponse from './agent-responses/DiseaseResponse';
import PriceResponse from './agent-responses/PriceResponse';
import BuyerConnectResponse from './agent-responses/BuyerConnectResponse';
import SchemeResponse from './agent-responses/SchemeResponse';

function ResponseDisplay({ response }) {
  if (!response) return null;

  // Debug: Log what we received
  console.log('📨 ResponseDisplay received:', response);
  console.log('🔍 Checking outputs:');
  console.log('  - disease_agent_output:', response.disease_agent_output);
  console.log('  - price_agent_output:', response.price_agent_output);
  console.log('  - scheme_agent_output:', response.scheme_agent_output);
  console.log('  - buyer_connect_agent_output:', response.buyer_connect_agent_output);

  // Extract agent outputs
  const diseaseOutput = response.disease_agent_output;
  const priceOutput = response.price_agent_output;
  const buyerConnectOutput = response.buyer_connect_agent_output;
  const schemeOutput = response.scheme_agent_output;
  const coordinatorOutput = response.coordinator_output;
  const finalResponse = response.final_response;
  const reasonerOutput = response.reasoner_output;
  
  // Check if reasoner_output is nested
  let intent = [];
  if (reasonerOutput) {
    if (typeof reasonerOutput === 'object') {
      intent = reasonerOutput.intent || reasonerOutput.reasoner_output?.intent || [];
    }
  }

  // Determine which agents were activated
  const activeAgents = [];
  if (diseaseOutput) activeAgents.push('disease');
  if (priceOutput) activeAgents.push('price');
  if (buyerConnectOutput) activeAgents.push('buyer_connect');
  if (schemeOutput) activeAgents.push('scheme');

  return (
    <div className="response-display">
      {(reasonerOutput || intent.length > 0) && (
        <div className="reasoner-info">
          <div className="info-badge">
            <span className="badge-icon">🤖</span>
            Intent Detected: {intent.length > 0 ? intent.join(', ') : (reasonerOutput?.intent?.join(', ') || reasonerOutput?.reasoner_output?.intent?.join(', ') || 'General Query')}
          </div>
        </div>
      )}

      {activeAgents.length > 0 && (
        <div className="agents-summary">
          <p className="summary-text">
            Analyzing with {activeAgents.length} specialist{activeAgents.length > 1 ? 's' : ''}:
            {' '}
            {activeAgents.map(agent => {
              const names = {
                disease: 'Disease Diagnosis',
                price: 'Market Price',
                buyer_connect: 'Buyer Connect',
                scheme: 'Government Schemes'
              };
              return names[agent] || agent;
            }).join(', ')}
          </p>
        </div>
      )}

      <div className="agent-responses">
        {diseaseOutput && (
          <DiseaseResponse output={diseaseOutput} />
        )}

        {priceOutput && (
          <PriceResponse output={priceOutput} />
        )}

        {buyerConnectOutput && (
          <BuyerConnectResponse output={buyerConnectOutput} />
        )}

        {schemeOutput && (
          <SchemeResponse output={schemeOutput} />
        )}
      </div>

      {finalResponse && (
        <div className="final-response">
          <h3 className="final-response-title">
            <span className="title-icon">💡</span>
            Summary & Recommendations
          </h3>
          <div className="final-response-content">
            {finalResponse}
          </div>
        </div>
      )}

      {coordinatorOutput && !finalResponse && (
        <div className="final-response">
          <h3 className="final-response-title">
            <span className="title-icon">💡</span>
            Response
          </h3>
          <div className="final-response-content">
            {typeof coordinatorOutput === 'string' 
              ? coordinatorOutput 
              : JSON.stringify(coordinatorOutput, null, 2)}
          </div>
        </div>
      )}
    </div>
  );
}

export default ResponseDisplay;

