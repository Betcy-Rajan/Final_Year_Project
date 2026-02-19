import React, { useState, useEffect, useRef } from 'react';
import './AgentResponse.css';
import './SchemeResponse-styles.css';

// Utility to clean markdown characters for DISPLAY
const cleanMarkdown = (text) => {
  if (!text) return "";
  return String(text)
    .replace(/\*\*/g, '')    // remove bold
    .replace(/\*/g, '')      // remove italic/list markers if standalone
    .replace(/__/g, '')      // remove underline
    .replace(/`/g, '')       // remove code
    .replace(/^#+\s/gm, '')  // remove header markers
    .trim();
};

// Utility to clean text specifically for SPEECH
const cleanTextForSpeech = (text) => {
  if (!text) return "";
  return String(text)
    .replace(/\*\*/g, "")       // Remove bold
    .replace(/\*/g, "")         // Remove italic
    .replace(/__/g, "")         // Remove underline
    .replace(/`/g, "")          // Remove code ticks
    .replace(/https?:\/\/[^\s]+/g, "visit the official website") // Replace URLs
    .replace(/www\.[^\s]+/g, "visit the official website")       // Replace www URLs
    .replace(/[-•●]/g, ".")    // Replace bullets with pauses (periods)
    .replace(/\n+/g, ". ")      // Replace newlines with pauses
    .replace(/\.\./g, ".")      // Fix double periods
    .trim();
};

// Helper for icons
const getCategoryIcon = (name) => {
  const n = String(name).toLowerCase();
  if (n.includes('agri') || n.includes('farm') || n.includes('crop') || n.includes('irrigation')) return '🌾';
  if (n.includes('bank') || n.includes('loan') || n.includes('credit') || n.includes('financ') || n.includes('money')) return '💰';
  if (n.includes('edu') || n.includes('scholarship') || n.includes('student') || n.includes('school')) return '🎓';
  if (n.includes('health') || n.includes('medic') || n.includes('doctor')) return '🏥';
  if (n.includes('women') || n.includes('girl') || n.includes('female')) return '👩';
  if (n.includes('house') || n.includes('housing') || n.includes('home')) return '🏠';
  if (n.includes('job') || n.includes('employ') || n.includes('skill') || n.includes('work')) return '💼';
  if (n.includes('animal') || n.includes('cattle') || n.includes('dairy') || n.includes('livestock')) return '🐄';
  if (n.includes('fish') || n.includes('marine')) return '🐟';
  if (n.includes('social') || n.includes('welfare')) return '🤝';
  return '📂';
};

