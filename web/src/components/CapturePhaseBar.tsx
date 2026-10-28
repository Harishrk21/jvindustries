import { Icon } from "./Icon";

type Phase = "PHOTO" | "AI" | "CONFIRM" | "SAVE";

const PHASES: { id: Phase; label: string }[] = [
  { id: "PHOTO", label: "Photo" },
  { id: "AI", label: "AI read" },
  { id: "CONFIRM", label: "Confirm" },
  { id: "SAVE", label: "Save" },
];

export function CapturePhaseBar({ active }: { active: Phase }) {
  const idx = PHASES.findIndex((p) => p.id === active);
  return (
    <ol className="ve-phase" aria-label="Capture stages">
      {PHASES.map((p, i) => (
        <li key={p.id} className={i === idx ? "on" : i < idx ? "done" : ""}>
          <span className="ve-phase-dot">
            {i < idx ? <Icon name="check" size={12} weight="bold" /> : i + 1}
          </span>
          <span className="ve-phase-label">{p.label}</span>
        </li>
      ))}
    </ol>
  );
}
