"use client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Printer, CheckCircle2, FileText, ArrowUpCircle, ArrowDownCircle,
  GitMerge, ReceiptText, AlertTriangle, Clock
} from "lucide-react";

const steps = [
  {
    num: 1,
    title: "Set up your business profile",
    icon: FileText,
    color: "text-blue-400",
    bg: "bg-blue-950/40",
    desc: "Before filing anything, make sure your business details are correct.",
    actions: [
      "Your GSTIN, legal name, and return frequency are pre-configured by your CA.",
      "If any detail looks wrong, contact support — do not guess.",
    ],
  },
  {
    num: 2,
    title: "Add your sales invoices (GSTR-1)",
    icon: ArrowUpCircle,
    color: "text-green-400",
    bg: "bg-green-950/40",
    desc: "Every invoice you raised to a customer this month must be entered here.",
    actions: [
      'Go to Invoices → Sales → click "Add Invoice".',
      "Fill in: Customer name, GSTIN (if B2B), invoice number, date, taxable value, and tax amounts.",
      "For B2B invoices (to registered businesses), customer GSTIN is mandatory.",
      "For B2C invoices (to individuals / unregistered), GSTIN can be left blank.",
      "Repeat for every sales invoice in the period.",
    ],
    tip: "Import via CSV coming soon. For now, add invoices one by one or ask your CA to bulk-import.",
  },
  {
    num: 3,
    title: "Add your purchase invoices (GSTR-2B)",
    icon: ArrowDownCircle,
    color: "text-purple-400",
    bg: "bg-purple-950/40",
    desc: "Every purchase invoice from a supplier must be entered to claim Input Tax Credit (ITC).",
    actions: [
      'Go to Invoices → Purchases → click "Add Invoice".',
      "Fill in: Supplier name, GSTIN (mandatory for ITC), invoice number, date, taxable value, and tax amounts.",
      "ITC can only be claimed if your supplier has filed their GSTR-1 (shown in GSTR-2B).",
    ],
    tip: "Run GSTR-2B reconciliation after adding purchases to verify which invoices are confirmed by the government portal.",
  },
  {
    num: 4,
    title: "Run GSTR-2B Reconciliation",
    icon: GitMerge,
    color: "text-yellow-400",
    bg: "bg-yellow-950/40",
    desc: "This compares your purchase entries against what your suppliers reported on the GST portal.",
    actions: [
      'Go to Reconciliation → GSTR-2B Reconciliation.',
      'Click "Run Reconciliation".',
      "Review the results by status:",
    ],
    statuses: [
      { label: "Matched", color: "bg-green-900 text-green-300", desc: "Safe to claim ITC." },
      { label: "Not in supplier filing", color: "bg-red-900 text-red-300", desc: "Supplier hasn't filed yet. Chase them." },
      { label: "Amount mismatch", color: "bg-yellow-900 text-yellow-300", desc: "Your amount differs from supplier's filing. Verify and correct." },
      { label: "Not in your books", color: "bg-orange-900 text-orange-300", desc: "Supplier filed an invoice you haven't entered. Add it." },
      { label: "Pending IMS", color: "bg-blue-900 text-blue-300", desc: "Use Accept / Reject buttons to act on IMS-flagged invoices." },
    ],
    tip: "Only claim ITC on 'Matched' invoices. Claiming ITC on unmatched invoices can lead to notices.",
  },
  {
    num: 5,
    title: "Compute and review GSTR-1",
    icon: ReceiptText,
    color: "text-blue-400",
    bg: "bg-blue-950/40",
    desc: "GSTR-1 is your outward sales return — it must be filed by the 11th of the next month.",
    actions: [
      'Go to Returns → GSTR-1.',
      'Click "Compute GSTR-1".',
      "Review the breakdown by invoice type (B2B, B2C Large, B2C Small, Exports).",
      "If numbers look correct, click File Return. (Currently mock-filed in demo mode.)",
    ],
    warning: "GSTR-1 deadline: 11th of every month for monthly filers.",
  },
  {
    num: 6,
    title: "Compute, review, and pay GSTR-3B",
    icon: CheckCircle2,
    color: "text-green-400",
    bg: "bg-green-950/40",
    desc: "GSTR-3B is the summary return where you pay the net GST liability. Due by the 20th.",
    actions: [
      'Go to Returns → GSTR-3B.',
      'Click "Compute GSTR-3B".',
      "Review the three sections: Outward Tax Liability, ITC Available, Net Tax Payable.",
      "Net Tax = Tax Collected on Sales − ITC from Purchases.",
      "Pay the net amount on the GST portal before filing.",
      'Click "File Return" once payment is done.',
    ],
    warning: "Always run GSTR-2B reconciliation before computing GSTR-3B. Without it, ITC will be ₹0.",
  },
];

