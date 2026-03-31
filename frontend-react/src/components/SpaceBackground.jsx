import { useEffect, useRef } from 'react';

export default function SpaceBackground() {
  const containerRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const starCount = 100;
    for (let i = 0; i < starCount; i++) {
      const star = document.createElement('div');
      star.className = 'star';
      star.style.left = Math.random() * 100 + '%';
      star.style.top = Math.random() * 100 + '%';
      star.style.animationDelay = Math.random() * 3 + 's';
      star.style.animationDuration = (Math.random() * 2 + 2) + 's';
      container.appendChild(star);
    }
  }, []);

  return (
    <div className="space-background">
      <div className="stars-container" ref={containerRef}></div>
      <div className="shooting-star"></div>
      <div className="shooting-star shooting-star-delay-1"></div>
      <div className="shooting-star shooting-star-delay-2"></div>
    </div>
  );
}
