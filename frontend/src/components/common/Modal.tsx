/** Shared confirmation dialog (COMPONENTS §6, Current since WF-02.03 D-48).
 *
 * A native <dialog> opened with showModal(): the page behind it is inert, so Tab stays inside the
 * dialog, and it sits in the top layer above the header and sidebar. Escape and Cancel close it
 * unless `busy` is set (a request is in flight). Focus goes to `initialFocus` (or the first control)
 * on open and returns to the element that had focus before, when it closes.
 *
 * Render it inside the dashboard so it inherits the --db-* theme tokens.
 */
import { useEffect, useId, useRef } from 'react';
import type { ReactNode, RefObject, SyntheticEvent } from 'react';

interface Props {
  open: boolean;
  /** Phrased as a question ("Approve this application?"). Rendered as the dialog's h3. */
  title: string;
  /** Called for Escape or the browser closing the dialog. Never called while `busy`. */
  onClose: () => void;
  /** While true, Escape is ignored so an in-flight request cannot be dismissed half-way. */
  busy?: boolean;
  initialFocus?: RefObject<HTMLElement | null>;
  children: ReactNode;
  /** Actions, right-aligned with gap-3: Cancel (secondary) first in the DOM, then confirm. */
  actions: ReactNode;
}

function restoreFocus(returnTo: { current: HTMLElement | null }) {
  const target = returnTo.current;
  returnTo.current = null;
  if (target?.isConnected) target.focus();
}

export default function Modal({ open, title, onClose, busy = false, initialFocus, children, actions }: Props) {
  const dialog = useRef<HTMLDialogElement>(null);
  const returnTo = useRef<HTMLElement | null>(null);
  const titleId = useId();
  const bodyId = useId();

  useEffect(() => {
    const node = dialog.current;
    if (!node) return;
    if (open && !node.open) {
      returnTo.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      node.showModal();
      (initialFocus?.current ?? node.querySelector<HTMLElement>('button, select, input, textarea, [tabindex]'))?.focus();
    } else if (!open && node.open) {
      node.close();
      // Synchronously, so a parent effect that runs after this one (for example, focusing a
      // result message) can still move focus somewhere else.
      restoreFocus(returnTo);
    }
  }, [open, initialFocus]);

  // A browser-initiated close also returns focus; never leave a modal open after unmounting.
  useEffect(() => {
    const node = dialog.current;
    if (!node) return;
    const restore = () => restoreFocus(returnTo);
    node.addEventListener('close', restore);
    return () => {
      node.removeEventListener('close', restore);
      if (node.open) node.close();
    };
  }, []);

  function cancel(event: SyntheticEvent<HTMLDialogElement>) {
    // Escape: the component state, not the browser, decides whether the dialog closes.
    event.preventDefault();
    if (!busy) onClose();
  }

  function closedByBrowser() {
    // Some browsers close anyway after a repeated Escape; keep the state in step. A queued close event
    // from an unmount/remount (React StrictMode on a dialog mounted already open) arrives after the
    // dialog was shown again: it is stale and must not dismiss the dialog.
    if (dialog.current?.open) return;
    if (open && !busy) onClose();
  }

  return (
    <dialog ref={dialog} aria-labelledby={titleId} aria-describedby={bodyId} onCancel={cancel} onClose={closedByBrowser}
      className="dashboard-dialog dashboard-panel m-auto w-[min(32rem,calc(100vw-2rem))] rounded-2xl border p-5 sm:p-6">
      <h3 id={titleId} className="dashboard-heading text-lg font-semibold">{title}</h3>
      <div id={bodyId} className="mt-3 space-y-3 text-sm">{children}</div>
      <div className="mt-6 flex flex-wrap justify-end gap-3">{actions}</div>
    </dialog>
  );
}
