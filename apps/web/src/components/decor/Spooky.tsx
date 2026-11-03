/**
 * Decorative Halloween artwork. Every component is aria-hidden and carries no
 * product data; it never stands in for API state.
 */
import type { CSSProperties } from "react";

type DecorProps = { className?: string; style?: CSSProperties };

export function Bat({ className = "", style }: DecorProps) {
  return (
    <svg
      className={`decor-bat ${className}`}
      style={style}
      viewBox="0 0 64 28"
      aria-hidden="true"
      focusable="false"
    >
      <path
        className="bat-wing bat-wing-left"
        d="M32 12c-3-6-9-9-16-8 3 2 4 4 3 6-3-2-8-2-12 1 3 1 5 3 5 6-2-1-6-1-9 1 6 1 11 3 15 7 2-4 6-7 14-8z"
      />
      <path
        className="bat-wing bat-wing-right"
        d="M32 12c3-6 9-9 16-8-3 2-4 4-3 6 3-2 8-2 12 1-3 1-5 3-5 6 2-1 6-1 9 1-6 1-11 3-15 7-2-4-6-7-14-8z"
      />
      <ellipse cx="32" cy="14" rx="4" ry="5.5" />
      <path d="M29 9l1-4 2 3 2-3 1 4z" />
      <circle cx="30.6" cy="12.4" r="0.9" className="bat-eye" />
      <circle cx="33.4" cy="12.4" r="0.9" className="bat-eye" />
    </svg>
  );
}

export function Pumpkin({ className = "", style }: DecorProps) {
  return (
    <svg
      className={`decor-pumpkin ${className}`}
      style={style}
      viewBox="0 0 80 72"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M38 12c0-6 3-10 9-11l1 3c-4 1-6 4-6 8z" fill="#4c7a3a" />
      <path
        d="M47 6c6-3 12-1 14 3-5-1-9 0-12 2z"
        fill="#5f9446"
        opacity="0.9"
      />
      <ellipse cx="22" cy="42" rx="18" ry="26" fill="#d9601f" />
      <ellipse cx="58" cy="42" rx="18" ry="26" fill="#d9601f" />
      <ellipse cx="40" cy="42" rx="20" ry="28" fill="#f07a2a" />
      <ellipse cx="30" cy="42" rx="10" ry="27" fill="#ff8a3d" opacity="0.55" />
      <ellipse cx="50" cy="42" rx="10" ry="27" fill="#ff8a3d" opacity="0.55" />
      <g className="pumpkin-face">
        <path d="M24 34l8-8 8 8z" />
        <path d="M40 34l8-8 8 8z" />
        <path d="M37 42h6l-3 5z" />
        <path d="M20 50c6 8 34 8 40 0-3 1-5 2-7 1l-2 5-4-4-3 5-4-5-3 5-4-5-4 4-2-5c-2 1-4 0-7-1z" />
      </g>
    </svg>
  );
}

export function Cobweb({ className = "", style }: DecorProps) {
  const rings = [22, 44, 68, 94, 122];
  const spokes = [0, 15, 30, 45, 60, 75, 90];
  return (
    <svg
      className={`decor-web ${className}`}
      style={style}
      viewBox="0 0 160 160"
      aria-hidden="true"
      focusable="false"
      fill="none"
    >
      {spokes.map((angle) => {
        const rad = (angle * Math.PI) / 180;
        return (
          <line
            key={angle}
            x1="0"
            y1="0"
            x2={Math.cos(rad) * 160}
            y2={Math.sin(rad) * 160}
          />
        );
      })}
      {rings.map((radius) => (
        <path
          key={radius}
          d={spokes
            .map((angle, index) => {
              const rad = (angle * Math.PI) / 180;
              const x = (Math.cos(rad) * radius).toFixed(1);
              const y = (Math.sin(rad) * radius).toFixed(1);
              if (index === 0) return `M${x} ${y}`;
              const mid = ((angle - 7.5) * Math.PI) / 180;
              const sag = radius * 0.86;
              return `Q${(Math.cos(mid) * sag).toFixed(1)} ${(Math.sin(mid) * sag).toFixed(1)} ${x} ${y}`;
            })
            .join(" ")}
        />
      ))}
    </svg>
  );
}

export function Spider({ className = "", style }: DecorProps) {
  return (
    <span
      className={`decor-spider ${className}`}
      style={style}
      aria-hidden="true"
    >
      <svg viewBox="0 0 40 36" focusable="false">
        <g stroke="currentColor" strokeWidth="1.6" fill="none">
          <path d="M14 16c-5-4-9-4-12 0M14 19c-5-1-9 1-11 5M15 22c-4 2-6 5-6 10M15 13c-4-5-8-7-11-6" />
          <path d="M26 16c5-4 9-4 12 0M26 19c5-1 9 1 11 5M25 22c4 2 6 5 6 10M25 13c4-5 8-7 11-6" />
        </g>
        <ellipse cx="20" cy="18" rx="7" ry="8" fill="currentColor" />
        <circle cx="20" cy="9" r="4.5" fill="currentColor" />
        <circle cx="18.3" cy="8.6" r="1" fill="#ff6b7a" />
        <circle cx="21.7" cy="8.6" r="1" fill="#ff6b7a" />
      </svg>
    </span>
  );
}

