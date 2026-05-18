const store = new Map<string, { data: unknown; at: number }>();
const TTL = 3 * 60 * 1000; // 3 minutes

export function cacheGet<T>(key: string): T | null {
  const entry = store.get(key);
  if (!entry) return null;
  if (Date.now() - entry.at > TTL) { store.delete(key); return null; }
  return entry.data as T;
}

export function cacheSet(key: string, data: unknown) {
  store.set(key, { data, at: Date.now() });
}

export function cacheClear(key: string) {
  store.delete(key);
}
