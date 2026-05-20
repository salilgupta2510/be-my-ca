"use client";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Loader2, CheckCircle2, AlertTriangle, FlaskConical, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { cacheClear } from "@/lib/cache";

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

// Realistic Indian GST sample invoices
const SAMPLE_OUTWARD = [
  { customer_name: "Tata Consultancy Services Ltd", customer_gstin: "27AAACT2727Q1ZW", invoice_number: "INV-2025-001", invoice_date: "2025-01-03", invoice_type: "b2b", taxable_value: "150000", igst: "0", cgst: "13500", sgst: "13500", place_of_supply: "27" },
  { customer_name: "Infosys Limited", customer_gstin: "29AABCI1681H1ZT", invoice_number: "INV-2025-002", invoice_date: "2025-01-07", invoice_type: "b2b", taxable_value: "85000", igst: "15300", cgst: "0", sgst: "0", place_of_supply: "29" },
  { customer_name: "Wipro Technologies", customer_gstin: "29AAACW0259L1ZV", invoice_number: "INV-2025-003", invoice_date: "2025-01-10", invoice_type: "b2b", taxable_value: "220000", igst: "39600", cgst: "0", sgst: "0", place_of_supply: "29" },
  { customer_name: "Reliance Industries Ltd", customer_gstin: "27AAACR5055K1Z5", invoice_number: "INV-2025-004", invoice_date: "2025-01-12", invoice_type: "b2b", taxable_value: "75000", igst: "0", cgst: "6750", sgst: "6750", place_of_supply: "27" },
  { customer_name: "Mahindra & Mahindra Ltd", customer_gstin: "27AAACM3025G1ZN", invoice_number: "INV-2025-005", invoice_date: "2025-01-15", invoice_type: "b2b", taxable_value: "180000", igst: "0", cgst: "16200", sgst: "16200", place_of_supply: "27" },
  { customer_name: "HCL Technologies", customer_gstin: "06AAACH1099P1Z3", invoice_number: "INV-2025-006", invoice_date: "2025-01-18", invoice_type: "b2b", taxable_value: "95000", igst: "17100", cgst: "0", sgst: "0", place_of_supply: "06" },
  { customer_name: "Retail Customer - Cash Sale", customer_gstin: null, invoice_number: "INV-2025-007", invoice_date: "2025-01-20", invoice_type: "b2c_small", taxable_value: "12000", igst: "0", cgst: "1080", sgst: "1080", place_of_supply: "27" },
  { customer_name: "Export Client USA", customer_gstin: null, invoice_number: "INV-2025-008", invoice_date: "2025-01-22", invoice_type: "export", taxable_value: "300000", igst: "0", cgst: "0", sgst: "0", place_of_supply: "96" },
  { customer_name: "Larsen & Toubro Ltd", customer_gstin: "27AAACL3043H1ZE", invoice_number: "INV-2025-009", invoice_date: "2025-01-25", invoice_type: "b2b", taxable_value: "420000", igst: "0", cgst: "37800", sgst: "37800", place_of_supply: "27" },
  { customer_name: "B2C Large Customer - Kerala", customer_gstin: null, invoice_number: "INV-2025-010", invoice_date: "2025-01-28", invoice_type: "b2c_large", taxable_value: "280000", igst: "50400", cgst: "0", sgst: "0", place_of_supply: "32" },
];

const SAMPLE_INWARD = [
  { supplier_name: "Amazon Web Services India", supplier_gstin: "29AABCA9096N1Z0", invoice_number: "AWS-JAN-2025-001", invoice_date: "2025-01-05", taxable_value: "45000", igst: "8100", cgst: "0", sgst: "0" },
  { supplier_name: "Microsoft Corporation India", supplier_gstin: "27AAACM1107N1Z7", invoice_number: "MSFT-001-2025", invoice_date: "2025-01-06", taxable_value: "28000", igst: "0", cgst: "2520", sgst: "2520" },
  { supplier_name: "Zoho Corporation Pvt Ltd", supplier_gstin: "33AABCZ2801H1Z5", invoice_number: "ZOHO-2025-JAN-01", invoice_date: "2025-01-08", taxable_value: "12000", igst: "2160", cgst: "0", sgst: "0" },
  { supplier_name: "Razorpay Software Pvt Ltd", supplier_gstin: "29AAGCR1034F1Z0", invoice_number: "RZP-INV-20250110", invoice_date: "2025-01-10", taxable_value: "8500", igst: "1530", cgst: "0", sgst: "0" },
  { supplier_name: "Office Supplies Co - Mumbai", supplier_gstin: "27AABCO5432R1ZK", invoice_number: "OSC/2025/001", invoice_date: "2025-01-12", taxable_value: "15000", igst: "0", cgst: "1350", sgst: "1350" },
  { supplier_name: "Airtel Business Solutions", supplier_gstin: "27AAABA2996L1ZW", invoice_number: "AIRTEL-B-JAN25-001", invoice_date: "2025-01-15", taxable_value: "6000", igst: "0", cgst: "540", sgst: "540" },
  { supplier_name: "HDFC Bank Ltd - Charges", supplier_gstin: "27AADCH0110H1ZV", invoice_number: "HDFC-GST-JAN-2025", invoice_date: "2025-01-16", taxable_value: "3500", igst: "0", cgst: "315", sgst: "315" },
  { supplier_name: "Print & Pack Solutions", supplier_gstin: "27AABCP8876K1ZT", invoice_number: "PPS/JAN/2025/045", invoice_date: "2025-01-18", taxable_value: "22000", igst: "0", cgst: "1980", sgst: "1980" },
  { supplier_name: "Delhi NCR Vendor (Unmatched)", supplier_gstin: "07AABCD1234E1ZF", invoice_number: "DNCR-2025-078", invoice_date: "2025-01-20", taxable_value: "35000", igst: "6300", cgst: "0", sgst: "0" },
  { supplier_name: "Stationery & Office Depot", supplier_gstin: "27AABCS9987M1ZB", invoice_number: "SOD/2025/JAN/012", invoice_date: "2025-01-22", taxable_value: "9800", igst: "0", cgst: "882", sgst: "882" },
];

