import { useEffect, useState } from "react";
import { getFields, getCoverageStats } from "../services/api";

export function useFields() {
  const [fields, setFields] = useState([]);
  const [coverage, setCoverage] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    Promise.all([getFields(), getCoverageStats()]).then(([f, c]) => {
      if (!mounted) return;
      setFields(f);
      setCoverage(c);
      setLoading(false);
    });
    return () => {
      mounted = false;
    };
  }, []);

  return { fields, coverage, loading };
}
