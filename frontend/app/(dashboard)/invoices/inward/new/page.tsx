"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { validateGstin } from "@/lib/gstin";

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

export default function NewInwardPage() {
  const router = useRouter();
  const [period] = useState(getPeriod);
  const [form, setForm] = useState({
    supplier_name: "", supplier_gstin: "",
    invoice_number: "", invoice_date: "",
    taxable_value: "", igst: "0", cgst: "0", sgst: "0",
    hsn_code: "", is_rcm: false,
  });
  const [saving, setSaving] = useState(false);

  function setF(k: string, v: string) { setForm(f => ({ ...f, [k]: v })); }

  async function handleSave() {
    setSaving(true);
    try {
      const res = await fetch(`${API}/invoices/inward`, {
        method: "POST",
        headers: authH(true),
        body: JSON.stringify({
          period: period,
          supplier_name: form.supplier_name,
          supplier_gstin: form.supplier_gstin || null,
          invoice_number: form.invoice_number,
          invoice_date: form.invoice_date,
          taxable_value: form.taxable_value,
          igst: form.igst || "0",
          cgst: form.cgst || "0",
          sgst: form.sgst || "0",
          hsn_code: form.hsn_code || null,
          is_rcm: form.is_rcm,
        }),
      });
      if (!res.ok) throw new Error((await res.json()).detail ?? "Save failed");
      toast.success("Invoice saved");
      router.push("/invoices/inward");
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center gap-3">
        <Link href="/invoices/inward">
          <Button variant="ghost" size="icon" className="text-slate-400 hover:text-white">
            <ArrowLeft className="w-4 h-4" />
          </Button>
        </Link>
        <h1 className="text-2xl font-bold text-white">Add Purchase Invoice</h1>
      </div>

      <Card className="bg-slate-900 border-slate-800">
        <CardHeader><CardTitle className="text-white text-base">Invoice details</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label className="text-slate-300 text-xs">Supplier Name</Label>
            <Input value={form.supplier_name} onChange={e => setF("supplier_name", e.target.value)}
              placeholder="Acme Supplies Ltd" className="bg-slate-800 border-slate-700 text-white" />
          </div>

          <div className="space-y-1.5">
            <Label className="text-slate-300 text-xs">Supplier GSTIN (optional)</Label>
            <Input value={form.supplier_gstin} onChange={e => setF("supplier_gstin", e.target.value.toUpperCase())}
              placeholder="27AABCS1429B1ZB" className={`bg-slate-800 border-slate-700 text-white font-mono ${form.supplier_gstin && validateGstin(form.supplier_gstin) ? "border-red-600" : ""}`} />
            {form.supplier_gstin && validateGstin(form.supplier_gstin) && (
              <p className="text-red-400 text-xs">{validateGstin(form.supplier_gstin)}</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label className="text-slate-300 text-xs">Invoice Number</Label>
              <Input value={form.invoice_number} onChange={e => setF("invoice_number", e.target.value)}
                placeholder="INV-2025-001" className="bg-slate-800 border-slate-700 text-white" />
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
              placeholder="100000" className="bg-slate-800 border-slate-700 text-white" />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label className="text-slate-300 text-xs">HSN / SAC Code (optional)</Label>
              <Input value={form.hsn_code} onChange={e => setF("hsn_code", e.target.value)}
                placeholder="998311" maxLength={8} className="bg-slate-800 border-slate-700 text-white font-mono" />
            </div>
            <div className="flex items-center gap-3 pt-5">
              <input type="checkbox" id="is_rcm" checked={form.is_rcm}
                onChange={e => setForm(f => ({ ...f, is_rcm: e.target.checked }))}
                className="w-4 h-4 accent-blue-500" />
              <Label htmlFor="is_rcm" className="text-slate-300 text-xs cursor-pointer">
                Reverse Charge (RCM)
              </Label>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            {[{ k: "igst", label: "IGST (₹)" }, { k: "cgst", label: "CGST (₹)" }, { k: "sgst", label: "SGST (₹)" }].map(({ k, label }) => (
              <div key={k} className="space-y-1.5">
                <Label className="text-slate-300 text-xs">{label}</Label>
                <Input type="number" value={(form as Record<string, unknown>)[k] as string}
                  onChange={e => setF(k, e.target.value)}
                  placeholder="0" className="bg-slate-800 border-slate-700 text-white" />
              </div>
            ))}
          </div>

          <Button className="w-full bg-blue-600 hover:bg-blue-700" onClick={handleSave} disabled={saving}>
            {saving ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Saving…</> : "Save Invoice"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
