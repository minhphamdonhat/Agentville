/*
 * Press & Paper ephemera: decorative inline SVGs for margins and section
 * openers only. Every ornament is aria-hidden and unfocusable, carries no
 * information of its own and never sits over text; whatever it says is also
 * written as live text on the page.
 */
import type {ReactNode} from 'react';

const INK = '#222020';
const BRICK = '#A32A22';
const RUST = '#9C2F16';
const MUSTARD = '#D4A017';
const CARD = '#FBF6EC';
const CREAM = '#F3E9DC';

type OrnamentProps = {className?: string};

function range(count: number): number[] {
  return Array.from({length: count}, (_, i) => i);
}

/** Perforated postage stamp: Agentville, 2026, Claude. */
export function Stamp({className}: OrnamentProps): ReactNode {
  const width = 120;
  const height = 150;
  const step = 10;
  const radius = 3.2;
  return (
    <svg
      className={className}
      aria-hidden="true"
      focusable="false"
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}>
      <rect width={width} height={height} fill={CARD} />
      {range(width / step + 1).map((i) => (
        <g key={`h${i}`}>
          <circle cx={i * step} cy={0} r={radius} fill={CREAM} />
          <circle cx={i * step} cy={height} r={radius} fill={CREAM} />
        </g>
      ))}
      {range(height / step + 1).map((i) => (
        <g key={`v${i}`}>
          <circle cx={0} cy={i * step} r={radius} fill={CREAM} />
          <circle cx={width} cy={i * step} r={radius} fill={CREAM} />
        </g>
      ))}
      <rect x="11" y="11" width={width - 22} height={height - 22} fill="none" stroke={BRICK} strokeWidth="2" />
      <rect x="15" y="15" width={width - 30} height={height - 30} fill="none" stroke={BRICK} strokeWidth="0.75" />
      <text
        x={width / 2}
        y="34"
        textAnchor="middle"
        fill={BRICK}
        fontFamily="Oswald, 'Arial Narrow', sans-serif"
        fontSize="11"
        letterSpacing="2">
        AGENTVILLE
      </text>
      <path d="M38 98 L60 56 L82 98 Z" fill="none" stroke={INK} strokeWidth="4" />
      <rect x="56" y="80" width="8" height="8" fill={INK} />
      <text
        x={width / 2}
        y="122"
        textAnchor="middle"
        fill={INK}
        fontFamily="Anton, Impact, sans-serif"
        fontSize="18"
        letterSpacing="1">
        2026
      </text>
    </svg>
  );
}

/** Circular postmark with wavy cancellation lines. */
export function Postmark({className}: OrnamentProps): ReactNode {
  return (
    <svg
      className={className}
      aria-hidden="true"
      focusable="false"
      width="190"
      height="96"
      viewBox="0 0 190 96">
      <g fill="none" stroke={RUST} strokeWidth="1.6" opacity="0.85">
        <circle cx="48" cy="48" r="42" />
        <circle cx="48" cy="48" r="30" />
        <path id="pp-postmark-arc" d="M14 48 A34 34 0 0 1 82 48" stroke="none" />
        {range(4).map((i) => (
          <path
            key={i}
            d={`M92 ${24 + i * 16} q12 -7 24 0 t24 0 t24 0 t24 0`}
            strokeWidth="1.8"
          />
        ))}
      </g>
      <text fill={RUST} opacity="0.85" fontFamily="Oswald, 'Arial Narrow', sans-serif" fontSize="9" letterSpacing="2">
        <textPath href="#pp-postmark-arc" startOffset="50%" textAnchor="middle">
          CHECKED · AGENTVILLE
        </textPath>
      </text>
      <text
        x="48"
        y="53"
        textAnchor="middle"
        fill={RUST}
        opacity="0.85"
        fontFamily="Oswald, 'Arial Narrow', sans-serif"
        fontSize="12"
        letterSpacing="1">
        REPORTED
      </text>
      <text
        x="48"
        y="68"
        textAnchor="middle"
        fill={RUST}
        opacity="0.85"
        fontFamily="Oswald, 'Arial Narrow', sans-serif"
        fontSize="8"
        letterSpacing="1.5">
        2026
      </text>
    </svg>
  );
}

/** Rust wax seal with an AV monogram; one per page. */
export function WaxSeal({className}: OrnamentProps): ReactNode {
  return (
    <svg
      className={className}
      aria-hidden="true"
      focusable="false"
      width="88"
      height="88"
      viewBox="0 0 88 88">
      <path
        d="M44 3 C52 6 56 2 63 8 C70 13 76 12 79 21 C83 29 87 33 84 42 C82 50 86 56 80 63 C75 70 74 76 65 79 C57 82 53 87 44 85 C36 83 30 87 23 81 C16 76 10 75 7 66 C4 58 0 53 3 44 C5 36 1 30 7 23 C12 16 14 10 23 7 C31 4 36 1 44 3 Z"
        fill={RUST}
      />
      <circle cx="44" cy="44" r="27" fill="none" stroke="#7A2410" strokeWidth="3" />
      <circle cx="44" cy="44" r="22" fill="none" stroke="#C0573A" strokeWidth="0.8" opacity="0.7" />
      <text
        x="44"
        y="54"
        textAnchor="middle"
        fill={CREAM}
        fontFamily="Anton, Impact, sans-serif"
        fontSize="26"
        letterSpacing="1">
        AV
      </text>
    </svg>
  );
}

/** Handwritten note on a small taped card. The same words are live text nearby. */
export function HandNote({className, lines}: OrnamentProps & {lines: [string, string]}): ReactNode {
  return (
    <svg
      className={className}
      aria-hidden="true"
      focusable="false"
      width="190"
      height="130"
      viewBox="0 0 190 130">
      <rect x="10" y="16" width="170" height="104" fill={CARD} stroke={INK} strokeWidth="0.75" />
      {range(4).map((i) => (
        <line key={i} x1="22" x2="168" y1={52 + i * 18} y2={52 + i * 18} stroke="#C9A878" strokeWidth="0.75" />
      ))}
      <rect x="70" y="4" width="54" height="22" fill={MUSTARD} opacity="0.55" transform="rotate(-4 97 15)" />
      <text
        x="26"
        y="64"
        fill={INK}
        fontFamily="'Segoe Print', 'Bradley Hand', 'Comic Sans MS', cursive"
        fontSize="19">
        {lines[0]}
      </text>
      <text
        x="26"
        y="92"
        fill={INK}
        fontFamily="'Segoe Print', 'Bradley Hand', 'Comic Sans MS', cursive"
        fontSize="17">
        {lines[1]}
      </text>
      <path d="M26 101 q20 6 40 0 t40 0" fill="none" stroke={BRICK} strokeWidth="1.6" />
    </svg>
  );
}

/** Thin barcode used as an ornament beside the folio. */
export function Barcode({className}: OrnamentProps): ReactNode {
  const bars = [2, 1, 3, 1, 1, 2, 1, 3, 2, 1, 1, 2, 3, 1, 2, 1, 1, 3, 1, 2, 2, 1, 3, 1, 1, 2];
  let x = 0;
  return (
    <svg
      className={className}
      aria-hidden="true"
      focusable="false"
      width="96"
      height="30"
      viewBox="0 0 96 30">
      {bars.map((w, i) => {
        const bar = i % 2 === 0 ? <rect key={i} x={x} y="0" width={w} height="30" fill={INK} /> : null;
        x += w + 1;
        return bar;
      })}
    </svg>
  );
}
