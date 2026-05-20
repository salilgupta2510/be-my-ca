import { useState, useEffect } from "react";

export function currentPeriod(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export function getPeriod(): string {
  if (typeof window === "undefined") return currentPeriod();
  return localStorage.getItem("bemyca_period") ?? currentPeriod();
}

export function formatPeriod(period: string): string {
  const [year, month] = period.split("-");
  return new Date(Number(year), Number(month) - 1, 1).toLocaleDateString("en-IN", {
    month: "long",
    year: "numeric",
  });
}

export function usePeriod(): [string, (p: string) => void] {
  const [period, setPeriodState] = useState<string>(getPeriod);

  useEffect(() => {
    function onStorage(e: StorageEvent) {
      if (e.key === "bemyca_period" && e.newValue) {
        setPeriodState(e.newValue);
      }
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  function setPeriod(p: string) {
    localStorage.setItem("bemyca_period", p);
    setPeriodState(p);
    window.dispatchEvent(new StorageEvent("storage", { key: "bemyca_period", newValue: p }));
  }

  return [period, setPeriod];
}
