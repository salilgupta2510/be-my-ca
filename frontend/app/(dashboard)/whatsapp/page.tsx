"use client";
import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { MessageCircle, CheckCircle, Loader2, Unlink } from "lucide-react";
import { toast } from "sonner";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

function token() {
  return typeof window !== "undefined" ? localStorage.getItem("bemyca_token") ?? "" : "";
}
function authH(json = false) {
  const h: Record<string, string> = { Authorization: `Bearer ${token()}` };
  if (json) h["Content-Type"] = "application/json";
  return h;
}

interface WAStatus {
  linked: boolean;
  number: string | null;
  alerts_enabled: boolean;
  alert_prefs: { deadlines: boolean; recon: boolean; itc_expiry: boolean };
}

type Step = "idle" | "otp_sent" | "verifying" | "unlinking";

export default function WhatsAppPage() {
  const [status, setStatus] = useState<WAStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [number, setNumber] = useState("");
  const [otp, setOtp] = useState("");
  const [step, setStep] = useState<Step>("idle");
  const [verifyingOtp, setVerifyingOtp] = useState(false);
  const [prefs, setPrefs] = useState({ deadlines: true, recon: true, itc_expiry: true });
  const [alertsEnabled, setAlertsEnabled] = useState(false);
  const [savingPrefs, setSavingPrefs] = useState(false);

  useEffect(() => {
    async function load() {
      const res = await fetch(`${API}/whatsapp/status`, { headers: authH() });
      if (res.ok) {
        const data: WAStatus = await res.json();
        setStatus(data);
        setAlertsEnabled(data.alerts_enabled);
        setPrefs(data.alert_prefs ?? { deadlines: true, recon: true, itc_expiry: true });
      }
      setLoading(false);
    }
    load();
  }, []);

  async function sendOtp() {
    if (!number.startsWith("+")) {
      toast.error("Enter number in E.164 format, e.g. +919876543210");
      return;
    }
    setStep("verifying");
    try {
      const res = await fetch(`${API}/whatsapp/link/send-otp`, {
        method: "POST",
        headers: authH(true),
        body: JSON.stringify({ number }),
      });
      if (!res.ok) throw new Error((await res.json()).detail ?? "Failed");
      setStep("otp_sent");
      toast.success("OTP sent to WhatsApp");
    } catch (e: unknown) {
      setStep("idle");
      toast.error(e instanceof Error ? e.message : "Failed to send OTP");
    }
  }

  async function verifyOtp() {
    setVerifyingOtp(true);
    try {
      const res = await fetch(`${API}/whatsapp/link/verify-otp`, {
        method: "POST",
        headers: authH(true),
        body: JSON.stringify({ number, code: otp }),
      });
      if (!res.ok) throw new Error((await res.json()).detail ?? "Invalid OTP");
      const newStatus: WAStatus = {
        linked: true,
        number,
        alerts_enabled: false,
        alert_prefs: { deadlines: true, recon: true, itc_expiry: true },
      };
      setStatus(newStatus);
      setStep("idle");
      setOtp("");
      toast.success("WhatsApp linked!");
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Verification failed");
    } finally {
      setVerifyingOtp(false);
    }
  }

  async function unlink() {
    if (!confirm("Unlink WhatsApp? You will stop receiving alerts.")) return;
    setStep("unlinking");
    try {
      const res = await fetch(`${API}/whatsapp/unlink`, { method: "POST", headers: authH(true) });
      if (!res.ok) throw new Error("Unlink failed");
      setStatus(s => s ? { ...s, linked: false, number: null } : s);
      setNumber("");
      setStep("idle");
      toast.success("WhatsApp unlinked");
    } catch {
      setStep("idle");
      toast.error("Unlink failed");
    }
  }

  async function savePrefs() {
    setSavingPrefs(true);
    try {
      const res = await fetch(`${API}/whatsapp/preferences`, {
        method: "PUT",
        headers: authH(true),
        body: JSON.stringify({ alerts_enabled: alertsEnabled, prefs }),
      });
      if (!res.ok) throw new Error("Save failed");
      toast.success("Preferences saved");
    } catch {
      toast.error("Failed to save preferences");
    } finally {
      setSavingPrefs(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-6 max-w-lg">
        <Skeleton className="h-8 w-48 bg-slate-800" />
        <Skeleton className="h-40 w-full bg-slate-800 rounded-xl" />
        <Skeleton className="h-48 w-full bg-slate-800 rounded-xl" />
      </div>
    );
  }

  const linked = status?.linked ?? false;

  return (
    <div className="space-y-6 max-w-lg">
      <div>
        <h1 className="text-2xl font-bold text-white">WhatsApp</h1>
        <p className="text-slate-400 text-sm mt-0.5">
          Get filing alerts and query your GST status on WhatsApp.
        </p>
      </div>

      {/* Link / Unlink card */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader className="pb-3">
          <CardTitle className="text-white text-sm flex items-center gap-2">
            <MessageCircle className="w-4 h-4 text-green-400" />
            Link your WhatsApp number
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {linked ? (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-400" />
                <span className="text-white text-sm font-medium">{status?.number}</span>
                <Badge variant="outline" className="border-green-700 text-green-400 text-xs">Linked</Badge>
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={unlink}
                disabled={step === "unlinking"}
                className="text-red-400 hover:text-red-300 hover:bg-red-950/30"
              >
                {step === "unlinking"
                  ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  : <><Unlink className="w-3.5 h-3.5 mr-1" /> Unlink</>
                }
              </Button>
            </div>
          ) : step === "otp_sent" ? (
            <div className="space-y-3">
              <p className="text-slate-400 text-xs">
                Enter the 6-digit code sent to <span className="text-white">{number}</span> on WhatsApp.
              </p>
              <Input
                value={otp}
                onChange={e => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
                placeholder="123456"
                maxLength={6}
                className="bg-slate-800 border-slate-700 text-white text-center text-xl tracking-widest"
              />
              <div className="flex gap-2">
                <Button onClick={verifyOtp} disabled={otp.length !== 6 || verifyingOtp} className="flex-1 bg-green-600 hover:bg-green-700">
                  {verifyingOtp ? <Loader2 className="w-4 h-4 animate-spin" /> : "Verify"}
                </Button>
                <Button variant="ghost" onClick={() => { setStep("idle"); setOtp(""); }}
                  className="text-slate-400 hover:text-white">
                  Back
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-slate-400 text-xs">
                Enter your WhatsApp number in international format. We'll send a verification code.
              </p>
              <Input
                value={number}
                onChange={e => setNumber(e.target.value)}
                placeholder="+919876543210"
                className="bg-slate-800 border-slate-700 text-white"
              />
              <Button
                onClick={sendOtp}
                disabled={step === "verifying" || number.length < 10}
                className="w-full bg-green-600 hover:bg-green-700"
              >
                {step === "verifying"
                  ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Sending…</>
                  : "Send OTP"
                }
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Alert preferences (only shown when linked) */}
      {linked && (
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-white text-sm">Alert Preferences</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white text-sm font-medium">Enable WhatsApp alerts</p>
                <p className="text-slate-400 text-xs">Master toggle for all alerts</p>
              </div>
              <Switch
                checked={alertsEnabled}
                onCheckedChange={setAlertsEnabled}
              />
            </div>

            {alertsEnabled && (
              <div className="border-t border-slate-800 pt-4 space-y-3">
                {[
                  { key: "deadlines" as const, label: "Filing deadlines", desc: "Remind me 3 days before GSTR-1 / GSTR-3B due" },
                  { key: "recon" as const, label: "Reconciliation issues", desc: "Alert when mismatches detected in GSTR-2B" },
                  { key: "itc_expiry" as const, label: "ITC expiry warnings", desc: "Warn before unclaimed ITC expires" },
                ].map(({ key, label, desc }) => (
                  <div key={key} className="flex items-center justify-between">
                    <div>
                      <p className="text-slate-200 text-sm">{label}</p>
                      <p className="text-slate-500 text-xs">{desc}</p>
                    </div>
                    <Switch
                      checked={prefs[key]}
                      onCheckedChange={v => setPrefs(p => ({ ...p, [key]: v }))}
                    />
                  </div>
                ))}
              </div>
            )}

            <Button
              onClick={savePrefs}
              disabled={savingPrefs}
              className="w-full bg-blue-600 hover:bg-blue-700"
            >
              {savingPrefs ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Saving…</> : "Save Preferences"}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* What you can do */}
      {!linked && (
        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-4">
            <p className="text-slate-300 text-sm font-medium mb-3">What you can do after linking:</p>
            <ul className="space-y-2 text-slate-400 text-sm">
              <li>• Filing deadline reminders (GSTR-1 & GSTR-3B)</li>
              <li>• Reconciliation mismatch alerts</li>
              <li>• Query filing status — just message "status"</li>
              <li>• Upload invoices via PDF/photo for auto-import</li>
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
