import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import type { ApiError } from '../../api/client';

export default function ApiErrorNotice({ error, children }: { error: ApiError; children?: ReactNode }) {
  const notice = useRef<HTMLDivElement>(null);
  useEffect(() => { notice.current?.focus(); }, [error]);
  return (
    <div ref={notice} role="alert" aria-live="assertive" aria-atomic="true" tabIndex={-1}
      className="notice mt-4 space-y-3 rounded-lg p-3 text-sm focus-visible:outline-2 focus-visible:outline-offset-2">
      <p>{error.message}</p>
      {error.requestId && <p className="text-xs">Request reference: <span>{error.requestId}</span></p>}
      {children}
    </div>
  );
}
