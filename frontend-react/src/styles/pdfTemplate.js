// pdfTemplate.js
// Inject this as a <style> block into the reportRef container before generating PDF.
// Usage: inject via a hidden <style> tag inside the ref div, or pass to html2pdf options.

export const PDF_TEMPLATE_STYLES = `
  /* ── TailorAI PDF template ── */

  .tailor-pdf-root {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: #ffffff;
    color: #0f0f14;
    width: 100%;
  }

  /* Header */
  .tailor-pdf-header {
    background: #0f0f14;
    padding: 20px 28px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .tailor-pdf-logo-group {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .tailor-pdf-logo-name {
    font-size: 17px;
    font-weight: 600;
    color: #ffffff;
    letter-spacing: 0.01em;
  }
  .tailor-pdf-header-meta {
    font-size: 11px;
    color: #888888;
    text-align: right;
    line-height: 1.6;
  }

  /* Gradient accent bar */
  .tailor-pdf-accent-bar {
    height: 3px;
    background: linear-gradient(90deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
  }

  /* Body */
  .tailor-pdf-body {
    padding: 28px 32px 32px;
    background: #ffffff;
  }

  /* Meta row */
  .tailor-pdf-meta-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 0.5px solid #e8e8e8;
  }
  .tailor-pdf-topic-label {
    font-size: 11px;
    color: #888888;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }
  .tailor-pdf-badges {
    display: flex;
    gap: 6px;
  }
  .tailor-pdf-badge {
    font-size: 11px;
    padding: 3px 9px;
    border-radius: 99px;
    border: 0.5px solid #e0e0e0;
    color: #555555;
  }
  .tailor-pdf-badge-skill {
    background: #EEEDFE;
    border-color: #AFA9EC;
    color: #3C3489;
  }
  .tailor-pdf-badge-mode {
    background: #E1F5EE;
    border-color: #9FE1CB;
    color: #085041;
  }

  /* Report title */
  .tailor-pdf-title {
    font-size: 22px;
    font-weight: 700;
    color: #0f0f14;
    line-height: 1.3;
    margin-bottom: 6px;
  }
  .tailor-pdf-subtitle {
    font-size: 13px;
    color: #888888;
    margin-bottom: 22px;
  }

  /* Executive summary */
  .tailor-pdf-exec-summary {
    background: #f8f7ff;
    border-left: 3px solid #7F77DD;
    border-radius: 0 8px 8px 0;
    padding: 12px 16px;
    margin-bottom: 22px;
  }
  .tailor-pdf-exec-summary p {
    font-size: 13px;
    color: #444444;
    line-height: 1.7;
    margin: 0;
  }

  /* Sections */
  .tailor-pdf-section {
    margin-bottom: 20px;
  }
  .tailor-pdf-section h2 {
    font-size: 15px;
    font-weight: 600;
    color: #0f0f14;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .tailor-pdf-section h2::before {
    content: '';
    display: inline-block;
    width: 4px;
    height: 14px;
    background: linear-gradient(180deg, #667eea, #f093fb);
    border-radius: 2px;
    flex-shrink: 0;
  }
  .tailor-pdf-section p {
    font-size: 13px;
    color: #333333;
    line-height: 1.75;
  }

  /* Code blocks */
  .tailor-pdf-code-block {
    background: #0f0f14;
    border-radius: 8px;
    margin: 10px 0 0;
    overflow: hidden;
  }
  .tailor-pdf-code-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 12px;
    border-bottom: 0.5px solid #2a2a35;
  }
  .tailor-pdf-code-lang {
    font-size: 11px;
    color: #888888;
    font-family: 'Courier New', monospace;
  }
  .tailor-pdf-code-body {
    padding: 12px 14px;
    font-size: 12px;
    color: #c9d1d9;
    font-family: 'Courier New', monospace;
    line-height: 1.6;
    white-space: pre;
    overflow-x: auto;
  }

  /* Divider */
  .tailor-pdf-divider {
    height: 0.5px;
    background: #ebebeb;
    margin: 20px 0;
  }

  /* Sources */
  .tailor-pdf-sources-label {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #aaaaaa;
    margin-bottom: 8px;
  }
  .tailor-pdf-source-item {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 5px;
  }
  .tailor-pdf-source-dot {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: #7F77DD;
    flex-shrink: 0;
  }
  .tailor-pdf-source-url {
    font-size: 11px;
    color: #7F77DD;
  }

  /* Footer */
  .tailor-pdf-footer {
    background: #0f0f14;
    padding: 12px 28px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .tailor-pdf-footer-text {
    font-size: 10px;
    color: #555555;
  }
  .tailor-pdf-footer-center {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .tailor-pdf-watermark-row {
    display: flex;
    justify-content: center;
    padding: 8px 0 12px;
    background: #ffffff;
  }
  .tailor-pdf-watermark {
    font-size: 10px;
    color: #cccccc;
    letter-spacing: 0.05em;
  }
`;

// SVG string for the TailorAI hex logo (reuse in header + footer)
export const TAILOR_HEX_SVG = (size = 28, strokeColor = 'url(#tailorGrad)') => `
  <svg width="${size}" height="${size}" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M16 3L27 9.5V22.5L16 29L5 22.5V9.5L16 3Z"
      stroke="${strokeColor}" stroke-width="1.5" fill="none"/>
    <defs>
      <linearGradient id="tailorGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#667eea"/>
        <stop offset="50%" stop-color="#764ba2"/>
        <stop offset="100%" stop-color="#f093fb"/>
      </linearGradient>
    </defs>
  </svg>
`;
