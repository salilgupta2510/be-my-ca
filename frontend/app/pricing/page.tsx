"use client";
import { useState } from "react";
import Link from "next/link";
import { CheckCircle2, X, ArrowRight, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import PublicNav from "@/components/public-nav";

const plans = [
  {
    name: "Starter",
    price: { monthly: 0, annual: 0 },
    tagline: "For solopreneurs just getting started",
    cta: "Request access",
    highlight: false,
    features: [
      { text: "1 business / GSTIN", included: true },
      { text: "Up to 20 invoices per month", included: true },
      { text: "Manual invoice entry", included: true },
      { text: "GSTR-1 computation", included: true },
      { text: "Basic filing deadlines tracker", included: true },
      { text: "AI photo OCR upload", included: false },
      { text: "GSTR-3B computation", included: false },
      { text: "GSTR-2B reconciliation", included: false },
      { text: "CSV bulk import", included: false },
      { text: "Email support", included: false },
    ],
  },
  {
    name: "Pro",
    price: { monthly: 499, annual: 399 },
    tagline: "For active traders and service businesses",
    cta: "Request access",
    highlight: true,
    badge: "Most popular",
    features: [
      { text: "1 business / GSTIN", included: true },
      { text: "Unlimited invoices", included: true },
      { text: "Manual invoice entry", included: true },
      { text: "GSTR-1 computation", included: true },
      { text: "Filing deadlines tracker", included: true },
      { text: "AI photo OCR upload", included: true },
      { text: "GSTR-3B computation", included: true },
      { text: "GSTR-2B reconciliation", included: true },
      { text: "CSV bulk import", included: false },
      { text: "Priority email support", included: true },
    ],
  },
  {
    name: "Business",
    price: { monthly: 1499, annual: 1199 },
    tagline: "For multi-GSTIN businesses and growing teams",
    cta: "Request access",
    highlight: false,
    features: [
      { text: "Up to 5 businesses / GSTINs", included: true },
      { text: "Unlimited invoices", included: true },
      { text: "Manual invoice entry", included: true },
      { text: "GSTR-1 computation", included: true },
      { text: "Filing deadlines tracker", included: true },
      { text: "AI photo OCR upload", included: true },
      { text: "GSTR-3B computation", included: true },
      { text: "GSTR-2B reconciliation", included: true },
      { text: "CSV bulk import", included: true },
      { text: "Phone + priority email support", included: true },
    ],
  },
];

const faqs = [
  {
    q: "Do I need a CA to use BeMyCa?",
    a: "No. BeMyCa is built for business owners with no accounting background. You upload invoices, we compute returns. You can optionally share the output with your CA.",
  },
  {
    q: "Is my data safe?",
    a: "Yes. All data is encrypted in transit and at rest. We never share your invoice data with third parties. Your GSTIN and financial records are stored securely.",
  },
  {
    q: "What is GSTR-2B reconciliation?",
    a: "GSTR-2B is a statement of purchases filed by your suppliers. If their filing doesn't match your purchase register, you lose ITC (tax credit). BeMyCa flags mismatches before you file.",
  },
  {
    q: "Does BeMyCa file directly with GSTN?",
    a: "Currently, BeMyCa computes your returns and provides ready-to-file data. Direct GST portal filing via GSP integration is coming in Q3 2025.",
  },
  {
    q: "Can I switch plans later?",
    a: "Yes. Upgrade or downgrade anytime. If you upgrade mid-month, you'll be charged a pro-rated amount. Downgrade takes effect at the next billing cycle.",
  },
  {
    q: "What invoice formats does OCR support?",
    a: "JPG, PNG, and WebP photos work well. Any standard Indian GST invoice printed or handwritten. The AI handles crumpled, rotated, or low-light photos.",
  },
];

export default function PricingPage() {
  const [annual, setAnnual] = useState(false);
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <PublicNav activePage="pricing" />

      {/* Invite-only banner */}
      <div className="bg-blue-950/60 border-b border-blue-900">
        <div className="max-w-6xl mx-auto px-4 py-2.5 flex items-center justify-center gap-2 text-sm text-blue-300">
          <Lock className="w-3.5 h-3.5 flex-shrink-0" />
          Currently invite-only — <Link href="/login" className="underline hover:text-white">sign in if you have access</Link>, or <a href="/#waitlist" className="underline hover:text-white">join the waitlist</a>
        </div>
      </div>

      {/* Header */}
      <div className="max-w-3xl mx-auto px-4 pt-20 pb-12 text-center">
        <h1 className="text-4xl sm:text-5xl font-bold mb-4">Simple, honest pricing</h1>
        <p className="text-slate-400 text-lg mb-8">
          No hidden fees. No per-return charges. File as many times as you need.
        </p>

        <div className="inline-flex items-center gap-3 bg-slate-900 border border-slate-800 rounded-full p-1">
          <button
            onClick={() => setAnnual(false)}
            className={`px-5 py-2 rounded-full text-sm font-medium transition-all ${!annual ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"}`}
          >
            Monthly
          </button>
          <button
            onClick={() => setAnnual(true)}
            className={`px-5 py-2 rounded-full text-sm font-medium transition-all flex items-center gap-2 ${annual ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"}`}
          >
            Annual
            <Badge className="bg-green-900 text-green-300 border-0 text-xs px-2 py-0">Save 20%</Badge>
          </button>
        </div>
      </div>

      {/* Plans */}
      <div className="max-w-6xl mx-auto px-4 pb-24">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
          {plans.map((plan) => (
            <div
              key={plan.name}
              className={`rounded-2xl border p-8 relative ${
                plan.highlight
                  ? "border-blue-600 bg-gradient-to-b from-blue-950/60 to-slate-900 shadow-xl shadow-blue-950/30"
                  : "border-slate-800 bg-slate-900"
              }`}
            >
              {plan.badge && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <Badge className="bg-blue-600 text-white border-0 px-4 py-1 text-xs">
                    {plan.badge}
                  </Badge>
                </div>
              )}

              <div className="mb-6">
                <h2 className="text-xl font-bold text-white mb-1">{plan.name}</h2>
                <p className="text-slate-400 text-sm">{plan.tagline}</p>
              </div>

              <div className="mb-8">
                {plan.price.monthly === 0 ? (
                  <div>
                    <span className="text-4xl font-black text-white">Free</span>
                    <p className="text-slate-500 text-sm mt-1">forever</p>
                  </div>
                ) : (
                  <div>
                    <div className="flex items-end gap-1">
                      <span className="text-slate-400 text-xl font-medium">₹</span>
                      <span className="text-4xl font-black text-white">
                        {annual ? plan.price.annual : plan.price.monthly}
                      </span>
                      <span className="text-slate-400 text-sm mb-1">/mo</span>
                    </div>
                    {annual && (
                      <p className="text-slate-500 text-xs mt-1">
                        ₹{plan.price.annual * 12}/year · billed annually
                      </p>
                    )}
                    {!annual && (
                      <p className="text-slate-500 text-xs mt-1">billed monthly</p>
                    )}
                  </div>
                )}
              </div>

              <Link href="/#waitlist">
                <Button
                  className={`w-full mb-8 ${
                    plan.highlight
                      ? "bg-blue-600 hover:bg-blue-700"
                      : "bg-slate-800 hover:bg-slate-700 text-white"
                  }`}
                >
                  {plan.cta} <ArrowRight className="w-4 h-4 ml-1" />
                </Button>
              </Link>

              <ul className="space-y-3">
                {plan.features.map((f) => (
                  <li key={f.text} className="flex items-start gap-3 text-sm">
                    {f.included ? (
                      <CheckCircle2 className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5" />
                    ) : (
                      <X className="w-4 h-4 text-slate-700 flex-shrink-0 mt-0.5" />
                    )}
                    <span className={f.included ? "text-slate-300" : "text-slate-600"}>{f.text}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <p className="text-center text-slate-500 text-sm mt-8">
          All plans include: 30-day money-back guarantee · TLS encryption · Unlimited data retention
        </p>
      </div>

      {/* Compare table */}
      <section className="bg-slate-900/50 border-y border-slate-800">
        <div className="max-w-4xl mx-auto px-4 py-20">
          <h2 className="text-2xl font-bold text-center mb-12">Full feature comparison</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-800">
                  <th className="text-left py-3 pr-8 text-slate-400 font-medium w-1/2">Feature</th>
                  {plans.map((p) => (
                    <th key={p.name} className="py-3 px-4 text-center text-white font-semibold">{p.name}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  { label: "Businesses / GSTINs", values: ["1", "1", "5"] },
                  { label: "Invoices per month", values: ["20", "Unlimited", "Unlimited"] },
                  { label: "Manual entry", values: [true, true, true] },
                  { label: "AI photo OCR", values: [false, true, true] },
                  { label: "GSTR-1 computation", values: [true, true, true] },
                  { label: "GSTR-3B computation", values: [false, true, true] },
                  { label: "GSTR-2B reconciliation", values: [false, true, true] },
                  { label: "CSV bulk import", values: [false, false, true] },
                  { label: "Deadline alerts", values: [true, true, true] },
                  { label: "Support", values: ["—", "Email", "Phone + Email"] },
                ].map((row) => (
                  <tr key={row.label} className="border-b border-slate-800/50">
                    <td className="py-3 pr-8 text-slate-400">{row.label}</td>
                    {row.values.map((v, i) => (
                      <td key={i} className="py-3 px-4 text-center">
                        {typeof v === "boolean" ? (
                          v ? (
                            <CheckCircle2 className="w-4 h-4 text-green-400 mx-auto" />
                          ) : (
                            <X className="w-4 h-4 text-slate-700 mx-auto" />
                          )
                        ) : (
                          <span className="text-slate-300">{v}</span>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="max-w-3xl mx-auto px-4 py-24">
        <h2 className="text-3xl font-bold text-center mb-12">Frequently asked questions</h2>
        <div className="space-y-3">
          {faqs.map((faq, i) => (
            <div key={i} className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
              <button
                className="w-full text-left px-6 py-4 flex justify-between items-center gap-4 hover:bg-slate-800/50 transition-colors"
                onClick={() => setOpenFaq(openFaq === i ? null : i)}
              >
                <span className="text-white font-medium text-sm">{faq.q}</span>
                <span className="text-slate-500 flex-shrink-0 text-lg leading-none">
                  {openFaq === i ? "−" : "+"}
                </span>
              </button>
              {openFaq === i && (
                <div className="px-6 pb-4 text-slate-400 text-sm leading-relaxed border-t border-slate-800 pt-4">
                  {faq.a}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="bg-gradient-to-r from-blue-950 to-slate-900 border-t border-blue-900">
        <div className="max-w-3xl mx-auto px-4 py-20 text-center">
          <h2 className="text-3xl font-bold mb-4">Already have access?</h2>
          <p className="text-slate-400 mb-8">Sign in to your account and start filing.</p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/login">
              <Button size="lg" className="bg-blue-600 hover:bg-blue-700 text-base px-8 py-6">
                Sign In <ArrowRight className="w-5 h-5 ml-2" />
              </Button>
            </Link>
            <Link href="/#waitlist">
              <Button size="lg" variant="outline" className="border-blue-700 text-slate-300 hover:text-white text-base px-8 py-6">
                Join waitlist
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800">
        <div className="max-w-6xl mx-auto px-4 py-8 flex flex-col sm:flex-row justify-between gap-4 text-slate-600 text-xs">
          <p>© 2025 BeMyCa. All rights reserved.</p>
          <div className="flex gap-6">
            <Link href="/" className="hover:text-white transition-colors">Home</Link>
            <Link href="/pricing" className="hover:text-white transition-colors">Pricing</Link>
            <Link href="/login" className="hover:text-white transition-colors">Sign in</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
