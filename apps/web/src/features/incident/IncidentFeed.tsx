import { useState } from "react";
import { Radio, Volume2, VolumeX } from "lucide-react";
import { Button } from "../../components/ui/button";
import type { SimulationSession } from "../../lib/api";
import { incidentUpdates, type Story } from "./narrative";

export function IncidentFeed({
  session,
  story,
}: {
  session: SimulationSession;
  story?: Story;
}) {
  const updates = incidentUpdates(session, story);
  const [shown, setShown] = useState(1);
  const [all, setAll] = useState(false);
  const [sound, setSound] = useState(false);
  const [audioError, setAudioError] = useState("");
  const visible = all ? updates : updates.slice(0, shown);
  const remaining = updates.length - visible.length;

  async function chime() {
    if (!sound) return;
    try {
      const context = new AudioContext();
      await context.resume();
      const oscillator = context.createOscillator();
      const gain = context.createGain();
      oscillator.type = "sine";
      oscillator.frequency.setValueAtTime(620, context.currentTime);
      oscillator.frequency.exponentialRampToValueAtTime(
        420,
        context.currentTime + 0.18,
      );
      gain.gain.setValueAtTime(0.04, context.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, context.currentTime + 0.22);
      oscillator.connect(gain).connect(context.destination);
      oscillator.start();
      oscillator.stop(context.currentTime + 0.23);
      oscillator.onended = () => {
        oscillator.disconnect();
        gain.disconnect();
        void context.close().catch(() => {
          setSound(false);
          setAudioError(
            "Audio could not close cleanly. Sound is now off; text updates remain available.",
          );
        });
      };
    } catch {
      setSound(false);
      setAudioError(
        "Sound is unavailable in this browser. All updates remain available as text.",
      );
    }
  }
  return (
    <section
      className="panel incident-feed"
      aria-labelledby="incident-feed-heading"
    >
      <header className="panel-heading">
        <div>
          <span className="eyebrow">
            <Radio size={14} aria-hidden="true" /> Incident channel
          </span>
          <h2 id="incident-feed-heading">Dispatch log</h2>
        </div>
        <button
          className="text-action"
          aria-pressed={sound}
          onClick={() => {
            setSound(!sound);
            setAudioError("");
          }}
        >
          {sound ? (
            <Volume2 size={16} aria-hidden="true" />
          ) : (
            <VolumeX size={16} aria-hidden="true" />
          )}
          Sound {sound ? "on" : "off"}
        </button>
      </header>
      <p className="muted">
        User-paced playback of recorded events. Your active decision is always
        available below.
      </p>
      <ol
        className="dispatch-list"
        aria-label="Recorded incident updates"
        tabIndex={0}
      >
        {visible.map((update) => (
          <li key={update.id}>
            <span className="dispatch-index">
              {String(update.sequence + 1).padStart(2, "0")}
            </span>
            <div>
              <strong>{update.title}</strong>
              <p>{update.detail}</p>
              <span className="eyebrow">
                Stored event {update.sequence + 1}
              </span>
            </div>
          </li>
        ))}
      </ol>
      <p role="status" className="muted">
        {remaining
          ? `${remaining} more recorded updates to inspect`
          : "All recorded updates shown"}
      </p>
      <div className="session-actions">
        <Button
          variant="outline"
          disabled={!remaining}
          onClick={() => {
            setShown(visible.length + 1);
            void chime();
          }}
        >
          Next update
        </Button>
        <button
          className="text-action"
          disabled={!remaining}
          onClick={() => setAll(true)}
        >
          Show all updates
        </button>
        <a href="#active-decision">Go to active decision ↓</a>
      </div>
      {audioError && <p role="status">{audioError}</p>}
    </section>
  );
}
