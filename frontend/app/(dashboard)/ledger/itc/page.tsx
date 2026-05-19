"use client";
import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { BookOpen } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

function token() { return typeof window !== "undefined" ? localStorage.getItem("bemyca_token") ?? "" : ""; }
function authH() { return { Authorization: `Bearer ${token()}` }; }
function fmt(n: number) { return "₹" + n.toLocaleString("en-IN", { minimumFractionDigits: 2 }); }

function last12Periods(): string[] {
  const now = new Date();
  return Array.from({ length: 12 }, (_, i) => {
    const d = new Date(now.getFullYear(), now.getMonth() - (11 - i), 1);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
  });
}

function periodLabel(p: string) {
  const [y, m] = p.split("-");
  return new Date(Number(y), Number(m) - 1, 1).toLocaleDateString("en-IN", { month: "short", year: "numeric" });
}

interface TrendPoint {
  period: string; taxable_value: number; tax_liability: number;
  itc_available: number; tax_paid: number; itc_claimed: number; invoice_count: number;
}

interface LedgerRow {
  period: string;
  itcAvailable: number;
  itcClaimed: number;
  taxLiability: number;
  taxPaid: number;
  netCash: number;
  balance: number;
}

export default function ITCLedgerPage() {
  const [rows, setRows] = useState<LedgerRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const periods = last12Periods();
      const res = await fetch(`${API}/returns/trends?periods=${periods.join(",")}`, { headers: authH() });
      if (!res.ok) { setLoading(false); return; }
      const data: TrendPoint[] = await res.json();

      let runningBalance = 0;
      const ledger: LedgerRow[] = data.map(d => {
        const netCash = Math.max(0, d.tax_liability - d.itc_claimed);
        runningBalance += d.itc_available - d.itc_claimed;
        return {
          period: d.period,
          itcAvailable: d.itc_available,
          itcClaimed: d.itc_claimed,
          taxLiability: d.tax_liability,
          taxPaid: d.tax_paid,
          netCash,
          balance: runningBalance,
        };
      });
      setRows(ledger);
      setLoading(false);
    }
    load();
  }, []);

  const totalAvailable = rows.reduce((s, r) => s + r.itcAvailable, 0);
  const totalClaimed = rows.reduce((s, r) => s + r.itcClaimed, 0);
  const totalCash = rows.reduce((s, r) => s + r.netCash, 0);

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <BookOpen className="w-6 h-6 text-blue-400" /> ITC Ledger
        </h1>
        <p className="text-slate-400 text-sm mt-0.5">
          Input Tax Credit — period-wise availability, utilization, and net cash paid.
        </p>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-12 w-full bg-slate-800 rounded" />)}
        </div>
      ) : rows.length === 0 ? (
        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-8 text-center text-slate-400">
            No data yet. Compute GSTR-3B for at least one period to populate the ledger.
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: "ITC Available (12m)", value: fmt(totalAvailable), color: "text-green-400" },
              { label: "ITC Utilized (12m)", value: fmt(totalClaimed), color: "text-blue-400" },
              { label: "Net Cash Paid (12m)", value: fmt(totalCash), color: "text-white" },
            ].map(s => (
              <Card key={s.label} className="bg-slate-900 border-slate-800">
                <CardContent className="p-4">
                  <p className={`text-xl font-bold ${s.color}`}>{s.value}</p>
                  <p className="text-slate-400 text-xs mt-0.5">{s.label}</p>
                </CardContent>
              </Card>
            ))}
          </div>

          <Card className="bg-slate-900 border-slate-800">
            <CardHeader className="pb-3">
              <CardTitle className="text-white text-sm">Period-wise Ledger</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-800">
                      {["Period", "ITC Available", "ITC Claimed", "Tax Liability", "Net Cash Paid", "Running Balance"].map(h => (
                        <th key={h} className={`text-slate-400 text-xs font-medium px-4 py-2 ${h === "Period" ? "text-left" : "text-right"}`}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map(row => (
                      <tr key={row.period} className="border-b border-slate-800/50 last:border-0 hover:bg-slate-800/30">
                        <td className="px-4 py-2.5 text-slate-300 font-mono text-xs">{periodLabel(row.period)}</td>
                        <td className="px-4 py-2.5 text-right text-green-400">{fmt(row.itcAvailable)}</td>
                        <td className="px-4 py-2.5 text-right text-blue-400">{fmt(row.itcClaimed)}</td>
                        <td className="px-4 py-2.5 text-right text-white">{fmt(row.taxLiability)}</td>
                        <td className="px-4 py-2.5 text-right text-white">{fmt(row.netCash)}</td>
                        <td className={`px-4 py-2.5 text-right font-semibold ${row.balance >= 0 ? "text-green-400" : "text-red-400"}`}>
                          {fmt(row.balance)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="border-t border-slate-700 bg-slate-800/30">
                      <td className="px-4 py-2.5 text-slate-300 text-xs font-medium">Total</td>
                      <td className="px-4 py-2.5 text-right text-green-400 font-semibold">{fmt(totalAvailable)}</td>
                      <td className="px-4 py-2.5 text-right text-blue-400 font-semibold">{fmt(totalClaimed)}</td>
                      <td className="px-4 py-2.5 text-right text-white font-semibold">{fmt(rows.reduce((s, r) => s + r.taxLiability, 0))}</td>
                      <td className="px-4 py-2.5 text-right text-white font-semibold">{fmt(totalCash)}</td>
                      <td className="px-4 py-2.5 text-right"></td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="p-4 space-y-1">
              <p className="text-slate-400 text-xs font-medium">Notes</p>
              <p className="text-slate-500 text-xs">• ITC Available = total GST on purchase invoices for period</p>
              <p className="text-slate-500 text-xs">• ITC Claimed = ITC set off against tax liability in GSTR-3B</p>
              <p className="text-slate-500 text-xs">• Net Cash Paid = Tax Liability − ITC Claimed (minimum 0)</p>
              <p className="text-slate-500 text-xs">• Running Balance = cumulative unclaimed ITC (credit carry-forward)</p>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
