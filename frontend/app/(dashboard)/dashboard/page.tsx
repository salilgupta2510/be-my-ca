"use client";
import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, ArrowRight, CalendarDays, CheckCircle2, FileText, PlusCircle, ReceiptText, TrendingUp } from "lucide-react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const PERIOD = "2025-01";

function token() {
  return typeof window !== "undefined" ? localStorage.getItem("bemyca_token") ?? "" : "";
}

function authHeaders() {
  return { Authorization: `Bearer ${token()}`, "Content-Type": "application/json" };
}

function fmt(n: number) {
  return "₹" + n.toLocaleString("en-IN");
}

interface Business {
  legal_name: string;
  gstin: string;
  state_code: string;
  return_frequency: string;
}

interface GSTR3BPayload {
  outward_tax_liability: { total: number };
  itc_available: { total: number };
  net_tax_payable: { total: number };
  reconciliation_done: boolean;
}

interface GSTR3B {
  id: string;
  status: string;
  total_tax_payable: number;
  itc_claimed: number;
  computed_payload: GSTR3BPayload | null;
}

interface ReconSummary {
  matched: number;
  missing_in_2b: number;
  missing_in_books: number;
  amount_mismatch: number;
}

function filingDeadline(day: number) {
  const now = new Date();
  const due = new Date(now.getFullYear(), now.getMonth(), day);
  const diff = Math.ceil((due.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  if (diff < 0) return { label: "Overdue", color: "bg-red-600" };
  if (diff === 0) return { label: "Due today", color: "bg-red-500" };
  if (diff <= 3) return { label: `${diff}d left`, color: "bg-orange-500" };
  return { label: `${diff}d left`, color: "bg-green-700" };
}

export default function DashboardPage() {
  const [business, setBusiness] = useState<Business | null>(null);
  const [gstr3b, setGstr3b] = useState<GSTR3B | null>(null);
  const [recon, setRecon] = useState<ReconSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [bRes, reconRes] = await Promise.all([
          fetch(`${API}/business/me`, { headers: authHeaders() }),
          fetch(`${API}/gst/reconciliation/summary?period=${PERIOD}`, { headers: authHeaders() }),
        ]);
        if (bRes.ok) setBusiness(await bRes.json());
        if (reconRes.ok) setRecon(await reconRes.json());

        const g3Res = await fetch(`${API}/returns/gstr3b?period=${PERIOD}`, { headers: authHeaders() });
        if (g3Res.ok) setGstr3b(await g3Res.json());
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const gstr1Due = filingDeadline(11);
  const gstr3bDue = filingDeadline(20);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">
            {business ? business.legal_name : "Dashboard"}
          </h1>
          <p className="text-slate-400 text-sm mt-0.5">
            {business ? `GSTIN ${business.gstin} · ${PERIOD}` : "Loading…"}
          </p>
        </div>
        <Link href="/invoices/outward/new">
          <Button className="bg-blue-600 hover:bg-blue-700">
            <PlusCircle className="w-4 h-4 mr-2" /> Add Invoice
          </Button>
        </Link>
      </div>

      {/* Hero: Net GST payable */}
      <Card className="bg-gradient-to-r from-blue-950 to-slate-900 border-blue-800">
        <CardContent className="p-6">
          <div className="flex items-start justify-between flex-wrap gap-4">
            <div>
              <p className="text-slate-400 text-sm">GST to pay this month</p>
              <p className="text-4xl font-bold text-white mt-1">
                {gstr3b ? fmt(gstr3b.total_tax_payable) : loading ? "Loading…" : "—"}
              </p>
              {gstr3b?.computed_payload && (
                <div className="flex gap-6 mt-3 text-sm text-slate-400">
                  <span>Tax collected: <span className="text-white">{fmt(gstr3b.computed_payload.outward_tax_liability.total)}</span></span>
                  <span>ITC credit: <span className="text-green-400">−{fmt(gstr3b.computed_payload.itc_available.total)}</span></span>
                </div>
              )}
              {!gstr3b && !loading && (
                <p className="text-slate-500 text-sm mt-2">Compute GSTR-3B to see your liability</p>
              )}
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

      {/* Filing deadlines */}
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

      {/* Activity cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            label: "Sales Invoices",
            value: "—",
            icon: ReceiptText,
            color: "text-blue-400",
            bg: "bg-blue-950/40",
            href: "/invoices/outward",
          },
          {
            label: "Purchase Invoices",
            value: "—",
            icon: FileText,
            color: "text-purple-400",
            bg: "bg-purple-950/40",
            href: "/invoices/inward",
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
        ].map((stat) => (
          <Link key={stat.label} href={stat.href}>
            <Card className="bg-slate-900 border-slate-800 hover:border-slate-700 transition-colors cursor-pointer">
              <CardContent className="p-5">
                <div className={`w-10 h-10 ${stat.bg} rounded-lg flex items-center justify-center mb-3`}>
                  <stat.icon className={`w-5 h-5 ${stat.color}`} />
                </div>
                <p className="text-2xl font-bold text-white">{stat.value}</p>
                <p className="text-slate-400 text-sm mt-0.5">{stat.label}</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      {/* Quick actions */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader className="pb-3">
          <CardTitle className="text-white text-base">Quick actions for {PERIOD}</CardTitle>
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
