import type { YardStepId } from "../lib/yardSteps";

const ENTRY: { id: YardStepId; label: string }[] = [
  { id: "location", label: "Location" },
  { id: "type", label: "Type" },
  { id: "lorry", label: "Photo" },
  { id: "driver", label: "Driver" },
  { id: "gate", label: "Gate" },
];

type Props = {
  step: YardStepId;
  doneIds: Set<YardStepId>;
};

export function YardEntryRail({ step, doneIds }: Props) {
  const order = ENTRY.map((e) => e.id) as string[];
  const pastEntry = !ENTRY.some((e) => e.id === step);
  const currentIdx = pastEntry ? ENTRY.length - 1 : Math.max(0, order.indexOf(step));
  const current = ENTRY[Math.min(currentIdx, ENTRY.length - 1)];

  return (
    <div className="ve-progress" aria-label="Vehicle entry progress">
      <div className="ve-progress-meta">
        <strong>
          Step {Math.min(currentIdx + 1, ENTRY.length)}/{ENTRY.length}
        </strong>
        <span>{pastEntry ? "Entry done" : current.label}</span>
      </div>
      <div className="ve-progress-track" aria-hidden>
        {ENTRY.map((e, i) => {
          const done =
            pastEntry ||
            doneIds.has(e.id) ||
            (e.id !== "location" && i < currentIdx) ||
            (e.id === "location" && currentIdx > 0);
          const active = !pastEntry && e.id === step;
          return <i key={e.id} className={`${done ? "done" : ""}${active ? " active" : ""}`} />;
        })}
      </div>
    </div>
  );
}
