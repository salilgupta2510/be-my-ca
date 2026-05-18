"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ArrowLeft, Loader2 } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

function token() { return typeof window !== "undefined" ? localStorage.getItem("bemyca_token") ?? "" : ""; }
function authH(json = false) {
  const h: Record<string, string> = { Authorization: `Bearer ${token()}` };
  if (json) h["Content-Type"] = "application/json";
  return h;
}

const TYPES = [
  { value: "b2b", label: "B2B" }, { value: "b2c_large", label: "B2C Large" },
  { value: "b2c_small", label: "B2C Small" }, { value: "export", label: "Export" },
  { value: "credit_note", label: "Credit Note" },
];

export default function EditOutwardPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [form, setForm] = useState({
    invoice_number: "", invoice_date: "", customer_name: "", customer_gstin: "",
    place_of_supply: "27", invoice_type: "b2b",
    taxable_value: "", igst: "0", cgst: "0", sgst: "0", cess: "0", period: "2025-01",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    (async () => {
      // Load full list and find by id (no single-get endpoint)
      const res = await fetch(`${API}/invoices/outward?period=2025-01`, { headers: authH() });
      if (res.ok) {
        const list = await res.json();
        const inv = list.find((i: { id: string }) => i.id === id);
        if (inv) setForm({
          invoice_number: inv.invoice_number,
          invoice_date: inv.invoice_date,
          customer_name: inv.customer_name,
          customer_gstin: inv.customer_gstin ?? "",
          place_of_supply: inv.place_of_supply,
          invoice_type: inv.invoice_type,
          taxable_value: inv.taxable_value,
          igst: inv.igst,
          cgst: inv.cgst,
          sgst: inv.sgst,
          cess: inv.cess ?? "0",
          period: inv.period,
        });
      }
      setLoading(false);
    })();
  }, [id]);

  function setF(k: string, v: string) { setForm(f => ({ ...f, [k]: v })); }

  async function handleSave() {
    setSaving(true);
    try {
      const res = await fetch(`${API}/invoices/outward/${id}`, {
        method: "PUT",
        headers: authH(true),
        body: JSON.stringify({
          ...form,
          customer_gstin: form.customer_gstin || null,
        }),
      });
      if (!res.ok) throw new Error((await res.json()).detail ?? "Save failed");
      toast.success("Invoice updated");
      router.push("/invoices/outward");
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className="text-slate-400 p-8">Loading…</div>;

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center gap-3">
        <Link href="/invoices/outward">
          <Button variant="ghost" size="icon" className="text-slate-400 hover:text-white">
            <ArrowLeft className="w-4 h-4" />
          </Button>
        </Link>
        <h1 className="text-2xl font-bold text-white">Edit Invoice</h1>
      </div>

      <Card className="bg-slate-900 border-slate-800">
        <CardHeader><CardTitle className="text-white text-base">Invoice details</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label className="text-slate-300 text-xs">Invoice Number</Label>
              <Input value={form.invoice_number} onChange={e => setF("invoice_number", e.target.value)}
                className="bg-slate-800 border-slate-700 text-white" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-slate-300 text-xs">Invoice Date</Label>
              <Input type="date" value={form.invoice_date} onChange={e => setF("invoice_date", e.target.value)}
                className="bg-slate-800 border-slate-700 text-white" />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label className="text-slate-300 text-xs">Customer Name</Label>
            <Input value={form.customer_name} onChange={e => setF("customer_name", e.target.value)}
              className="bg-slate-800 border-slate-700 text-white" />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label className="text-slate-300 text-xs">Customer GSTIN</Label>
              <Input value={form.customer_gstin} onChange={e => setF("customer_gstin", e.target.value.toUpperCase())}
                className="bg-slate-800 border-slate-700 text-white font-mono" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-slate-300 text-xs">Place of Supply</Label>
              <Input value={form.place_of_supply} onChange={e => setF("place_of_supply", e.target.value)}
                maxLength={2} className="bg-slate-800 border-slate-700 text-white font-mono" />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label className="text-slate-300 text-xs">Invoice Type</Label>
            <select value={form.invoice_type} onChange={e => setF("invoice_type", e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 text-white rounded-md px-3 py-2 text-sm">
              {TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>

          <div className="space-y-1.5">
            <Label className="text-slate-300 text-xs">Taxable Value (₹)</Label>
            <Input type="number" value={form.taxable_value} onChange={e => setF("taxable_value", e.target.value)}
              className="bg-slate-800 border-slate-700 text-white" />
          </div>

          <div className="grid grid-cols-3 gap-3">
            {[{ k: "igst", label: "IGST" }, { k: "cgst", label: "CGST" }, { k: "sgst", label: "SGST" }].map(({ k, label }) => (
              <div key={k} className="space-y-1.5">
                <Label className="text-slate-300 text-xs">{label} (₹)</Label>
                <Input type="number" value={(form as Record<string, string>)[k]} onChange={e => setF(k, e.target.value)}
                  className="bg-slate-800 border-slate-700 text-white" />
              </div>
            ))}
          </div>

          <Button className="w-full bg-blue-600 hover:bg-blue-700" onClick={handleSave} disabled={saving}>
            {saving ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Saving…</> : "Update Invoice"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
