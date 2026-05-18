"use client";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Loader2, RefreshCw, CheckCircle, AlertTriangle, FileCheck } from "lucide-react";
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

interface GSTR3BReturn {
  id: string;
  period: string;
  status: string;
  arn: string | null;
  total_tax_payable: string;
  itc_claimed: string;
  computed_payload: {
    outward_tax_liability: {
      igst: number; cgst: number; sgst: number; cess: number; total: number;
    };
    itc_available: {
      igst: number; cgst: number; sgst: number; cess: number; total: number;
    };
    net_tax_payable: {
      igst: number; cgst: number; sgst: number; cess: number; total: number;
    };
    reconciliation_done: boolean;
    invoice_count: number;
  } | null;
}

const STATUS_COLORS: Record<string, string> = {
  draft: "border-slate-600 text-slate-400",
  ready_to_file: "border-blue-600 text-blue-400",
  filed: "border-green-600 text-green-400",
  filing_failed: "border-red-600 text-red-400",
};

export default function GSTR3BPage() {
  const [ret, setRet] = useState<GSTR3BReturn | null>(null);
  const [computing, setComputing] = useState(false);
  const [filing, setFiling] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [loaded, setLoaded] = useState(false);

  async function loadExisting() {
    const res = await fetch(`${API}/returns/gstr3b?period=${PERIOD}`, { headers: authH() });
    if (res.ok) setRet(await res.json());
    setLoaded(true);
  }

  async function compute() {
    setComputing(true);
    try {
      const res = await fetch(`${API}/returns/gstr3b/compute?period=${PERIOD}`, {
        method: "POST", headers: authH(true),
      });
      if (!res.ok) throw new Error((await res.json()).detail ?? "Compute failed");
      setRet(await res.json());
      toast.success("GSTR-3B computed");
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Compute failed");
    } finally {
      setComputing(false);
    }
  }

  async function file() {
    if (!ret) return;
    setFiling(true);
    setShowConfirm(false);
    try {
      const res = await fetch(`${API}/returns/${ret.id}/file`, {
        method: "POST", headers: authH(true),
      });
      if (!res.ok) throw new Error((await res.json()).detail ?? "Filing failed");
      setRet(await res.json());
      toast.success("Return filed successfully!");
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Filing failed");
    } finally {
      setFiling(false);
    }
  }

  if (!loaded) { loadExisting(); }

  const p = ret?.computed_payload;
  const canFile = ret && ret.status !== "filed";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">GSTR-3B</h1>
          <p className="text-slate-400 text-sm mt-0.5">Summary return + tax payment · Period: {PERIOD}</p>
        </div>
        <div className="flex items-center gap-3">
          {ret && (
            <Badge variant="outline" className={STATUS_COLORS[ret.status] ?? "border-slate-600 text-slate-400"}>
              {ret.status.replace(/_/g, " ").toUpperCase()}
            </Badge>
          )}
          <Button onClick={compute} disabled={computing || filing} variant="outline"
            className="border-slate-700 text-slate-300 hover:text-white">
            {computing
              ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Computing…</>
              : <><RefreshCw className="w-4 h-4 mr-2" /> {ret ? "Recompute" : "Compute GSTR-3B"}</>
            }
          </Button>
          {canFile && !showConfirm && (
            <Button onClick={() => setShowConfirm(true)} disabled={filing}
              className="bg-green-600 hover:bg-green-700">
              <FileCheck className="w-4 h-4 mr-2" /> File Return
            </Button>
          )}
        </div>
      </div>

      {/* Filing confirm */}
      {showConfirm && (
        <Card className="bg-amber-950/30 border-amber-700">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-amber-300 font-medium text-sm">Confirm filing</p>
                <p className="text-amber-500 text-xs mt-1">
                  Net tax payable: <strong>{fmt(ret?.total_tax_payable ?? 0)}</strong>. This will be mock-filed and cannot be undone.
                </p>
                <div className="flex gap-2 mt-3">
                  <Button size="sm" onClick={file} disabled={filing} className="bg-green-600 hover:bg-green-700">
                    {filing ? <><Loader2 className="w-3 h-3 mr-1 animate-spin" /> Filing…</> : "Confirm & File"}
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setShowConfirm(false)}
                    className="text-slate-400 hover:text-white">Cancel</Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ARN success */}
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

      {/* Recon warning */}
      {p && !p.reconciliation_done && (
        <Card className="bg-amber-950/20 border-amber-800/50">
          <CardContent className="p-4 flex items-center gap-3">
            <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
            <p className="text-amber-400 text-sm">
              GSTR-2B reconciliation not run — ITC set to ₹0. Run reconciliation first to claim input tax credit.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Tax breakdown */}
      {p && (
        <div className="space-y-4">
          {[
            { title: "Outward Tax Liability", data: p.outward_tax_liability, color: "text-red-400" },
            { title: "ITC Available (from purchases)", data: p.itc_available, color: "text-green-400" },
            { title: "Net Tax Payable", data: p.net_tax_payable, color: "text-blue-400" },
          ].map(({ title, data, color }) => (
            <Card key={title} className="bg-slate-900 border-slate-800">
              <CardHeader className="pb-2">
                <CardTitle className={`text-sm ${color}`}>{title}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-4 gap-4">
                  {[
                    { label: "IGST", value: data.igst },
                    { label: "CGST", value: data.cgst },
                    { label: "SGST", value: data.sgst },
                    { label: "Total", value: data.total },
                  ].map(({ label, value }) => (
                    <div key={label}>
                      <p className="text-slate-400 text-xs">{label}</p>
                      <p className="text-white font-semibold text-sm mt-0.5">{fmt(value)}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}

          {/* Net payable hero */}
          <Card className="bg-blue-950/30 border-blue-800">
            <CardContent className="p-6 text-center">
              <p className="text-slate-400 text-sm">Total GST to pay</p>
              <p className="text-4xl font-bold text-white mt-1">{fmt(ret?.total_tax_payable ?? 0)}</p>
              <p className="text-slate-500 text-xs mt-2">Due by 20th of next month</p>
            </CardContent>
          </Card>
        </div>
      )}

      {!ret && !computing && (
        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-12 text-center">
            <p className="text-slate-400 text-sm">No GSTR-3B computed yet.</p>
            <p className="text-slate-500 text-xs mt-1">Click "Compute GSTR-3B" to calculate your tax liability.</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
