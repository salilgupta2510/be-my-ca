"use client";
import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Loader2, RefreshCw, FileText } from "lucide-react";
import { toast } from "sonner";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

function token() { return typeof window !== "undefined" ? localStorage.getItem("bemyca_token") ?? "" : ""; }
function authH(json = false) {
  const h: Record<string, string> = { Authorization: `Bearer ${token()}` };
  if (json) h["Content-Type"] = "application/json";
  return h;
}
function fmt(n: number | string | undefined | null) {
  if (n === undefined || n === null) return "₹0.00";
  const num = Number(n);
  if (isNaN(num)) return "₹0.00";
  return "₹" + num.toLocaleString("en-IN", { minimumFractionDigits: 2 });
}

function currentFY(): string {
  const now = new Date();
  const y = now.getFullYear();
  const m = now.getMonth() + 1;
  const startYear = m >= 4 ? y : y - 1;
  return `${startYear}-${String(startYear + 1).slice(2)}`;
}

function fyOptions(): string[] {
  const fys: string[] = [];
  const now = new Date();
  const y = now.getFullYear();
  const m = now.getMonth() + 1;
  const latest = m >= 4 ? y : y - 1;
  for (let i = 0; i < 5; i++) {
    const start = latest - i;
    fys.push(`${start}-${String(start + 1).slice(2)}`);
  }
  return fys;
}

interface ByTypeEntry { count: number; taxable_value: number; igst: number; cgst: number; sgst: number; }
interface PeriodWiseEntry {
  outward_count: number; outward_taxable: number; outward_tax: number;
  inward_count: number; inward_itc: number; tax_paid: number;
  gstr1_filed: boolean; gstr3b_filed: boolean;
}
interface GSTR9Payload {
  financial_year: string;
  periods: string[];
  outward_supplies: {
    by_type: Record<string, ByTypeEntry>;
    total_taxable_value: number; total_igst: number; total_cgst: number;
    total_sgst: number; total_tax: number; invoice_count: number;
  };
  inward_supplies: { total_igst: number; total_cgst: number; total_sgst: number; total_itc: number; invoice_count: number; };
  returns_summary: {
    gstr1_filed_count: number; gstr3b_filed_count: number;
    gstr1_total: number; gstr3b_total: number;
    tax_paid_via_gstr3b: number; itc_claimed_via_gstr3b: number;
  };
  period_wise: Record<string, PeriodWiseEntry>;
}

interface GSTR9Return { id: string; period: string; status: string; computed_payload: GSTR9Payload | null; }

const STATUS_COLORS: Record<string, string> = {
  draft: "border-slate-600 text-slate-400",
  ready_to_file: "border-blue-600 text-blue-400",
  filed: "border-green-600 text-green-400",
};

const TYPE_LABELS: Record<string, string> = {
  b2b: "B2B (Registered)", b2c_large: "B2C Large", b2c_small: "B2C Small",
  export: "Exports", credit_note: "Credit Notes",
};

function periodLabel(p: string) {
  const [y, m] = p.split("-");
  return new Date(Number(y), Number(m) - 1, 1).toLocaleDateString("en-IN", { month: "short", year: "numeric" });
}

