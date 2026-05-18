"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, CheckCircle2, Upload, FileText, ShieldCheck, Clock, Zap, BarChart3, Menu, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export default function LandingPage() {
  const [authed, setAuthed] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    setAuthed(!!localStorage.getItem("bemyca_token"));
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Nav */}
      <nav className="sticky top-0 z-50 border-b border-slate-800 bg-slate-950/90 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <img src="/logo.svg" alt="BeMyCa" className="h-9 w-auto" />

          <div className="hidden md:flex items-center gap-8 text-sm text-slate-400">
            <Link href="/" className="hover:text-white transition-colors">Home</Link>
            <a href="#how-it-works" className="hover:text-white transition-colors">How it works</a>
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <Link href="/pricing" className="hover:text-white transition-colors">Pricing</Link>
          </div>

          <div className="hidden md:flex items-center gap-3">
            {authed ? (
              <Link href="/dashboard">
                <Button className="bg-blue-600 hover:bg-blue-700 text-sm">Go to Dashboard <ArrowRight className="w-4 h-4 ml-1" /></Button>
              </Link>
            ) : (
              <>
                <Link href="/login">
                  <Button variant="ghost" className="text-slate-300 hover:text-white text-sm">Sign in</Button>
                </Link>
                <Link href="/register">
                  <Button className="bg-blue-600 hover:bg-blue-700 text-sm">Get Started Free</Button>
                </Link>
              </>
            )}
          </div>

          <button className="md:hidden text-slate-400 hover:text-white" onClick={() => setMenuOpen(!menuOpen)}>
            {menuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {menuOpen && (
          <div className="md:hidden border-t border-slate-800 bg-slate-950 px-4 py-4 flex flex-col gap-4 text-sm">
            <Link href="/" className="text-slate-400 hover:text-white" onClick={() => setMenuOpen(false)}>Home</Link>
            <a href="#how-it-works" className="text-slate-400 hover:text-white" onClick={() => setMenuOpen(false)}>How it works</a>
            <a href="#features" className="text-slate-400 hover:text-white" onClick={() => setMenuOpen(false)}>Features</a>
            <Link href="/pricing" className="text-slate-400 hover:text-white" onClick={() => setMenuOpen(false)}>Pricing</Link>
            <div className="flex flex-col gap-2 pt-2 border-t border-slate-800">
              {authed ? (
                <Link href="/dashboard"><Button className="bg-blue-600 hover:bg-blue-700 w-full">Go to Dashboard</Button></Link>
              ) : (
                <>
                  <Link href="/login"><Button variant="outline" className="border-slate-700 text-slate-300 w-full">Sign in</Button></Link>
                  <Link href="/register"><Button className="bg-blue-600 hover:bg-blue-700 w-full">Get Started Free</Button></Link>
                </>
              )}
            </div>
          </div>
        )}
      </nav>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-950/40 via-transparent to-transparent pointer-events-none" />
        <div className="absolute inset-0 opacity-5 pointer-events-none"
          style={{ backgroundImage: "linear-gradient(rgba(148,163,184,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(148,163,184,0.3) 1px, transparent 1px)", backgroundSize: "48px 48px" }} />

        <div className="relative max-w-6xl mx-auto px-4 pt-24 pb-20 text-center">
          <Badge className="bg-blue-950 text-blue-300 border border-blue-800 mb-6 text-xs px-3 py-1">
            Built for Indian small businesses
          </Badge>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight mb-6">
            Upload your bills.{" "}
            <span className="bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
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
                <Button size="lg" className="bg-blue-600 hover:bg-blue-700 text-base px-8 py-6">
                  Go to Dashboard <ArrowRight className="w-5 h-5 ml-2" />
                </Button>
              </Link>
            ) : (
              <>
                <Link href="/register">
                  <Button size="lg" className="bg-blue-600 hover:bg-blue-700 text-base px-8 py-6">
                    Start filing free <ArrowRight className="w-5 h-5 ml-2" />
                  </Button>
                </Link>
                <Link href="#how-it-works">
                  <Button size="lg" variant="outline" className="border-slate-700 text-slate-300 hover:text-white text-base px-8 py-6">
                    See how it works
                  </Button>
                </Link>
              </>
            )}
          </div>

          <div className="flex flex-wrap justify-center gap-8 text-center">
            {[
              { value: "₹0", label: "to start" },
              { value: "3 min", label: "avg filing time" },
              { value: "100%", label: "GST compliant" },
              { value: "0", label: "CA fees" },
            ].map((s) => (
              <div key={s.label}>
                <p className="text-3xl font-bold text-white">{s.value}</p>
                <p className="text-slate-500 text-sm mt-0.5">{s.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Trust bar */}
      <div className="border-y border-slate-800 bg-slate-900/40">
        <div className="max-w-6xl mx-auto px-4 py-4 flex flex-wrap justify-center gap-6 text-slate-500 text-sm">
          {["GSTIN validated", "Bank-grade encryption", "Auto GSTR-2B sync", "Deadline reminders"].map((t) => (
            <span key={t} className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-green-500" /> {t}
            </span>
          ))}
        </div>
      </div>

      {/* How it works */}
      <section id="how-it-works" className="max-w-6xl mx-auto px-4 py-24">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">How it works</h2>
          <p className="text-slate-400 max-w-xl mx-auto">Three steps. No accounting knowledge required.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {[
            {
              step: "01",
              icon: Upload,
              title: "Upload your invoices",
              desc: "Photograph your sales bills and purchase invoices. Our AI reads the amounts, GSTIN, and invoice numbers automatically.",
            },
            {
              step: "02",
              icon: BarChart3,
              title: "We compute your returns",
              desc: "BeMyCa calculates your GSTR-1 (sales) and GSTR-3B (summary), reconciles purchases against your supplier filings, and shows exactly what you owe.",
            },
            {
              step: "03",
              icon: ShieldCheck,
              title: "File with one click",
              desc: "Review the computed figures, check your ITC, and file — or hand it to your CA in one clean export. No portal login juggling.",
            },
          ].map((item) => (
            <div key={item.step} className="relative bg-slate-900 border border-slate-800 rounded-2xl p-8">
              <div className="text-5xl font-black text-slate-800 absolute top-6 right-8 select-none">{item.step}</div>
              <div className="w-12 h-12 bg-blue-950 rounded-xl flex items-center justify-center mb-5">
                <item.icon className="w-6 h-6 text-blue-400" />
              </div>
              <h3 className="text-white font-semibold text-lg mb-2">{item.title}</h3>
              <p className="text-slate-400 text-sm leading-relaxed">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section id="features" className="bg-slate-900/50 border-y border-slate-800">
        <div className="max-w-6xl mx-auto px-4 py-24">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">Everything GST, handled</h2>
            <p className="text-slate-400 max-w-xl mx-auto">One dashboard. All returns. Zero confusion.</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              {
                icon: Upload,
                color: "text-blue-400",
                bg: "bg-blue-950/50",
                title: "AI Invoice Reader",
                desc: "Photograph any bill. Claude AI extracts invoice number, GSTIN, taxable value, IGST, CGST, SGST — even from crumpled receipts.",
              },
              {
                icon: FileText,
                color: "text-purple-400",
                bg: "bg-purple-950/50",
                title: "GSTR-1 Computation",
                desc: "Automatically categorises your sales into B2B, B2C, exports, and credit notes. Section-wise breakdown ready to verify.",
              },
              {
                icon: BarChart3,
                color: "text-cyan-400",
                bg: "bg-cyan-950/50",
                title: "GSTR-2B Reconciliation",
                desc: "Compares your purchase register against supplier-filed GSTR-2B. Flags missing invoices before you lose ITC credit.",
              },
              {
                icon: Zap,
                color: "text-yellow-400",
                bg: "bg-yellow-950/50",
                title: "GSTR-3B & Net Tax",
                desc: "Subtracts eligible ITC from output tax liability. Shows exactly how much cash to transfer to the GST portal.",
              },
              {
                icon: Clock,
                color: "text-orange-400",
                bg: "bg-orange-950/50",
                title: "Deadline Tracker",
                desc: "Traffic-light alerts for GSTR-1 (11th) and GSTR-3B (20th). Never pay a late fee again.",
              },
              {
                icon: ShieldCheck,
                color: "text-green-400",
                bg: "bg-green-950/50",
                title: "Secure & Compliant",
                desc: "Your data stays encrypted. GSTIN validation on every invoice. Audit-ready records stored forever.",
              },
            ].map((f) => (
              <div key={f.title} className="bg-slate-900 border border-slate-800 rounded-xl p-6 hover:border-slate-700 transition-colors">
                <div className={`w-10 h-10 ${f.bg} rounded-lg flex items-center justify-center mb-4`}>
                  <f.icon className={`w-5 h-5 ${f.color}`} />
                </div>
                <h3 className="text-white font-semibold mb-2">{f.title}</h3>
                <p className="text-slate-400 text-sm leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="max-w-6xl mx-auto px-4 py-24">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">Trusted by small business owners</h2>
          <p className="text-slate-400">From Surat to Kochi, businesses file GST without a CA</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            {
              name: "Ramesh Agarwal",
              role: "Textile trader, Surat",
              quote: "Earlier I paid ₹3,000/month to a CA just to upload my bills. BeMyCa does it in minutes and costs nothing.",
            },
            {
              name: "Priya Nair",
              role: "Bakery owner, Kochi",
              quote: "The photo upload is magic. I click a picture of the bill, it fills everything. I filed GSTR-3B myself for the first time.",
            },
            {
              name: "Vikram Chawla",
              role: "Hardware supplier, Ludhiana",
              quote: "The GSTR-2B reconciliation caught 4 invoices my suppliers hadn't filed. Saved me ₹18,000 in ITC that I almost lost.",
            },
          ].map((t) => (
            <div key={t.name} className="bg-slate-900 border border-slate-800 rounded-xl p-6">
              <div className="flex gap-1 mb-4">
                {[...Array(5)].map((_, i) => (
                  <svg key={i} className="w-4 h-4 text-yellow-400 fill-yellow-400" viewBox="0 0 20 20">
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                ))}
              </div>
              <p className="text-slate-300 text-sm leading-relaxed mb-4">"{t.quote}"</p>
              <div>
                <p className="text-white font-medium text-sm">{t.name}</p>
                <p className="text-slate-500 text-xs">{t.role}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="bg-gradient-to-r from-blue-950 to-slate-900 border-y border-blue-900">
        <div className="max-w-3xl mx-auto px-4 py-20 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">Start filing in 3 minutes</h2>
          <p className="text-slate-400 mb-8 text-lg">No credit card. No CA. No portal passwords. Just upload your bills.</p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            {authed ? (
              <Link href="/dashboard">
                <Button size="lg" className="bg-blue-600 hover:bg-blue-700 text-base px-8 py-6">
                  Open Dashboard <ArrowRight className="w-5 h-5 ml-2" />
                </Button>
              </Link>
            ) : (
              <>
                <Link href="/register">
                  <Button size="lg" className="bg-blue-600 hover:bg-blue-700 text-base px-8 py-6">
                    Create free account <ArrowRight className="w-5 h-5 ml-2" />
                  </Button>
                </Link>
                <Link href="/pricing">
                  <Button size="lg" variant="outline" className="border-blue-700 text-slate-300 hover:text-white text-base px-8 py-6">
                    View pricing
                  </Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800 bg-slate-950">
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
                  <a href="#features" className="hover:text-white transition-colors">Features</a>
                  <Link href="/pricing" className="hover:text-white transition-colors">Pricing</Link>
                  <a href="#how-it-works" className="hover:text-white transition-colors">How it works</a>
                </div>
              </div>
              <div>
                <p className="text-white font-medium mb-3">Account</p>
                <div className="flex flex-col gap-2 text-slate-500">
                  <Link href="/register" className="hover:text-white transition-colors">Sign up free</Link>
                  <Link href="/login" className="hover:text-white transition-colors">Sign in</Link>
                  <Link href="/dashboard" className="hover:text-white transition-colors">Dashboard</Link>
                </div>
              </div>
            </div>
          </div>
          <div className="border-t border-slate-800 mt-8 pt-8 flex flex-col sm:flex-row justify-between gap-3 text-slate-600 text-xs">
            <p>© 2025 BeMyCa. All rights reserved.</p>
            <p>Made in India for Indian businesses</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
