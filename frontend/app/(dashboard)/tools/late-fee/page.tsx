"use client";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, Calculator } from "lucide-react";

function fmt(n: number) { return "₹" + n.toLocaleString("en-IN", { minimumFractionDigits: 2 }); }

function dueDateFor(period: string, returnType: "gstr1" | "gstr3b"): Date {
  const [y, m] = period.split("-").map(Number);
  const nextMonth = m === 12 ? 1 : m + 1;
  const nextYear = m === 12 ? y + 1 : y;
  const day = returnType === "gstr1" ? 11 : 20;
  return new Date(nextYear, nextMonth - 1, day);
}

function calcLateFee(daysLate: number, isNilReturn: boolean, returnType: "gstr1" | "gstr3b") {
  if (daysLate <= 0) return { cgst: 0, sgst: 0, total: 0, capped: false };
  const dailyRate = isNilReturn ? 10 : 25; // per component
  const maxPerComponent = returnType === "gstr1" ? 5000 : 5000;
  const cgst = Math.min(dailyRate * daysLate, maxPerComponent);
  const sgst = Math.min(dailyRate * daysLate, maxPerComponent);
  return { cgst, sgst, total: cgst + sgst, capped: dailyRate * daysLate > maxPerComponent };
}

function calcInterest(taxAmount: number, daysLate: number) {
  if (daysLate <= 0 || taxAmount <= 0) return 0;
  return (taxAmount * 0.18 * daysLate) / 365;
}

