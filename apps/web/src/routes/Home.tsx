import { Link } from "react-router-dom";
import {
  ArrowRight,
  FileText,
  GitBranch,
  Ghost,
  GitFork,
  FileCheck2,
  Play,
  ScrollText,
} from "lucide-react";
import { Button } from "../components/ui/button";
import {
  Bat,
  Cobweb,
  Pumpkin,
  Spider,
  Tombstone,
} from "../components/decor/Spooky";

const graves = [
  {
    lines: ["NO RULE", "MATCHED"],
    title: "Uncovered path",
    text: "Zero choices fit the facts. The run stops instead of guessing.",
    tone: "amber",
  },
  {
    lines: ["TWO RULES", "MATCHED"],
    title: "Potential overlap",
    text: "More than one choice fits. Precedence is undocumented, so it stops.",
    tone: "amber",
  },
  {
    lines: ["OFF THE", "MODEL"],
    title: "Deviation",
    text: "A person chose a path the model did not match. It is recorded, never hidden.",
    tone: "coral",
  },
];

const pillars = [
  {
    icon: FileText,
    title: "Read the source",
    text: "Import text, Markdown or a text-based PDF. Every section gets a stable, citable reference in an immutable document.",
    tone: "violet",
  },
  {
    icon: GitBranch,
    title: "Trace the rules",
    text: "Model decisions as declarative conditions, linked to the exact sentences they rely on. Humans approve; citations only locate.",
    tone: "mint",
  },
  {
    icon: Ghost,
    title: "Find the ghosts",
    text: "Rehearse a fictional disruption. When no rule matches, or two do, the run stops and shows you the gap — no invented answers.",
    tone: "amber",
  },
];

const ritual = [
  { icon: Play, label: "Rehearse", text: "Make real choices" },
  { icon: Ghost, label: "Expose", text: "Stop on uncovered paths" },
  { icon: GitFork, label: "Fork", text: "Rewind to a checkpoint" },
  { icon: FileCheck2, label: "Compare", text: "Export what changed" },
];

export function Home() {
  return (
    <div className="home">
      <section className="home-hero">
        <div className="home-copy">
          <span className="eyebrow">Kiroween 2026 · Operational rehearsal</span>
          <h1>
            Every playbook
            <br />
            has a <em>ghost path.</em>
            <br />
            Find it first.
          </h1>
          <p className="home-lede">
            GhostShift turns static procedures into source-linked decision
            graphs, then haunts them with realistic disruptions. Expose missing
            or conflicting instructions before a real incident does.
          </p>
          <div className="hero-actions">
            <Button asChild>
              <Link to="/studio">
                Explore demo <ArrowRight size={18} />
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link to="/import">Import procedure</Link>
            </Button>
            <Button asChild variant="ghost">
              <Link to="/guide">
                <ScrollText size={16} /> How it works
              </Link>
            </Button>
          </div>
          <p className="home-foot">
            Fictional demo data · No AI key required · Deterministic, replayable
            runs
          </p>
        </div>
        <HauntedGraph />
      </section>

      <section className="home-pillars" aria-label="What GhostShift does">
        <Spider className="pillars-spider" />
        {pillars.map(({ icon: Icon, title, text, tone }, index) => (
          <article className={`pillar pillar-${tone}`} key={title}>
            <span className="pillar-index">0{index + 1}</span>
            <span className="pillar-icon">
              <Icon size={22} aria-hidden="true" />
            </span>
            <h2>{title}</h2>
            <p>{text}</p>
          </article>
        ))}
      </section>

      <section className="home-graveyard" aria-labelledby="graveyard-heading">
        <Cobweb className="graveyard-web" />
        <div className="graveyard-copy">
          <span className="eyebrow">The graveyard of missing rules</span>
          <h2 id="graveyard-heading">
            Three ways a playbook gives up the ghost.
          </h2>
          <p>
            The engine never invents an authoritative answer. These are the
            findings a rehearsal can surface, each linked back to the source.
          </p>
        </div>
        <ul className="graves">
          {graves.map((grave) => (
            <li key={grave.title} className={`grave grave-${grave.tone}`}>
              <Tombstone lines={grave.lines} />
              <h3>{grave.title}</h3>
              <p>{grave.text}</p>
            </li>
          ))}
        </ul>
        <div className="graveyard-pumpkins">
          <Pumpkin className="pumpkin-lg" />
          <Pumpkin className="pumpkin-sm" />
        </div>
      </section>

      <section className="home-ritual" aria-labelledby="ritual-heading">
        <div>
          <span className="eyebrow">The séance, step by step</span>
          <h2 id="ritual-heading">
            Unit tests for the playbooks nobody reads.
          </h2>
        </div>
        <ol>
          {ritual.map(({ icon: Icon, label, text }) => (
            <li key={label}>
              <Icon size={18} aria-hidden="true" />
              <strong>{label}</strong>
              <span>{text}</span>
            </li>
          ))}
        </ol>
        <Link className="ritual-link" to="/guide">
          Read the getting-started guide <ArrowRight size={15} />
        </Link>
      </section>

      <p className="home-disclaimer">
        A rehearsal and documentation-testing tool, not a live emergency
        response system. Evidence first. Human judgment always.
      </p>
    </div>
  );
}

