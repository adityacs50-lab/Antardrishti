import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "./api";

export interface QueryState<T> {
  data: T | undefined;
  error: string | undefined;
  loading: boolean;
  offline: boolean;
  refetch: () => void;
}

/**
 * Minimal fetch-on-mount hook. Deliberately tiny — no cache layer, no retries
 * that could mask an unreachable backend. `offline` is true only when the API
 * could not be reached at all, which the UI surfaces prominently rather than
 * papering over with sample data.
 *
 * Uses a generation counter (not a shared `alive` boolean) so React Strict Mode
 * remounts and fast route changes cannot drop the latest successful response
 * or leave the shell stuck on "Connecting…".
 */
export function useQuery<T>(fn: () => Promise<T>, deps: unknown[] = []): QueryState<T> {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<string>();
  const [offline, setOffline] = useState(false);
  const [loading, setLoading] = useState(true);
  const [nonce, setNonce] = useState(0);
  const generation = useRef(0);
  const fnRef = useRef(fn);
  fnRef.current = fn;

  useEffect(() => {
    const gen = ++generation.current;
    setLoading(true);
    fnRef
      .current()
      .then((result) => {
        if (gen !== generation.current) return;
        setData(result);
        setError(undefined);
        setOffline(false);
      })
      .catch((err: unknown) => {
        if (gen !== generation.current) return;
        const isApi = err instanceof ApiError;
        setError(err instanceof Error ? err.message : String(err));
        setOffline(isApi && err.status === undefined);
        setData(undefined);
      })
      .finally(() => {
        if (gen === generation.current) setLoading(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);

  const refetch = useCallback(() => setNonce((n) => n + 1), []);
  return { data, error, loading, offline, refetch };
}
