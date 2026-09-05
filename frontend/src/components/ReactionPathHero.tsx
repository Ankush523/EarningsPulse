/**
 * The after-hours print, drawn: one price path runs into the report, then
 * branches into the three outcomes the playbook models. Draws once on load.
 */

const OUTCOMES = [
  { label: "Beat, dips then rallies", color: "var(--up)", y: 100 },
  { label: "Inline, stays muted", color: "var(--ink-soft)", y: 216 },
  { label: "Miss, gaps down", color: "var(--down)", y: 350 },
] as const;

export function ReactionPathHero() {
  return (
    <figure className="glass-chip m-0 rounded-2xl p-3 sm:p-4">
      <svg
        viewBox="0 0 760 430"
        className="h-auto w-full"
        role="img"
        aria-label="A stock price path running into the earnings report and branching into three outcomes: a beat that dips then rallies, an inline print that stays muted, and a miss that gaps down."
      >
        <line
          x1="260"
          y1="48"
          x2="260"
          y2="392"
          stroke="var(--rule)"
          strokeWidth="1.25"
          strokeDasharray="3 6"
        />
        <text
          x="260"
          y="416"
          textAnchor="middle"
          fill="var(--ink-soft)"
          fontSize="15"
          fontStyle="italic"
          className="hidden sm:block"
        >
          4:00 pm, the report
        </text>

        <path
          d="M0 214 C 35 212, 50 224, 80 208 S 125 188, 160 200 S 215 224, 240 208 S 252 206, 260 210"
          fill="none"
          stroke="var(--ink)"
          strokeWidth="2.75"
          strokeLinecap="round"
          pathLength={1}
          className="draw-path"
        />

        <path
          d="M260 210 C 280 210, 296 278, 318 270 S 356 204, 400 176 S 520 116, 560 100"
          fill="none"
          stroke="var(--up)"
          strokeWidth="2.75"
          strokeLinecap="round"
          pathLength={1}
          className="draw-path draw-path-late"
        />
        <path
          d="M260 210 C 320 210, 340 226, 390 214 S 500 206, 560 216"
          fill="none"
          stroke="var(--ink-soft)"
          strokeWidth="2.75"
          strokeLinecap="round"
          pathLength={1}
          className="draw-path draw-path-late"
        />
        <path
          d="M260 210 C 268 210, 272 302, 292 318 S 420 346, 560 350"
          fill="none"
          stroke="var(--down)"
          strokeWidth="2.75"
          strokeLinecap="round"
          pathLength={1}
          className="draw-path draw-path-late"
        />

        <g className="draw-label" fontSize="17">
          {OUTCOMES.map((outcome) => (
            <g key={outcome.label}>
              <circle cx="560" cy={outcome.y} r="4.5" fill={outcome.color} />
              <text
                x="574"
                y={outcome.y + 5.5}
                fill={outcome.color}
                className="hidden sm:block"
              >
                {outcome.label}
              </text>
            </g>
          ))}
        </g>
      </svg>
      <figcaption className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-[0.9rem] sm:hidden">
        <span className="italic text-ink-soft">Dashed line: 4:00 pm, the report.</span>
        {OUTCOMES.map((outcome) => (
          <span key={outcome.label} className="flex items-center gap-2" style={{ color: outcome.color }}>
            <span
              aria-hidden
              className="inline-block h-2 w-2 rounded-full"
              style={{ background: outcome.color }}
            />
            {outcome.label}
          </span>
        ))}
      </figcaption>
    </figure>
  );
}