const GST_RATES = [5, 12, 18, 28];

function randAmount(min: number, max: number) {
  return Math.round((Math.random() * (max - min) + min) / 500) * 500;
}

function randSuffix() {
  return Math.floor(Math.random() * 90000 + 10000).toString();
}

function randomizeOutward(tpl: typeof SAMPLE_OUTWARD[0]) {
  const ranges: Record<string, [number, number]> = {
    b2b:       [30000,  500000],
    b2c_small: [5000,   50000],
    b2c_large: [100000, 400000],
    export:    [100000, 600000],
  };
  const [lo, hi] = ranges[tpl.invoice_type] ?? [10000, 200000];
  const taxable = randAmount(lo, hi);
  const isExport = tpl.invoice_type === "export";
  const rate = isExport ? 0 : GST_RATES[Math.floor(Math.random() * GST_RATES.length)];
  const isIGST = tpl.igst !== "0";
  const igst = isIGST && !isExport ? Math.round(taxable * rate / 100) : 0;
  const cgst = !isIGST && !isExport ? Math.round(taxable * rate / 200) : 0;
  return {
    ...tpl,
    taxable_value: taxable.toString(),
    igst: igst.toString(),
    cgst: cgst.toString(),
    sgst: cgst.toString(),
    invoice_number: tpl.invoice_number.replace(/\d+$/, randSuffix()),
  };
}

function randomizeInward(tpl: typeof SAMPLE_INWARD[0]) {
  const taxable = randAmount(3000, 120000);
  const rate = GST_RATES[Math.floor(Math.random() * GST_RATES.length)];
  const isIGST = tpl.igst !== "0";
  const igst = isIGST ? Math.round(taxable * rate / 100) : 0;
  const cgst = !isIGST ? Math.round(taxable * rate / 200) : 0;
  return {
    ...tpl,
    taxable_value: taxable.toString(),
    igst: igst.toString(),
    cgst: cgst.toString(),
    sgst: cgst.toString(),
    invoice_number: tpl.invoice_number.replace(/\d+$/, randSuffix()),
  };
}

interface Result { type: "outward" | "inward"; invoice_number: string; ok: boolean; error?: string; }

