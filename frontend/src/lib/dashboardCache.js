// Module-scoped, so it survives the Dashboard component unmounting
// when you navigate to /methodology and back — React Router destroys
// and recreates the whole component on route change, which was
// causing a full refetch + loading flash every single time.
//
// This is intentionally simple (no external cache lib): hold the last
// successful payload in memory for the life of the browser tab, hand
// it back instantly on remount, and silently refresh in the
// background so the data doesn't go stale for a long session.

let cache = null; // { fields, coverage, commandArea, validation, methodology, ts }

export function getDashboardCache() {
  return cache;
}

export function setDashboardCache(data) {
  cache = { ...data, ts: Date.now() };
}

export function isCacheFresh(maxAgeMs = 5 * 60 * 1000) {
  return !!cache && Date.now() - cache.ts < maxAgeMs;
}
