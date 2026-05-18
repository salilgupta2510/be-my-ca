"use client";
import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Search, RefreshCw, CheckCircle, XCircle, Clock, AlertTriangle, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { cacheGet, cacheSet } from "@/lib/cache";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const PERIOD = "2025-01";
const CACHE_KEY = `reconciliation:${PERIOD}`;

function token() { return typeof window !== "undefined" ? localStorage.getItem("bemyca_token") ?? "" : ""; }
function authH(json = false) {
  const h: Record<string, string> = { Authorization: `Bearer ${token()}` };
  if (json) h["Content-Type"] = "application/json";
  return h;
}
function fmt(n: string | number) { return "₹" + Number(n).toLocaleString("en-IN"); }

type Status = "missing_in_2b" | "missing_in_books" | "amount_mismatch" | "matched" | "pending_ims";

const STATUS_CONFIG: Record<Status, { label: string; color: string; icon: React.ElementType }> = {
  missing_in_2b: { label: "Not in supplier filing", color: "border-red-600 text-red-400", icon: XCircle },
  missing_in_books: { label: "Not in your books", color: "border-orange-600 text-orange-400", icon: AlertTriangle },
  amount_mismatch: { label: "Amount mismatch", color: "border-yellow-600 text-yellow-400", icon: AlertTriangle },
  matched: { label: "Matched", color: "border-green-700 text-green-400", icon: CheckCircle },
  pending_ims: { label: "Pending IMS", color: "border-blue-600 text-blue-400", icon: Clock },
};

interface ReconRow {
  id: string; supplier_name: string; supplier_gstin: string | null;
  invoice_number: string; invoice_date: string; taxable_value: string;
  igst: string; cgst: string; sgst: string; status: Status;
  match_confidence: number | null; ims_action: string | null;
}

function TableSkeleton() {
  return (
    <div className="divide-y divide-slate-800">
      {[...Array(6)].map((_, i) => (
        <div key={i} className="flex gap-4 px-4 py-3">
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-40 bg-slate-800" />
            <Skeleton className="h-3 w-32 bg-slate-800" />
          </div>
          <Skeleton className="h-4 w-24 bg-slate-800 self-center" />
          <Skeleton className="h-4 w-20 bg-slate-800 self-center" />
          <Skeleton className="h-5 w-28 bg-slate-800 rounded-full self-center" />
        </div>
      ))}
    </div>
  );
}

