"use client";
import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Loader2, RefreshCw, CheckCircle, AlertTriangle, FileCheck } from "lucide-react";
import { toast } from "sonner";
import { cacheGet, cacheSet } from "@/lib/cache";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

function getPeriod() {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("bemyca_period") ?? "";
}

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
    outward_tax_liability: { igst: number; cgst: number; sgst: number; cess: number; total: number; };
    itc_available: { igst: number; cgst: number; sgst: number; cess: number; total: number; };
    net_cash_payable: { igst: number; cgst: number; sgst: number; cess: number; total: number; };
    reconciliation_done: boolean;
    invoice_count: number;
    itc_blocked_count?: number;
    itc_expired_count?: number;
  } | null;
}

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
          <Skeleton className="h-8 w-32 bg-slate-800" />
          <Skeleton className="h-4 w-56 bg-slate-800" />
        </div>
        <Skeleton className="h-10 w-44 bg-slate-800" />
      </div>
      {[1, 2, 3].map(i => (
        <Card key={i} className="bg-slate-900 border-slate-800">
          <CardHeader className="pb-2"><Skeleton className="h-4 w-40 bg-slate-800" /></CardHeader>
          <CardContent>
            <div className="grid grid-cols-4 gap-4">
              {[...Array(4)].map((_, j) => (
                <div key={j} className="space-y-1">
                  <Skeleton className="h-3 w-10 bg-slate-800" />
                  <Skeleton className="h-5 w-20 bg-slate-800" />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      ))}
      <Skeleton className="h-32 w-full bg-slate-800 rounded-xl" />
    </div>
  );
}

export default function GSTR3BPage() {
  const [period] = useState(getPeriod);
  const cacheKey = `gstr3b:${period}`;
  const cached = cacheGet<GSTR3BReturn | "none">(cacheKey);
  const [ret, setRet] = useState<GSTR3BReturn | null>(
    cached && cached !== "none" ? cached : null
  );
  const [loading, setLoading] = useState(!cached);
  const [computing, setComputing] = useState(false);
  const [filing, setFiling] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  useEffect(() => {
    async function load(silent: boolean) {
      if (!silent) setLoading(true);
      const res = await fetch(`${API}/returns/gstr3b?period=${period}`, { headers: authH() });
      if (res.ok) {
        const data = await res.json();
        setRet(data);
        cacheSet(cacheKey, data);
      } else {
        cacheSet(cacheKey, "none");
      }
      setLoading(false);
    }
    load(!!cached);
  }, [period]);

  async function compute() {
    setComputing(true);
    try {
      const res = await fetch(`${API}/returns/gstr3b/compute?period=${period}`, {
        method: "POST", headers: authH(true),
      });
      if (!res.ok) throw new Error((await res.json()).detail ?? "Compute failed");
      const data = await res.json();
      setRet(data);
      cacheSet(cacheKey, data);
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
      const data = await res.json();
      setRet(data);
      cacheSet(cacheKey, data);
      toast.success("Return filed successfully!");
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Filing failed");
    } finally {
      setFiling(false);
    }
  }

  if (loading) return <PageSkeleton />;

  const p = ret?.computed_payload;
  const canFile = ret && ret.status !== "filed";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">GSTR-3B</h1>
          <p className="text-slate-400 text-sm mt-0.5">Summary return + tax payment · Period: {period}</p>
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

      {p && !p.reconciliation_done && (
        <Card className="bg-amber-950/20 border-amber-800/50">
          <CardContent className="p-4 flex items-center gap-3">
            <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
            <p className="text-amber-400 text-sm">
              GSTR-2B reconciliation not run — ITC set to ₹0. Go to Reconciliation, run it, then recompute GSTR-3B to claim input tax credit.
            </p>
          </CardContent>
        </Card>
      )}

      {p && (
        <div className="space-y-4">
          {[
            { title: "Outward Tax Liability", data: p.outward_tax_liability, color: "text-red-400" },
            { title: "ITC Available (from purchases)", data: p.itc_available, color: "text-green-400" },
            { title: "Net Tax Payable (Cash)", data: p.net_cash_payable, color: "text-blue-400" },
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
