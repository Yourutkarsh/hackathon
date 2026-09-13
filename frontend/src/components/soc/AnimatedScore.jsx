import { useEffect, useRef, useState } from "react";
import { animate } from "framer-motion";

// Count-up display for a backend-provided number. Purely visual; the value
// itself is always the authoritative backend score.
export function AnimatedScore({ value, decimals = 2, className }) {
  const target = typeof value === "number" ? value : 0;
  const [display, setDisplay] = useState(target);
  const prev = useRef(target);

  useEffect(() => {
    const controls = animate(prev.current, target, {
      duration: 0.9,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => setDisplay(v),
    });
    prev.current = target;
    return () => controls.stop();
  }, [target]);

  return <span className={className}>{display.toFixed(decimals)}</span>;
}
