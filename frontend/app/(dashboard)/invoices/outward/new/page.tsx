"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Upload, FileText, Loader2, ArrowLeft, CheckCircle } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";

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

const TYPES = [
  { value: "b2b", label: "B2B (Registered buyer)" },
  { value: "b2c_large", label: "B2C Large (>₹2.5L, inter-state)" },
  { value: "b2c_small", label: "B2C Small" },
  { value: "export", label: "Export" },
  { value: "credit_note", label: "Credit Note" },
];

interface DraftValues {
  invoice_number: string;
  invoice_date: string;
  customer_name: string;
  taxable_value: string;
  cgst: string;
  sgst: string;
  igst: string;
}

export default function NewOutwardPage() {
  const router = useRouter();
  const [period] = useState(getPeriod);
  const [tab, setTab] = useState<"upload" | "manual">("upload");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [draftId, setDraftId] = useState<string | null>(null);
  const [draft, setDraft] = useState<DraftValues | null>(null);

  // Manual / confirm form fields
  const [form, setForm] = useState({
    invoice_number: "", invoice_date: "", customer_name: "", customer_gstin: "",
    place_of_supply: "27", invoice_type: "b2b",
    taxable_value: "", igst: "0", cgst: "0", sgst: "0", cess: "0",
  });
  const [saving, setSaving] = useState(false);

  function setF(k: string, v: string) { setForm(f => ({ ...f, [k]: v })); }

  async function handleUpload() {
    if (!file) { toast.error("Select a file first"); return; }
    setUploading(true);
    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await fetch(`${API}/invoices/outward/upload?period=${period}`, {
        method: "POST", headers: authH(), body: fd,
      });
      if (!res.ok) throw new Error((await res.json()).detail ?? "Upload failed");
      const data = await res.json();
      setDraftId(data.draft_id);
      setDraft(data.extracted);
      setForm(f => ({
        ...f,
        invoice_number: data.extracted.invoice_number ?? f.invoice_number,
        invoice_date: data.extracted.invoice_date ?? f.invoice_date,
        customer_name: data.extracted.customer_name ?? f.customer_name,
        taxable_value: data.extracted.taxable_value ?? f.taxable_value,
        cgst: data.extracted.cgst ?? f.cgst,
        sgst: data.extracted.sgst ?? f.sgst,
        igst: data.extracted.igst ?? f.igst,
      }));
      toast.success("Invoice read. Review and confirm below.");
      setTab("manual");
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function handleSave() {
    setSaving(true);
    try {
      const body = {
        period: period,
        invoice_number: form.invoice_number,
        invoice_date: form.invoice_date,
        customer_name: form.customer_name,
        customer_gstin: form.customer_gstin || null,
        place_of_supply: form.place_of_supply,
        invoice_type: form.invoice_type,
        taxable_value: form.taxable_value,
        igst: form.igst || "0",
        cgst: form.cgst || "0",
        sgst: form.sgst || "0",
        cess: form.cess || "0",
      };

      let res: Response;
      if (draftId) {
        res = await fetch(`${API}/invoices/outward/${draftId}`, {
          method: "PUT", headers: authH(true), body: JSON.stringify(body),
        });
      } else {
        res = await fetch(`${API}/invoices/outward`, {
          method: "POST", headers: authH(true), body: JSON.stringify(body),
        });
      }

      if (!res.ok) throw new Error((await res.json()).detail ?? "Save failed");
      toast.success("Invoice saved");
      router.push("/invoices/outward");
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center gap-3">
        <Link href="/invoices/outward">
          <Button variant="ghost" size="icon" className="text-slate-400 hover:text-white">
            <ArrowLeft className="w-4 h-4" />
          </Button>
        </Link>
        <h1 className="text-2xl font-bold text-white">Add Sales Invoice</h1>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-800 p-1 rounded-lg w-fit">
        {(["upload", "manual"] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              tab === t ? "bg-slate-700 text-white" : "text-slate-400 hover:text-white"
            }`}
          >
            {t === "upload" ? "📷 Upload photo" : "✏️ Manual entry"}
          </button>
        ))}
      </div>

      {/* Upload tab */}
      {tab === "upload" && (
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="text-white text-base">Upload invoice image</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <label
              className={`block border-2 border-dashed rounded-lg p-10 text-center cursor-pointer transition-colors ${
                file ? "border-green-600 bg-green-950/20" : "border-slate-700 hover:border-blue-600"
              }`}
            >
              <input
                type="file"
                accept="image/*,application/pdf"
                className="hidden"
                onChange={e => setFile(e.target.files?.[0] ?? null)}
              />
              {file ? (
                <div className="flex flex-col items-center gap-2 text-green-400">
                  <CheckCircle className="w-8 h-8" />
                  <span className="font-medium">{file.name}</span>
                  <span className="text-sm text-slate-400">Click to change</span>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-2 text-slate-400">
                  <Upload className="w-8 h-8" />
                  <span className="font-medium text-white">Drop invoice here or click to browse</span>
                  <span className="text-sm">JPG, PNG or PDF · max 10 MB</span>
                </div>
              )}
            </label>

            <Button
              className="w-full bg-blue-600 hover:bg-blue-700"
              onClick={handleUpload}
              disabled={!file || uploading}
            >
              {uploading ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Reading invoice…</>
              ) : (
                "Extract & Pre-fill →"
              )}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Manual / confirm form */}
      {tab === "manual" && (
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="text-white text-base flex items-center gap-2">
              <FileText className="w-4 h-4 text-blue-400" />
              {draft ? "Confirm extracted values" : "Invoice details"}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
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
              <Label className="text-slate-300 text-xs">Customer Name</Label>
              <Input value={form.customer_name} onChange={e => setF("customer_name", e.target.value)}
                placeholder="Acme Corp Ltd" className="bg-slate-800 border-slate-700 text-white" />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label className="text-slate-300 text-xs">Customer GSTIN (optional for B2C)</Label>
                <Input value={form.customer_gstin} onChange={e => setF("customer_gstin", e.target.value.toUpperCase())}
                  placeholder="27AABCS1429B1ZB" className="bg-slate-800 border-slate-700 text-white font-mono" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-slate-300 text-xs">Place of Supply (state code)</Label>
                <Input value={form.place_of_supply} onChange={e => setF("place_of_supply", e.target.value)}
                  placeholder="27" maxLength={2} className="bg-slate-800 border-slate-700 text-white font-mono" />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label className="text-slate-300 text-xs">Invoice Type</Label>
              <select
                value={form.invoice_type}
                onChange={e => setF("invoice_type", e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 text-white rounded-md px-3 py-2 text-sm"
              >
                {TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>

            <div className="space-y-1.5">
              <Label className="text-slate-300 text-xs">Taxable Value (₹)</Label>
              <Input type="number" value={form.taxable_value} onChange={e => setF("taxable_value", e.target.value)}
                placeholder="100000" className="bg-slate-800 border-slate-700 text-white" />
            </div>

            <div className="grid grid-cols-3 gap-3">
              {[
                { k: "igst", label: "IGST (₹)" },
                { k: "cgst", label: "CGST (₹)" },
                { k: "sgst", label: "SGST (₹)" },
              ].map(({ k, label }) => (
                <div key={k} className="space-y-1.5">
                  <Label className="text-slate-300 text-xs">{label}</Label>
                  <Input type="number" value={(form as Record<string, string>)[k]}
                    onChange={e => setF(k, e.target.value)}
                    placeholder="0" className="bg-slate-800 border-slate-700 text-white" />
                </div>
              ))}
            </div>

            <Button
              className="w-full bg-blue-600 hover:bg-blue-700"
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Saving…</> : "Save Invoice"}
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
