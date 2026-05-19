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

function getPeriod() {
  return typeof window !== "undefined" ? localStorage.getItem("bemyca_period") ?? "" : "";
}

export default function EditInwardPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [form, setForm] = useState({
    supplier_name: "", supplier_gstin: "",
    invoice_number: "", invoice_date: "",
    taxable_value: "", igst: "0", cgst: "0", sgst: "0",
    period: "",
  });
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    (async () => {
      const period = getPeriod();
      const res = await fetch(`${API}/invoices/inward?period=${period}`, { headers: authH() });
      if (res.ok) {
        const list = await res.json();
        const inv = list.find((i: { id: string }) => i.id === id);
        if (inv) {
          setForm({
            supplier_name: inv.supplier_name,
            supplier_gstin: inv.supplier_gstin ?? "",
            invoice_number: inv.invoice_number,
            invoice_date: inv.invoice_date,
            taxable_value: inv.taxable_value,
            igst: inv.igst,
            cgst: inv.cgst,
            sgst: inv.sgst,
            period: inv.period,
          });
        } else {
          setNotFound(true);
        }
      } else {
        setNotFound(true);
      }
      setLoading(false);
    })();
  }, [id]);

  function setF(k: string, v: string) { setForm(f => ({ ...f, [k]: v })); }

  async function handleSave() {
    setSaving(true);
    try {
      const res = await fetch(`${API}/invoices/inward/${id}`, {
        method: "PUT",
        headers: authH(true),
        body: JSON.stringify({
          ...form,
          supplier_gstin: form.supplier_gstin || null,
        }),
      });
      if (!res.ok) throw new Error((await res.json()).detail ?? "Save failed");
      toast.success("Invoice updated");
      router.push("/invoices/inward");
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className="text-slate-400 p-8">Loading…</div>;

  if (notFound) return (
    <div className="space-y-4 max-w-2xl">
      <div className="flex items-center gap-3">
        <Link href="/invoices/inward">
          <Button variant="ghost" size="icon" className="text-slate-400 hover:text-white">
            <ArrowLeft className="w-4 h-4" />
          </Button>
        </Link>
        <h1 className="text-2xl font-bold text-white">Edit Invoice</h1>
      </div>
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-8 text-center">
        <p className="text-slate-400 text-sm">Invoice not found for the current period.</p>
        <p className="text-slate-500 text-xs mt-1">Make sure the correct period is selected in the dashboard.</p>
        <Link href="/invoices/inward">
          <Button variant="outline" className="mt-4 border-slate-700 text-slate-300 hover:text-white">Back to invoices</Button>
        </Link>
      </div>
    </div>
  );

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center gap-3">
        <Link href="/invoices/inward">
          <Button variant="ghost" size="icon" className="text-slate-400 hover:text-white">
            <ArrowLeft className="w-4 h-4" />
          </Button>
        </Link>
        <h1 className="text-2xl font-bold text-white">Edit Invoice</h1>
      </div>

      <Card className="bg-slate-900 border-slate-800">
        <CardHeader><CardTitle className="text-white text-base">Invoice details</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label className="text-slate-300 text-xs">Supplier Name</Label>
            <Input value={form.supplier_name} onChange={e => setF("supplier_name", e.target.value)}
              className="bg-slate-800 border-slate-700 text-white" />
          </div>

          <div className="space-y-1.5">
            <Label className="text-slate-300 text-xs">Supplier GSTIN</Label>
            <Input value={form.supplier_gstin} onChange={e => setF("supplier_gstin", e.target.value.toUpperCase())}
              className="bg-slate-800 border-slate-700 text-white font-mono" />
          </div>

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
