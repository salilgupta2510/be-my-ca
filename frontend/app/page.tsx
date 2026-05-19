"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, CheckCircle2, Upload, FileText, ShieldCheck, Clock, Zap, BarChart3, Loader2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import api from "@/lib/api";
import PublicNav from "@/components/public-nav";

// GST terminology streams for the animated background
const GST_STREAMS = [
  ["18%", "GSTR-3B", "ITC", "CGST", "Sec 16", "GSTIN", "ARN"],
  ["28%", "₹ Credit", "B2B", "HSN 8471", "Export", "CESS"],
  ["5%", "GSTR-1", "SGST", "Input Tax", "B2C", "Nil Rated"],
  ["12%", "GSTR-2B", "IGST", "₹ 18,000", "Exempt", "RCM"],
  ["₹ 0", "QRMP", "Composition", "Late Fee", "27AABCS", "ISD"],
];

export default function LandingPage() {
  const [authed, setAuthed] = useState(false);
  const [waitlistEmail, setWaitlistEmail] = useState("");
  const [waitlistName, setWaitlistName] = useState("");
  const [waitlistLoading, setWaitlistLoading] = useState(false);
  const [waitlistDone, setWaitlistDone] = useState(false);

  async function handleWaitlist(e: React.FormEvent) {
    e.preventDefault();
    setWaitlistLoading(true);
    try {
      const { data } = await api.post("/waitlist", { email: waitlistEmail, name: waitlistName || undefined });
      setWaitlistDone(true);
      if (data.already_registered) toast.info("You're already on our list!");
    } catch {
      toast.error("Something went wrong. Please try again.");
    } finally {
      setWaitlistLoading(false);
    }
  }

  useEffect(() => {
    setAuthed(!!localStorage.getItem("bemyca_token"));
  }, []);

  return (
    <div className="min-h-screen bg-[#06080F] text-white">
      <style>{`
        @keyframes floatUp {
          0%   { transform: translateY(110vh); opacity: 0; }
          6%   { opacity: 1; }
          94%  { opacity: 0.55; }
          100% { transform: translateY(-15vh); opacity: 0; }
        }
        @keyframes orbPulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50%       { opacity: 0.55; transform: scale(1.1); }
        }
        @keyframes ledgerDrift {
          from { background-position: 0 0; }
          to   { background-position: 0 48px; }
        }
        @keyframes fadeSlideUp {
          from { opacity: 0; transform: translateY(16px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        .gst-stream   { animation: floatUp linear infinite; will-change: transform; }
        .orb-gold     { animation: orbPulse 7s ease-in-out infinite; }
        .orb-indigo   { animation: orbPulse 9s ease-in-out infinite 3.5s; }
        .ledger-lines { animation: ledgerDrift 3s linear infinite; }
        .card-hover   { transition: border-color 0.2s ease, box-shadow 0.2s ease; }
        .card-hover:hover {
          border-color: rgba(245,158,11,0.28);
          box-shadow: 0 0 0 1px rgba(245,158,11,0.08), 0 8px 32px rgba(0,0,0,0.5);
        }
      `}</style>

      <PublicNav activePage="home" />

      {/* ─── HERO ─────────────────────────────────────────────── */}
      <section className="relative overflow-hidden min-h-[92vh] flex items-center">

        {/* Ambient orb — gold, top-right */}
        <div className="orb-gold absolute pointer-events-none"
          style={{ top: "-180px", right: "-160px", width: "820px", height: "820px", borderRadius: "50%",
            background: "radial-gradient(circle, rgba(245,158,11,0.28) 0%, rgba(245,158,11,0.10) 40%, transparent 68%)" }} />

        {/* Ambient orb — indigo, bottom-left */}
        <div className="orb-indigo absolute pointer-events-none"
          style={{ bottom: "-240px", left: "-160px", width: "700px", height: "700px", borderRadius: "50%",
            background: "radial-gradient(circle, rgba(99,102,241,0.20) 0%, rgba(99,102,241,0.07) 45%, transparent 68%)" }} />

        {/* Ambient orb — gold, center-bottom (extra warmth) */}
        <div className="absolute pointer-events-none"
          style={{ bottom: "-60px", left: "50%", transform: "translateX(-50%)", width: "600px", height: "300px", borderRadius: "50%",
            background: "radial-gradient(ellipse, rgba(245,158,11,0.10) 0%, transparent 70%)" }} />

        {/* Animated ledger lines — suggest accounting ledger paper */}
        <div className="ledger-lines absolute inset-0 pointer-events-none"
          style={{ backgroundImage: "linear-gradient(rgba(245,158,11,0.11) 1px, transparent 1px)", backgroundSize: "100% 48px" }} />

        {/* Floating GST terminology columns */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none select-none" aria-hidden="true">
          {GST_STREAMS.map((col, ci) => (
            <div
              key={ci}
              className="gst-stream absolute flex flex-col gap-12 font-mono text-[11px] tracking-widest"
              style={{
                left: `${5 + ci * 19}%`,
                color: ci % 2 === 0 ? "rgba(245,158,11,0.46)" : "rgba(139,92,246,0.34)",
                animationDuration: `${22 + ci * 6}s`,
                animationDelay: `${-ci * 4.5}s`,
              }}
            >
              {[...col, ...col].map((t, ti) => <span key={ti}>{t}</span>)}
            </div>
          ))}
        </div>

        {/* Giant ₹ watermark */}
        <div
          className="absolute bottom-0 right-0 pointer-events-none select-none overflow-hidden"
          aria-hidden="true"
          style={{ fontSize: "30rem", fontWeight: 900, color: "rgba(245,158,11,0.082)", lineHeight: 0.82 }}
        >₹</div>

        {/* Edge vignette — keeps text readable */}
        <div className="absolute inset-0 pointer-events-none"
          style={{ background: "radial-gradient(ellipse 88% 65% at 50% 42%, transparent 28%, rgba(6,8,15,0.84) 100%)" }} />

        <div className="relative max-w-6xl mx-auto px-4 pt-24 pb-20 text-center w-full">

          {/* Pill badge */}
          <div className="inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-xs mb-6 border"
            style={{ background: "rgba(28,18,2,0.85)", borderColor: "rgba(180,120,10,0.4)", color: "#FCD34D" }}>
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse inline-block" />
            Built for Indian small businesses
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight mb-6">
            Upload your bills.{" "}
            <span className="bg-gradient-to-r from-amber-400 via-yellow-200 to-amber-400 bg-clip-text text-transparent">
              We handle your GST.
            </span>
            <br />Forever.
          </h1>

          <p className="text-slate-400 text-lg sm:text-xl max-w-2xl mx-auto mb-10 leading-relaxed">
            BeMyCa reads your invoices with AI, computes GSTR-1 and GSTR-3B automatically,
            reconciles your purchases against GSTR-2B, and keeps you compliant — without a CA.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-14">
            {authed ? (
              <Link href="/dashboard">
                <Button size="lg"
                  className="bg-gradient-to-br from-amber-400 to-amber-600 hover:from-amber-300 hover:to-amber-500 text-slate-900 border-0 font-semibold text-base px-8 py-6">
                  Go to Dashboard <ArrowRight className="w-5 h-5 ml-2" />
                </Button>
              </Link>
            ) : (
              <>
                <Link href="#waitlist">
                  <Button size="lg"
                    className="bg-gradient-to-br from-amber-400 to-amber-600 hover:from-amber-300 hover:to-amber-500 text-slate-900 border-0 font-semibold text-base px-8 py-6">
                    Request early access <ArrowRight className="w-5 h-5 ml-2" />
                  </Button>
                </Link>
                <Link href="#how-it-works">
                  <Button size="lg" variant="outline"
                    className="border-amber-900/50 text-slate-300 hover:text-white hover:border-amber-700/60 text-base px-8 py-6">
                    See how it works
                  </Button>
                </Link>
              </>
            )}
          </div>

          <div className="flex flex-wrap justify-center gap-8 sm:gap-14">
            {[
              { value: "₹0", label: "to start" },
              { value: "3 min", label: "avg filing time" },
              { value: "100%", label: "GST compliant" },
              { value: "0", label: "CA fees" },
            ].map((s) => (
              <div key={s.label}>
                <p className="text-3xl font-bold text-amber-400">{s.value}</p>
                <p className="text-slate-500 text-sm mt-0.5">{s.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── TRUST BAR ─────────────────────────────────────────── */}
      <div className="relative border-y" style={{ borderColor: "rgba(180,120,10,0.14)", background: "rgba(16,11,2,0.7)" }}>
        <div className="absolute inset-0 pointer-events-none"
          style={{ background: "linear-gradient(90deg, transparent 0%, rgba(245,158,11,0.04) 50%, transparent 100%)" }} />
        <div className="relative max-w-6xl mx-auto px-4 py-4 flex flex-wrap justify-center gap-6 text-slate-400 text-sm">
          {["GSTIN validated", "PDF invoices", "Auto GSTR-2B sync", "HSN summary (Table 12)", "Late fee calculator"].map((t) => (
            <span key={t} className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-amber-500" /> {t}
            </span>
          ))}
        </div>
      </div>

      {/* ─── HOW IT WORKS ──────────────────────────────────────── */}
      <section id="how-it-works" className="max-w-6xl mx-auto px-4 py-24">
        <div className="text-center mb-16">
          <p className="text-amber-500 text-xs font-semibold tracking-[0.2em] uppercase mb-3">Process</p>
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">Three steps to GST freedom</h2>
          <p className="text-slate-400 max-w-xl mx-auto">No accounting knowledge required.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {[
            { step: "01", icon: Upload, title: "Upload your invoices", color: "text-amber-400", iconBg: "rgba(245,158,11,0.10)",
              desc: "Photograph sales bills and purchase invoices. Our AI reads amounts, GSTIN, HSN codes, and invoice numbers automatically. Or type them in — your choice. Export any list to CSV." },
            { step: "02", icon: BarChart3, title: "We compute your returns", color: "text-violet-400", iconBg: "rgba(139,92,246,0.10)",
              desc: "BeMyCa calculates GSTR-1 (with HSN Table 12 summary), GSTR-3B, and GSTR-9 annual return. Reconciles purchases against GSTR-2B. Shows exactly what you owe and your ITC balance." },
            { step: "03", icon: ShieldCheck, title: "File with confidence", color: "text-emerald-400", iconBg: "rgba(16,185,129,0.10)",
              desc: "Review computed figures, download PDF invoices for your records, check the ITC Ledger for running credit balance, calculate any late fee before paying. Export to CA or file directly." },
          ].map((item) => (
            <div key={item.step}
              className="card-hover relative rounded-2xl p-8 border border-slate-800"
              style={{ background: "rgba(10,12,20,0.85)" }}>
              <div className="absolute top-5 right-6 text-6xl font-black select-none"
                style={{ color: "rgba(245,158,11,0.07)" }}>{item.step}</div>
              <div className="w-12 h-12 rounded-xl flex items-center justify-center mb-5"
                style={{ background: item.iconBg }}>
                <item.icon className={`w-6 h-6 ${item.color}`} />
              </div>
              <h3 className="text-white font-semibold text-lg mb-2">{item.title}</h3>
              <p className="text-slate-400 text-sm leading-relaxed">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ─── FEATURES ──────────────────────────────────────────── */}
      <section id="features" className="relative border-y border-slate-800/40">
        <div className="absolute inset-0 pointer-events-none"
          style={{ background: "linear-gradient(180deg, rgba(10,12,20,0.7) 0%, rgba(14,10,2,0.35) 50%, rgba(10,12,20,0.7) 100%)" }} />
        <div className="relative max-w-6xl mx-auto px-4 py-24">
          <div className="text-center mb-16">
            <p className="text-amber-500 text-xs font-semibold tracking-[0.2em] uppercase mb-3">Features</p>
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">Everything GST, handled</h2>
            <p className="text-slate-400 max-w-xl mx-auto">One dashboard. All returns. Zero confusion.</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              { icon: Upload, color: "text-amber-400", iconBg: "rgba(245,158,11,0.10)", title: "AI Invoice Reader",
                desc: "Photograph any bill. Claude AI extracts invoice number, GSTIN, taxable value, IGST, CGST, SGST — even from crumpled receipts." },
              { icon: FileText, color: "text-violet-400", iconBg: "rgba(139,92,246,0.10)", title: "GSTR-1 with HSN Summary",
                desc: "Auto-categorises sales into B2B, B2C, exports, credit notes. Includes Table 12 HSN/SAC summary — grouped, totalled, ready to verify." },
              { icon: BarChart3, color: "text-cyan-400", iconBg: "rgba(6,182,212,0.08)", title: "GSTR-2B Reconciliation",
                desc: "Compares your purchase register against supplier-filed GSTR-2B. Flags missing invoices and amount mismatches before you lose ITC credit." },
              { icon: Zap, color: "text-amber-300", iconBg: "rgba(245,158,11,0.08)", title: "GSTR-3B & ITC Ledger",
                desc: "Computes net tax payable after ITC. 12-month ledger tracks ITC available, claimed, net cash paid, and running credit balance across periods." },
              { icon: Clock, color: "text-orange-400", iconBg: "rgba(249,115,22,0.08)", title: "GSTR-9 Annual Return",
                desc: "One-click aggregation of all 12 monthly returns into GSTR-9. Month-wise breakdown with GSTR-1 and GSTR-3B filing status per period." },
              { icon: ShieldCheck, color: "text-emerald-400", iconBg: "rgba(16,185,129,0.08)", title: "Late Fee & Interest Calculator",
                desc: "Instantly compute late fee (₹50/day, capped ₹10,000) and 18% p.a. interest on delayed payments. Works for GSTR-1 and GSTR-3B." },
              { icon: Upload, color: "text-pink-400", iconBg: "rgba(236,72,153,0.08)", title: "PDF Invoice Generation",
                desc: "Download any sales invoice as a professional PDF — business name, GSTIN, HSN code, tax breakdowns, grand total. No extra software needed." },
              { icon: BarChart3, color: "text-blue-400", iconBg: "rgba(59,130,246,0.08)", title: "6-Month Trend Dashboard",
                desc: "Visual chart of tax liability, ITC, and turnover over the past 6 months. Spot patterns and plan cash flow before the filing deadline." },
              { icon: ShieldCheck, color: "text-slate-400", iconBg: "rgba(100,116,139,0.08)", title: "CSV Export & GSTIN Validation",
                desc: "Export any invoice list to CSV with one click. Real-time GSTIN format validation on every form — catch errors before they cause rejections." },
            ].map((f) => (
              <div key={f.title}
                className="card-hover rounded-xl p-6 border border-slate-800"
                style={{ background: "rgba(10,12,20,0.85)" }}>
                <div className="w-10 h-10 rounded-lg flex items-center justify-center mb-4"
                  style={{ background: f.iconBg }}>
                  <f.icon className={`w-5 h-5 ${f.color}`} />
                </div>
                <h3 className="text-white font-semibold mb-2">{f.title}</h3>
                <p className="text-slate-400 text-sm leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── TESTIMONIALS ──────────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-4 py-24">
        <div className="text-center mb-16">
          <p className="text-amber-500 text-xs font-semibold tracking-[0.2em] uppercase mb-3">Testimonials</p>
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">Trusted by small business owners</h2>
          <p className="text-slate-400">From Surat to Kochi, businesses file GST without a CA</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            { name: "Ramesh Agarwal", role: "Textile trader, Surat",
              quote: "Earlier I paid ₹3,000/month to a CA just to upload my bills. BeMyCa does it in minutes and costs nothing." },
            { name: "Priya Nair", role: "Bakery owner, Kochi",
              quote: "The photo upload is magic. I click a picture of the bill, it fills everything. I filed GSTR-3B myself for the first time." },
            { name: "Vikram Chawla", role: "Hardware supplier, Ludhiana",
              quote: "The GSTR-2B reconciliation caught 4 invoices my suppliers hadn't filed. Saved me ₹18,000 in ITC that I almost lost." },
          ].map((t) => (
            <div key={t.name}
              className="card-hover rounded-xl p-6 border border-slate-800"
              style={{ background: "rgba(10,12,20,0.85)" }}>
              <div className="flex gap-1 mb-4">
                {[...Array(5)].map((_, i) => (
                  <svg key={i} className="w-4 h-4 fill-amber-400" viewBox="0 0 20 20">
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                ))}
              </div>
              <p className="text-slate-300 text-sm leading-relaxed mb-4">"{t.quote}"</p>
              <p className="text-white font-medium text-sm">{t.name}</p>
              <p className="text-slate-500 text-xs">{t.role}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ─── CTA ───────────────────────────────────────────────── */}
      <section className="relative overflow-hidden border-y" style={{ borderColor: "rgba(180,120,10,0.14)" }}>
        <div className="absolute inset-0 pointer-events-none"
          style={{ background: "linear-gradient(135deg, rgba(20,12,1,0.98) 0%, rgba(6,8,15,0.98) 100%)" }} />
        <div className="absolute pointer-events-none"
          style={{ top: "-120px", left: "-80px", width: "420px", height: "420px", borderRadius: "50%",
            background: "radial-gradient(circle, rgba(245,158,11,0.08) 0%, transparent 70%)" }} />
        <div className="absolute pointer-events-none"
          style={{ bottom: "-100px", right: "-80px", width: "360px", height: "360px", borderRadius: "50%",
            background: "radial-gradient(circle, rgba(99,102,241,0.06) 0%, transparent 70%)" }} />
        <div className="relative max-w-3xl mx-auto px-4 py-20 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">Start filing in 3 minutes</h2>
          <p className="text-slate-400 mb-8 text-lg">No credit card. No CA. No portal passwords. Just upload your bills.</p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            {authed ? (
              <Link href="/dashboard">
                <Button size="lg"
                  className="bg-gradient-to-br from-amber-400 to-amber-600 hover:from-amber-300 hover:to-amber-500 text-slate-900 border-0 font-semibold text-base px-8 py-6">
                  Open Dashboard <ArrowRight className="w-5 h-5 ml-2" />
                </Button>
              </Link>
            ) : (
              <>
                <Link href="#waitlist">
                  <Button size="lg"
                    className="bg-gradient-to-br from-amber-400 to-amber-600 hover:from-amber-300 hover:to-amber-500 text-slate-900 border-0 font-semibold text-base px-8 py-6">
                    Request early access <ArrowRight className="w-5 h-5 ml-2" />
                  </Button>
                </Link>
                <Link href="/pricing">
                  <Button size="lg" variant="outline"
                    className="border-amber-900/40 text-slate-300 hover:text-white hover:border-amber-700/40 text-base px-8 py-6">
                    View pricing
                  </Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </section>

      {/* ─── WAITLIST ──────────────────────────────────────────── */}
      <section id="waitlist" className="max-w-2xl mx-auto px-4 py-24">
        <div className="relative rounded-2xl p-8 sm:p-12 text-center overflow-hidden border"
          style={{ borderColor: "rgba(180,120,10,0.22)", background: "linear-gradient(135deg, rgba(20,14,2,0.97) 0%, rgba(10,8,20,0.97) 100%)" }}>
          {/* Inner top glow */}
          <div className="absolute inset-0 pointer-events-none rounded-2xl"
            style={{ background: "radial-gradient(ellipse 80% 55% at 50% 0%, rgba(245,158,11,0.07) 0%, transparent 70%)" }} />

          <div className="relative">
            <div className="inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-sm mb-6 border"
              style={{ background: "rgba(28,18,2,0.85)", borderColor: "rgba(180,120,10,0.35)", color: "#FCD34D" }}>
              <Sparkles className="w-3.5 h-3.5" />
              Limited early access
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold text-white mb-3">Want early access?</h2>
            <p className="text-slate-400 mb-8 leading-relaxed">
              We're onboarding businesses one by one to ensure quality. Drop your email — we'll reach out personally when your spot is ready.
            </p>

            {waitlistDone ? (
              <div className="flex flex-col items-center gap-3 py-4">
                <div className="w-14 h-14 rounded-full flex items-center justify-center"
                  style={{ background: "rgba(245,158,11,0.12)" }}>
                  <CheckCircle2 className="w-7 h-7 text-amber-400" />
                </div>
                <p className="text-white font-semibold text-lg">You're on the list!</p>
                <p className="text-slate-400 text-sm">We'll email you when your spot opens up. Usually within a few days.</p>
              </div>
            ) : (
              <form onSubmit={handleWaitlist} className="flex flex-col gap-3">
                <Input type="text" placeholder="Your name (optional)" value={waitlistName}
                  onChange={(e) => setWaitlistName(e.target.value)}
                  className="bg-slate-800/50 border-slate-700 text-white placeholder:text-slate-500 h-12 text-center" />
                <Input type="email" placeholder="your@email.com" value={waitlistEmail}
                  onChange={(e) => setWaitlistEmail(e.target.value)} required
                  className="bg-slate-800/50 border-slate-700 text-white placeholder:text-slate-500 h-12 text-center" />
                <Button type="submit" size="lg" disabled={waitlistLoading}
                  className="bg-gradient-to-br from-amber-400 to-amber-600 hover:from-amber-300 hover:to-amber-500 text-slate-900 border-0 font-semibold h-12 text-base mt-1">
                  {waitlistLoading
                    ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Joining...</>
                    : <>Request early access <ArrowRight className="w-4 h-4 ml-2" /></>}
                </Button>
                <p className="text-slate-600 text-xs mt-1">No spam. No password required. Just an email when you're up.</p>
              </form>
            )}
          </div>
        </div>
      </section>

      {/* ─── FOOTER ────────────────────────────────────────────── */}
      <footer className="border-t border-slate-800/40" style={{ background: "rgba(5,7,13,0.98)" }}>
        <div className="max-w-6xl mx-auto px-4 py-12">
          <div className="flex flex-col md:flex-row justify-between gap-8">
            <div>
              <img src="/logo.svg" alt="BeMyCa" className="h-8 w-auto mb-3" />
              <p className="text-slate-500 text-sm max-w-xs">GST filing for Indian small businesses. Upload bills. We handle the rest.</p>
            </div>
            <div className="flex flex-wrap gap-12 text-sm">
              <div>
                <p className="text-white font-medium mb-3">Product</p>
                <div className="flex flex-col gap-2 text-slate-500">
                  <a href="#features" className="hover:text-amber-400 transition-colors">Features</a>
                  <Link href="/pricing" className="hover:text-amber-400 transition-colors">Pricing</Link>
                  <a href="#how-it-works" className="hover:text-amber-400 transition-colors">How it works</a>
                </div>
              </div>
              <div>
                <p className="text-white font-medium mb-3">Account</p>
                <div className="flex flex-col gap-2 text-slate-500">
                  <Link href="/login" className="hover:text-amber-400 transition-colors">Sign in</Link>
                  <Link href="/dashboard" className="hover:text-amber-400 transition-colors">Dashboard</Link>
                </div>
              </div>
            </div>
          </div>
          <div className="border-t border-slate-800/40 mt-8 pt-8 flex flex-col sm:flex-row justify-between gap-3 text-slate-600 text-xs">
            <p>© 2026 BeMyCa. All rights reserved.</p>
            <p>Made in India for Indian businesses</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
