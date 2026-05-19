"use client";
import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { PlusCircle, Search, Pencil, Trash2, Download } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { cacheGet, cacheSet } from "@/lib/cache";
import { downloadCsv } from "@/lib/csv";
import { downloadInvoicePdf } from "@/components/invoice-pdf";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

function getPeriod() {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("bemyca_period") ?? "";
}

function token() { return typeof window !== "undefined" ? localStorage.getItem("bemyca_token") ?? "" : ""; }
function authH() { return { Authorization: `Bearer ${token()}` }; }
function fmt(n: string | number) { return "₹" + Number(n).toLocaleString("en-IN"); }

interface Invoice {
  id: string; invoice_number: string; invoice_date: string; customer_name: string;
  customer_gstin: string | null; invoice_type: string; taxable_value: string;
  igst: string; cgst: string; sgst: string; cess?: string; hsn_code?: string | null;
  place_of_supply?: string; source: string;
}

interface Business { legal_name: string; gstin: string; pan: string; state_code: string; }

const TYPE_LABELS: Record<string, string> = {
  b2b: "B2B", b2c_large: "B2C Large", b2c_small: "B2C Small", export: "Export", credit_note: "Credit Note",
};

function ListSkeleton() {
  return (
    <div className="divide-y divide-slate-800">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="flex items-center gap-4 px-4 py-3">
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-48 bg-slate-800" />
            <Skeleton className="h-3 w-64 bg-slate-800" />
          </div>
          <div className="text-right space-y-2">
            <Skeleton className="h-4 w-20 bg-slate-800 ml-auto" />
            <Skeleton className="h-3 w-16 bg-slate-800 ml-auto" />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function OutwardListPage() {
  const [period] = useState(getPeriod);
  const cacheKey = `invoices:outward:${period}`;
  const cached = cacheGet<Invoice[]>(cacheKey);
  const [invoices, setInvoices] = useState<Invoice[]>(cached ?? []);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(!cached);
  const [business, setBusiness] = useState<Business | null>(null);

  useEffect(() => {
    async function load(silent: boolean) {
      if (!silent) setLoading(true);
      const [invRes, bizRes] = await Promise.all([
        fetch(`${API}/invoices/outward?period=${period}`, { headers: authH() }),
        fetch(`${API}/business/me`, { headers: authH() }),
      ]);
      if (invRes.ok) {
        const data = await invRes.json();
        setInvoices(data);
        cacheSet(cacheKey, data);
      }
      if (bizRes.ok) setBusiness(await bizRes.json());
      setLoading(false);
    }
    load(!!cached);
  }, [period]);

  async function del(id: string) {
    if (!confirm("Delete this invoice?")) return;
    const res = await fetch(`${API}/invoices/outward/${id}`, { method: "DELETE", headers: authH() });
    if (res.ok) {
      toast.success("Deleted");
      const updated = invoices.filter(i => i.id !== id);
      setInvoices(updated);
      cacheSet(cacheKey, updated);
    } else toast.error("Delete failed");
  }

  const filtered = invoices.filter(i =>
    i.customer_name.toLowerCase().includes(search.toLowerCase()) ||
    i.invoice_number.toLowerCase().includes(search.toLowerCase())
  );
  const totalTax = invoices.reduce((s, i) => s + Number(i.igst) + Number(i.cgst) + Number(i.sgst), 0);
  const totalTaxable = invoices.reduce((s, i) => s + Number(i.taxable_value), 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Sales Invoices</h1>
          <p className="text-slate-400 text-sm mt-0.5">Period: {period}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="border-slate-700 text-slate-300 hover:text-white"
            onClick={() => downloadCsv(`sales-invoices-${period}.csv`, invoices.map(i => ({
              invoice_number: i.invoice_number, invoice_date: i.invoice_date,
              customer_name: i.customer_name, customer_gstin: i.customer_gstin ?? "",
              invoice_type: i.invoice_type, taxable_value: i.taxable_value,
              igst: i.igst, cgst: i.cgst, sgst: i.sgst,
              total_tax: Number(i.igst) + Number(i.cgst) + Number(i.sgst),
            })))} disabled={invoices.length === 0}>
            <Download className="w-4 h-4 mr-2" /> Export CSV
          </Button>
          <Link href="/invoices/outward/new">
            <Button className="bg-blue-600 hover:bg-blue-700">
              <PlusCircle className="w-4 h-4 mr-2" /> Add Invoice
            </Button>
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {loading ? (
          [...Array(3)].map((_, i) => (
            <Card key={i} className="bg-slate-900 border-slate-800">
              <CardContent className="p-4 space-y-2">
                <Skeleton className="h-7 w-24 bg-slate-800" />
                <Skeleton className="h-4 w-20 bg-slate-800" />
              </CardContent>
            </Card>
          ))
        ) : (
          [
            { label: "Invoices", value: String(invoices.length) },
            { label: "Total Taxable", value: fmt(totalTaxable) },
            { label: "GST Collected", value: fmt(totalTax) },
          ].map(s => (
            <Card key={s.label} className="bg-slate-900 border-slate-800">
              <CardContent className="p-4">
                <p className="text-2xl font-bold text-white">{s.value}</p>
                <p className="text-slate-400 text-sm mt-0.5">{s.label}</p>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      <Card className="bg-slate-900 border-slate-800">
        <CardContent className="p-0">
          <div className="p-4 border-b border-slate-800">
            <div className="relative">
              <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
              <Input
                placeholder="Search customer or invoice number…"
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="pl-9 bg-slate-800 border-slate-700 text-white placeholder:text-slate-500"
              />
            </div>
          </div>

          {loading ? (
            <ListSkeleton />
          ) : filtered.length === 0 ? (
            <div className="p-8 text-center text-slate-400">
              No invoices.{" "}
              <Link href="/invoices/outward/new" className="text-blue-400 hover:underline">Add one?</Link>
            </div>
          ) : (
            <div className="divide-y divide-slate-800">
              {filtered.map(inv => (
                <div key={inv.id} className="flex items-center gap-4 px-4 py-3 hover:bg-slate-800/50 transition-colors">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-white text-sm font-medium">{inv.customer_name}</span>
                      <Badge variant="outline" className="text-xs border-slate-600 text-slate-400">
                        {TYPE_LABELS[inv.invoice_type] ?? inv.invoice_type}
                      </Badge>
                    </div>
                    <p className="text-slate-400 text-xs font-mono mt-0.5">
                      {inv.invoice_number} · {inv.invoice_date}
                      {inv.customer_gstin && ` · ${inv.customer_gstin}`}
                    </p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <p className="text-white text-sm font-semibold">{fmt(inv.taxable_value)}</p>
                    <p className="text-slate-400 text-xs">GST: {fmt(Number(inv.igst) + Number(inv.cgst) + Number(inv.sgst))}</p>
                  </div>
                  <div className="flex gap-1 flex-shrink-0">
                    {business && (
                      <Button size="icon" variant="ghost" className="w-8 h-8 text-slate-400 hover:text-blue-400"
                        title="Download PDF"
                        onClick={() => downloadInvoicePdf(business, { ...inv, cess: inv.cess ?? "0", place_of_supply: inv.place_of_supply ?? inv.customer_gstin?.slice(0, 2) ?? business.state_code ?? "27" })}>
                        <Download className="w-3.5 h-3.5" />
                      </Button>
                    )}
                    <Link href={`/invoices/outward/${inv.id}`}>
                      <Button size="icon" variant="ghost" className="w-8 h-8 text-slate-400 hover:text-white">
                        <Pencil className="w-3.5 h-3.5" />
                      </Button>
                    </Link>
                    <Button size="icon" variant="ghost" className="w-8 h-8 text-slate-400 hover:text-red-400" onClick={() => del(inv.id)}>
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
