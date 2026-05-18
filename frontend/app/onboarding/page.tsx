"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const GSTIN_RE = /^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/;

function token() {
  return typeof window !== "undefined" ? localStorage.getItem("bemyca_token") ?? "" : "";
}

export default function OnboardingPage() {
  const router = useRouter();
  const [legalName, setLegalName] = useState("");
  const [gstin, setGstin] = useState("");
  const [frequency, setFrequency] = useState<"monthly" | "quarterly">("monthly");
  const [loading, setLoading] = useState(false);
  const [isUpdate, setIsUpdate] = useState(false);

  const pan = gstin.length === 15 ? gstin.slice(2, 12) : "";
  const stateCode = gstin.length === 15 ? gstin.slice(0, 2) : "";

  useEffect(() => {
    fetch(`${API}/business/me`, {
      headers: { Authorization: `Bearer ${token()}` },
    }).then(async (res) => {
      if (!res.ok) return;
      const biz = await res.json();
      setLegalName(biz.legal_name ?? "");
      setGstin(biz.gstin ?? "");
      setFrequency(biz.return_frequency ?? "monthly");
      setIsUpdate(true);
    }).catch(() => {});
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!legalName.trim()) { toast.error("Enter your business name"); return; }
    if (!GSTIN_RE.test(gstin)) { toast.error("Invalid GSTIN format (15 characters, e.g. 27AABCS1429B1ZB)"); return; }

    setLoading(true);
    try {
      const res = await fetch(`${API}/business`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token()}` },
        body: JSON.stringify({ legal_name: legalName.trim(), gstin, return_frequency: frequency }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? "Registration failed");
      }
      toast.success(isUpdate ? "Business details updated." : "Business registered! Welcome to BeMyCa.");
      router.push("/dashboard");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        <div className="flex flex-col items-center mb-8 gap-3">
          <Link href="/"><img src="/logo.svg" alt="BeMyCa" className="h-14 w-auto" /></Link>
          <p className="text-slate-400 text-sm">Upload your bills. We handle your GST. Forever.</p>
        </div>

        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="text-white text-lg">
              {isUpdate ? "Update your business" : "Set up your business"}
            </CardTitle>
            <CardDescription className="text-slate-400">
              {isUpdate ? "Change your details below and save." : "Takes 30 seconds. You'll never need to touch a GST portal again."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <Label className="text-slate-300">Business / Legal Name</Label>
                <Input
                  value={legalName}
                  onChange={(e) => setLegalName(e.target.value)}
                  placeholder="Acme Textiles Pvt Ltd"
                  className="bg-slate-800 border-slate-700 text-white placeholder:text-slate-500"
                />
              </div>

              <div className="space-y-2">
                <Label className="text-slate-300">GSTIN</Label>
                <Input
                  value={gstin}
                  onChange={(e) => setGstin(e.target.value.toUpperCase())}
                  placeholder="27AABCS1429B1ZB"
                  maxLength={15}
                  className="bg-slate-800 border-slate-700 text-white font-mono placeholder:text-slate-500"
                />
                {gstin.length > 0 && (
                  <div className="flex gap-4 text-xs text-slate-400 mt-1">
                    {stateCode && <span>State: <span className="text-white font-mono">{stateCode}</span></span>}
                    {pan && <span>PAN: <span className="text-white font-mono">{pan}</span></span>}
                    {!GSTIN_RE.test(gstin) && gstin.length > 3 && (
                      <span className="text-red-400">Invalid format</span>
                    )}
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <Label className="text-slate-300">Filing frequency</Label>
                <div className="grid grid-cols-2 gap-3">
                  {(["monthly", "quarterly"] as const).map((f) => (
                    <button
                      key={f}
                      type="button"
                      onClick={() => setFrequency(f)}
                      className={`p-3 rounded-lg border text-sm font-medium transition-all text-left ${
                        frequency === f
                          ? "border-blue-500 bg-blue-950/40 text-white"
                          : "border-slate-700 bg-slate-800 text-slate-400 hover:border-slate-600"
                      }`}
                    >
                      <span className="block font-semibold capitalize">{f}</span>
                      <span className="text-xs text-slate-500">
                        {f === "monthly" ? "GSTR-1 by 11th, GSTR-3B by 20th" : "QRMP scheme — quarterly filing"}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              <Button
                type="submit"
                disabled={loading}
                className="w-full bg-blue-600 hover:bg-blue-700 text-base py-5"
              >
                {loading ? (isUpdate ? "Saving…" : "Setting up…") : (isUpdate ? "Save changes →" : "Start filing →")}
              </Button>

              {isUpdate && (
                <button
                  type="button"
                  onClick={() => router.push("/dashboard")}
                  className="w-full text-sm text-slate-400 hover:text-white text-center"
                >
                  Cancel, go back to dashboard
                </button>
              )}
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