function SchemeResponse({ output, onQuery, finalMarkdown }) {
  const [selectedScheme, setSelectedScheme] = useState(null);

  // TTS State
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const synthRef = useRef(window.speechSynthesis);
  const utteranceRef = useRef(null);

  // Category Search & Filter State
  const [catSearch, setCatSearch] = useState('');
  const [catFilter, setCatFilter] = useState('All');
  const [showAllCats, setShowAllCats] = useState(false);

  // State for collapsible sections in detail view
  const [expandedSections, setExpandedSections] = useState({
    overview: true,
    benefits: true,
    eligibility: true,
    exclusions: false,
    documents: false,
    process: false,
    links: true
  });

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  // TTS Lifecycle
  useEffect(() => {
    // Cleanup on unmount
    return () => {
      if (synthRef.current) {
        synthRef.current.cancel();
      }
    };
  }, []);

  const handleSpeak = () => {
    if (!finalMarkdown) return;

    // Resume if paused
    if (isPaused) {
      synthRef.current.resume();
      setIsPaused(false);
      setIsSpeaking(true);
      return;
    }

    // Stop current speech
    synthRef.current.cancel();

    const textToRead = cleanTextForSpeech(finalMarkdown);
    const utterance = new SpeechSynthesisUtterance(textToRead);

    // Configure voice
    utterance.rate = 0.9; // Slightly slower for clarity
    utterance.pitch = 1.0;
    const voices = synthRef.current.getVoices();
    // Try to find an Indian English voice, fallback to generic English
    const preferredVoice = voices.find(v => v.lang.includes('en-IN')) || voices.find(v => v.lang.includes('en-US'));
    if (preferredVoice) utterance.voice = preferredVoice;

    utterance.onstart = () => {
      setIsSpeaking(true);
      setIsPaused(false);
    };

    utterance.onend = () => {
      setIsSpeaking(false);
      setIsPaused(false);
    };

    utterance.onerror = (e) => {
      console.error("TTS Error:", e);
      setIsSpeaking(false);
      setIsPaused(false);
    };

    utteranceRef.current = utterance;
    synthRef.current.speak(utterance);
  };

  const handlePause = () => {
    if (synthRef.current.speaking && !synthRef.current.paused) {
      synthRef.current.pause();
      setIsPaused(true);
      setIsSpeaking(false); // Visually indicate paused state (or keep speaking true but paused true?)
      // Let's keep isSpeaking true but manage specific UI for paused
    }
  };

  const handleStop = () => {
    if (synthRef.current) {
      synthRef.current.cancel();
      setIsSpeaking(false);
      setIsPaused(false);
    }
  };

  if (!output) return null;

  // Robust data access
  const schemes = output.schemes || (output.scheme_info && output.scheme_info.schemes) || [];
  const uiContent = output.ui_content || {};

  // Extract Summary
  const summary = uiContent.summary_card || {
    title: "Government Schemes",
    overview: "Based on your query, here are the relevant schemes."
  };

  // Extract Next Steps
  const nextSteps = uiContent.next_steps || [
    { title: "Check Eligibility", text: "Read criteria carefully." },
    { title: "Prepare Documents", text: "Get your papers ready." },
    { title: "Apply", text: "Visit official office." }
  ];

  // Extract Tips
  const tips = uiContent.tips_card || [
    "Keep your documents updated.",
    "Apply before deadlines."
  ];

  // Extract Footer
  const footerText = uiContent.footer_card || "Start your application today!";

  // Helper to determine status color/text
  const getStatusInfo = (status) => {
    switch (status) {
      case 'likely_eligible': return { class: 'likely', label: 'Likely Eligible', icon: '✅' };
      case 'possibly_eligible': return { class: 'possibly', label: 'Possibly Eligible', icon: '⚠️' };
      case 'unlikely': return { class: 'unlikely', label: 'Not Eligible', icon: '❌' };
      default: return { class: 'check', label: 'Check Eligibility', icon: '❓' };
    }
  };

  const handleDownload = (e, link) => {
    e.stopPropagation();
    if (link) window.open(link, '_blank');
  };

  // Retrieve subcategories if available
  const subcategories = output.subcategories ||
    output.sub_categories ||
    (output.subcategories_info && output.subcategories_info.sub_categories) ||
    (output.subcategories_info && output.subcategories_info.subcategories) ||
    [];
  const isSubcategoryMode = output.response_type === 'subcategories' || subcategories.length > 0;

  const handleSubCategoryClick = (subCategoryName) => {
    if (onQuery) {
      if (output.original_query) {
        const queryText = `${output.original_query} ${subCategoryName}`;
        onQuery(queryText);
        return;
      }
      let state = output.search_params?.state || output.location || '';
      const queryText = state ? `Schemes for ${subCategoryName} in ${state}` : `Schemes for ${subCategoryName}`;
      onQuery(queryText);
    }
  };


  // Helper to clean and preprocess benefits data
  const preprocessListItems = (items) => {
    if (!items || !Array.isArray(items)) return [];

    return items.flatMap(item => {
      if (typeof item !== 'string') return [item];
      // Split by <br>, <br/>, <br />, &lt;br&gt;, \n
      // Also strictly filter out "1. ", "2. " prefixes if they are just formatting? 
      // Actually, keeping numbering inside the text is fine, but splitting multi-line strings is key.
      return item.split(/<br\s*\/?>|&lt;br&gt;|\n/gi)
        .map(s => cleanMarkdown(s.trim()))
        .filter(s => s.length > 0 && s !== '<br>' && s !== '&lt;br&gt;');
    });
  };

  // ---------------------------------------------------------
  // SCHEME DETAIL VIEW (Overhauled)
  // ---------------------------------------------------------
  if (selectedScheme) {
    const statusInfo = getStatusInfo(selectedScheme.eligibility_status);
    const category = Array.isArray(selectedScheme.category) ? selectedScheme.category[0] : (selectedScheme.category || 'General');

    // Attempt to infer/get additional data for Quick Summary
    // Since we don't always have these fields, we check or provide defaults/null
    const applicationMode = cleanMarkdown(selectedScheme.application_mode || "Physical/Online");
    const benefitType = cleanMarkdown(selectedScheme.benefit_type || "Financial/Kind");

    const processedBenefits = preprocessListItems(selectedScheme.benefits);
    const processedEligibility = preprocessListItems(selectedScheme.eligibility);
    const processedExclusions = preprocessListItems(selectedScheme.exclusions);
    const processedDocuments = preprocessListItems(selectedScheme.documents);

    return (
      <div className="agent-response scheme-response scheme-detail-container">
        <div className="detail-content-wrapper fade-in">

          {/* Navigation */}
          <div className="nav-bar">
            <button className="btn-back-nav" onClick={() => setSelectedScheme(null)}>
              ← Back to Schemes List
            </button>
          </div>

          {/* 1. Header Card */}
          <div className="detail-header-card">
            <div className="header-badges">
              <span className={`status-badge-block ${statusInfo.class}`}>
                {statusInfo.icon} {statusInfo.label}
              </span>
              <span className="scheme-type-badge">
                {selectedScheme.state && selectedScheme.state !== 'Central' ? 'State Scheme' : 'Central Scheme'}
              </span>
              <span className="scheme-category-tag">{category}</span>
            </div>

            <h1 className="scheme-title-large">{cleanMarkdown(selectedScheme.name || selectedScheme.scheme_name)}</h1>

            <div className="primary-actions">
              {(selectedScheme.link || (selectedScheme.references && selectedScheme.references[0]?.url)) ? (
                <a
                  href={(selectedScheme.references && selectedScheme.references[0]?.url) || selectedScheme.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-primary-action"
                >
                  🚀 Apply Now
                </a>
              ) : (
                <button className="btn-primary-action" disabled style={{ opacity: 0.6, cursor: 'not-allowed' }}>
                  Offline Process
                </button>
              )}


            </div>


          </div>

          {/* 2. Quick Summary Card */}
          <div className="quick-summary-card">
            <div className="summary-item">
              <span className="summary-label">Scheme Type</span>
              <span className="summary-value">{selectedScheme.state && selectedScheme.state !== 'Central' ? 'State' : 'Central'}</span>
            </div>
            <div className="summary-item">
              <span className="summary-label">Application Mode</span>
              <span className="summary-value">{applicationMode}</span>
            </div>
            <div className="summary-item">
              <span className="summary-label">Benefit Type</span>
              <span className="summary-value">{benefitType}</span>
            </div>
            <div className="summary-item">
              <span className="summary-label">Category</span>
              <span className="summary-value">{category}</span>
            </div>
          </div>


          {/* 3. Section: Overview */}
          <div className="detail-section-card">
            <div className="section-header" onClick={() => toggleSection('overview')}>
              <h3><span className="section-icon">📄</span> Overview</h3>
              <span className={`toggle-icon ${expandedSections.overview ? 'expanded' : ''}`}>▼</span>
            </div>
            {expandedSections.overview && (
              <div className="section-content">
                <p className="detail-text" style={{ lineHeight: '1.7', fontSize: '1rem' }}>
                  {cleanMarkdown(selectedScheme.brief_description || selectedScheme.description || 'No detailed overview available for this scheme.')}
                </p>
              </div>
            )}
          </div>

          {/* 4. Section: Benefits */}
          <div className="detail-section-card" style={{ height: 'auto' }}>
            <div className="section-header" onClick={() => toggleSection('benefits')}>
              <h3><span className="section-icon">🎁</span> Benefits</h3>
              <span className={`toggle-icon ${expandedSections.benefits ? 'expanded' : ''}`}>▼</span>
            </div>
            {expandedSections.benefits && (
              <div className="section-content">
                <ul className="checklist-list" style={{ height: 'auto', overflow: 'visible' }}>
                  {processedBenefits.length > 0 ? (
                    processedBenefits.map((b, i) => (
                      <li key={i} className="checklist-item">
                        <span className="check-icon">✓</span>
                        <span>{b}</span>
                      </li>
                    ))
                  ) : (
                    <li className="checklist-item">
                      <span className="check-icon">✓</span>
                      <span>{cleanMarkdown(selectedScheme.benefit || selectedScheme.subsidy_amount || 'Benefits details not available.')}</span>
                    </li>
                  )}
                </ul>
              </div>
            )}
          </div>

          {/* 5. Section: Eligibility Criteria */}
          <div className="detail-section-card" style={{ height: 'auto' }}>
            <div className="section-header" onClick={() => toggleSection('eligibility')}>
              <h3><span className="section-icon">✅</span> Eligibility Criteria</h3>
              <span className={`toggle-icon ${expandedSections.eligibility ? 'expanded' : ''}`}>▼</span>
            </div>
            {expandedSections.eligibility && (
              <div className="section-content">
                <ul className="checklist-list" style={{ height: 'auto', overflow: 'visible' }}>
                  {processedEligibility.length > 0 ? (
                    processedEligibility.map((e, i) => (
                      <li key={i} className="checklist-item">
                        <span className="check-icon">🔹</span>
                        <span>{e}</span>
                      </li>
                    ))
                  ) : (
                    <li className="checklist-item">
                      <span className="check-icon">🔹</span>
                      <span>{cleanMarkdown(selectedScheme.eligibility || selectedScheme.eligibility_summary || 'Check specific guidelines.')}</span>
                    </li>
                  )}
                </ul>
              </div>
            )}
          </div>

          {/*5.Section: Exclusioions*/}

          <div className="detail-section-card" style={{ height: 'auto' }}>
            <div className="section-header" onClick={() => toggleSection('exclusions')}>
              <h3><span className="section-icon">❌</span> Exclusions</h3>
              <span className={`toggle-icon ${expandedSections.exclusions ? 'expanded' : ''}`}>▼</span>
            </div>

            {expandedSections.exclusions && (
              <div className="section-content">
                <ul className="checklist-list" style={{ height: 'auto', overflow: 'visible' }}>
                  {processedExclusions && processedExclusions.length > 0 ? (
                    processedExclusions.map((item, i) => (
                      <li key={i} className="checklist-item">
                        <span className="check-icon" style={{ color: '#d32f2f' }}>✖</span>
                        <span>{item}</span>
                      </li>
                    ))
                  ) : (
                    <li className="checklist-item">
                      <span className="check-icon" style={{ color: '#999' }}>ℹ️</span>
                      <span>No specific exclusions mentioned for this scheme.</span>
                    </li>
                  )}
                </ul>
              </div>
            )}
          </div>

          {/* 6. Section: Required Documents */}
          <div className="detail-section-card" style={{ height: 'auto' }}>
            <div className="section-header" onClick={() => toggleSection('documents')}>
              <h3><span className="section-icon">📂</span> Required Documents</h3>
              <span className={`toggle-icon ${expandedSections.documents ? 'expanded' : ''}`}>▼</span>
            </div>
            {expandedSections.documents && (
              <div className="section-content">
                <ul className="checklist-list" style={{ height: 'auto', overflow: 'visible' }}>
                  {processedDocuments.length > 0 ? (
                    processedDocuments.map((d, i) => (
                      <li key={i} className="checklist-item">
                        <span className="check-icon">📝</span>
                        <span>{d}</span>
                      </li>
                    ))
                  ) : (
                    <div className="detail-note">
                      <p>Please refer to official guidelines for documents.</p>
                    </div>
                  )}
                </ul>
              </div>
            )}
          </div>

          {/* 7. Section: Application Process (Visual Stepper) */}
          <div className="detail-section-card">
            <div className="section-header" onClick={() => toggleSection('process')}>
              <h3><span className="section-icon">📝</span> Application Process</h3>
              <span className={`toggle-icon ${expandedSections.process ? 'expanded' : ''}`}>▼</span>
            </div>
            {expandedSections.process && (
              <div className="section-content">
                <div className="visual-stepper">
                  {/* Attempt to parse process if it's a string, otherwise use list */}
                  {/* If it's a single string, we treat it as one text block. If it's steps, we map. */}
                  {/* Since data might be string, we can try to split by numbering or newlines if simple, but for robustness: */}
                  {selectedScheme.application_process ? (
                    // If it's a long string, maybe display as one step or display as one text block.
                    <div className="stepper-step">
                      <div className="step-circle">1</div>
                      <div className="step-info">
                        <h5>Follow Instructions</h5>
                        <p>{cleanMarkdown(selectedScheme.application_process)}</p>
                      </div>
                    </div>
                  ) : (
                    <div className="stepper-step">
                      <div className="step-circle">1</div>
                      <div className="step-info">
                        <h5>Visit Official Website/Office</h5>
                        <p>Go to the department website or nearest office.</p>
                      </div>
                    </div>
                  )}
                  {/* Note: If we had a structural list of steps in backend, we would map them here. */}
                </div>
              </div>
            )}
          </div>

          {/* 8. Section: Official Links */}
          <div className="detail-section-card">
            <div className="section-header" onClick={() => toggleSection('links')}>
              <h3><span className="section-icon">🔗</span> Official Links</h3>
              <span className={`toggle-icon ${expandedSections.links ? 'expanded' : ''}`}>▼</span>
            </div>
            {expandedSections.links && (
              <div className="section-content">
                <div className="links-grid">
                  {selectedScheme.references && selectedScheme.references.length > 0 ? (
                    selectedScheme.references.map((ref, i) => (
                      <a key={i} href={ref.url} target="_blank" rel="noopener noreferrer" className="link-btn-card">
                        <span className="link-btn-icon">🌐</span>
                        <span className="link-btn-text">{cleanMarkdown(ref.title) || 'Official Guidelines'}</span>
                      </a>
                    ))
                  ) : selectedScheme.link ? (
                    <a href={selectedScheme.link} target="_blank" rel="noopener noreferrer" className="link-btn-card">
                      <span className="link-btn-icon">🌐</span>
                      <span className="link-btn-text">Visit Official Website</span>
                    </a>
                  ) : (
                    <div className="no-links">No direct links available.</div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* 9. Similar Schemes (Placeholder/Mock) */}
          <div className="similar-schemes-section">
            <div className="section-label">Similar Schemes You Might Like</div>
            <div className="similar-scroll-container">
              {/* We can filter from 'schemes' prop if available, else show a message */}
              {schemes.filter(s => s.name !== selectedScheme.name).slice(0, 5).map((simScheme, idx) => (
                <div key={idx} className="similar-card" onClick={() => {
                  setSelectedScheme(simScheme);
                  window.scrollTo(0, 0);
                }}>
                  <div className="similar-name">{cleanMarkdown(simScheme.name || simScheme.scheme_name)}</div>
                  <div className="scheme-type-badge" style={{ display: 'inline-block' }}>
                    {simScheme.state && simScheme.state !== 'Central' ? 'State' : 'Central'}
                  </div>
                </div>
              ))}
              {schemes.filter(s => s.name !== selectedScheme.name).length === 0 && (
                <p style={{ color: '#777', paddingLeft: '1rem' }}>No similar schemes found in this search context.</p>
              )}
            </div>
          </div>

        </div>

        {/* Sticky Apply Button (Mobile) */}
        <div className="sticky-apply-bar">
          <div className="sticky-info">
            <strong>{cleanMarkdown(selectedScheme.name?.substring(0, 20))}...</strong>
          </div>
          {(selectedScheme.link || (selectedScheme.references && selectedScheme.references[0]?.url)) ? (
            <a
              href={(selectedScheme.references && selectedScheme.references[0]?.url) || selectedScheme.link}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-sticky-apply"
            >
              Apply Now
            </a>
          ) : (
            <button className="btn-sticky-apply" disabled style={{ opacity: 0.7 }}>Offline</button>
          )}
        </div>

      </div>
    );
  }

  // MAIN LISTING VIEW
  return (
    <div className="agent-response scheme-response">
      <div className="response-content">

        {/* Subcategory Selection Mode */}
        {schemes.length === 0 && isSubcategoryMode && (
          <div className="category-selection-container fade-in">

            {/* Header Section */}
            <div className="category-header-section">
              <div className="header-breadcrumbs">
                <span className="breadcrumb-item">Home</span>
                <span className="breadcrumb-separator">/</span>
                <span className="breadcrumb-item active">Schemes</span>
              </div>
              <h2 className="category-main-title">Explore {output.search_params?.state ? `${output.search_params.state} ` : ''}Schemes</h2>
              <p className="category-subtitle">Select a category to find relevant government schemes for you.</p>
            </div>

            {/* Search and Filter Section */}
            <div className="category-controls">
              <div className="category-search-bar">
                <span className="search-icon">🔍</span>
                <input
                  type="text"
                  placeholder="Search categories (e.g. Loan, Education)..."
                  value={catSearch}
                  onChange={(e) => setCatSearch(e.target.value)}
                />
              </div>

              <div className="category-filter-chips">
                {['All', 'Agriculture', 'Finance', 'Education', 'Employment'].map(filter => (
                  <button
                    key={filter}
                    className={`filter-chip ${catFilter === filter ? 'active' : ''}`}
                    onClick={() => setCatFilter(filter)}
                  >
                    {filter}
                  </button>
                ))}
              </div>
            </div>

            {/* Categories Display Logic */}
            {(() => {
              // 1. Filter Logic
              const filtered = subcategories.filter(sub => {
                const name = (sub.name || sub).toLowerCase();
                const matchesSearch = name.includes(catSearch.toLowerCase());

                let matchesFilter = true;
                if (catFilter !== 'All') {
                  const f = catFilter.toLowerCase();
                  if (f === 'agriculture') matchesFilter = name.includes('agri') || name.includes('farm') || name.includes('crop') || name.includes('irrigation') || name.includes('soil');
                  else if (f === 'finance') matchesFilter = name.includes('loan') || name.includes('credit') || name.includes('subsidy') || name.includes('bank') || name.includes('insurance') || name.includes('pension');
                  else if (f === 'education') matchesFilter = name.includes('education') || name.includes('scholarship') || name.includes('student') || name.includes('training') || name.includes('university');
                  else if (f === 'employment') matchesFilter = name.includes('employ') || name.includes('job') || name.includes('work') || name.includes('skill') || name.includes('wage');
                }
                return matchesSearch && matchesFilter;
              });

              // 2. Grouping (Only if no search/filter active)
              const isDefaultView = catSearch === '' && catFilter === 'All';
              const popularCount = 6;

              const popularCats = isDefaultView ? filtered.slice(0, popularCount) : [];
              const mainGridCats = isDefaultView ? filtered.slice(popularCount) : filtered;

              // Show More Logic
              const visibleMainCats = showAllCats || !isDefaultView ? mainGridCats : mainGridCats.slice(0, 9);
              const hiddenCount = mainGridCats.length - visibleMainCats.length;

              if (filtered.length === 0) {
                return (
                  <div className="no-categories-found">
                    <span className="no-cat-icon">🔍</span>
                    <p>No categories found matching your filters.</p>
                    <button className="btn-reset-filters" onClick={() => { setCatSearch(''); setCatFilter('All'); }}>
                      Reset Filters
                    </button>
                  </div>
                );
              }

              return (
                <div className="categories-layout">

                  {/* Popular Section */}
                  {popularCats.length > 0 && (
                    <div className="category-section">
                      <h4 className="section-title-cat">🔥 Popular Categories</h4>
                      <div className="categories-grid popular-grid">
                        {popularCats.map((sub, idx) => (
                          <button
                            key={`pop-${idx}`}
                            className="category-card popular-card"
                            onClick={() => handleSubCategoryClick(sub.name || sub)}
                          >
                            <div className="cat-icon-wrapper">
                              <span className="cat-icon">{getCategoryIcon(sub.name || sub)}</span>
                            </div>
                            <div className="cat-info">
                              <span className="cat-name">{sub.name || sub}</span>
                            </div>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Main Grid Section */}
                  <div className="category-section">
                    {popularCats.length > 0 && <h4 className="section-title-cat">📂 All Categories</h4>}
                    <div className="categories-grid">
                      {visibleMainCats.map((sub, idx) => (
                        <button
                          key={idx}
                          className="category-card"
                          onClick={() => handleSubCategoryClick(sub.name || sub)}
                        >
                          <div className="cat-icon-wrapper">
                            <span className="cat-icon">{getCategoryIcon(sub.name || sub)}</span>
                          </div>
                          <div className="cat-info">
                            <span className="cat-name">{sub.name || sub}</span>
                          </div>
                        </button>
                      ))}
                    </div>

                    {/* Show More Button */}
                    {hiddenCount > 0 && (
                      <div className="show-more-container">
                        <button className="btn-show-more" onClick={() => setShowAllCats(true)}>
                          Show {hiddenCount} More Categories ▼
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })()}

          </div>
        )}

        {/* 1. Summary & Recommendations Card (TTS Enabled) */}
        {finalMarkdown ? (
          <div className="summary-recommendations-card fade-in">
            <h3>💡 Summary & Recommendations</h3>
            <div className="summary-text-content">
              {cleanMarkdown(finalMarkdown)}
            </div>

            {/* Audio Controls */}
            <div className="audio-controls-bar">
              {!isSpeaking && !isPaused ? (
                <button className="btn-audio-action" onClick={handleSpeak}>
                  <span>▶</span> Play Audio
                </button>
              ) : (
                <>
                  <button className="btn-audio-action" onClick={handlePause} disabled={isPaused}>
                    <span>⏸</span> Pause
                  </button>
                  {isPaused && (
                    <button className="btn-audio-action" onClick={handleSpeak}>
                      <span>▶</span> Resume
                    </button>
                  )}
                  <button className="btn-audio-action" onClick={handleStop}>
                    <span>⏹</span> Stop
                  </button>
                </>
              )}
            </div>
          </div>
        ) : (
          /* Fallback Compact Summary if no markdown */
          schemes.length > 0 && (
            <div className="summary-card compact-summary">
              <div className="summary-row">
                <div className="summary-info">
                  <h4>{cleanMarkdown(summary.title)}</h4>
                  <p className="summary-text-compact">{cleanMarkdown(summary.overview)}</p>
                </div>
                {summary.subtitle && <div className="summary-badge">{cleanMarkdown(summary.subtitle)}</div>}
              </div>
            </div>
          )
        )}

        {/* 2. Scheme Cards (Responsive Grid) */}
        {schemes.length > 0 ? (
          <div className="schemes-grid-responsive">
            {schemes.map((scheme, idx) => {
              const status = scheme.eligibility_status || 'check_eligibility';
              const statusInfo = getStatusInfo(status);
              const categoryName = Array.isArray(scheme.category) ? scheme.category[0] : (scheme.category || 'General');

              return (
                <div key={idx} className="scheme-card-modern">
                  <div className="card-modern-header">
                    <span className={`status-pill ${statusInfo.class}`}>
                      {statusInfo.icon} {statusInfo.label}
                    </span>
                    <span className="type-pill">
                      {scheme.state && scheme.state !== 'Central' ? 'State' : 'Central'}
                    </span>
                  </div>

                  <div className="card-modern-body">
                    <h3 className="scheme-heading" title={scheme.name || scheme.scheme_name}>
                      {cleanMarkdown(scheme.name || scheme.scheme_name)}
                    </h3>
                    <div className="scheme-tags">
                      <span className="scheme-tag">📂 {cleanMarkdown(categoryName)}</span>
                    </div>
                  </div>

                  <div className="card-modern-footer">
                    <button className="btn-modern-details" onClick={() => setSelectedScheme(scheme)}>
                      View Details
                    </button>

                    {(scheme.link || (scheme.references && scheme.references[0]?.url)) ? (
                      <a
                        href={(scheme.references && scheme.references[0]?.url) || scheme.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-modern-apply"
                      >
                        Apply ↗
                      </a>
                    ) : (
                      <span className="offline-badge">Offline</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          !isSubcategoryMode && (
            <div className="no-schemes-card">
              <p>No schemes found tailored to your specific query. Try adjusting filters.</p>
            </div>
          )
        )}
      </div>
    </div>
  );
}

export default SchemeResponse;