export default function SampleDataPage() {
  const [period] = useState(getPeriod);
  const [seeding, setSeeding] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [results, setResults] = useState<Result[]>([]);
  const [done, setDone] = useState(false);

  function periodDate(date: string) {
    return date.replace(/^\d{4}-\d{2}/, period);
  }

  function clearCaches() {
    [`dashboard:${period}`, `invoices:outward:${period}`, `invoices:inward:${period}`, `reconciliation:${period}`, `gstr1:${period}`, `gstr3b:${period}`, `gstr4:${period}`].forEach(cacheClear);
  }

  async function seed() {
    setSeeding(true);
    setResults([]);
    setDone(false);
    const newResults: Result[] = [];

    for (const inv of SAMPLE_OUTWARD) {
      const randomized = randomizeOutward(inv);
      const res = await fetch(`${API}/invoices/outward`, {
        method: "POST", headers: authH(true),
        body: JSON.stringify({ ...randomized, period, invoice_date: periodDate(inv.invoice_date) }),
      });
      newResults.push({ type: "outward", invoice_number: randomized.invoice_number, ok: res.ok, error: res.ok ? undefined : (await res.json()).detail });
      setResults([...newResults]);
    }

    for (const inv of SAMPLE_INWARD) {
      const randomized = randomizeInward(inv);
      const res = await fetch(`${API}/invoices/inward`, {
        method: "POST", headers: authH(true),
        body: JSON.stringify({ ...randomized, period, invoice_date: periodDate(inv.invoice_date) }),
      });
      newResults.push({ type: "inward", invoice_number: randomized.invoice_number, ok: res.ok, error: res.ok ? undefined : (await res.json()).detail });
      setResults([...newResults]);
    }

    clearCaches();
    setSeeding(false);
    setDone(true);
    const failed = newResults.filter(r => !r.ok).length;
    if (failed === 0) toast.success(`All ${newResults.length} sample invoices created!`);
    else toast.warning(`${newResults.length - failed} created, ${failed} skipped (likely already exist)`);
  }

  async function clearAll() {
    if (!confirm(`Delete ALL invoices and computed returns for period ${period}? This cannot be undone.`)) return;
    setClearing(true);
    try {
      const res = await fetch(`${API}/invoices/period/${period}`, { method: "DELETE", headers: authH() });
      if (!res.ok) throw new Error();
      clearCaches();
      setResults([]);
      setDone(false);
      toast.success(`Cleared all data for period ${period}`);
    } catch {
      toast.error("Clear failed");
    } finally {
      setClearing(false);
    }
  }

  const successCount = results.filter(r => r.ok).length;
  const failCount = results.filter(r => !r.ok).length;

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <FlaskConical className="w-6 h-6 text-purple-400" /> Sample Data
        </h1>
        <p className="text-slate-400 text-sm mt-0.5">
          Seed realistic Indian GST invoices for period {period} to test the tool end-to-end.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-4">
            <p className="text-2xl font-bold text-white">{SAMPLE_OUTWARD.length}</p>
            <p className="text-slate-400 text-sm mt-0.5">Sales invoices</p>
            <div className="flex flex-wrap gap-1 mt-2">
              {["B2B", "B2C Large", "B2C Small", "Export"].map(t => (
                <Badge key={t} variant="outline" className="text-xs border-slate-700 text-slate-400">{t}</Badge>
              ))}
            </div>
          </CardContent>
        </Card>
        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-4">
            <p className="text-2xl font-bold text-white">{SAMPLE_INWARD.length}</p>
            <p className="text-slate-400 text-sm mt-0.5">Purchase invoices</p>
            <p className="text-slate-500 text-xs mt-2">Mix of matched / unmatched for reconciliation testing</p>
          </CardContent>
        </Card>
      </div>

      <Card className="bg-amber-950/20 border-amber-800/50">
        <CardContent className="p-4 flex items-start gap-3">
          <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
          <p className="text-amber-300 text-sm">
            This creates real records in your account for period <strong>{period}</strong>. Use only for testing — delete before going live.
          </p>
        </CardContent>
      </Card>

      <div className="flex gap-3 flex-wrap">
        <Button onClick={seed} disabled={seeding || clearing} className="bg-blue-600 hover:bg-blue-700">
          {seeding ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Creating {results.length}/{SAMPLE_OUTWARD.length + SAMPLE_INWARD.length}…</> : "Seed sample invoices"}
        </Button>
        <Button onClick={clearAll} disabled={seeding || clearing} variant="outline"
          className="border-red-800 text-red-400 hover:bg-red-950 hover:text-red-300">
          {clearing ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Clearing…</> : <><Trash2 className="w-4 h-4 mr-2" /> Clear all invoices</>}
        </Button>
      </div>

      {results.length > 0 && (
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-white text-sm flex items-center gap-3">
              Results
              {done && (
                <span className="flex gap-2">
                  <Badge className="bg-green-900 text-green-300 text-xs">{successCount} created</Badge>
                  {failCount > 0 && <Badge className="bg-red-900 text-red-300 text-xs">{failCount} skipped</Badge>}
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-slate-800 max-h-80 overflow-y-auto">
              {results.map((r, i) => (
                <div key={i} className="flex items-center gap-3 px-4 py-2.5">
                  {r.ok
                    ? <CheckCircle2 className="w-4 h-4 text-green-400 flex-shrink-0" />
                    : <AlertTriangle className="w-4 h-4 text-yellow-400 flex-shrink-0" />}
                  <span className="text-slate-300 text-xs font-mono flex-1">{r.invoice_number}</span>
                  <Badge variant="outline" className={`text-xs ${r.type === "outward" ? "border-blue-800 text-blue-400" : "border-purple-800 text-purple-400"}`}>
                    {r.type === "outward" ? "Sale" : "Purchase"}
                  </Badge>
                  {!r.ok && <span className="text-yellow-500 text-xs">{r.error ?? "skipped"}</span>}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {done && successCount > 0 && (
        <Card className="bg-green-950/20 border-green-800/50">
          <CardContent className="p-4">
            <p className="text-green-300 font-medium text-sm mb-2">What to do next:</p>
            <ol className="space-y-1 text-green-400 text-sm list-decimal list-inside">
              <li>Go to <strong>Invoices → Sales</strong> to review sales invoices</li>
              <li>Go to <strong>Invoices → Purchases</strong> to review purchase invoices</li>
              <li>Go to <strong>Reconciliation</strong> and click "Run Reconciliation"</li>
              <li>Go to <strong>Returns → GSTR-1</strong> and click "Compute GSTR-1"</li>
              <li>Go to <strong>Returns → GSTR-3B</strong> and click "Compute GSTR-3B"</li>
              <li>Check the <strong>Dashboard</strong> for your full GST summary</li>
            </ol>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
