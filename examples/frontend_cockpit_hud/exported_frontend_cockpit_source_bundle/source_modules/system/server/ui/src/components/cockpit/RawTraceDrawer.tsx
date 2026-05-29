// [PURPOSE] Raw Trace drawer for the cockpit — Surface 4.
//
// In Pass 1 the drawer mounts the legacy AgentDiagnostics body (.claude/ +
// .codex/ wiring snapshot) so the original /agent-diagnostics URL still
// surfaces what it always did, just demoted from primary view to drilldown.
//
// In Pass 3 (out of scope here) this drawer will switch to per-session JSONL
// trace paging via /api/cockpit/sessions/{id}/trace.
import { useEffect, useState, type ReactNode } from 'react';
import clsx from 'clsx';
import { ChevronDown, ChevronUp, Terminal } from 'lucide-react';
import AgentDiagnostics from '../../pages/AgentDiagnostics';
import { getSafeLocalStorage } from '../../lib/browserStorage';

const STORAGE_KEY = 'cockpit_raw_trace_open';

function readStoredOpen(): boolean {
  try {
    return getSafeLocalStorage()?.getItem(STORAGE_KEY) === 'true';
  } catch {
    return false;
  }
}

export default function RawTraceDrawer({
  defaultOpen,
  hostNote,
}: {
  defaultOpen?: boolean;
  hostNote?: ReactNode;
} = {}) {
  const [open, setOpen] = useState<boolean>(() => defaultOpen ?? readStoredOpen());

  useEffect(() => {
    try {
      getSafeLocalStorage()?.setItem(STORAGE_KEY, String(open));
    } catch {
      // best-effort; localStorage may be unavailable in capture mode
    }
  }, [open]);

  return (
    <section
      data-cockpit-section="raw-trace"
      className={clsx(
        'shrink-0 rounded-[14px] border border-white/[0.10] bg-black/30',
        open ? 'flex flex-col min-h-0' : '',
      )}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-white/80 transition-colors hover:text-white"
        aria-expanded={open}
      >
        <Terminal size={12} className="text-white/45" />
        <span className="font-mono text-[11px] uppercase tracking-[0.2em]">
          Raw trace · agent dotfiles
        </span>
        <span className="ml-auto font-mono text-[9.5px] uppercase tracking-[0.2em] text-white/40">
          {open ? 'collapse' : 'expand'}
        </span>
        {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>
      {hostNote && open && (
        <div className="mx-3 mb-2 rounded-[10px] border border-white/[0.10] bg-white/[0.03] px-3 py-2 text-[11px] leading-[1.45] text-white/65">
          {hostNote}
        </div>
      )}
      {open && (
        <div className="min-h-[480px] flex-1 overflow-hidden border-t border-white/[0.08]">
          {/*
            AgentDiagnostics owns its own dashboard-shell + scroll region. We
            host it inside a bounded container so the drawer scrolls
            independently from the cockpit body.
          */}
          <AgentDiagnostics />
        </div>
      )}
    </section>
  );
}
