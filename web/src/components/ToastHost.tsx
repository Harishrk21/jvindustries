import { Icon } from "./Icon";
import { useToast, type ToastKind } from "../state/toast";

function kindIcon(kind: ToastKind) {
  if (kind === "success") return "check" as const;
  if (kind === "error") return "shield" as const;
  return "bell" as const;
}

export function ToastHost() {
  const items = useToast((s) => s.items);
  const dismiss = useToast((s) => s.dismiss);

  if (items.length === 0) return null;

  return (
    <div className="toast-host" aria-live="polite" aria-relevant="additions">
      {items.map((t) => (
        <div key={t.id} className={`toast toast-${t.kind}`} role="status">
          <span className="toast-ico">
            <Icon name={kindIcon(t.kind)} size={18} weight="bold" />
          </span>
          <div className="toast-body">
            <strong>{t.title}</strong>
            {t.detail ? <span>{t.detail}</span> : null}
          </div>
          <button type="button" className="toast-x" aria-label="Dismiss" onClick={() => dismiss(t.id)}>
            ✕
          </button>
        </div>
      ))}
    </div>
  );
}
