"use client";
import { useState } from "react";
import Link from "next/link";
import { CheckCircle2, X, ArrowRight, Lock, Sparkles, Zap } from "lucide-react";
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
      { text: "Up to 20 invoices / month", included: true },
      { text: "Manual invoice entry", included: true },
      { text: "GSTR-1 computation", included: true },
      { text: "Deadline tracker", included: true },
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
      { text: "Deadline tracker", included: true },
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
      { text: "Deadline tracker", included: true },
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

const compareRows = [
  { label: "Businesses / GSTINs", values: ["1", "1", "5"] },
  { label: "Invoices per month", values: ["20", "Unlimited", "Unlimited"] },
  { label: "Manual invoice entry", values: [true, true, true] },
  { label: "AI photo OCR", values: [false, true, true] },
  { label: "GSTR-1 computation", values: [true, true, true] },
  { label: "GSTR-3B computation", values: [false, true, true] },
  { label: "GSTR-2B reconciliation", values: [false, true, true] },
  { label: "CSV bulk import", values: [false, false, true] },
  { label: "Deadline alerts", values: [true, true, true] },
  { label: "Support", values: ["—", "Email", "Phone + Email"] },
];

export default function PricingPage() {
  const [annual, setAnnual] = useState(false);
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  return (
    <div className="min-h-screen bg-[#06080F] text-white">
      <style>{`
        @keyframes orbPulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50%       { opacity: 0.55; transform: scale(1.08); }
        }
        @keyframes ledgerDrift {
          from { background-position: 0 0; }
          to   { background-position: 0 48px; }
        }
        .orb-gold-p  { animation: orbPulse 8s ease-in-out infinite; }
        .orb-ind-p   { animation: orbPulse 11s ease-in-out infinite 4s; }
        .ledger-p    { animation: ledgerDrift 4s linear infinite; }
        .plan-card   { transition: border-color 0.2s ease, box-shadow 0.2s ease; }
        .plan-card:hover {
          border-color: rgba(245,158,11,0.32);
          box-shadow: 0 0 0 1px rgba(245,158,11,0.08), 0 16px 48px rgba(0,0,0,0.5);
        }
        .faq-item { transition: border-color 0.15s ease; }
        .faq-item.open { border-color: rgba(245,158,11,0.28); }
      `}</style>

      <PublicNav activePage="pricing" />

      {/* Invite-only banner */}
      <div className="relative border-b" style={{ borderColor: "rgba(180,120,10,0.22)", background: "rgba(20,13,2,0.85)" }}>
        <div className="max-w-6xl mx-auto px-4 py-2.5 flex items-center justify-center gap-2 text-sm"
          style={{ color: "#FCD34D" }}>
          <Lock className="w-3.5 h-3.5 flex-shrink-0 text-amber-400" />
          Currently invite-only —{" "}
          <Link href="/login" className="underline hover:text-white transition-colors">sign in if you have access</Link>
          , or{" "}
          <a href="/#waitlist" className="underline hover:text-white transition-colors">join the waitlist</a>
        </div>
      </div>

      {/* Ambient background */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden" aria-hidden="true" style={{ zIndex: 0 }}>
        <div className="orb-gold-p absolute"
          style={{ top: "-200px", right: "-180px", width: "700px", height: "700px", borderRadius: "50%",
            background: "radial-gradient(circle, rgba(245,158,11,0.16) 0%, rgba(245,158,11,0.05) 45%, transparent 68%)" }} />
        <div className="orb-ind-p absolute"
          style={{ bottom: "-200px", left: "-160px", width: "580px", height: "580px", borderRadius: "50%",
            background: "radial-gradient(circle, rgba(99,102,241,0.12) 0%, rgba(99,102,241,0.04) 50%, transparent 70%)" }} />
        <div className="ledger-p absolute inset-0"
          style={{ backgroundImage: "linear-gradient(rgba(245,158,11,0.055) 1px, transparent 1px)", backgroundSize: "100% 48px" }} />
      </div>

      {/* ─── HEADER ─────────────────────────────────────────────── */}
      <div className="relative max-w-3xl mx-auto px-4 pt-20 pb-14 text-center" style={{ zIndex: 1 }}>
        <div className="inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-xs mb-5 border"
          style={{ background: "rgba(28,18,2,0.85)", borderColor: "rgba(180,120,10,0.4)", color: "#FCD34D" }}>
          <Sparkles className="w-3.5 h-3.5" />
          Simple, honest pricing
        </div>
        <h1 className="text-4xl sm:text-5xl font-bold mb-4 leading-tight">
          Pay for what you{" "}
          <span className="bg-gradient-to-r from-amber-400 via-yellow-200 to-amber-400 bg-clip-text text-transparent">
            actually use
          </span>
        </h1>
        <p className="text-slate-400 text-lg mb-10 max-w-xl mx-auto leading-relaxed">
          No hidden fees. No per-return charges. File as many times as you need.
        </p>

        {/* Billing toggle */}
        <div className="inline-flex items-center gap-1 rounded-full p-1 border"
          style={{ background: "rgba(10,12,20,0.9)", borderColor: "rgba(100,80,20,0.35)" }}>
          <button
            onClick={() => setAnnual(false)}
            className={`px-6 py-2.5 rounded-full text-sm font-medium transition-all ${
              !annual
                ? "bg-gradient-to-br from-amber-400 to-amber-600 text-slate-900 shadow-lg"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Monthly
          </button>
          <button
            onClick={() => setAnnual(true)}
            className={`px-6 py-2.5 rounded-full text-sm font-medium transition-all flex items-center gap-2 ${
              annual
                ? "bg-gradient-to-br from-amber-400 to-amber-600 text-slate-900 shadow-lg"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Annual
            <span className="rounded-full px-2 py-0.5 text-xs font-semibold"
              style={{ background: "rgba(16,185,129,0.18)", color: "#6EE7B7" }}>
              −20%
            </span>
          </button>
        </div>
      </div>

      {/* ─── PLAN CARDS ─────────────────────────────────────────── */}
      <div className="relative max-w-6xl mx-auto px-4 pb-28" style={{ zIndex: 1 }}>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
          {plans.map((plan) => {
            const isPro = plan.highlight;
            return (
              <div
                key={plan.name}
                className={`plan-card relative rounded-2xl border flex flex-col ${
                  isPro ? "md:-my-4" : ""
                }`}
                style={isPro ? {
                  borderColor: "rgba(245,158,11,0.45)",
                  background: "linear-gradient(160deg, rgba(28,17,2,0.98) 0%, rgba(10,8,22,0.98) 100%)",
                  boxShadow: "0 0 0 1px rgba(245,158,11,0.12), 0 32px 80px rgba(245,158,11,0.10), 0 8px 32px rgba(0,0,0,0.6)",
                } : {
                  borderColor: "rgba(100,100,120,0.22)",
                  background: "rgba(9,11,19,0.92)",
                }}
              >
                {/* Pro top glow */}
                {isPro && (
                  <div className="absolute inset-0 rounded-2xl pointer-events-none"
                    style={{ background: "radial-gradient(ellipse 75% 40% at 50% 0%, rgba(245,158,11,0.10) 0%, transparent 70%)" }} />
                )}

                {/* Badge */}
                {plan.badge && (
                  <div className="absolute -top-3.5 left-0 right-0 flex justify-center">
                    <span className="rounded-full px-4 py-1 text-xs font-semibold text-slate-900"
                      style={{ background: "linear-gradient(90deg, #F59E0B, #FCD34D)" }}>
                      {plan.badge}
                    </span>
                  </div>
                )}

                <div className={`relative flex flex-col flex-1 p-8 ${isPro ? "pt-10" : ""}`}>

                  {/* Plan name + tagline */}
                  <div className="mb-6">
                    <h2 className={`text-xl font-bold mb-1 ${isPro ? "text-amber-300" : "text-white"}`}>
                      {plan.name}
                    </h2>
                    <p className="text-slate-400 text-sm leading-snug">{plan.tagline}</p>
                  </div>

                  {/* Price */}
                  <div className="mb-8">
                    {plan.price.monthly === 0 ? (
                      <div>
                        <span className="text-5xl font-black text-white">Free</span>
                        <p className="text-slate-500 text-sm mt-1.5">forever · no card required</p>
                      </div>
                    ) : (
                      <div>
                        <div className="flex items-end gap-1">
                          <span className="text-slate-400 text-2xl font-medium mb-1">₹</span>
                          <span className={`text-5xl font-black ${isPro ? "text-amber-300" : "text-white"}`}>
                            {annual ? plan.price.annual : plan.price.monthly}
                          </span>
                          <span className="text-slate-400 text-sm mb-2">/mo</span>
                        </div>
                        <p className="text-slate-500 text-xs mt-1.5">
                          {annual
                            ? `₹${plan.price.annual * 12}/year · billed annually`
                            : "billed monthly"}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* CTA */}
                  <Link href="/#waitlist" className="mb-8 block">
                    <Button className={`w-full font-semibold py-5 ${
                      isPro
                        ? "bg-gradient-to-br from-amber-400 to-amber-600 hover:from-amber-300 hover:to-amber-500 text-slate-900 border-0"
                        : "border text-slate-300 hover:text-white"
                    }`}
                    style={!isPro ? {
                      background: "rgba(15,18,30,0.8)",
                      borderColor: "rgba(100,100,130,0.3)",
                    } : {}}>
                      {plan.cta} <ArrowRight className="w-4 h-4 ml-1.5" />
                    </Button>
                  </Link>

                  {/* Divider */}
                  <div className="border-t mb-6" style={{ borderColor: isPro ? "rgba(245,158,11,0.15)" : "rgba(255,255,255,0.06)" }} />

                  {/* Features */}
                  <ul className="space-y-3 flex-1">
                    {plan.features.map((f) => (
                      <li key={f.text} className="flex items-start gap-3 text-sm">
                        {f.included ? (
                          <CheckCircle2 className={`w-4 h-4 flex-shrink-0 mt-0.5 ${isPro ? "text-amber-400" : "text-emerald-500"}`} />
                        ) : (
                          <X className="w-4 h-4 text-slate-700 flex-shrink-0 mt-0.5" />
                        )}
                        <span className={f.included ? (isPro ? "text-slate-200" : "text-slate-300") : "text-slate-600"}>
                          {f.text}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            );
          })}
        </div>

        <p className="text-center text-slate-600 text-xs mt-10">
          All plans include: 30-day money-back guarantee · TLS encryption · Unlimited data retention
        </p>
      </div>

      {/* ─── COMPARE TABLE ──────────────────────────────────────── */}
      <section className="relative border-y" style={{ borderColor: "rgba(100,80,20,0.18)", background: "rgba(8,10,18,0.8)", zIndex: 1 }}>
        <div className="max-w-4xl mx-auto px-4 py-20">
          <div className="text-center mb-12">
            <p className="text-amber-500 text-xs font-semibold tracking-[0.2em] uppercase mb-3">Compare</p>
            <h2 className="text-2xl sm:text-3xl font-bold">Full feature comparison</h2>
          </div>
          <div className="overflow-x-auto rounded-xl border" style={{ borderColor: "rgba(100,80,20,0.18)" }}>
            <table className="w-full text-sm">
              <thead>
                <tr style={{ background: "rgba(10,12,20,0.9)" }}>
                  <th className="text-left py-4 px-6 text-slate-400 font-medium w-2/5 border-b"
                    style={{ borderColor: "rgba(100,80,20,0.18)" }}>Feature</th>
                  {plans.map((p) => (
                    <th key={p.name}
                      className="py-4 px-4 text-center font-semibold border-b"
                      style={{
                        borderColor: "rgba(100,80,20,0.18)",
                        background: p.highlight ? "rgba(245,158,11,0.06)" : "transparent",
                        color: p.highlight ? "#FCD34D" : "#E2E8F0",
                      }}>
                      {p.name}
                      {p.highlight && (
                        <span className="ml-2 text-[10px] font-semibold rounded-full px-2 py-0.5"
                          style={{ background: "rgba(245,158,11,0.15)", color: "#F59E0B" }}>
                          ★
                        </span>
                      )}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {compareRows.map((row, ri) => (
                  <tr key={row.label}
                    className="border-b"
                    style={{ borderColor: "rgba(255,255,255,0.04)" }}>
                    <td className="py-3.5 px-6 text-slate-400">{row.label}</td>
                    {row.values.map((v, i) => (
                      <td key={i}
                        className="py-3.5 px-4 text-center"
                        style={i === 1 ? { background: "rgba(245,158,11,0.04)" } : {}}>
                        {typeof v === "boolean" ? (
                          v ? (
                            <CheckCircle2 className={`w-4 h-4 mx-auto ${i === 1 ? "text-amber-400" : "text-emerald-500"}`} />
                          ) : (
                            <X className="w-4 h-4 text-slate-700 mx-auto" />
                          )
                        ) : (
                          <span className={i === 1 ? "text-amber-300 font-medium" : "text-slate-300"}>{v}</span>
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

      {/* ─── FAQ ────────────────────────────────────────────────── */}
      <section className="relative max-w-3xl mx-auto px-4 py-24" style={{ zIndex: 1 }}>
        <div className="text-center mb-12">
          <p className="text-amber-500 text-xs font-semibold tracking-[0.2em] uppercase mb-3">FAQ</p>
          <h2 className="text-2xl sm:text-3xl font-bold">Common questions</h2>
        </div>
        <div className="space-y-2">
          {faqs.map((faq, i) => {
            const isOpen = openFaq === i;
            return (
              <div key={i}
                className={`faq-item rounded-xl border overflow-hidden ${isOpen ? "open" : ""}`}
                style={{ background: "rgba(9,11,19,0.92)", borderColor: isOpen ? "rgba(245,158,11,0.28)" : "rgba(255,255,255,0.07)" }}>
                <button
                  className="w-full text-left px-6 py-4 flex justify-between items-center gap-4 hover:bg-white/[0.02] transition-colors"
                  onClick={() => setOpenFaq(isOpen ? null : i)}
                >
                  <span className="text-white font-medium text-sm">{faq.q}</span>
                  <span className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-sm font-bold transition-colors ${
                    isOpen ? "text-amber-400" : "text-slate-500"
                  }`}
                    style={{ background: isOpen ? "rgba(245,158,11,0.12)" : "rgba(255,255,255,0.05)" }}>
                    {isOpen ? "−" : "+"}
                  </span>
                </button>
                {isOpen && (
                  <div className="px-6 pb-5 text-slate-400 text-sm leading-relaxed border-t"
                    style={{ borderColor: "rgba(245,158,11,0.12)" }}>
                    <div className="pt-4">{faq.a}</div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* ─── BOTTOM CTA ─────────────────────────────────────────── */}
      <section className="relative overflow-hidden border-y" style={{ borderColor: "rgba(180,120,10,0.18)", zIndex: 1 }}>
        <div className="absolute inset-0 pointer-events-none"
          style={{ background: "linear-gradient(135deg, rgba(22,13,1,0.98) 0%, rgba(6,8,15,0.98) 100%)" }} />
        <div className="absolute pointer-events-none"
          style={{ top: "-100px", left: "-60px", width: "380px", height: "380px", borderRadius: "50%",
            background: "radial-gradient(circle, rgba(245,158,11,0.10) 0%, transparent 70%)" }} />
        <div className="absolute pointer-events-none"
          style={{ bottom: "-80px", right: "-60px", width: "320px", height: "320px", borderRadius: "50%",
            background: "radial-gradient(circle, rgba(99,102,241,0.08) 0%, transparent 70%)" }} />
        <div className="relative max-w-2xl mx-auto px-4 py-20 text-center">
          <div className="inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-xs mb-6 border"
            style={{ background: "rgba(28,18,2,0.85)", borderColor: "rgba(180,120,10,0.35)", color: "#FCD34D" }}>
            <Zap className="w-3.5 h-3.5" />
            Get started today
          </div>
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">Already have access?</h2>
          <p className="text-slate-400 mb-8 text-lg">Sign in to your account and start filing in minutes.</p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/login">
              <Button size="lg"
                className="bg-gradient-to-br from-amber-400 to-amber-600 hover:from-amber-300 hover:to-amber-500 text-slate-900 border-0 font-semibold text-base px-8 py-6">
                Sign In <ArrowRight className="w-5 h-5 ml-2" />
              </Button>
            </Link>
            <Link href="/#waitlist">
              <Button size="lg" variant="outline"
                className="border-amber-900/50 text-slate-300 hover:text-white hover:border-amber-700/60 text-base px-8 py-6">
                Join waitlist
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* ─── FOOTER ─────────────────────────────────────────────── */}
      <footer className="border-t" style={{ borderColor: "rgba(255,255,255,0.06)", background: "rgba(4,5,10,0.98)" }}>
        <div className="max-w-6xl mx-auto px-4 py-8 flex flex-col sm:flex-row justify-between gap-4 text-slate-600 text-xs">
          <p>© 2025 BeMyCa. All rights reserved.</p>
          <div className="flex gap-6">
            <Link href="/" className="hover:text-amber-400 transition-colors">Home</Link>
            <Link href="/pricing" className="hover:text-amber-400 transition-colors">Pricing</Link>
            <Link href="/login" className="hover:text-amber-400 transition-colors">Sign in</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