export function Tombstone({
  className = "",
  style,
  lines,
}: DecorProps & { lines: string[] }) {
  return (
    <svg
      className={`decor-tomb ${className}`}
      style={style}
      viewBox="0 0 120 140"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M14 136V52C14 24 34 8 60 8s46 16 46 44v84z"
        className="tomb-stone"
      />
      <path d="M22 52c0-22 16-36 38-36" className="tomb-shine" fill="none" />
      <path d="M4 136h112v4H4z" className="tomb-ground" />
      <path
        d="M10 136c6-8 10-10 14-2 3-7 7-8 10 0M88 136c4-9 9-10 12-2 2-5 6-6 10 2"
        className="tomb-grass"
        fill="none"
      />
      <text x="60" y="50" textAnchor="middle" className="tomb-rip">
        R.I.P.
      </text>
      {lines.map((line, index) => (
        <text
          key={line}
          x="60"
          y={74 + index * 15}
          textAnchor="middle"
          className="tomb-text"
        >
          {line}
        </text>
      ))}
    </svg>
  );
}

export function Moon({ className = "", style }: DecorProps) {
  return (
    <svg
      className={`decor-moon ${className}`}
      style={style}
      viewBox="0 0 200 200"
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <radialGradient id="moon-face" cx="40%" cy="38%" r="65%">
          <stop offset="0" stopColor="#fffaf0" />
          <stop offset="0.6" stopColor="#f1e6c8" />
          <stop offset="1" stopColor="#cbb98f" />
        </radialGradient>
      </defs>
      <circle cx="100" cy="100" r="80" fill="url(#moon-face)" />
      <g fill="#bfae86" opacity="0.55">
        <circle cx="70" cy="80" r="14" />
        <circle cx="125" cy="128" r="18" />
        <circle cx="132" cy="70" r="8" />
        <circle cx="82" cy="138" r="7" />
        <circle cx="108" cy="96" r="5" />
      </g>
    </svg>
  );
}

/** Silhouette skyline: hills, a crooked tree, fence, tombstones and lit pumpkins. */
export function Graveyard({ className = "" }: { className?: string }) {
  return (
    <svg
      className={`decor-graveyard ${className}`}
      viewBox="0 0 1440 160"
      preserveAspectRatio="xMidYMax slice"
      aria-hidden="true"
      focusable="false"
    >
      <path
        className="gy-far"
        d="M0 120c120-40 260-50 400-20s300 30 440-10 360-50 600 10v60H0z"
      />
      <g className="gy-near">
        <path d="M0 140c200-25 380-20 560 0s420 15 620-5 200-10 260 0v25H0z" />
        {/* crooked tree */}
        <path d="M1180 140c4-30 2-56-10-82l6-2c8 16 12 30 13 44 8-18 22-30 40-36l2 6c-20 8-32 22-36 44-2 10-2 18-1 26z" />
        <path d="M1172 60c-14-6-24-16-30-30l5-3c6 12 16 21 28 26zM1206 74c14-12 30-16 46-12l-1 6c-14-3-28 0-40 10z" />
        {/* fence */}
        {Array.from({ length: 14 }, (_, index) => (
          <path key={index} d={`M${120 + index * 18} 140v-34l4-6 4 6v34z`} />
        ))}
        <path d="M118 112h254v4H118zM118 128h254v4H118z" />
        {/* tombstones */}
        <path d="M470 140v-30c0-12 9-20 20-20s20 8 20 20v30z" />
        <path d="M530 140v-22c0-9 7-15 15-15s15 6 15 15v22z" />
        <path d="M612 140v-44h8v-12h8v12h8v8h-8v36z" />
        <path d="M860 140v-26c0-10 8-17 17-17s17 7 17 17v26z" />
        <path d="M940 140v-36h6v-10h7v10h6v7h-6v29z" />
      </g>
      {/* pumpkins */}
      <g className="gy-pumpkins">
        <ellipse cx="700" cy="134" rx="16" ry="12" />
        <ellipse cx="730" cy="137" rx="11" ry="8" />
        <ellipse cx="1080" cy="135" rx="14" ry="10" />
      </g>
      <g className="gy-pumpkin-eyes">
        <path d="M692 131l4-4 4 4zM702 131l4-4 4 4zM694 137c4 3 10 3 14 0z" />
        <path d="M726 135l3-3 3 3zM733 135l3-3 3 3z" />
        <path d="M1073 132l4-4 4 4zM1082 132l4-4 4 4zM1074 138c4 2 9 2 12 0z" />
      </g>
    </svg>
  );
}
