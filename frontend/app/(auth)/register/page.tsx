"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import api from "@/lib/api";
import Link from "next/link";

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({ email: "", password: "", full_name: "", phone: "", role: "layman" });
  const [loading, setLoading] = useState(false);

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await api.post("/api/v1/auth/register", form);
      localStorage.setItem("bemyca_token", data.access_token);
      localStorage.setItem("bemyca_user", JSON.stringify({ id: data.user_id, role: data.role }));
      router.push("/onboarding");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="flex justify-center mb-8">
          <Link href="/"><img src="/logo.svg" alt="BeMyCa" className="h-14 w-auto" /></Link>
        </div>
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="text-white">Create account</CardTitle>
            <CardDescription className="text-slate-400">Free for 30 days. No credit card.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleRegister} className="space-y-4">
              {[
                { id: "full_name", label: "Full Name", type: "text", placeholder: "Rahul Sharma" },
                { id: "email", label: "Email", type: "email", placeholder: "rahul@example.com" },
                { id: "phone", label: "Phone (optional)", type: "tel", placeholder: "+91 98765 43210" },
                { id: "password", label: "Password", type: "password", placeholder: "" },
              ].map(({ id, label, type, placeholder }) => (
                <div key={id} className="space-y-2">
                  <Label htmlFor={id} className="text-slate-300">{label}</Label>
                  <Input
                    id={id}
                    type={type}
                    value={(form as any)[id]}
                    onChange={(e) => setForm({ ...form, [id]: e.target.value })}
                    required={id !== "phone"}
                    placeholder={placeholder}
                    className="bg-slate-800 border-slate-700 text-white placeholder:text-slate-500"
                  />
                </div>
              ))}
              <div className="space-y-2">
                <Label className="text-slate-300">I am a</Label>
                <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v ?? "layman" })}>
                  <SelectTrigger className="w-full bg-slate-800 border-slate-700 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-800 border-slate-700 text-white [&_*]:text-white [&_[data-highlighted]]:bg-slate-700">
                    <SelectItem value="layman" className="text-white focus:bg-slate-700 focus:text-white cursor-pointer">Individual / Business Owner</SelectItem>
                    <SelectItem value="ca" className="text-white focus:bg-slate-700 focus:text-white cursor-pointer">Chartered Accountant (CA)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Button type="submit" className="w-full bg-blue-600 hover:bg-blue-700" disabled={loading}>
                {loading ? "Creating account..." : "Get started free"}
              </Button>
            </form>
            <p className="text-center text-slate-400 text-sm mt-4">
              Already have an account?{" "}
              <Link href="/login" className="text-blue-400 hover:underline">Sign in</Link>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
