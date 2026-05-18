"use client";
import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { PlusCircle, Search, Pencil, Trash2 } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const PERIOD = "2025-01";

function token() { return typeof window !== "undefined" ? localStorage.getItem("bemyca_token") ?? "" : ""; }
function authH() { return { Authorization: `Bearer ${token()}` }; }
function fmt(n: string | number) { return "₹" + Number(n).toLocaleString("en-IN"); }

interface Invoice {
  id: string;
  invoice_number: string;
  invoice_date: string;
  customer_name: string;
  customer_gstin: string | null;
  invoice_type: string;
  taxable_value: string;
  igst: string;
  cgst: string;
  sgst: string;
  source: string;
}

const TYPE_LABELS: Record<string, string> = {
  b2b: "B2B", b2c_large: "B2C Large", b2c_small: "B2C Small", export: "Export", credit_note: "Credit Note",
};

export default function OutwardListPage() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    const res = await fetch(`${API}/invoices/outward?period=${PERIOD}`, { headers: authH() });
    if (res.ok) setInvoices(await res.json());
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  async function del(id: string) {
    if (!confirm("Delete this invoice?")) return;
    const res = await fetch(`${API}/invoices/outward/${id}`, { method: "DELETE", headers: authH() });
    if (res.ok) { toast.success("Deleted"); setInvoices(inv => inv.filter(i => i.id !== id)); }
    else toast.error("Delete failed");
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
          <p className="text-slate-400 text-sm mt-0.5">Period: {PERIOD}</p>
        </div>
        <Link href="/invoices/outward/new">
          <Button className="bg-blue-600 hover:bg-blue-700">
            <PlusCircle className="w-4 h-4 mr-2" /> Add Invoice
          </Button>
        </Link>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {[
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
        ))}
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
            <div className="p-8 text-center text-slate-400">Loading…</div>
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
                    <p className="text-slate-400 text-xs">
                      GST: {fmt(Number(inv.igst) + Number(inv.cgst) + Number(inv.sgst))}
                    </p>
                  </div>
                  <div className="flex gap-1 flex-shrink-0">
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
