const GSTIN_RE = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;

export function validateGstin(gstin: string): string | null {
  if (!gstin) return null;
  if (gstin.length !== 15) return "Must be 15 characters";
  if (!GSTIN_RE.test(gstin)) return "Invalid GSTIN format";
  return null;
}

export function gstinStateCode(gstin: string): string {
  return gstin.slice(0, 2);
}
