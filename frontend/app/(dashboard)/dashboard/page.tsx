"use client";
import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { AlertTriangle, ArrowRight, CalendarDays, CheckCircle2, FileText, Loader2, PlusCircle, ReceiptText, TrendingUp } from "lucide-react";
import Link from "next/link";
import { cacheGet, cacheSet } from "@/lib/cache";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

function token() {
  return typeof window !== "undefined" ? localStorage.getItem("bemyca_token") ?? "" : "";
}
function authHeaders() {
  return { Authorization: `Bearer ${token()}`, "Content-Type": "application/json" };
}
function fmt(n: number) {
  return "₹" + n.toLocaleString("en-IN");
}

function generatePeriods(): string[] {
  const periods: string[] = [];
  const now = new Date();
  for (let i = 0; i < 24; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    periods.push(`${y}-${m}`);
  }
  return periods;
}

function formatPeriodLabel(period: string): string {
  const [year, month] = period.split("-");
  const date = new Date(Number(year), Number(month) - 1, 1);
  return date.toLocaleDateString("en-IN", { month: "long", year: "numeric" });
}

const PERIODS = generatePeriods();

interface Business { legal_name: string; gstin: string; state_code: string; return_frequency: string; }
interface GSTR3BPayload {
  outward_tax_liability: { total: number };
  itc_available: { total: number };
  net_cash_payable: { total: number };
  reconciliation_done: boolean;
}
interface GSTR3B { id: string; status: string; total_tax_payable: number; itc_claimed: number; computed_payload: GSTR3BPayload | null; }
interface ReconSummary { matched: number; missing_in_2b: number; missing_in_books: number; amount_mismatch: number; }
interface CacheData {
  business: Business | null;
  gstr3b: GSTR3B | null;
  recon: ReconSummary | null;
  outCount: number | null;
  inCount: number | null;
}