const faq = [
  {
    q: "What is GSTIN?",
    a: "A 15-character unique identifier for every GST-registered business in India. Format: 2-digit state code + 10-char PAN + 1 entity type + Z + 1 check digit. Example: 27AABCU9603R1ZX",
  },
  {
    q: "What is ITC (Input Tax Credit)?",
    a: "The GST you paid on purchases, which you can deduct from the GST you owe on sales. If you collected ₹10,000 GST on sales and paid ₹3,000 GST on purchases, you only pay ₹7,000 to the government.",
  },
  {
    q: "What is GSTR-2B?",
    a: "A government-generated statement showing all purchase invoices your suppliers have filed on your behalf. It's released on the 14th of every month and is the basis for ITC claims.",
  },
  {
    q: "B2B vs B2C — what's the difference?",
    a: "B2B (Business-to-Business): sale to a GST-registered buyer — GSTIN required. B2C (Business-to-Consumer): sale to an individual or unregistered buyer — no GSTIN needed. B2C Large = inter-state invoice > ₹2.5 lakh, reported separately.",
  },
  {
    q: "What is IMS?",
    a: "Invoice Management System — a GST portal feature where suppliers can push invoices directly to your GSTR-2B. You can accept or reject them. Accepted invoices flow into your ITC automatically.",
  },
  {
    q: "What if I miss the filing deadline?",
    a: "Late fee: ₹50/day (₹25 CGST + ₹25 SGST) for returns with tax liability. ₹20/day for nil returns. Plus interest at 18% p.a. on unpaid tax.",
  },
];

export default function GuidePage() {
  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">How to use BeMyCa</h1>
          <p className="text-slate-400 text-sm mt-0.5">Step-by-step guide to GST filing</p>
        </div>
        <Button variant="outline" className="border-slate-700 text-slate-300 hover:text-white print:hidden"
          onClick={() => window.print()}>
          <Printer className="w-4 h-4 mr-2" /> Save as PDF
        </Button>
      </div>

      {/* Monthly workflow overview */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader className="pb-3">
          <CardTitle className="text-white text-base flex items-center gap-2">
            <Clock className="w-4 h-4 text-blue-400" /> Monthly GST workflow
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 flex-wrap text-sm">
            {[
              { label: "Add Invoices", color: "bg-blue-900 text-blue-300" },
              { label: "→", color: "" },
              { label: "Run 2B Reconciliation", color: "bg-purple-900 text-purple-300" },
              { label: "→", color: "" },
              { label: "File GSTR-1 by 11th", color: "bg-green-900 text-green-300" },
              { label: "→", color: "" },
              { label: "File GSTR-3B by 20th", color: "bg-yellow-900 text-yellow-300" },
            ].map((item, i) =>
              item.color ? (
                <Badge key={i} className={`${item.color} text-xs`}>{item.label}</Badge>
              ) : (
                <span key={i} className="text-slate-500">{item.label}</span>
              )
            )}
          </div>
        </CardContent>
      </Card>

      {/* Steps */}
      {steps.map(step => {
        const Icon = step.icon;
        return (
          <div key={step.num} className="space-y-3">
            <div className="flex items-center gap-3">
              <div className={`w-9 h-9 ${step.bg} rounded-lg flex items-center justify-center flex-shrink-0`}>
                <Icon className={`w-4 h-4 ${step.color}`} />
              </div>
              <div>
                <h2 className="text-white font-semibold text-base">
                  <span className="text-slate-500 mr-2">Step {step.num}.</span>{step.title}
                </h2>
                <p className="text-slate-400 text-sm">{step.desc}</p>
              </div>
            </div>

            <div className="ml-12 space-y-3">
              <ul className="space-y-2">
                {step.actions.map((action, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                    <span className="text-slate-600 mt-0.5 flex-shrink-0">•</span>
                    {action}
                  </li>
                ))}
              </ul>

              {step.statuses && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {step.statuses.map(s => (
                    <div key={s.label} className="flex items-start gap-2">
                      <Badge className={`${s.color} text-xs flex-shrink-0 mt-0.5`}>{s.label}</Badge>
                      <span className="text-slate-400 text-xs">{s.desc}</span>
                    </div>
                  ))}
                </div>
              )}

              {step.tip && (
                <div className="flex items-start gap-2 bg-blue-950/30 border border-blue-900/50 rounded-lg p-3">
                  <CheckCircle2 className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
                  <p className="text-blue-300 text-xs">{step.tip}</p>
                </div>
              )}

              {step.warning && (
                <div className="flex items-start gap-2 bg-amber-950/30 border border-amber-800/50 rounded-lg p-3">
                  <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                  <p className="text-amber-300 text-xs">{step.warning}</p>
                </div>
              )}
            </div>
          </div>
        );
      })}

      {/* FAQ */}
      <div className="space-y-4">
        <h2 className="text-white font-semibold text-lg">Frequently asked questions</h2>
        <div className="space-y-3">
          {faq.map(item => (
            <Card key={item.q} className="bg-slate-900 border-slate-800">
              <CardContent className="p-4">
                <p className="text-white text-sm font-medium mb-1">{item.q}</p>
                <p className="text-slate-400 text-sm">{item.a}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      <div className="text-center text-slate-600 text-xs pb-6">
        BeMyCa · GST Filing Assistant · bemyca.cloud · 2025
      </div>
    </div>
  );
}