export default function GSTReconciliationPage() {
  const cached = cacheGet<ReconRow[]>(CACHE_KEY);
  const [rows, setRows] = useState<ReconRow[]>(cached ?? []);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [loading, setLoading] = useState(!cached);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    async function load(silent: boolean) {
      if (!silent) setLoading(true);
      const res = await fetch(`${API}/gst/reconciliation/results?period=${PERIOD}`, { headers: authH() });
      if (res.ok) {
        const data = await res.json();
        setRows(data);
        cacheSet(CACHE_KEY, data);
      }
      setLoading(false);
    }
    load(!!cached);
  }, []);

  async function runRecon() {
    setRunning(true);
    try {
      const res = await fetch(`${API}/gst/reconciliation/run?period=${PERIOD}`, { method: "POST", headers: authH(true) });
      if (!res.ok) throw new Error((await res.json()).detail ?? "Reconciliation failed");
      const res2 = await fetch(`${API}/gst/reconciliation/results?period=${PERIOD}`, { headers: authH() });
      if (res2.ok) {
        const data = await res2.json();
        setRows(data);
        cacheSet(CACHE_KEY, data);
      }
      toast.success("Reconciliation complete");
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed");
    } finally {
      setRunning(false);
    }
  }

  async function imsAction(id: string, action: "accept" | "reject" | "pending") {
    const res = await fetch(`${API}/gst/ims/${id}`, { method: "PUT", headers: authH(true), body: JSON.stringify({ action }) });
    if (res.ok) {
      const updated = rows.map(row => row.id === id ? { ...row, ims_action: action } : row);
      setRows(updated);
      cacheSet(CACHE_KEY, updated);
      toast.success(`Invoice ${action}ed`);
    } else toast.error("Action failed");
  }

  const filtered = rows.filter(row => {
    const matchSearch = !search || row.supplier_name.toLowerCase().includes(search.toLowerCase()) || (row.supplier_gstin ?? "").includes(search);
    const matchStatus = statusFilter === "all" || row.status === statusFilter;
    return matchSearch && matchStatus;
  });

  const counts = Object.fromEntries(Object.keys(STATUS_CONFIG).map(s => [s, rows.filter(r => r.status === s).length]));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">GSTR-2B Reconciliation</h1>
          <p className="text-slate-400 text-sm mt-0.5">Your purchases vs what suppliers filed · Period: {PERIOD}</p>
        </div>
        <Button onClick={runRecon} disabled={running} className="bg-blue-600 hover:bg-blue-700">
          {running ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Running…</> : <><RefreshCw className="w-4 h-4 mr-2" /> Run Reconciliation</>}
        </Button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        {(Object.entries(STATUS_CONFIG) as [Status, typeof STATUS_CONFIG[Status]][]).map(([status, config]) => (
          loading ? (
            <Card key={status} className="bg-slate-900 border-slate-800">
              <CardContent className="p-4 text-center space-y-2">
                <Skeleton className="h-7 w-10 bg-slate-800 mx-auto" />
                <Skeleton className="h-3 w-20 bg-slate-800 mx-auto" />
              </CardContent>
            </Card>
          ) : (
            <Card
              key={status}
              className={`bg-slate-900 border-slate-800 cursor-pointer transition-all hover:border-slate-600 ${statusFilter === status ? "ring-2 ring-blue-500" : ""}`}
              onClick={() => setStatusFilter(statusFilter === status ? "all" : status)}
            >
              <CardContent className="p-4 text-center">
                <p className="text-2xl font-bold text-white">{counts[status] ?? 0}</p>
                <p className={`text-xs mt-1 ${config.color.split(" ")[1]}`}>{config.label}</p>
              </CardContent>
            </Card>
          )
        ))}
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
        <Input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search supplier or GSTIN…"
          className="pl-9 bg-slate-900 border-slate-700 text-white placeholder:text-slate-500" />
      </div>

      <Card className="bg-slate-900 border-slate-800">
        <CardContent className="p-0">
          {loading ? (
            <TableSkeleton />
          ) : filtered.length === 0 ? (
            <div className="p-8 text-center">
              <p className="text-slate-400 text-sm">
                {rows.length === 0 ? "No reconciliation data. Add purchase invoices and run reconciliation." : "No rows match filter."}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-800">
                    {["Supplier", "Invoice", "Date", "Taxable", "Tax", "Status", "IMS"].map(h => (
                      <th key={h} className="text-left text-slate-400 text-xs font-medium px-4 py-3">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.map(row => {
                    const cfg = STATUS_CONFIG[row.status];
                    const Icon = cfg.icon;
                    const tax = Number(row.igst) + Number(row.cgst) + Number(row.sgst);
                    return (
                      <tr key={row.id} className="border-b border-slate-800/50 last:border-0 hover:bg-slate-800/40">
                        <td className="px-4 py-3">
                          <p className="text-white text-sm font-medium">{row.supplier_name}</p>
                          {row.supplier_gstin && <p className="text-slate-500 text-xs font-mono">{row.supplier_gstin}</p>}
                        </td>
                        <td className="px-4 py-3 text-slate-300 text-xs font-mono">{row.invoice_number}</td>
                        <td className="px-4 py-3 text-slate-400 text-xs">{row.invoice_date}</td>
                        <td className="px-4 py-3 text-white text-sm">{fmt(row.taxable_value)}</td>
                        <td className="px-4 py-3 text-white text-sm">{fmt(tax)}</td>
                        <td className="px-4 py-3">
                          <Badge variant="outline" className={`text-xs gap-1 ${cfg.color}`}>
                            <Icon className="w-3 h-3" />{cfg.label}
                            {row.match_confidence != null && ` (${row.match_confidence}%)`}
                          </Badge>
                        </td>
                        <td className="px-4 py-3">
                          {row.status === "pending_ims" && !row.ims_action ? (
                            <div className="flex gap-1">
                              <Button size="sm" variant="outline" onClick={() => imsAction(row.id, "accept")}
                                className="h-6 text-xs border-green-700 text-green-400 hover:bg-green-950 px-2">Accept</Button>
                              <Button size="sm" variant="outline" onClick={() => imsAction(row.id, "reject")}
                                className="h-6 text-xs border-red-700 text-red-400 hover:bg-red-950 px-2">Reject</Button>
                            </div>
                          ) : row.ims_action ? (
                            <Badge className={`text-xs ${row.ims_action === "accept" ? "bg-green-900 text-green-300" : "bg-red-900 text-red-300"}`}>
                              {row.ims_action}ed
                            </Badge>
                          ) : <span className="text-slate-600 text-xs">—</span>}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
