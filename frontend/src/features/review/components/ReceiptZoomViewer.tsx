import { useState, useRef, useCallback } from "react";
import { useTranslation } from "react-i18next";

interface ReceiptZoomViewerProps {
  src: string;
  onRefreshed: (newUrl: string) => void;
  onRefreshError: () => void;
}

export default function ReceiptZoomViewer({ src, onRefreshed: _onRefreshed, onRefreshError }: ReceiptZoomViewerProps) {
  const { t } = useTranslation("review");
  const [error, setError] = useState(false);
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const containerRef = useRef<HTMLDivElement>(null);
  const isDragging = useRef(false);
  const lastPos = useRef({ x: 0, y: 0 });
  const hasAutoRefreshed = useRef(false);
  const currentSrc = useRef(src);

  if (src !== currentSrc.current) {
    currentSrc.current = src;
    setError(false);
    hasAutoRefreshed.current = false;
  }

  const handleImageError = useCallback(() => {
    if (!hasAutoRefreshed.current) {
      hasAutoRefreshed.current = true;
      onRefreshError();
      return;
    }
    setError(true);
  }, [onRefreshError]);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    setScale((prev) => Math.min(Math.max(prev + (e.deltaY > 0 ? -0.1 : 0.1), 0.5), 5));
  }, []);

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    isDragging.current = true;
    lastPos.current = { x: e.clientX, y: e.clientY };
  }, []);

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    if (!isDragging.current) return;
    const dx = e.clientX - lastPos.current.x;
    const dy = e.clientY - lastPos.current.y;
    setPosition((prev) => ({ x: prev.x + dx, y: prev.y + dy }));
    lastPos.current = { x: e.clientX, y: e.clientY };
  }, []);

  const handlePointerUp = useCallback(() => {
    isDragging.current = false;
  }, []);

  const handleDoubleClick = useCallback(() => {
    setScale((prev) => (prev > 1 ? 1 : 2.5));
  }, []);

  const handlePinchStart = useCallback((e: React.TouchEvent) => {
    if (e.touches.length !== 2) return;
    const dx = e.touches[0].clientX - e.touches[1].clientX;
    const dy = e.touches[0].clientY - e.touches[1].clientY;
    lastPos.current = { x: Math.sqrt(dx * dx + dy * dy), y: 0 };
  }, []);

  const handlePinchMove = useCallback((e: React.TouchEvent) => {
    if (e.touches.length !== 2) return;
    const dx = e.touches[0].clientX - e.touches[1].clientX;
    const dy = e.touches[0].clientY - e.touches[1].clientY;
    const dist = Math.sqrt(dx * dx + dy * dy);
    const delta = dist - lastPos.current.x;
    setScale((prev) => Math.min(Math.max(prev + delta * 0.005, 0.5), 5));
    lastPos.current = { x: dist, y: 0 };
  }, []);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center p-8 bg-gray-800 rounded-lg text-gray-400">
        <p>{t("detail.receiptLoadError")}</p>
        <button
          onClick={() => {
            setError(false);
            hasAutoRefreshed.current = false;
            onRefreshError();
          }}
          className="mt-3 px-4 py-2 bg-gray-700 rounded hover:bg-gray-600 min-h-[44px]"
        >
          {t("detail.receiptRetry")}
        </button>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="relative overflow-hidden rounded-lg bg-gray-800 cursor-grab active:cursor-grabbing"
      style={{ minHeight: "300px", maxHeight: "70vh", touchAction: "none" }}
      onWheel={handleWheel}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerLeave={handlePointerUp}
      onDoubleClick={handleDoubleClick}
      onTouchStart={handlePinchStart}
      onTouchMove={handlePinchMove}
      role="img"
      aria-label={t("detail.receipt")}
    >
      <div
        style={{
          transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`,
          transformOrigin: "center center",
          transition: isDragging.current ? "none" : "transform 0.1s ease-out",
        }}
      >
        <img
          src={src}
          alt={t("detail.receipt")}
          className="max-w-full block"
          onError={handleImageError}
          draggable={false}
        />
      </div>
      <div className="absolute bottom-2 end-2 flex gap-1">
        <button
          onClick={() => setScale((s) => Math.min(s + 0.2, 5))}
          className="w-11 h-11 bg-gray-700/80 rounded text-white text-lg flex items-center justify-center hover:bg-gray-600"
          aria-label={t("detail.zoomIn")}
        >
          +
        </button>
        <button
          onClick={() => setScale((s) => Math.max(s - 0.2, 0.5))}
          className="w-11 h-11 bg-gray-700/80 rounded text-white text-lg flex items-center justify-center hover:bg-gray-600"
          aria-label={t("detail.zoomOut")}
        >
          −
        </button>
      </div>
    </div>
  );
}