function filingDeadline(period: string, day: number) {
  const [year, month] = period.split("-").map(Number);
  // deadline is in the month following the period
  const due = new Date(year, month, day); // month is 0-indexed, so month = next month
  const now = new Date();
  const diff = Math.ceil((due.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  if (diff < 0) return { label: "Overdue", color: "bg-red-600" };
  if (diff === 0) return { label: "Due today", color: "bg-red-500" };
  if (diff <= 3) return { label: `${diff}d left`, color: "bg-orange-500" };
  return { label: `${diff}d left`, color: "bg-green-700" };
}

function Spin({ className = "" }: { className?: string }) {
  return <Loader2 className={`animate-spin shrink-0 ${className}`} />;
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton className="h-8 w-64 bg-slate-800" />
          <Skeleton className="h-4 w-48 bg-slate-800" />
        </div>
        <Skeleton className="h-10 w-36 bg-slate-800" />
      </div>
      <Skeleton className="h-36 w-full bg-slate-800 rounded-xl" />
      <div className="grid grid-cols-2 gap-4">
        <Skeleton className="h-20 bg-slate-800 rounded-xl" />
        <Skeleton className="h-20 bg-slate-800 rounded-xl" />
      </div>
      <div className="grid grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-32 bg-slate-800 rounded-xl" />)}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [period, setPeriod] = useState<string>(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("bemyca_period") ?? PERIODS[0];
    }
    return PERIODS[0];
  });

  const cacheKey = `dashboard:${period}`;
  const cached = cacheGet<CacheData>(cacheKey);

  const [business, setBusiness] = useState<Business | null>(cached?.business ?? null);
  const [gstr3b, setGstr3b] = useState<GSTR3B | null>(cached?.gstr3b ?? null);
  const [recon, setRecon] = useState<ReconSummary | null>(cached?.recon ?? null);
  const [outCount, setOutCount] = useState<number | null>(cached?.outCount ?? null);
  const [inCount, setInCount] = useState<number | null>(cached?.inCount ?? null);
  const [loading, setLoading] = useState(!cached);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    const cached = cacheGet<CacheData>(cacheKey);
    if (!cached) {
      setBusiness(null);
      setGstr3b(null);
      setRecon(null);
      setOutCount(null);
      setInCount(null);
    }

    async function load(silent: boolean) {
      if (!silent) setLoading(true);
      else setRefreshing(true);
      try {
        const [bRes, reconRes, outRes, inRes] = await Promise.all([
          fetch(`${API}/business/me`, { headers: authHeaders() }),
          fetch(`${API}/gst/reconciliation/summary?period=${period}`, { headers: authHeaders() }),
          fetch(`${API}/invoices/outward?period=${period}`, { headers: authHeaders() }),
          fetch(`${API}/invoices/inward?period=${period}`, { headers: authHeaders() }),
        ]);
        const bData: Business | null = bRes.ok ? await bRes.json() : null;
        const reconData: ReconSummary | null = reconRes.ok ? await reconRes.json() : null;
        const outData = outRes.ok ? await outRes.json() : null;
        const inData = inRes.ok ? await inRes.json() : null;

        if (bData) setBusiness(bData);
        if (reconData) setRecon(reconData);
        if (outData) setOutCount(Array.isArray(outData) ? outData.length : 0);
        if (inData) setInCount(Array.isArray(inData) ? inData.length : 0);

        const g3Res = await fetch(`${API}/returns/gstr3b?period=${period}`, { headers: authHeaders() });
        const g3Data: GSTR3B | null = g3Res.ok ? await g3Res.json() : null;
        if (g3Data) setGstr3b(g3Data);

        cacheSet(cacheKey, {
          business: bData,
          gstr3b: g3Data,
          recon: reconData,
          outCount: outData ? (Array.isArray(outData) ? outData.length : 0) : null,
          inCount: inData ? (Array.isArray(inData) ? inData.length : 0) : null,
        });
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    }

    load(!!cached);
  }, [period]);

  function handlePeriodChange(value: string) {
    setPeriod(value);
    if (typeof window !== "undefined") {
      localStorage.setItem("bemyca_period", value);
    }
  }

  if (loading) return <DashboardSkeleton />;

  const gstr1Due = filingDeadline(period, 11);
  const gstr3bDue = filingDeadline(period, 20);

  const stats = [
    {
      label: "Sales Invoices",
      value: outCount !== null ? String(outCount) : "—",
      icon: ReceiptText,
      color: "text-blue-400",
      bg: "bg-blue-950/40",
      href: `/invoices/outward?period=${period}`,
    },
    {
      label: "Purchase Invoices",
      value: inCount !== null ? String(inCount) : "—",
      icon: FileText,
      color: "text-purple-400",
      bg: "bg-purple-950/40",
      href: `/invoices/inward?period=${period}`,
    },
    {
      label: "Matched (GSTR-2B)",
      value: recon ? String(recon.matched) : "—",
      icon: CheckCircle2,
      color: "text-green-400",
      bg: "bg-green-950/40",
      href: "/reconciliation/gst",
    },
    {
      label: "ITC at Risk",
      value: recon ? String(recon.missing_in_books + recon.amount_mismatch) + " invoices" : "—",
      icon: AlertTriangle,
      color: "text-red-400",
      bg: "bg-red-950/40",
      href: "/reconciliation/gst",
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            {business?.legal_name ?? "Dashboard"}
            {refreshing && <Spin className="w-4 h-4 text-slate-600" />}
          </h1>
          <p className="text-slate-400 text-sm mt-0.5">
            {business ? `GSTIN ${business.gstin}` : "GST Dashboard"}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={period} onValueChange={handlePeriodChange}>
            <SelectTrigger className="w-48 bg-slate-900 border-slate-700 text-white">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-slate-900 border-slate-700 text-white">
              {PERIODS.map((p) => (
                <SelectItem key={p} value={p} className="text-white hover:bg-slate-800 focus:bg-slate-800">
                  {formatPeriodLabel(p)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Link href="/invoices/outward/new">
            <Button className="bg-blue-600 hover:bg-blue-700">
              <PlusCircle className="w-4 h-4 mr-2" /> Add Invoice
            </Button>
          </Link>
        </div>
      </div>

      {/* GST liability card */}
      <Card className="bg-gradient-to-r from-blue-950 to-slate-900 border-blue-800">
        <CardContent className="p-6">
          <div className="flex items-start justify-between flex-wrap gap-4">
            <div>
              <p className="text-slate-400 text-sm">GST to pay · {formatPeriodLabel(period)}</p>
              <p className="text-4xl font-bold text-white mt-1 flex items-center gap-2">
                {gstr3b ? fmt(gstr3b.total_tax_payable) : "—"}
                {refreshing && <Spin className="w-5 h-5 text-slate-600" />}
              </p>
              {gstr3b?.computed_payload && (
                <div className="flex gap-6 mt-3 text-sm text-slate-400">
                  <span>Tax collected: <span className="text-white">{fmt(gstr3b.computed_payload.outward_tax_liability.total)}</span></span>
                  <span>ITC credit: <span className="text-green-400">−{fmt(gstr3b.computed_payload.itc_available.total)}</span></span>
                </div>
              )}
              {!gstr3b && <p className="text-slate-500 text-sm mt-2">Compute GSTR-3B to see your liability</p>}
            </div>
            <div className="flex flex-col gap-2">
              <Link href="/returns/gstr3b">
                <Button className="bg-blue-600 hover:bg-blue-700 w-full">
                  {gstr3b?.status?.toUpperCase() === "FILED" ? "Filed ✓" : "Review & File GSTR-3B"}
                  <ArrowRight className="w-4 h-4 ml-1" />
                </Button>
              </Link>
              <Link href="/returns/gstr1">
                <Button variant="outline" className="border-blue-700 text-slate-300 hover:text-white w-full">
                  Review GSTR-1
                </Button>
              </Link>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Deadline cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {[
          { label: "GSTR-1 (Outward Sales)", due: gstr1Due, desc: "11th of next month", href: "/returns/gstr1" },
          { label: "GSTR-3B (Summary + Payment)", due: gstr3bDue, desc: "20th of next month", href: "/returns/gstr3b" },
        ].map((item) => (
          <Link key={item.label} href={item.href}>
            <Card className="bg-slate-900 border-slate-800 hover:border-slate-700 transition-colors cursor-pointer">
              <CardContent className="p-4 flex items-center gap-4">
                <CalendarDays className="w-8 h-8 text-slate-500 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-white text-sm font-medium">{item.label}</p>
                  <p className="text-slate-500 text-xs">{item.desc}</p>
                </div>
                <Badge className={`${item.due.color} text-white text-xs flex-shrink-0`}>{item.due.label}</Badge>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      {/* Stat tiles */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <Link key={stat.label} href={stat.href}>
            <Card className="bg-slate-900 border-slate-800 hover:border-slate-700 transition-colors cursor-pointer">
              <CardContent className="p-5">
                <div className={`w-10 h-10 ${stat.bg} rounded-lg flex items-center justify-center mb-3`}>
                  <stat.icon className={`w-5 h-5 ${stat.color}`} />
                </div>
                <p className="text-2xl font-bold text-white flex items-center gap-1.5">
                  {stat.value}
                  {refreshing && <Spin className="w-3.5 h-3.5 text-slate-600" />}
                </p>
                <p className="text-slate-400 text-sm mt-0.5">{stat.label}</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      {/* Quick actions */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader className="pb-3">
          <CardTitle className="text-white text-base">Quick actions · {formatPeriodLabel(period)}</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <Link href="/invoices/outward/new">
            <Button variant="outline" className="border-slate-700 text-slate-300 hover:text-white">
              <PlusCircle className="w-4 h-4 mr-2" /> Add sales invoice
            </Button>
          </Link>
          <Link href="/invoices/inward/new">
            <Button variant="outline" className="border-slate-700 text-slate-300 hover:text-white">
              <PlusCircle className="w-4 h-4 mr-2" /> Add purchase invoice
            </Button>
          </Link>
          <Link href="/reconciliation/gst">
            <Button variant="outline" className="border-slate-700 text-slate-300 hover:text-white">
              <TrendingUp className="w-4 h-4 mr-2" /> Run GSTR-2B reconciliation
            </Button>
          </Link>
          <Link href="/returns/gstr1">
            <Button variant="outline" className="border-slate-700 text-slate-300 hover:text-white">
              <FileText className="w-4 h-4 mr-2" /> Compute GSTR-1
            </Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
