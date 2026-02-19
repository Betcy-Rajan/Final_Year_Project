import React, { useState, useEffect } from 'react';
import './AgentResponse.css';

// Enhanced Markdown Parser Helper
function parseMarkdown(md) {
  if (!md) return {};
  const sections = {};
  const lines = md.split('\n');
  let currentSection = 'intro';
  sections[currentSection] = [];

  // Helper to normalize section titles
  const normalizeTitle = (t) => t.trim().toLowerCase().replace(/[^a-z0-9]/g, '');

  lines.forEach(line => {
    // Match headers like ## What is Apple Scab? or ### Immediate Actions
    const headerMatch = line.match(/^(#{2,})\s+(?:(\d+)\.\s+)?(.+)/);

    if (headerMatch) {
      const rawTitle = headerMatch[3];
      const title = normalizeTitle(rawTitle);

      if (title.includes('whatis') || title.includes('description') || title.includes('symptoms')) currentSection = 'description';
      else if (title.includes('immediate') || title.includes('actions') || title.includes('Recommended Actions') || title.includes('treatment')) currentSection = 'immediate';
      else if (title.includes('fungicide') || title.includes('recommendation')) currentSection = 'fungicides'; // New section for fungicides
      else if (title.includes('prevention') || title.includes('preventive')) currentSection = 'prevention';
      else if (title.includes('shop') || title.includes('store') || title.includes('nearby')) currentSection = 'shops';
      else if (title.includes('nextsteps') || title.includes('checklist') || title.includes('bottomline')) currentSection = 'checklist';
      else currentSection = 'other';

      sections[currentSection] = [];
    } else {
      // Push line to current section if it's not empty or just a separator
      if (line.trim() && !line.match(/^[-*]{3,}$/)) {
        sections[currentSection].push(line);
      }
    }
  });
  return sections;
}

// Utility to clean markdown characters
const cleanText = (text) => {
  if (!text) return "";
  return text
    .replace(/\*\*/g, "") // Remove double asterisks
    .replace(/\*/g, "")   // Remove single asterisks
    .replace(/__/g, "")   // Remove double underscores
    .replace(/_/g, " ")   // Replace single underscores with space (better readability for snake_case)
    .replace(/`/g, "")    // Remove backticks
    .trim();
};

function DiseaseResponse({ output, finalMarkdown }) {
  const [checklist, setChecklist] = useState({});
  const [isPreventiveExpanded, setIsPreventiveExpanded] = useState(false);
  const [parsedContent, setParsedContent] = useState(null);

  // --- Text-to-Speech Logic (Moved Up) ---
  const [speakingSection, setSpeakingSection] = useState(null);
  const [synth, setSynth] = useState(window.speechSynthesis);

  useEffect(() => {
    // Cleanup speech on unmount
    return () => {
      if (synth) {
        synth.cancel();
      }
    };
  }, [synth]);

  const stopSpeaking = () => {
    if (synth) {
      synth.cancel();
      setSpeakingSection(null);
    }
  };

  const speak = (text, section) => {
    if (!synth) return;

    // If currently speaking this section, stop it
    if (speakingSection === section) {
      stopSpeaking();
      return;
    }

    // Stop any other speech
    synth.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.9;
    utterance.pitch = 1;

    const voices = synth.getVoices();
    const preferredVoice = voices.find(v => v.lang.includes('en-IN')) || voices.find(v => v.lang.includes('en-US'));
    if (preferredVoice) utterance.voice = preferredVoice;

    utterance.onstart = () => setSpeakingSection(section);
    utterance.onend = () => setSpeakingSection(null);
    utterance.onerror = () => setSpeakingSection(null);

    synth.speak(utterance);
  };

  useEffect(() => {
    if (finalMarkdown) {
      const sections = parseMarkdown(finalMarkdown);
      setParsedContent(sections);
    }
  }, [finalMarkdown]);

  if (!output) return null;

  // --- Data Extraction Strategies ---
  const diseaseInfo = output.disease_info || {};
  const diagnosis = output.disease_diagnosis || {};
  const remedyInfo = output.remedy_info || {};
  const shopsInfo = output.shops_info || {};
  const imageNote = output.image_processing_note || {};
  const detectionMethod = output.detection_method;

  // 1. Diagnosis Information
  const identifiedDisease = diseaseInfo.identified_disease || diseaseInfo.disease || "Unknown Disease";
  const confidence = diseaseInfo.confidence_score || (diseaseInfo.confidence === 'high' ? 0.8 : 0.5);
  const confidencePercent = confidence ? (confidence * 100).toFixed(0) + '%' : 'N/A';
  const isHealthy = (identifiedDisease && identifiedDisease.toLowerCase().includes("healthy")) || output.disease_diagnosis?.is_healthy;

  // Description Logic
  let description = "Analysis complete.";
  if (parsedContent?.description?.length > 0) {
    // Join lines and clean up markdown
    description = cleanText(parsedContent.description.join(' '));
  } else if (diseaseInfo.description) {
    description = cleanText(diseaseInfo.description);
  } else if (diagnosis.explanation) {
    description = cleanText(diagnosis.explanation);
  }

  // 2. Immediate Actions Extraction
  // We need to handle both Markdown Tables and simple lists
  let immediateActions = [];

  if (parsedContent?.immediate?.length > 0) {
    const rawLines = parsedContent.immediate;

    // Check for Table format (lines starting with |)
    const tableRows = rawLines.filter(line => line.trim().startsWith('|'));

    if (tableRows.length > 0) {
      // We assume valid rows don't contain "---" (separator lines)
      // And we skip the header row if it contains "Step" or "What to Do"
      const validRows = tableRows.filter(row => !row.includes('---') && !row.toLowerCase().includes('what to do'));

      immediateActions = validRows.map(row => {
        // Split by pipe and trim white space
        // Example: | **1. Inspect** | Look for lesions | Early detection |
        const cells = row.split('|').map(c => c.trim()).filter(c => c.length > 0);

        if (cells.length >= 2) {
          // Usually Cell 0 is "Step/Action", Cell 1 is "Detail", Cell 2 is "Why"
          // Let's combine them nicely
          const action = cleanText(cells[0]);
          const detail = cleanText(cells[1] || '');
          const why = cells[2] ? ` (${cleanText(cells[2])})` : '';

          // If action is just a number/bold header, and detail is the real text
          if (action.match(/^\d+/) || action.length < 20) {
            return `${action}: ${detail}${why}`;
          }
          return `${action} - ${detail}${why}`;
        }
        return cleanText(row.replace(/\|/g, ''));
      });
    } else {
      // Fallback to List format
      immediateActions = rawLines
        .filter(line => line.trim().match(/^[-*]\s/) || line.trim().match(/^\d+\.\s/))
        .map(line => cleanText(line.replace(/^[-*]\s/, '').replace(/^\d+\.\s/, '')));
    }
  }

  // Fallback to structured data if nothing parsed
  if (immediateActions.length === 0) {
    if (remedyInfo.steps && Array.isArray(remedyInfo.steps)) {
      immediateActions.push(...remedyInfo.steps.map(cleanText));
    }
    if (remedyInfo.chemical_control) {
      const acts = Array.isArray(remedyInfo.chemical_control) ? remedyInfo.chemical_control : [remedyInfo.chemical_control];
      immediateActions.push(...acts.map(cleanText));
    }
    if (remedyInfo.biological_control) {
      const acts = Array.isArray(remedyInfo.biological_control) ? remedyInfo.biological_control : [remedyInfo.biological_control];
      immediateActions.push(...acts.map(cleanText));
    }
  }

  // 3. Fungicide Recommendations (New Section handling)
  let fungicides = [];
  if (parsedContent?.fungicides?.length > 0) {
    const rawLines = parsedContent.fungicides;
    const tableRows = rawLines.filter(line => line.trim().startsWith('|'));

    if (tableRows.length > 0) {
      const validRows = tableRows.filter(row => !row.includes('---') && !row.toLowerCase().includes('typical dose'));
      fungicides = validRows.map(row => {
        const cells = row.split('|').map(c => c.trim()).filter(c => c);
        // Cell 0: Name, Cell 1: Dose, Cell 2: Freq
        const name = cleanText(cells[0] || '');
        const dose = cleanText(cells[1] || '');
        return `${name}: ${dose}`;
      });
    } else {
      fungicides = rawLines.filter(l => l.trim().length > 0 && !l.startsWith('>')).map(cleanText);
    }
  }

  // Fallback for fungicides using remedy_name
  if (fungicides.length === 0 && remedyInfo.remedy_name) {
    fungicides.push(cleanText(remedyInfo.remedy_name));
  }

  // 4. Prevention Extraction
  let preventiveCare = [];
  if (parsedContent?.prevention?.length > 0) {
    preventiveCare = parsedContent.prevention
      .filter(line => line.trim().match(/^[-*]\s/))
      .map(line => cleanText(line.replace(/^[-*]\s/, '')));
  } else if (remedyInfo.prevention) {
    const prev = Array.isArray(remedyInfo.prevention) ? remedyInfo.prevention : [remedyInfo.prevention];
    preventiveCare.push(...prev.map(cleanText));
  } else if (remedyInfo.cultural_control) {
    // sometimes prevention is under cultural control
    const prev = Array.isArray(remedyInfo.cultural_control) ? remedyInfo.cultural_control : [remedyInfo.cultural_control];
    preventiveCare.push(...prev.map(cleanText));
  }

  // Fallback for preventive care from immediate actions (heuristic)
  if (preventiveCare.length === 0 && immediateActions.length > 0) {
    const preventionKeywords = ['avoid', 'improve', 'remove', 'clean', 'rotate', 'space', 'ensure', 'maintain', 'manage', 'monitor'];
    const pSteps = immediateActions.filter(action =>
      preventionKeywords.some(keyword => action.toLowerCase().includes(keyword))
    );
    if (pSteps.length > 0) {
      preventiveCare.push(...pSteps);
    }
  }

  // 5. Checklist / Next Steps Extraction
  let nextSteps = [];
  if (parsedContent?.checklist?.length > 0) {
    nextSteps = parsedContent.checklist.filter(l => l.trim().length > 0).map(cleanText);
  } else {
    // Generate default checklist based on diagnosis
    if (!isHealthy) {
      nextSteps.push(cleanText(`Confirm diagnosis of ${identifiedDisease}`));
      if (immediateActions.length > 0) nextSteps.push("Apply immediate treatment measures");
      nextSteps.push("Monitor plant for 3-5 days");
      nextSteps.push("Visit local agro-shop if symptoms persist");
    } else {
      nextSteps.push("Continue regular watering schedule");
      nextSteps.push("Monitor for any changes");
    }
  }




  // Prepare text for sections
  const diagnosisText = `Diagnosis Report. ${isHealthy ? "Healthy Plant Detected." : "Disease Detected: " + identifiedDisease}. Confidence: ${confidencePercent}. ${description.substring(0, 150)}`;

  const immediateActionsText = `Immediate Actions. ${immediateActions.map((action, idx) => `Step ${idx + 1}. ${action.replace(/\*/g, '')}`).join('. ')}`;

  const preventiveText = `Preventive Care. ${preventiveCare.map(item => item.replace(/\*/g, '')).join('. ')}`;

  const summaryText = `Summary. ${nextSteps.join('. ')}`;


  return (
    <div className="agent-response disease-response-container fade-in">

      {/* 1. Diagnosis Card */}
      <div className={`summary-card disease-diagnosis-card ${isHealthy ? 'status-healthy' : 'status-alert'}`}>
        <div className="card-top card-top-no-style">
          <div className="response-header" style={{ justifyContent: 'space-between', width: '100%' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <span className="agent-icon is-large">{isHealthy ? '✅' : '🚨'}</span>
              <div className="header-text">
                <h4 className={`header-text-color ${isHealthy ? 'healthy-color' : 'alert-color'} font-size-1-2rem`}>
                  {isHealthy ? "Healthy Plant Detected" : "Disease Detected"}
                </h4>
                <span className={`confidence-badge ${confidence > 0.8 ? 'high' : 'medium'}`}>
                  {confidencePercent} Confidence
                </span>
              </div>
            </div>
            <button
              className={`btn-audio-control ${speakingSection === 'diagnosis' ? 'playing' : ''}`}
              onClick={() => speak(diagnosisText, 'diagnosis')}
              title={speakingSection === 'diagnosis' ? "Stop Reading" : "Read Diagnosis"}
            >
              {speakingSection === 'diagnosis' ? '⏹️' : '🔊'}
            </button>
          </div>
          <div className="diagnosis-main margin-top-1rem">
            <h2 className="disease-name font-size-1-5rem margin-bottom-0-5rem">{identifiedDisease}</h2>
            {diseaseInfo.crop && <span className="crop-tag crop-tag-style">Crop: {diseaseInfo.crop}</span>}

            {/* Description Render */}
            <p className="diagnosis-description margin-top-0-75rem font-size-1rem line-height-1-6">
              {description}
            </p>

            {detectionMethod === 'CNN' && (
              <div className="detection-method-tag margin-top-0-5rem font-size-0-8rem text-color-666">
                📸 Analyzed via Image
              </div>
            )}

            {imageNote.cnn_unavailable && (
              <div className="note-box info note-box-info-style">
                <span className="note-icon">ℹ️</span>
                <span>Image analysis unavailable. Diagnosis based on text description.</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 2. Immediate Actions Card (Enhanced with Tables Support) */}
      {!isHealthy && immediateActions.length > 0 && (
        <div className="summary-card immediate-actions-card margin-top-1-5rem border-left-orange">
          <div className="card-top">
            <div className="response-header" style={{ justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span className="agent-icon">⚡</span>
                <h4>Immediate Actions</h4>
              </div>
              <button
                className={`btn-audio-control ${speakingSection === 'actions' ? 'playing' : ''}`}
                onClick={() => speak(immediateActionsText, 'actions')}
                title="Read Actions"
              >
                {speakingSection === 'actions' ? '⏹️' : '🔊'}
              </button>
            </div>
          </div>
          <div className="card-body">
            <div className="visual-stepper">
              {immediateActions.map((action, idx) => (
                <div key={idx} className="stepper-step">
                  <div className="step-circle">{idx + 1}</div>
                  <div className="step-info">
                    <h5>Step {idx + 1}</h5>
                    <p>{action}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 2.1 Fungicides Card (If detected) */}
      {!isHealthy && fungicides.length > 0 && (
        <div className="summary-card fungicide-card margin-top-1-5rem border-left-brown background-efebe9">
          <div className="card-top">
            <div className="response-header">
              <span className="agent-icon">💊</span>
              <h4>Recommended Fungicides</h4>
            </div>
          </div>
          <div className="card-body card-body-padding-0-1rem">
            <ul className="checklist-list">
              {fungicides.map((f, i) => (
                <li key={i} className="checklist-item align-items-center">
                  <span className="check-icon check-icon-brown">•</span>
                  <span>{f}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* 3. Preventive Care Card */}
      {(preventiveCare.length > 0 || isHealthy) && (
        <div className="summary-card preventive-card margin-top-1-5rem border-left-blue background-f5f5f5">
          <div className="card-top card-top-clickable">
            <div className="response-header" style={{ flexGrow: 1 }} onClick={() => setIsPreventiveExpanded(!isPreventiveExpanded)}>
              <span className="agent-icon">🛡️</span>
              <h4>Preventive Care {isHealthy && "& Maintenance"}</h4>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <button
                className={`btn-audio-control ${speakingSection === 'prevention' ? 'playing' : ''}`}
                onClick={(e) => { e.stopPropagation(); speak(preventiveText, 'prevention'); }}
                title="Read Prevention"
              >
                {speakingSection === 'prevention' ? '⏹️' : '🔊'}
              </button>
              <span className={`toggle-icon ${isPreventiveExpanded ? 'expanded' : ''}`} onClick={() => setIsPreventiveExpanded(!isPreventiveExpanded)}>▼</span>
            </div>
          </div>
          {isPreventiveExpanded && (
            <div className="card-body slide-down-animation">
              <ul className="checklist-list">
                {preventiveCare.map((item, i) => (
                  <li key={i} className="checklist-item">
                    <span className="check-icon check-icon-blue">•</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* 4. Nearby Shops Card */}
      {/* 4. Nearby Shops Card -- Always shown if disease detected */}
      {!isHealthy && (
        <div className="summary-card shops-card-container margin-top-1-5rem border-left-teal">
          <div className="card-top">
            <div className="response-header">
              <span className="agent-icon">🏪</span>
              <h4>Nearby Agro-Input Shops</h4>
            </div>
          </div>
          <div className="card-body">

            {/* Show Specific Results if Available */}
            {shopsInfo && shopsInfo.results ? (
              <>
                {shopsInfo.location && (
                  <p className="shop-location-info">
                    Radius: 20km around <strong>{shopsInfo.location.display_name || "Current Location"}</strong>
                  </p>
                )}

                {/* Shops Grid Logic */}
                {shopsInfo.results.shops ? (
                  <div className="shops-grid shops-grid-auto-fill margin-bottom-1rem">
                    {shopsInfo.results.shops.map((shop, idx) => (
                      <div key={idx} className="shop-card shop-card-style">
                        <strong className="shop-type-strong">{shop.type}</strong>
                        <a href={shop.url} target="_blank" rel="noopener noreferrer" className="btn-link btn-link-shop">
                          📍 Open map
                        </a>
                      </div>
                    ))}
                  </div>
                ) : (Array.isArray(shopsInfo.results) && shopsInfo.results.length > 0) ? (
                  <div className="shops-grid shops-grid-auto-fill-250 margin-bottom-1rem">
                    {shopsInfo.results.slice(0, 3).map((shop, idx) => (
                      <div key={idx} className="shop-card shop-card-style">
                        <strong className="shop-name-strong">{shop.name || shop.type || "Shop"}</strong>
                        <p className="shop-address-p">{shop.vicinity || shop.address || "Nearby"}</p>
                        <a href={shop.url || `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent((shop.name || '') + ' ' + (shop.vicinity || ''))}`} target="_blank" rel="noopener noreferrer" className="btn-link btn-link-shop-view">
                          📍 View on Maps
                        </a>
                      </div>
                    ))}
                  </div>
                ) : null}
              </>
            ) : (
              <p className="no-shop-links-p" style={{ marginBottom: '1rem' }}>
                Find authorized agricultural inputs and verified treatment centers near you.
              </p>
            )}

            {/* Always Show Action Buttons */}
            <div className="shops-action-buttons" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>

              {/* <a
                href={`https://www.google.com/maps/search/${identifiedDisease.replace(' ', '+')}+treatment+shops+near+me`}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-view-details-full btn-view-details-full-style"
                style={{ textAlign: 'center' }}
              >
                🔍 Find {identifiedDisease} Treatment Shops
              </a> */}

              <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                <a
                  href="https://www.google.com/maps/search/Agro+Chemical+Shop+near+me"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-secondary-action"
                  style={{ flex: 1, textAlign: 'center', justifyContent: 'center', minWidth: '150px' }}
                >
                  🏪 General Agro Shops
                </a>
                <a
                  href="https://www.google.com/maps/search/Organic+Fertilizer+Shop+near+me"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-secondary-action"
                  style={{ flex: 1, textAlign: 'center', justifyContent: 'center', minWidth: '150px' }}
                >
                  🌱 Organic Inputs
                </a>
              </div>
            </div>

          </div>
        </div>
      )}

      {/* 5. Summary / Bottom Line */}
      {nextSteps.length > 0 && (
        <div className="summary-card checklist-summary-card margin-top-1-5rem border-left-gray">
          <div className="card-top">
            <div className="response-header" style={{ justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span className="agent-icon">📝</span>
                <h4>Summary & Next Steps</h4>
              </div>
              <button
                className={`btn-audio-control ${speakingSection === 'summary' ? 'playing' : ''}`}
                onClick={() => speak(summaryText, 'summary')}
                title="Read Summary"
              >
                {speakingSection === 'summary' ? '⏹️' : '🔊'}
              </button>
            </div>
          </div>
          <div className="card-body">
            <div className="checklist-container">
              {nextSteps.map((step, i) => (
                <p key={i} className="next-step-paragraph">
                  {step}
                </p>
              ))}
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

export default DiseaseResponse;
// import React, { useState, useMemo } from 'react';
// import './AgentResponse.css';
// import './DiseaseResponse.css';
// import Card from '../response-sections/Card';
// import { mergeResponseData } from '../../utils/parseResponse';

// function DiseaseResponse({ output, finalResponse }) {
//   // Merge final_response data with disease output
//   const mergedOutput = useMemo(() => {
//     if (!output) return null;
//     if (finalResponse) {
//       return mergeResponseData(output, finalResponse);
//     }
//     return output;
//   }, [output, finalResponse]);

//   if (!mergedOutput) return null;

//   const diseaseInfo = mergedOutput.disease_info || {};
//   const remedy = mergedOutput.remedy || mergedOutput.remedy_info || {};
//   const identifiedDisease = diseaseInfo.identified_disease || diseaseInfo.disease || 'Unknown Disease';
//   const confidence = diseaseInfo.confidence || diseaseInfo.confidence_score || null;
//   const symptoms = diseaseInfo.symptoms || [];
//   const description = diseaseInfo.description || '';
//   const treatments = remedy.treatments || [];
//   const prevention = remedy.prevention || [];
//   const imageNote = mergedOutput.image_processing_note || null;
//   const shopInfo = mergedOutput.shop_info || null;
//   const checklistData = mergedOutput.checklist || null;

//   // Determine detection method (CNN or LLM)
//   const getDetectionMethod = () => {
//     // Check if detection_method is explicitly set in disease_info
//     if (diseaseInfo.detection_method === 'CNN') {
//       return 'CNN';
//     }
//     // Check if image_processing_note indicates CNN was unavailable (fallback to LLM)
//     if (imageNote && imageNote.cnn_unavailable) {
//       return 'LLM';
//     }
//     // Check if image_processing_note exists without cnn_unavailable flag (CNN was used)
//     if (imageNote && !imageNote.cnn_unavailable) {
//       return 'CNN';
//     }
//     // Check if description mentions CNN
//     if (description && description.toLowerCase().includes('cnn')) {
//       return 'CNN';
//     }
//     // Default to LLM for text-based diagnosis
//     return 'LLM';
//   };

//   const detectionMethod = getDetectionMethod();

//   // Parse shop information - always return data structure, even if empty
//   const parseShopInfo = (shopInfo) => {
//     const defaultData = { location: null, mapsUrls: [], radius: null, text: null };

//     if (!shopInfo) return defaultData;

//     if (typeof shopInfo === 'string') {
//       // Try to extract Google Maps URLs from text
//       const urlRegex = /(https?:\/\/[^\s\)]+)/g;
//       const urls = shopInfo.match(urlRegex) || [];
//       // Filter to only Google Maps URLs
//       const mapsUrls = urls.filter(url =>
//         url.includes('google.com/maps') ||
//         url.includes('maps.google') ||
//         url.includes('google.com/maps/search')
//       );
//       return {
//         location: null,
//         mapsUrls: mapsUrls.length > 0 ? mapsUrls.map(url => ({
//           url: url.trim(),
//           label: url.includes('fertilizer') ? 'Fertilizer Shop' :
//             url.includes('agro') ? 'Agro Shop' :
//               url.includes('pesticide') ? 'Pesticide Shop' :
//                 url.includes('seed') ? 'Seed Store' : 'View on Google Maps'
//         })) : [],
//         radius: null,
//         text: shopInfo
//       };
//     }

//     if (typeof shopInfo === 'object') {
//       const results = shopInfo.results || shopInfo;
//       const location = shopInfo.location || results.location || {};
//       let mapsUrls = [];

//       // Handle different URL formats
//       if (results.google_maps_search_urls) {
//         mapsUrls = Array.isArray(results.google_maps_search_urls)
//           ? results.google_maps_search_urls.map((url, idx) => {
//             if (typeof url === 'string') {
//               return { url, label: `Search Option ${idx + 1}` };
//             }
//             // If it's an object, extract url and label/query
//             const urlStr = url.url || url.alt_url || '';
//             const label = url.query || url.label || `Search Option ${idx + 1}`;
//             return { url: urlStr, label };
//           })
//           : [];
//       }

//       // Also check for URLs in the object itself
//       if (mapsUrls.length === 0) {
//         const urlPattern = /(https?:\/\/[^\s\)]+google\.com\/maps[^\s\)]+)/gi;
//         const shopInfoStr = JSON.stringify(shopInfo);
//         const foundUrls = shopInfoStr.match(urlPattern) || [];
//         mapsUrls = foundUrls.map((url, idx) => ({
//           url: url.trim(),
//           label: `Search Option ${idx + 1}`
//         }));
//       }

//       const radius = results.location?.radius_meters || location.radius_meters || results.radius_meters || null;
//       return { location, mapsUrls, radius, text: null };
//     }

//     return defaultData;
//   };

//   const shopData = parseShopInfo(shopInfo);

//   // Generate default Google Maps search URL if none found
//   const getDefaultMapsUrl = () => {
//     // Try to get location from shopData or use a generic search
//     if (shopData.location && shopData.location.lat && shopData.location.lon) {
//       return `https://www.google.com/maps/search/fertilizer+shop/@${shopData.location.lat},${shopData.location.lon},15z`;
//     }
//     // Generic search URL
//     return 'https://www.google.com/maps/search/fertilizer+shop+near+me';
//   };

//   // Generate checklist items from treatments, prevention, or parsed final_response
//   const generateChecklist = () => {
//     // Use parsed checklist from final_response if available
//     if (checklistData && Array.isArray(checklistData) && checklistData.length > 0) {
//       return checklistData.slice(0, 5);
//     }

//     // Otherwise generate from treatments and prevention
//     const items = [];
//     if (treatments.length > 0) {
//       treatments.slice(0, 3).forEach((treatment, idx) => {
//         const text = typeof treatment === 'string'
//           ? treatment
//           : treatment.name || treatment.description || `Treatment ${idx + 1}`;
//         items.push({ text, completed: false });
//       });
//     }
//     if (prevention.length > 0 && items.length < 5) {
//       prevention.slice(0, 5 - items.length).forEach((tip) => {
//         items.push({ text: tip, completed: false });
//       });
//     }
//     return items.slice(0, 5);
//   };

//   const checklistItems = generateChecklist();

//   // Format confidence badge
//   const getConfidenceBadge = () => {
//     if (!confidence) return null;
//     if (typeof confidence === 'number' && confidence > 0) {
//       return (
//         <span className="confidence-badge">
//           {Math.round(confidence * 100)}% Confidence
//         </span>
//       );
//     }
//     if (typeof confidence === 'string' && confidence !== 'low') {
//       return (
//         <span className="confidence-badge">
//           {confidence.charAt(0).toUpperCase() + confidence.slice(1)} Confidence
//         </span>
//       );
//     }
//     return null;
//   };

//   // Get alert color based on disease severity
//   const getAlertColor = () => {
//     if (identifiedDisease === 'Healthy' || identifiedDisease === 'No disease detected') {
//       return 'success';
//     }
//     return 'danger';
//   };

//   return (
//     <div className="disease-response-container">
//       {/* Image Processing Notice */}
//       {imageNote && imageNote.cnn_unavailable && (
//         <div className="error-notice">
//           <strong>⚠️ Image Processing Unavailable</strong>
//           <p>
//             {imageNote.message || 'Image-based disease detection requires TensorFlow. Please install it: pip install tensorflow>=2.13.0'}
//           </p>
//           {imageNote.fallback_to_text && (
//             <p className="fallback-note">
//               Falling back to text-based diagnosis based on your query.
//             </p>
//           )}
//         </div>
//       )}

//       {/* 1. Diagnosis Card */}
//       <Card
//         title="Diagnosis"
//         icon="🦠"
//         className="diagnosis-card"
//         alertStyle={true}
//       >
//         <div className="diagnosis-content">
//           <div className="disease-title-section">
//             <h4 className="disease-name">{identifiedDisease}</h4>
//             {getConfidenceBadge()}
//           </div>

//           {/* Detection Method Indicator */}
//           <p className="detection-method-indicator">
//             <strong>Detection Method:</strong> {detectionMethod === 'CNN'
//               ? 'CNN (Convolutional Neural Network) - AI image analysis'
//               : 'LLM (Large Language Model) - Text-based analysis'}
//           </p>

//           {description && (
//             <p className="disease-description">
//               {description}
//             </p>
//           )}

//           {symptoms.length > 0 && (
//             <div className="symptoms-section">
//               <h5 className="section-subtitle">Symptoms Identified:</h5>
//               <ul className="symptoms-list">
//                 {symptoms.map((symptom, idx) => (
//                   <li key={idx}>{symptom}</li>
//                 ))}
//               </ul>
//             </div>
//           )}
//         </div>
//       </Card>

//       {/* 2. Immediate Actions Card (Most Important) */}
//       {treatments.length > 0 && (
//         <Card
//           title="Immediate Actions"
//           icon="⚡"
//           className="immediate-actions-card"
//           priority={true}
//         >
//           <div className="immediate-actions-content">
//             <ul className="actions-bullet-list">
//               {treatments.map((treatment, idx) => {
//                 // Extract action text and "why it helps"
//                 let actionText = '';
//                 let whyText = '';

//                 if (typeof treatment === 'string') {
//                   actionText = treatment;
//                 } else {
//                   // Build action text from available fields
//                   const parts = [];
//                   if (treatment.name) parts.push(treatment.name);
//                   if (treatment.description) parts.push(treatment.description);
//                   if (treatment.dosage) parts.push(`Dosage: ${treatment.dosage}`);
//                   actionText = parts.join('. ');

//                   // Get "why it helps" if available
//                   if (treatment.why) {
//                     whyText = treatment.why;
//                   }
//                 }

//                 return (
//                   <li key={idx} className="action-bullet-item">
//                     <span className="action-bullet-text">
//                       {actionText}
//                       {whyText && (
//                         <span className="action-why-inline">
//                           {' '}<strong>Why it helps:</strong> {whyText}
//                         </span>
//                       )}
//                     </span>
//                   </li>
//                 );
//               })}
//             </ul>
//           </div>
//         </Card>
//       )}

//       {/* 3. Preventive Care Card */}
//       {prevention.length > 0 && (
//         <Card
//           title="Preventive Care"
//           icon="🛡️"
//           className="preventive-care-card"
//           collapsible={true}
//           defaultExpanded={false}
//         >
//           <ul className="prevention-list">
//             {prevention.map((tip, idx) => (
//               <li key={idx}>{tip}</li>
//             ))}
//           </ul>
//         </Card>
//       )}

//       {/* 4. Nearby Fertilizer & Agro-Input Shops Card - ALWAYS SHOWN */}
//       <Card
//         title="Nearby Fertilizer & Agro-Input Shops"
//         icon="🏪"
//         className="nearby-shops-card"
//       >
//         <div className="shops-content">
//           {shopData.location && (
//             <div className="shop-location-info">
//               <p className="location-text">
//                 <strong>Location:</strong> {shopData.location.name || 'Current location'}
//               </p>
//               {shopData.radius && (
//                 <p className="radius-text">
//                   <strong>Search Radius:</strong> {Math.round(shopData.radius / 1000)} km
//                 </p>
//               )}
//             </div>
//           )}

//           {shopData.text && (
//             <div className="shop-text-info">
//               <p>{shopData.text}</p>
//             </div>
//           )}

//           {/* Always show Google Maps links section */}
//           <div className="maps-links-section">
//             {shopData.mapsUrls.length > 0 ? (
//               <>
//                 <h5 className="maps-section-title">Google Maps Search Links:</h5>
//                 <div className="maps-buttons">
//                   {shopData.mapsUrls.map((urlObj, idx) => {
//                     const url = typeof urlObj === 'string' ? urlObj : urlObj.url;
//                     const label = typeof urlObj === 'string'
//                       ? `Search Option ${idx + 1}`
//                       : urlObj.label || urlObj.query || `Search Option ${idx + 1}`;
//                     return (
//                       <a
//                         key={idx}
//                         href={url}
//                         target="_blank"
//                         rel="noopener noreferrer"
//                         className="maps-link-button"
//                       >
//                         <span className="maps-link-icon">📍</span>
//                         {label}
//                       </a>
//                     );
//                   })}
//                 </div>
//               </>
//             ) : (
//               <>
//                 <p className="no-shops-message">
//                   No shops found in the current search radius. Use the button below to search on Google Maps.
//                 </p>
//                 <div className="maps-buttons">
//                   <a
//                     href={getDefaultMapsUrl()}
//                     target="_blank"
//                     rel="noopener noreferrer"
//                     className="maps-link-button maps-link-button-primary"
//                   >
//                     <span className="maps-link-icon">📍</span>
//                     Search Nearby Fertilizer Shops
//                   </a>
//                 </div>
//               </>
//             )}
//             <button className="expand-radius-button">
//               Expand Search Radius
//             </button>
//           </div>
//         </div>
//       </Card>
//     </div>
//   );
// }

// // Checklist Item Component
// function ChecklistItem({ text }) {
//   const [completed, setCompleted] = useState(false);

//   return (
//     <li className="checklist-item">
//       <label className="checklist-label">
//         <input
//           type="checkbox"
//           checked={completed}
//           onChange={(e) => setCompleted(e.target.checked)}
//           className="checklist-checkbox"
//         />
//         <span className={`checklist-text ${completed ? 'completed' : ''}`}>
//           {text}
//         </span>
//       </label>
//     </li>
//   );
// }

// export default DiseaseResponse;