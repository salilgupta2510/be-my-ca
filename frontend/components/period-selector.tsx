"use client";
import { useState, useEffect } from "react";
import { CalendarDays, Download, ChevronDown, CheckCircle2, Clock, Loader2 } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { formatPeriod, currentPeriod } from "@/lib/period";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

function token() {
  return typeof window !== "undefined" ? localStorage.getItem("bemyca_token") ?? "" : "";
}

interface FiledPeriod {
  period: string;
  gstr1_status: string;
  gstr3b_status: string;
}

function generateMonths(): string[] {
  const months: string[] = [];
  const now = new Date();
  for (let i = 0; i < 24; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    months.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`);
  }
  return months;
}

const MONTHS = generateMonths();

interface Props {
  period: string;
  onSelect: (period: string) => void;
}

export function PeriodSelector({ period, onSelect }: Props) {
  const [open, setOpen] = useState(false);
  const [filedPeriods, setFiledPeriods] = useState<FiledPeriod[]>([]);
  const [loading, setLoading] = useState(false);
  const [manualPeriod, setManualPeriod] = useState(period);

  async function fetchFiledPeriods() {
    setLoading(true);
    try {
      const res = await fetch(`${API}/gst/filed-periods`, {
        headers: { Authorization: `Bearer ${token()}` },
      });
      if (res.ok) {
        const data = await res.json();
        setFiledPeriods(data.periods);
      }
    } finally {
      setLoading(false);
    }
  }

  function handleOpen() {
    setOpen(true);
    setManualPeriod(period);
    fetchFiledPeriods();
  }

  function select(p: string) {
    onSelect(p);
    setOpen(false);
  }

  return (
    <>
      <button
        onClick={handleOpen}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-sm font-medium transition-colors border border-slate-700"
      >
        <CalendarDays className="w-4 h-4 text-blue-400" />
        {formatPeriod(period)}
        <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
      </button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="bg-slate-900 border-slate-800 text-white max-w-md">
          <DialogHeader>
            <DialogTitle className="text-white">Select Filing Period</DialogTitle>
          </DialogHeader>

          <Tabs defaultValue="gsp">
            <TabsList className="w-full bg-slate-800 border border-slate-700">
              <TabsTrigger value="gsp" className="flex-1 data-[state=active]:bg-blue-600 data-[state=active]:text-white text-slate-400">
                <Download className="w-3.5 h-3.5 mr-1.5" />
                From GSP Portal
              </TabsTrigger>
              <TabsTrigger value="manual" className="flex-1 data-[state=active]:bg-blue-600 data-[state=active]:text-white text-slate-400">
                <CalendarDays className="w-3.5 h-3.5 mr-1.5" />
                Select Manually
              </TabsTrigger>
            </TabsList>

            <TabsContent value="gsp" className="mt-4">
              <p className="text-slate-400 text-xs mb-3">
                Periods fetched from GSP portal with filing status.
                <span className="text-amber-400 ml-1">(Mock data)</span>
              </p>
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-5 h-5 animate-spin text-blue-400" />
                </div>
              ) : (
                <div className="space-y-1.5 max-h-72 overflow-y-auto pr-1">
                  {filedPeriods.map((fp) => {
                    const bothFiled = fp.gstr1_status === "filed" && fp.gstr3b_status === "filed";
                    const active = fp.period === period;
                    return (
                      <button
                        key={fp.period}
                        onClick={() => select(fp.period)}
                        className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm transition-colors border ${
                          active
                            ? "bg-blue-600/20 border-blue-600 text-white"
                            : "bg-slate-800 border-slate-700 text-slate-300 hover:border-slate-600 hover:text-white"
                        }`}
                      >
                        <span className="font-medium">{formatPeriod(fp.period)}</span>
                        <div className="flex items-center gap-1.5">
                          <Badge
                            className={`text-xs px-1.5 py-0 ${
                              fp.gstr1_status === "filed"
                                ? "bg-green-900/50 text-green-400 border-green-800"
                                : "bg-slate-700 text-slate-400 border-slate-600"
                            }`}
                            variant="outline"
                          >
                            GSTR-1
                          </Badge>
                          <Badge
                            className={`text-xs px-1.5 py-0 ${
                              fp.gstr3b_status === "filed"
                                ? "bg-green-900/50 text-green-400 border-green-800"
                                : "bg-slate-700 text-slate-400 border-slate-600"
                            }`}
                            variant="outline"
                          >
                            GSTR-3B
                          </Badge>
                          {active && <CheckCircle2 className="w-4 h-4 text-blue-400 ml-1" />}
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </TabsContent>

            <TabsContent value="manual" className="mt-4">
              <p className="text-slate-400 text-xs mb-4">
                Select any past or current period to view or file returns.
              </p>
              <Select value={manualPeriod} onValueChange={(v) => { if (v) setManualPeriod(v); }}>
                <SelectTrigger className="bg-slate-800 border-slate-700 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-slate-800 border-slate-700">
                  {MONTHS.map((m) => (
                    <SelectItem key={m} value={m} className="text-slate-200 focus:bg-slate-700 focus:text-white">
                      {formatPeriod(m)}
                      {m === currentPeriod() && (
                        <span className="ml-2 text-blue-400 text-xs">Current</span>
                      )}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                onClick={() => select(manualPeriod)}
                className="w-full mt-4 bg-blue-600 hover:bg-blue-700"
              >
                Apply Period
              </Button>
            </TabsContent>
          </Tabs>
        </DialogContent>
      </Dialog>
    </>
  );
}
