// ReportPDFWrapper.jsx
// Drop this around the agent message bubble that contains data.report (deep research result).
// It wraps the markdown report in the TailorAI branded template and adds a Download PDF button.
//
// Usage in Chat.jsx — replace the existing deep research aiMsg render block:
//
//   if (data.success && data.report) {
//     const aiMsg = {
//       role: 'agent',
//       content: data.report,
//       isDeepResearch: true,          // ← add this flag
//       reportMeta: {
//         topic: userMsg,
//         skillLevel: profileScore,
//         mode: modeChoice,
//         sources: data.sources || [],  // ← add if your backend returns sources
//       },
//       ...
//     };
//   }
//
// Then in MessageBubble, when message.isDeepResearch is true, render:
//   <ReportPDFWrapper message={message} userName={user?.name || profile?.name} userEmail={user?.email} />

import { useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useDownloadPDF } from '../hooks/useDownloadPDF';   // adjust path
import { PDF_TEMPLATE_STYLES, TAILOR_HEX_SVG } from './pdfTemplate';  // adjust path

const HEX_GRADIENT_SVG = `
<svg width="28" height="28" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M16 3L27 9.5V22.5L16 29L5 22.5V9.5L16 3Z"
    stroke="url(#hdrGrad)" stroke-width="1.5" fill="none"/>
  <defs>
    <linearGradient id="hdrGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#667eea"/>
      <stop offset="50%" stop-color="#764ba2"/>
      <stop offset="100%" stop-color="#f093fb"/>
    </linearGradient>
  </defs>
</svg>`;

const HEX_MUTED_SVG = `
<svg width="14" height="14" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M16 3L27 9.5V22.5L16 29L5 22.5V9.5L16 3Z"
    stroke="#555555" stroke-width="1.5" fill="none"/>
</svg>`;

function now() {
  return new Date().toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: 'numeric', minute: '2-digit',
  });
}

function slugify(str = '') {
  return str.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 60);
}

export function ReportPDFWrapper({ message, userName = 'Student', userEmail = '' }) {
  const reportRef = useRef(null);
  const { downloadPDF, isGenerating } = useDownloadPDF();

  const meta = message.reportMeta || {};
  const topic = meta.topic || 'Deep Research Report';
  const skillLevel = meta.skillLevel || 'Intermediate';
  const mode = meta.mode || 'auto';
  const sources = Array.isArray(meta.sources) ? meta.sources : [];

  // Count subtopics by counting ## headings in the report markdown
  const subtopicCount = (message.content.match(/^## /gm) || []).length;

  const filename = `tailorai-report-${slugify(topic)}`;

  // Capture the styled wrapper (not just the markdown)
  const handleDownload = () => {
    downloadPDF(reportRef, filename);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', width: '100%' }}>

      {/* ── Download button — above the report ── */}
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <button
          onClick={handleDownload}
          disabled={isGenerating}
          style={{
            display: 'flex', alignItems: 'center', gap: '6px',
            padding: '7px 14px',
            fontSize: '13px', fontWeight: 500,
            border: '0.5px solid #e2e8f0',
            borderRadius: '8px',
            background: isGenerating ? '#f8f8f8' : '#ffffff',
            color: isGenerating ? '#aaa' : '#0f0f14',
            cursor: isGenerating ? 'not-allowed' : 'pointer',
            transition: 'background 0.15s',
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          {isGenerating ? 'Generating…' : 'Download PDF'}
        </button>
      </div>

      {/* ── PDF template wrapper (this is what gets captured) ── */}
      <div
        ref={reportRef}
        className="tailor-pdf-root"
        style={{ fontFamily: "'Segoe UI', system-ui, sans-serif" }}
      >
        {/* Inject template styles only inside the capture zone */}
        <style>{PDF_TEMPLATE_STYLES}</style>

        {/* Header */}
        <div className="tailor-pdf-header">
          <div className="tailor-pdf-logo-group">
            <span dangerouslySetInnerHTML={{ __html: HEX_GRADIENT_SVG }} />
            <span className="tailor-pdf-logo-name">TailorAI</span>
          </div>
          <div className="tailor-pdf-header-meta">
            <div>Deep Research Report</div>
            <div>Generated {now()}</div>
          </div>
        </div>

        {/* Accent bar */}
        <div className="tailor-pdf-accent-bar" />

        {/* Body */}
        <div className="tailor-pdf-body">

          {/* Meta row */}
          <div className="tailor-pdf-meta-row">
            <span className="tailor-pdf-topic-label">Deep Learning</span>
            <div className="tailor-pdf-badges">
              <span className="tailor-pdf-badge tailor-pdf-badge-skill">{skillLevel}</span>
              {mode !== 'auto' && (
                <span className="tailor-pdf-badge tailor-pdf-badge-mode">{mode}</span>
              )}
            </div>
          </div>

          {/* Title */}
          <div className="tailor-pdf-title">{topic}</div>
          <div className="tailor-pdf-subtitle">
            A comprehensive technical brief
            {subtopicCount > 0 ? ` · ${subtopicCount} subtopics` : ''}
            {sources.length > 0 ? ` · ${sources.length} sources` : ''}
          </div>

          {/* Report markdown — ReactMarkdown renders ## headings as h2, which get the gradient bar via CSS */}
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              // Map markdown elements to PDF template classes
              h1: ({ children }) => <div className="tailor-pdf-title" style={{ marginBottom: 16 }}>{children}</div>,
              h2: ({ children }) => (
                <div className="tailor-pdf-section">
                  <h2>{children}</h2>
                </div>
              ),
              p: ({ children }) => (
                <div className="tailor-pdf-section">
                  <p>{children}</p>
                </div>
              ),
              blockquote: ({ children }) => (
                <div className="tailor-pdf-exec-summary">{children}</div>
              ),
              code({ node, inline, className, children }) {
                const lang = (className || '').replace('language-', '') || 'code';
                if (inline) return <code style={{ background: '#f0f0f0', padding: '1px 4px', borderRadius: 3, fontSize: 12 }}>{children}</code>;
                return (
                  <div className="tailor-pdf-code-block">
                    <div className="tailor-pdf-code-header">
                      <span className="tailor-pdf-code-lang">{lang}</span>
                    </div>
                    <div className="tailor-pdf-code-body">{children}</div>
                  </div>
                );
              },
              hr: () => <div className="tailor-pdf-divider" />,
            }}
          >
            {message.content}
          </ReactMarkdown>

          {/* Sources */}
          {sources.length > 0 && (
            <>
              <div className="tailor-pdf-divider" />
              <div>
                <div className="tailor-pdf-sources-label">Sources</div>
                {sources.map((src, i) => (
                  <div key={i} className="tailor-pdf-source-item">
                    <div className="tailor-pdf-source-dot" />
                    <span className="tailor-pdf-source-url">{src.url || src}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="tailor-pdf-footer">
          <span className="tailor-pdf-footer-text">{userEmail || userName}</span>
          <div className="tailor-pdf-footer-center">
            <span dangerouslySetInnerHTML={{ __html: HEX_MUTED_SVG }} />
            <span className="tailor-pdf-footer-text">TailorAI</span>
          </div>
          <span className="tailor-pdf-footer-text">Page 1</span>
        </div>

        <div className="tailor-pdf-watermark-row">
          <span className="tailor-pdf-watermark">generated by tailorai · adaptive learning platform</span>
        </div>
      </div>
    </div>
  );
}
