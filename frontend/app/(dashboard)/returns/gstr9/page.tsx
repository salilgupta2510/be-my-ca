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
function fmt(n: number | string) { return "₹" + Number(n).toLocaleString("en-IN", { minimumFractionDigits: 2 }); }

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

interface PeriodBreakdown {
  period: string; outward_taxable: number; outward_tax: number; itc_available: number; itc_claimed: number;
}

interface GSTR9Payload {
  fy: string;
  total_outward_taxable: number; total_outward_tax: number;
  total_itc_available: number; total_itc_claimed: number;
  net_tax_payable: number;
  outward_by_type: Record<string, { taxable: number; tax: number; count: number }>;
  period_breakdown: PeriodBreakdown[];
}

interface GSTR9Return {
  id: string; period: string; status: string; computed_payload: GSTR9Payload | null;
}

const STATUS_COLORS: Record<string, string> = {
  draft: "border-slate-600 text-slate-400",
  ready_to_file: "border-blue-600 text-blue-400",
  filed: "border-green-600 text-green-400",
};

const TYPE_LABELS: Record<string, string> = {
  b2b: "B2B (Registered)", b2c_large: "B2C Large", b2c_small: "B2C Small",
  exports: "Exports", credit_notes: "Credit Notes",
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

      {!payload && !computing && (
        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-12 text-center">
            <p className="text-slate-400 text-sm">No GSTR-9 computed for FY {fy}.</p>
            <p className="text-slate-500 text-xs mt-1">Click "Compute GSTR-9" to aggregate all monthly returns for this financial year.</p>
          </CardContent>
        </Card>
      )}

      {payload && (
        <>
          {/* Summary tiles */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              { label: "Outward Taxable", value: fmt(payload.total_outward_taxable) },
              { label: "Output Tax", value: fmt(payload.total_outward_tax) },
              { label: "ITC Available", value: fmt(payload.total_itc_available) },
              { label: "Net Tax Payable", value: fmt(payload.net_tax_payable) },
            ].map(s => (
              <Card key={s.label} className="bg-slate-900 border-slate-800">
                <CardContent className="p-4">
                  <p className="text-lg font-bold text-white truncate">{s.value}</p>
                  <p className="text-slate-400 text-xs mt-0.5">{s.label}</p>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Outward by type */}
          {payload.outward_by_type && Object.keys(payload.outward_by_type).length > 0 && (
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
                        <th className="text-right text-slate-400 text-xs font-medium px-4 py-2">Tax</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(payload.outward_by_type).map(([type, data]) => (
                        <tr key={type} className="border-b border-slate-800/50 last:border-0">
                          <td className="px-4 py-2 text-slate-300">{TYPE_LABELS[type] ?? type}</td>
                          <td className="px-4 py-2 text-right text-white">{data.count}</td>
                          <td className="px-4 py-2 text-right text-white">{fmt(data.taxable)}</td>
                          <td className="px-4 py-2 text-right text-slate-300">{fmt(data.tax)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Period breakdown */}
          {payload.period_breakdown?.length > 0 && (
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
                        <th className="text-right text-slate-400 text-xs font-medium px-4 py-2">ITC Available</th>
                        <th className="text-right text-slate-400 text-xs font-medium px-4 py-2">ITC Claimed</th>
                      </tr>
                    </thead>
                    <tbody>
                      {payload.period_breakdown.map(pb => (
                        <tr key={pb.period} className="border-b border-slate-800/50 last:border-0">
                          <td className="px-4 py-2 text-slate-300 font-mono text-xs">{periodLabel(pb.period)}</td>
                          <td className="px-4 py-2 text-right text-white">{fmt(pb.outward_taxable)}</td>
                          <td className="px-4 py-2 text-right text-white">{fmt(pb.outward_tax)}</td>
                          <td className="px-4 py-2 text-right text-green-400">{fmt(pb.itc_available)}</td>
                          <td className="px-4 py-2 text-right text-blue-400">{fmt(pb.itc_claimed)}</td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr className="border-t border-slate-700 bg-slate-800/30">
                        <td className="px-4 py-2 text-slate-300 text-xs font-medium">Total</td>
                        <td className="px-4 py-2 text-right text-white font-semibold">{fmt(payload.total_outward_taxable)}</td>
                        <td className="px-4 py-2 text-right text-white font-semibold">{fmt(payload.total_outward_tax)}</td>
                        <td className="px-4 py-2 text-right text-green-400 font-semibold">{fmt(payload.total_itc_available)}</td>
                        <td className="px-4 py-2 text-right text-blue-400 font-semibold">{fmt(payload.total_itc_claimed)}</td>
                      </tr>
                    </tfoot>
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
