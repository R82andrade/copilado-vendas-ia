import { useCallback, useEffect, useState } from 'react';

export function useApiData(loader, dependencies = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const refresh = useCallback(async () => {
    setLoading(true);
    setError('');
    try { setData(await loader()); }
    catch (reason) { setError(reason.message || 'Não foi possível carregar os dados.'); }
    finally { setLoading(false); }
  // The loader is intentionally supplied by the caller and dependencies control reloads.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencies);
  useEffect(() => { refresh(); }, [refresh]);
  return { data, loading, error, refresh, setData };
}
