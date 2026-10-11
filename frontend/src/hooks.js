import { useCallback, useEffect, useState } from "react";
import { parseError } from "./api/client";

/** Runs an async loader; exposes {body, data, loading, error, reload}. Never substitutes fake data on failure. */
export function useFetch(loader, deps = []) {
  const [state, setState] = useState({ body: null, loading: true, error: null });
  const run = useCallback(() => {
    setState((s) => ({ ...s, loading: true, error: null }));
    return loader()
      .then((body) => setState({ body, loading: false, error: null }))
      .catch((e) => setState({ body: null, loading: false, error: parseError(e).message }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  useEffect(() => { run(); }, [run]);
  return { ...state, data: state.body?.data ?? null, reload: run };
}
