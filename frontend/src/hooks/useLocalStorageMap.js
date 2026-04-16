import { useCallback, useState } from "react";

function readMap(key) {
  try {
    const parsed = JSON.parse(localStorage.getItem(key) || "{}");
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch (_err) {
    return {};
  }
}

export function useLocalStorageMap(key) {
  const [map, setMap] = useState(() => readMap(key));

  const setValue = useCallback(
    (entryKey, value) => {
      setMap((prev) => {
        const next = { ...prev };
        if (!value) {
          delete next[entryKey];
        } else {
          next[entryKey] = value;
        }
        localStorage.setItem(key, JSON.stringify(next));
        return next;
      });
    },
    [key],
  );

  const setAll = useCallback(
    (nextMap) => {
      const safe = nextMap && typeof nextMap === "object" ? nextMap : {};
      setMap(safe);
      localStorage.setItem(key, JSON.stringify(safe));
    },
    [key],
  );

  return { map, setValue, setAll };
}