export default function GSTR9Page() {
  const [fy, setFy] = useState(currentFY);
  const [ret, setRet] = useState<GSTR9Return | null>(null);
  const [computing, setComputing] = useState(false);
  const [fetching, setFetching] = useState(false);

  async function fetchGSTR9(selectedFy: string) {
    setFetching(true);
    try {
      const res = await fetch(`${API}/returns/gstr9?fy=${selectedFy}`, { headers: authH() });
      if (res.ok) setRet(await res.json());
      else setRet(null);
    } finally {
      setFetching(false);
    }
  }

  useEffect(() => { fetchGSTR9(fy); }, []);

  async function compute() {
    setComputing(true);
    try {
      const res = await fetch(`${API}/returns/gstr9/compute?fy=${fy}`, {
        method: "POST", headers: authH(true),
      });
      if (!res.ok) throw new Error((await res.json()).detail ?? "Compute failed");
      const data = await res.json();
      setRet(data);
      toast.success("GSTR-9 computed");
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Compute failed");
    } finally {
      setComputing(false);
    }
  }

  function handleFyChange(val: string) {
    setFy(val);
    fetchGSTR9(val);
  }

  const payload = ret?.computed_payload;
  const out = payload?.outward_supplies;
  const inn = payload?.inward_supplies;
  const rs = payload?.returns_summary;

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <FileText className="w-6 h-6 text-blue-400" /> GSTR-9
          </h1>
          <p className="text-slate-400 text-sm mt-0.5">Annual return — aggregate of all monthly returns</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={fy}
            onChange={e => handleFyChange(e.target.value)}
            className="bg-slate-800 border border-slate-700 text-white rounded-md px-3 py-2 text-sm"
          >
            {fyOptions().map(f => <option key={f} value={f}>{f}</option>)}
          </select>
          {ret && (
            <Badge variant="outline" className={STATUS_COLORS[ret.status] ?? "border-slate-600 text-slate-400"}>
              {ret.status.replace("_", " ").toUpperCase()}
            </Badge>
          )}
          <Button onClick={compute} disabled={computing || fetching} className="bg-blue-600 hover:bg-blue-700">
            {computing
              ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Computing…</>
              : <><RefreshCw className="w-4 h-4 mr-2" /> {ret ? "Recompute" : `Compute GSTR-9`}</>
            }
          </Button>
        </div>
      </div>

      {!payload && !computing && !fetching && (
        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-12 text-center">
            <p className="text-slate-400 text-sm">No GSTR-9 computed for FY {fy}.</p>
            <p className="text-slate-500 text-xs mt-1">Click "Compute GSTR-9" to aggregate all monthly returns for this financial year.</p>
          </CardContent>
        </Card>
      )}

      {payload && out && inn && rs && (
        <>
          {/* Summary tiles */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              { label: "Outward Taxable", value: fmt(out.total_taxable_value) },
              { label: "Output Tax", value: fmt(out.total_tax) },
              { label: "ITC Available", value: fmt(inn.total_itc) },
              { label: "Tax Paid (via 3B)", value: fmt(rs.tax_paid_via_gstr3b) },
            ].map(s => (
              <Card key={s.label} className="bg-slate-900 border-slate-800">
                <CardContent className="p-4">
                  <p className="text-lg font-bold text-white truncate">{s.value}</p>
                  <p className="text-slate-400 text-xs mt-0.5">{s.label}</p>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Returns filing summary */}
          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="p-4">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                {[
                  { label: "GSTR-1 Filed", value: `${rs.gstr1_filed_count} / ${rs.gstr1_total}` },
                  { label: "GSTR-3B Filed", value: `${rs.gstr3b_filed_count} / ${rs.gstr3b_total}` },
                  { label: "ITC Claimed (3B)", value: fmt(rs.itc_claimed_via_gstr3b) },
                  { label: "Invoices (Outward)", value: String(out.invoice_count) },
                ].map(s => (
                  <div key={s.label}>
                    <p className="text-slate-400 text-xs">{s.label}</p>
                    <p className="text-white font-medium mt-0.5">{s.value}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Outward by type */}
          {out.by_type && Object.keys(out.by_type).length > 0 && (
            <Card className="bg-slate-900 border-slate-800">
              <CardHeader className="pb-3">
                <CardTitle className="text-white text-sm">Table 4 — Outward Supplies by Type</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-800">
                        <th className="text-left text-slate-400 text-xs font-medium px-4 py-2">Type</th>
                        <th className="text-right text-slate-400 text-xs font-medium px-4 py-2">Count</th>
                        <th className="text-right text-slate-400 text-xs font-medium px-4 py-2">Taxable Value</th>
                        <th className="text-right text-slate-400 text-xs font-medium px-4 py-2">IGST</th>
                        <th className="text-right text-slate-400 text-xs font-medium px-4 py-2">CGST</th>
                        <th className="text-right text-slate-400 text-xs font-medium px-4 py-2">SGST</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(out.by_type).filter(([, d]) => d.count > 0).map(([type, data]) => (
                        <tr key={type} className="border-b border-slate-800/50 last:border-0">
                          <td className="px-4 py-2 text-slate-300">{TYPE_LABELS[type] ?? type}</td>
                          <td className="px-4 py-2 text-right text-white">{data.count}</td>
                          <td className="px-4 py-2 text-right text-white">{fmt(data.taxable_value)}</td>
                          <td className="px-4 py-2 text-right text-slate-300">{fmt(data.igst)}</td>
                          <td className="px-4 py-2 text-right text-slate-300">{fmt(data.cgst)}</td>
                          <td className="px-4 py-2 text-right text-slate-300">{fmt(data.sgst)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Period-wise breakdown */}
          {payload.period_wise && Object.keys(payload.period_wise).length > 0 && (
            <Card className="bg-slate-900 border-slate-800">
              <CardHeader className="pb-3">
                <CardTitle className="text-white text-sm">Month-wise Breakdown</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-800">
                        <th className="text-left text-slate-400 text-xs font-medium px-4 py-2">Month</th>
                        <th className="text-right text-slate-400 text-xs font-medium px-4 py-2">Taxable</th>
                        <th className="text-right text-slate-400 text-xs font-medium px-4 py-2">Output Tax</th>
                        <th className="text-right text-slate-400 text-xs font-medium px-4 py-2">ITC</th>
                        <th className="text-right text-slate-400 text-xs font-medium px-4 py-2">Tax Paid</th>
                        <th className="text-center text-slate-400 text-xs font-medium px-4 py-2">GSTR-1</th>
                        <th className="text-center text-slate-400 text-xs font-medium px-4 py-2">GSTR-3B</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(payload.period_wise).map(([p, d]) => (
                        <tr key={p} className="border-b border-slate-800/50 last:border-0">
                          <td className="px-4 py-2 text-slate-300 font-mono text-xs">{periodLabel(p)}</td>
                          <td className="px-4 py-2 text-right text-white">{fmt(d.outward_taxable)}</td>
                          <td className="px-4 py-2 text-right text-white">{fmt(d.outward_tax)}</td>
                          <td className="px-4 py-2 text-right text-green-400">{fmt(d.inward_itc)}</td>
                          <td className="px-4 py-2 text-right text-blue-400">{fmt(d.tax_paid)}</td>
                          <td className="px-4 py-2 text-center">
                            <span className={d.gstr1_filed ? "text-green-400 text-xs" : "text-slate-500 text-xs"}>
                              {d.gstr1_filed ? "Filed" : "Pending"}
                            </span>
                          </td>
                          <td className="px-4 py-2 text-center">
                            <span className={d.gstr3b_filed ? "text-green-400 text-xs" : "text-slate-500 text-xs"}>
                              {d.gstr3b_filed ? "Filed" : "Pending"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="p-4 space-y-1">
              <p className="text-slate-400 text-xs font-medium">Note</p>
              <p className="text-slate-500 text-xs">GSTR-9 is auto-computed from GSTR-1 and GSTR-3B returns. Due date: 31 December following end of financial year. Verify against portal data before filing.</p>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
