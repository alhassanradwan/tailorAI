// useDownloadPDF.js
// Drop this hook anywhere in your project (e.g. src/hooks/useDownloadPDF.js)
// Usage: const { downloadPDF, isGenerating } = useDownloadPDF()
//        <button onClick={() => downloadPDF(reportRef, title)}>Download PDF</button>

import { useState, useCallback } from "react";

export function useDownloadPDF() {
  const [isGenerating, setIsGenerating] = useState(false);

  const downloadPDF = useCallback(async (ref, filename = "research-report") => {
    if (!ref?.current) return;
    setIsGenerating(true);

    // Dynamically load html2pdf.js only when needed (no install required)
    if (!window.html2pdf) {
      await new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src =
          "https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js";
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
      });
    }

    const options = {
      margin: [12, 14, 12, 14],          // top, right, bottom, left (mm)
      filename: `${filename}.pdf`,
      image: { type: "jpeg", quality: 0.98 },
      html2canvas: {
        scale: 2,                          // retina-quality
        useCORS: true,
        logging: false,
      },
      jsPDF: {
        unit: "mm",
        format: "a4",
        orientation: "portrait",
      },
      pagebreak: { mode: ["avoid-all", "css", "legacy"] },
    };

    try {
      await window.html2pdf().set(options).from(ref.current).save();
    } finally {
      setIsGenerating(false);
    }
  }, []);

  return { downloadPDF, isGenerating };
}
