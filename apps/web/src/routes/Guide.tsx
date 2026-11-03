import { Link } from "react-router-dom";
import { Button } from "../components/ui/button";
const steps = [
  {
    title: "Start with the source",
    text: "Import text, Markdown or a text-based PDF, or explore a fictional demo. Source sections keep stable references within an immutable document.",
    to: "/import",
    action: "Import a procedure",
  },
  {
    title: "Model and review the rules",
    text: "Define choices and conditions, select supporting source sections, and verify every threshold yourself. A citation locates text; it does not prove that the rule represents it correctly.",
    to: "/library?tab=playbooks",
    action: "Open your models",
  },
  {
    title: "Author a rehearsal",
    text: "From a saved model, create a fictional scenario. Supply facts and schedule changes before named steps. Draft models require explicit consent when rehearsing.",
    to: "/library?tab=playbooks",
    action: "Choose a model",
  },
  {
    title: "Find the missing instruction",
    text: "Make real choices. No match stops on an uncovered path; multiple matches stop on overlap. A nonmatching selection records a deviation. The engine never invents an authoritative fallback.",
    to: "/simulation",
    action: "Explore the demo",
  },
  {
    title: "Rewind and test a change",
    text: "Open Replay Lab from a run to inspect a saved event or fork a decision. To change policy, save an explicitly unapproved proposal at a gap or overlap, rehearse it, then compare actual outcomes.",
    to: "/library?tab=sessions",
    action: "Open your rehearsals",
  },
  {
    title: "Keep the evidence",
    text: "Download a session or comparison report. Exports contain cited source text, exact replay inputs and logical events. Public demo workspaces expire, so export before the displayed deadline.",
    to: "/library?tab=sessions",
    action: "Find a report",
  },
];
export function Guide() {
  return (
    <section className="review-page">
      <span className="eyebrow">Getting started / Evidence first</span>
      <h1>A procedure you can put to the test.</h1>
      <p>
        GhostShift is a rehearsal tool. Start with the fictional Night Market
        demo for a complete example, then model your own procedure. No AI key is
        needed.
      </p>
      <div className="session-actions">
        <Button asChild>
          <Link to="/simulation?scenario=night-market">
            Explore the Night Market demo
          </Link>
        </Button>
        <Link to="/library">Open workspace</Link>
      </div>
      <ol className="guide-steps">
        {steps.map((step, index) => (
          <li className="panel report-section" key={step.title}>
            <span className="badge mint">Step {index + 1}</span>
            <h2>{step.title}</h2>
            <p>{step.text}</p>
            <Link to={step.to}>{step.action} ↗</Link>
          </li>
        ))}
      </ol>
      <section id="built-with-kiro" className="panel report-section">
        <span className="eyebrow">Build notes / Honest attribution</span>
        <h2>Built around a Kiro-authored engine.</h2>
        <p>
          Kiro authored the initial simulation specifications, deterministic
          engine and 60 tests. Codex separately reviewed and corrected the
          engine, then built persistence, policy review and this incident
          experience around it. The running app needs no AI key.
        </p>
        <p>
          <a href="https://github.com/joyboyreturns/GhostShift/blob/main/docs/kiro-evidence.md">
            Read the genuine Kiro contribution record ↗
          </a>
        </p>
        <p>
          <a href="https://github.com/joyboyreturns/GhostShift/tree/main/.kiro/specs/simulation-engine">
            Inspect the engine specifications ↗
          </a>
        </p>
      </section>
      <p className="muted">
        Keep live response decisions with qualified people. Source review and
        experiment completion are separate from operational authority.
      </p>
    </section>
  );
}
