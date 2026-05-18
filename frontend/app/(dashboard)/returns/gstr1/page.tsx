"use client";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Loader2, RefreshCw, CheckCircle } from "lucide-react";
import { toast } from "sonner";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const PERIOD = "2025-01";

function token() { return typeof window !== "undefined" ? localStorage.getItem("bemyca_token") ?? "" : ""; }
function authH(json = false) {
  const h: Record<string, string> = { Authorization: `Bearer ${token()}` };
  if (json) h["Content-Type"] = "application/json";
  return h;
}
function fmt(n: string | number) { return "₹" + Number(n).toLocaleString("en-IN"); }

interface GSTR1Section {
  type: string;
  count: number;
  taxable_value: number;
  igst: number;
  cgst: number;
  sgst: number;
  cess: number;
}

interface GSTR1Return {
  id: string;
  period: string;
  status: string;
  arn: string | null;
  total_tax_payable: string;
  computed_payload: {
    b2b: GSTR1Section[];
    b2c_large: GSTR1Section[];
    b2c_small: GSTR1Section[];
    exports: GSTR1Section[];
    credit_notes: GSTR1Section[];
    summary: {
      total_taxable_value: number;
      total_igst: number;
      total_cgst: number;
      total_sgst: number;
      total_cess: number;
      total_tax: number;
      invoice_count: number;
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

export default function GSTR1Page() {
  const [ret, setRet] = useState<GSTR1Return | null>(null);
  const [computing, setComputing] = useState(false);
  const [loaded, setLoaded] = useState(false);

  async function loadExisting() {
    const res = await fetch(`${API}/returns/gstr1?period=${PERIOD}`, { headers: authH() });
    if (res.ok) {
      const data = await res.json();
      setRet(data);
    }
    setLoaded(true);
  }

  async function compute() {
    setComputing(true);
    try {
      const res = await fetch(`${API}/returns/gstr1/compute?period=${PERIOD}`, {
        method: "POST", headers: authH(true),
      });
      if (!res.ok) throw new Error((await res.json()).detail ?? "Compute failed");
      const data = await res.json();
      setRet(data);
      toast.success("GSTR-1 computed");
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Compute failed");
    } finally {
      setComputing(false);
    }
  }

  // Load existing on mount
  if (!loaded) { loadExisting(); }

  const summary = ret?.computed_payload?.summary;
  const sections = ret?.computed_payload
    ? Object.entries(ret.computed_payload).filter(([k]) => k !== "summary") as [string, GSTR1Section[]][]
    : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">GSTR-1</h1>
          <p className="text-slate-400 text-sm mt-0.5">Outward supplies return · Period: {PERIOD}</p>
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