export default function LateFeeCalculatorPage() {
  const [period, setPeriod] = useState("");
  const [filingDate, setFilingDate] = useState("");
  const [returnType, setReturnType] = useState<"gstr1" | "gstr3b">("gstr3b");
  const [isNil, setIsNil] = useState(false);
  const [taxAmount, setTaxAmount] = useState("");

  const dueDate = period ? dueDateFor(period, returnType) : null;
  const filing = filingDate ? new Date(filingDate) : null;
  const daysLate = dueDate && filing ? Math.max(0, Math.ceil((filing.getTime() - dueDate.getTime()) / 86400000)) : 0;

  const lateFee = calcLateFee(daysLate, isNil, returnType);
  const interest = calcInterest(Number(taxAmount) || 0, daysLate);
  const total = lateFee.total + interest;

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Calculator className="w-6 h-6 text-blue-400" /> Late Fee & Interest Calculator
        </h1>
        <p className="text-slate-400 text-sm mt-0.5">
          Calculate GSTR-1 / GSTR-3B late fees and 18% interest on delayed tax payment.
        </p>
      </div>

      <Card className="bg-slate-900 border-slate-800">
        <CardHeader><CardTitle className="text-white text-sm">Input Details</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label className="text-slate-300 text-xs">Return Type</Label>
              <select value={returnType} onChange={e => setReturnType(e.target.value as "gstr1" | "gstr3b")}
                className="w-full bg-slate-800 border border-slate-700 text-white rounded-md px-3 py-2 text-sm">
                <option value="gstr3b">GSTR-3B (due 20th)</option>
                <option value="gstr1">GSTR-1 (due 11th)</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-slate-300 text-xs">Period (YYYY-MM)</Label>
              <Input value={period} onChange={e => setPeriod(e.target.value)}
                placeholder="2025-01" className="bg-slate-800 border-slate-700 text-white font-mono" />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label className="text-slate-300 text-xs">Actual Filing Date</Label>
            <Input type="date" value={filingDate} onChange={e => setFilingDate(e.target.value)}
              className="bg-slate-800 border-slate-700 text-white" />
          </div>

          {dueDate && (
            <p className="text-slate-400 text-xs">
              Due date: <span className="text-white font-mono">{dueDate.toISOString().split("T")[0]}</span>
              {daysLate > 0
                ? <span className="text-red-400 ml-2">· {daysLate} days late</span>
                : filing ? <span className="text-green-400 ml-2">· On time</span> : null}
            </p>
          )}

          {returnType === "gstr3b" && (
            <div className="space-y-1.5">
              <Label className="text-slate-300 text-xs">Tax Payable (₹) — for interest calculation</Label>
              <Input type="number" value={taxAmount} onChange={e => setTaxAmount(e.target.value)}
                placeholder="0" className="bg-slate-800 border-slate-700 text-white" />
            </div>
          )}

          <div className="flex items-center gap-3">
            <input type="checkbox" id="nil" checked={isNil} onChange={e => setIsNil(e.target.checked)}
              className="w-4 h-4 accent-blue-500" />
            <Label htmlFor="nil" className="text-slate-300 text-xs cursor-pointer">Nil return (lower late fee)</Label>
          </div>
        </CardContent>
      </Card>

      {daysLate > 0 && (
        <div className="space-y-4">
          <Card className="bg-slate-900 border-slate-800">
            <CardHeader><CardTitle className="text-white text-sm">Late Fee Breakdown</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-3 gap-4">
                {[
                  { label: "CGST Late Fee", value: lateFee.cgst },
                  { label: "SGST Late Fee", value: lateFee.sgst },
                  { label: "Total Late Fee", value: lateFee.total },
                ].map(({ label, value }) => (
                  <div key={label}>
                    <p className="text-slate-400 text-xs">{label}</p>
                    <p className="text-white font-semibold text-sm mt-0.5">{fmt(value)}</p>
                  </div>
                ))}
              </div>
              {lateFee.capped && (
                <div className="flex items-center gap-2 text-amber-400 text-xs">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  Late fee capped at ₹5,000 per component (₹10,000 total max).
                </div>
              )}
              <p className="text-slate-500 text-xs">
                Rate: {isNil ? "₹20/day (nil return)" : "₹50/day"} · {daysLate} days
              </p>
            </CardContent>
          </Card>

          {returnType === "gstr3b" && taxAmount && Number(taxAmount) > 0 && (
            <Card className="bg-slate-900 border-slate-800">
              <CardHeader><CardTitle className="text-white text-sm">Interest on Delayed Payment</CardTitle></CardHeader>
              <CardContent className="space-y-2">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-slate-400 text-xs">Interest @ 18% p.a.</p>
                    <p className="text-white font-semibold text-sm mt-0.5">{fmt(interest)}</p>
                  </div>
                  <div>
                    <p className="text-slate-400 text-xs">Formula</p>
                    <p className="text-slate-300 text-xs mt-1 font-mono">
                      {fmt(Number(taxAmount))} × 18% × {daysLate} ÷ 365
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          <Card className="bg-red-950/30 border-red-800">
            <CardContent className="p-4 flex items-center justify-between">
              <div>
                <p className="text-red-300 text-sm font-medium">Total Amount Due</p>
                <p className="text-red-500 text-xs mt-0.5">Late fee + interest</p>
              </div>
              <div className="text-right">
                <p className="text-white text-2xl font-bold">{fmt(total)}</p>
                <div className="flex gap-1 mt-1 justify-end">
                  <Badge className="bg-red-900 text-red-300 text-xs">{fmt(lateFee.total)} fee</Badge>
                  {interest > 0 && <Badge className="bg-orange-900 text-orange-300 text-xs">{fmt(interest)} interest</Badge>}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {daysLate === 0 && filing && dueDate && (
        <Card className="bg-green-950/20 border-green-800/50">
          <CardContent className="p-4">
            <p className="text-green-300 font-medium text-sm">Filed on time — no late fee or interest.</p>
          </CardContent>
        </Card>
      )}

      <Card className="bg-slate-900 border-slate-800">
        <CardContent className="p-4 space-y-1">
          <p className="text-slate-400 text-xs font-medium">Reference</p>
          <p className="text-slate-500 text-xs">• GSTR-1 due: 11th of following month · GSTR-3B due: 20th</p>
          <p className="text-slate-500 text-xs">• Late fee: ₹50/day (₹25 CGST + ₹25 SGST) · nil return: ₹20/day</p>
          <p className="text-slate-500 text-xs">• Max late fee: ₹10,000 (₹5,000 per component) under recent amendments</p>
          <p className="text-slate-500 text-xs">• Interest: 18% p.a. on unpaid tax (Section 50 CGST Act)</p>
        </CardContent>
      </Card>
    </div>
  );
}
