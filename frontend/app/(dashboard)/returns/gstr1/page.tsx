"use client";
import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Loader2, RefreshCw, CheckCircle } from "lucide-react";
import { toast } from "sonner";
import { cacheGet, cacheSet } from "@/lib/cache";
import { usePeriod } from "@/lib/period";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

function token() { return typeof window !== "undefined" ? localStorage.getItem("bemyca_token") ?? "" : ""; }
function authH(json = false) {
  const h: Record<string, string> = { Authorization: `Bearer ${token()}` };
  if (json) h["Content-Type"] = "application/json";
  return h;
}
function fmt(n: string | number) { return "₹" + Number(n).toLocaleString("en-IN"); }

interface GSTR1Section {
  type: string; count: number; taxable_value: number;
  igst: number; cgst: number; sgst: number; cess: number;
}

interface OutwardInvoice {
  hsn_code: string | null; invoice_type: string;
  taxable_value: string; igst: string; cgst: string; sgst: string;
}

interface HsnRow {
  hsn: string; count: number; taxable: number; igst: number; cgst: number; sgst: number;
}

interface GSTR1Return {
  id: string; period: string; status: string; arn: string | null; total_tax_payable: string;
  computed_payload: {
    b2b: GSTR1Section[]; b2c_large: GSTR1Section[]; b2c_small: GSTR1Section[];
    exports: GSTR1Section[]; credit_notes: GSTR1Section[];
    summary: {
      total_taxable_value: number; total_igst: number; total_cgst: number;
      total_sgst: number; total_cess: number; total_tax: number; invoice_count: number;
    };
  } | null;
}

const TYPE_LABELS: Record<string, string> = {
  b2b: "B2B (Registered Buyers)",
  b2c_large: "B2C Large (>₹2.5L Inter-state)",
  b2c_small: "B2C Small",
  exports: "Exports",
  credit_notes: "Credit Notes",
};

const STATUS_COLORS: Record<string, string> = {
  draft: "border-slate-600 text-slate-400",
  ready_to_file: "border-blue-600 text-blue-400",
  filed: "border-green-600 text-green-400",
  filing_failed: "border-red-600 text-red-400",
};

function PageSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="space-y-2">
          <Skeleton className="h-8 w-28 bg-slate-800" />
          <Skeleton className="h-4 w-56 bg-slate-800" />
        </div>
        <Skeleton className="h-10 w-44 bg-slate-800" />
      </div>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <Card key={i} className="bg-slate-900 border-slate-800">
            <CardContent className="p-4 space-y-2">
              <Skeleton className="h-6 w-24 bg-slate-800" />
              <Skeleton className="h-3 w-20 bg-slate-800" />
            </CardContent>
          </Card>
        ))}
      </div>
      {[...Array(3)].map((_, i) => (
        <Card key={i} className="bg-slate-900 border-slate-800">
          <CardHeader className="pb-3"><Skeleton className="h-4 w-40 bg-slate-800" /></CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-slate-800">
              {[...Array(2)].map((_, j) => (
                <div key={j} className="flex gap-4 px-4 py-2">
                  {[...Array(6)].map((__, k) => <Skeleton key={k} className="h-4 flex-1 bg-slate-800" />)}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export default function GSTR1Page() {
  const [period] = usePeriod();
  const cacheKey = `gstr1:${period}`;
  const cached = cacheGet<GSTR1Return | "none">(cacheKey);
  const [ret, setRet] = useState<GSTR1Return | null>(
    cached && cached !== "none" ? cached : null
  );
  const [loading, setLoading] = useState(!cached);
  const [computing, setComputing] = useState(false);
  const [hsnRows, setHsnRows] = useState<HsnRow[]>([]);

  useEffect(() => {
    async function load(silent: boolean) {
      if (!silent) setLoading(true);
      const [res, invRes] = await Promise.all([
        fetch(`${API}/returns/gstr1?period=${period}`, { headers: authH() }),
        fetch(`${API}/invoices/outward?period=${period}`, { headers: authH() }),
      ]);
      if (res.ok) {
        const data = await res.json();
        setRet(data);
        cacheSet(cacheKey, data);
      } else {
        cacheSet(cacheKey, "none");
      }
      if (invRes.ok) {
        const invs: OutwardInvoice[] = await invRes.json();
        const map = new Map<string, HsnRow>();
        for (const inv of invs) {
          const key = inv.hsn_code?.trim() || "—";
          const existing = map.get(key) ?? { hsn: key, count: 0, taxable: 0, igst: 0, cgst: 0, sgst: 0 };
          map.set(key, {
            ...existing,
            count: existing.count + 1,
            taxable: existing.taxable + Number(inv.taxable_value),
            igst: existing.igst + Number(inv.igst),
            cgst: existing.cgst + Number(inv.cgst),
            sgst: existing.sgst + Number(inv.sgst),
          });
        }
        setHsnRows(Array.from(map.values()).sort((a, b) => b.taxable - a.taxable));
      }
      setLoading(false);
    }
    load(!!cached);
  }, [period]);

  async function compute() {
    setComputing(true);
    try {
      const res = await fetch(`${API}/returns/gstr1/compute?period=${period}`, {
        method: "POST", headers: authH(true),
      });
      if (!res.ok) throw new Error((await res.json()).detail ?? "Compute failed");
      const data = await res.json();
      setRet(data);
      cacheSet(cacheKey, data);
      toast.success("GSTR-1 computed");
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Compute failed");
    } finally {
      setComputing(false);
    }
  }

  if (loading) return <PageSkeleton />;

  const summary = ret?.computed_payload?.summary;
  const sections = ret?.computed_payload
    ? Object.entries(ret.computed_payload).filter(([k]) => k !== "summary") as [string, GSTR1Section[]][]
    : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">GSTR-1</h1>
          <p className="text-slate-400 text-sm mt-0.5">Outward supplies return · Period: {period}</p>
        </div>
        <div className="flex items-center gap-3">
          {ret && (
            <Badge variant="outline" className={STATUS_COLORS[ret.status] ?? "border-slate-600 text-slate-400"}>
              {ret.status.replace("_", " ").toUpperCase()}
            </Badge>
          )}
          <Button onClick={compute} disabled={computing} className="bg-blue-600 hover:bg-blue-700">
            {computing
              ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Computing…</>
              : <><RefreshCw className="w-4 h-4 mr-2" /> {ret ? "Recompute" : "Compute GSTR-1"}</>
            }
          </Button>
        </div>
      </div>

      {ret?.arn && (
        <Card className="bg-green-950/30 border-green-800">
          <CardContent className="p-4 flex items-center gap-3">
            <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0" />
            <div>
              <p className="text-green-300 font-medium text-sm">Filed successfully</p>
              <p className="text-green-500 text-xs font-mono">ARN: {ret.arn}</p>
            </div>
          </CardContent>
        </Card>
      )}

      {summary && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            { label: "Invoices", value: String(summary.invoice_count) },
            { label: "Taxable Value", value: fmt(summary.total_taxable_value) },
            { label: "Total Tax", value: fmt(summary.total_tax) },
            { label: "IGST / CGST / SGST", value: `${fmt(summary.total_igst)} / ${fmt(summary.total_cgst)} / ${fmt(summary.total_sgst)}` },
          ].map(s => (
            <Card key={s.label} className="bg-slate-900 border-slate-800">
              <CardContent className="p-4">
                <p className="text-lg font-bold text-white truncate">{s.value}</p>
                <p className="text-slate-400 text-xs mt-0.5">{s.label}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {sections.length > 0 && (
        <div className="space-y-4">
          {sections.map(([key, rows]) => rows.length > 0 && (
            <Card key={key} className="bg-slate-900 border-slate-800">
              <CardHeader className="pb-3">
                <CardTitle className="text-white text-sm">{TYPE_LABELS[key] ?? key}</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-800">
                        <th className="text-left text-slate-400 text-xs font-medium px-4 py-2">Type</th>
                        <th className="text-right text-slate-400 text-xs font-medium px-4 py-2">Count</th>
                        <th className="text-right text-slate-400 text-xs font-medium px-4 py-2">Taxable</th>
                        <th className="text-right text-slate-400 text-xs font-medium px-4 py-2">IGST</th>
                        <th className="text-right text-slate-400 text-xs font-medium px-4 py-2">CGST</th>
                        <th className="text-right text-slate-400 text-xs font-medium px-4 py-2">SGST</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((row, i) => (
                        <tr key={i} className="border-b border-slate-800/50 last:border-0">
                          <td className="px-4 py-2 text-slate-300">{row.type}</td>
                          <td className="px-4 py-2 text-right text-white">{row.count}</td>
                          <td className="px-4 py-2 text-right text-white">{fmt(row.taxable_value)}</td>
                          <td className="px-4 py-2 text-right text-slate-300">{fmt(row.igst)}</td>
                          <td className="px-4 py-2 text-right text-slate-300">{fmt(row.cgst)}</td>
                          <td className="px-4 py-2 text-right text-slate-300">{fmt(row.sgst)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {hsnRows.length > 0 && (
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-white text-sm">Table 12 — HSN / SAC Summary</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-800">
                    <th className="text-left text-slate-400 text-xs font-medium px-4 py-2">HSN / SAC</th>
                    <th className="text-right text-slate-400 text-xs font-medium px-4 py-2">Invoices</th>
                    <th className="text-right text-slate-400 text-xs font-medium px-4 py-2">Taxable</th>
                    <th className="text-right text-slate-400 text-xs font-medium px-4 py-2">IGST</th>
                    <th className="text-right text-slate-400 text-xs font-medium px-4 py-2">CGST</th>
                    <th className="text-right text-slate-400 text-xs font-medium px-4 py-2">SGST</th>
                  </tr>
                </thead>
                <tbody>
                  {hsnRows.map(row => (
                    <tr key={row.hsn} className="border-b border-slate-800/50 last:border-0">
                      <td className="px-4 py-2 text-white font-mono text-xs">{row.hsn}</td>
                      <td className="px-4 py-2 text-right text-slate-300">{row.count}</td>
                      <td className="px-4 py-2 text-right text-white">{fmt(row.taxable)}</td>
                      <td className="px-4 py-2 text-right text-slate-300">{fmt(row.igst)}</td>
                      <td className="px-4 py-2 text-right text-slate-300">{fmt(row.cgst)}</td>
                      <td className="px-4 py-2 text-right text-slate-300">{fmt(row.sgst)}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="border-t border-slate-700">
                    <td className="px-4 py-2 text-slate-400 text-xs font-medium">Total</td>
                    <td className="px-4 py-2 text-right text-slate-300">{hsnRows.reduce((s, r) => s + r.count, 0)}</td>
                    <td className="px-4 py-2 text-right text-white font-semibold">{fmt(hsnRows.reduce((s, r) => s + r.taxable, 0))}</td>
                    <td className="px-4 py-2 text-right text-slate-300">{fmt(hsnRows.reduce((s, r) => s + r.igst, 0))}</td>
                    <td className="px-4 py-2 text-right text-slate-300">{fmt(hsnRows.reduce((s, r) => s + r.cgst, 0))}</td>
                    <td className="px-4 py-2 text-right text-slate-300">{fmt(hsnRows.reduce((s, r) => s + r.sgst, 0))}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {!ret && !computing && (
        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-12 text-center">
            <p className="text-slate-400 text-sm">No GSTR-1 computed yet.</p>
            <p className="text-slate-500 text-xs mt-1">Click "Compute GSTR-1" to generate the return from your sales invoices.</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