/** Decorative illustration only: an abstract page dissolving into a graph. */
function HauntedGraph() {
  return (
    <div className="haunted-graph" aria-hidden="true">
      <div className="hg-moon" />
      <Bat className="hg-bat hg-bat-1" />
      <Bat className="hg-bat hg-bat-2" />
      <Bat className="hg-bat hg-bat-3" />
      <Pumpkin className="hg-pumpkin hg-pumpkin-1" />
      <Pumpkin className="hg-pumpkin hg-pumpkin-2" />
      <svg
        className="hg-scene"
        viewBox="0 0 460 420"
        role="presentation"
        focusable="false"
      >
        <defs>
          <linearGradient id="hg-edge" x1="0" x2="1">
            <stop offset="0" stopColor="#a78bfa" stopOpacity="0.2" />
            <stop offset="1" stopColor="#7cf5c6" stopOpacity="0.9" />
          </linearGradient>
          <radialGradient id="hg-glow">
            <stop offset="0" stopColor="#7cf5c6" stopOpacity="0.55" />
            <stop offset="1" stopColor="#7cf5c6" stopOpacity="0" />
          </radialGradient>
          <filter id="hg-blur" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="6" />
          </filter>
        </defs>

        {/* Source page */}
        <g className="hg-page">
          <rect
            x="18"
            y="70"
            width="150"
            height="196"
            rx="14"
            fill="#161128"
            stroke="#a78bfa"
            strokeOpacity="0.4"
          />
          {[0, 1, 2, 3, 4, 5, 6].map((line) => (
            <rect
              key={line}
              className="hg-line"
              x="38"
              y={98 + line * 22}
              width={line % 3 === 2 ? 70 : 108}
              height="6"
              rx="3"
              fill={line === 3 ? "#7cf5c6" : "#a78bfa"}
              opacity={line === 3 ? 0.9 : 0.32}
              style={{ animationDelay: `${line * 0.25}s` }}
            />
          ))}
        </g>

        {/* Edges */}
        <g fill="none" strokeWidth="2" className="hg-edges">
          <path
            d="M146 167 C 200 167, 200 110, 252 110"
            stroke="url(#hg-edge)"
          />
          <path
            d="M302 110 C 340 110, 340 200, 378 200"
            stroke="url(#hg-edge)"
          />
          <path d="M302 110 C 330 110, 320 60, 380 52" stroke="url(#hg-edge)" />
          <path
            d="M146 167 C 210 190, 210 300, 262 310"
            stroke="#ff6b7a"
            strokeOpacity="0.6"
            strokeDasharray="5 7"
          />
        </g>

        {/* Nodes */}
        <circle cx="277" cy="110" r="38" fill="url(#hg-glow)" />
        <rect
          x="252"
          y="90"
          width="50"
          height="40"
          rx="12"
          fill="#211a3a"
          stroke="#ffb45c"
        />
        <rect
          x="378"
          y="182"
          width="58"
          height="36"
          rx="12"
          fill="#211a3a"
          stroke="#7cf5c6"
        />
        <rect
          x="380"
          y="34"
          width="58"
          height="36"
          rx="12"
          fill="#211a3a"
          stroke="#c9b8ff"
        />
        <circle
          cx="290"
          cy="312"
          r="30"
          fill="#ff6b7a"
          opacity="0.18"
          filter="url(#hg-blur)"
        />
        <rect
          x="262"
          y="292"
          width="56"
          height="40"
          rx="12"
          fill="none"
          stroke="#ff6b7a"
          strokeDasharray="4 5"
        />

        {/* Ghost peeking at the uncovered branch */}
        <g className="hg-ghost">
          <path
            d="M330 300c0-26 18-44 40-44s40 18 40 44v52l-10-9-10 9-10-9-10 9-10-9-10 9-10-9z"
            fill="#f3f0fa"
            opacity="0.94"
          />
          <ellipse cx="358" cy="296" rx="5" ry="7" fill="#0a0714" />
          <ellipse cx="384" cy="296" rx="5" ry="7" fill="#0a0714" />
          <ellipse
            cx="371"
            cy="318"
            rx="6"
            ry="4"
            fill="#0a0714"
            opacity="0.8"
          />
        </g>
        <text
          x="290"
          y="317"
          textAnchor="middle"
          fontSize="18"
          fill="#ff6b7a"
          fontFamily="JetBrains Mono Variable, monospace"
        >
          ?
        </text>
      </svg>
    </div>
  );
}
