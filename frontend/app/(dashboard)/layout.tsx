"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LayoutDashboard, FileText, ArrowUpCircle, ArrowDownCircle, GitMerge, LogOut, Menu, ChevronDown, BookOpen, FlaskConical, Calculator, Wallet, BarChart3 } from "lucide-react";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  {
    label: "Invoices", icon: FileText, prefix: "/invoices", children: [
      { href: "/invoices/outward", label: "Sales", icon: ArrowUpCircle },
      { href: "/invoices/inward", label: "Purchases", icon: ArrowDownCircle },
    ],
  },
  { href: "/reconciliation/gst", label: "GSTR-2B Recon", icon: GitMerge },
  {
    label: "Returns", icon: BarChart3, prefix: "/returns", children: [
      { href: "/returns/gstr1", label: "GSTR-1", icon: FileText },
      { href: "/returns/gstr3b", label: "GSTR-3B", icon: FileText },
      { href: "/returns/gstr9", label: "GSTR-9 Annual", icon: FileText },
    ],
  },
  { href: "/ledger/itc", label: "ITC Ledger", icon: Wallet },
  {
    label: "Tools", icon: Calculator, prefix: "/tools", children: [
      { href: "/tools/late-fee", label: "Late Fee & Interest", icon: Calculator },
    ],
  },
  { href: "/guide", label: "User Guide", icon: BookOpen },
  { href: "/seed", label: "Sample Data", icon: FlaskConical },
];

type NavChild = { href: string; label: string; icon: React.ComponentType<{ className?: string }> };
type NavItem =
  | { href: string; label: string; icon: React.ComponentType<{ className?: string }>; children?: never; prefix?: never }
  | { href?: never; label: string; icon: React.ComponentType<{ className?: string }>; prefix: string; children: NavChild[] };

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [openGroups, setOpenGroups] = useState<Set<string>>(() => {
    const initial = new Set<string>();
    for (const item of NAV) {
      if (item.children && item.prefix && pathname.startsWith(item.prefix)) {
        initial.add(item.label);
      }
    }
    return initial;
  });

  function toggleGroup(label: string) {
    setOpenGroups(prev => {
      const next = new Set(prev);
      next.has(label) ? next.delete(label) : next.add(label);
      return next;
    });
  }

  useEffect(() => {
    const token = localStorage.getItem("bemyca_token");
    if (!token) {
      router.replace("/login");
    }
  }, [router]);

  function handleLogout() {
    localStorage.removeItem("bemyca_token");
    localStorage.removeItem("bemyca_user");
    router.push("/login");
  }

  return (
    <div className="flex h-screen bg-slate-950 overflow-hidden">
      {/* Sidebar */}
      <aside className={`fixed inset-y-0 left-0 z-50 w-64 bg-slate-900 border-r border-slate-800 transform transition-transform lg:relative lg:translate-x-0 ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="flex flex-col h-full">
          <div className="p-4 border-b border-slate-800 flex items-center">
            <Link href="/">
              <img src="/logo.svg" alt="BeMyCa" className="h-10 w-auto" />
            </Link>
          </div>
          <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
            {(NAV as NavItem[]).map((item) => {
              if (item.children) {
                const groupActive = item.prefix ? pathname.startsWith(item.prefix) : false;
                const isOpen = openGroups.has(item.label);
                return (
                  <div key={item.label}>
                    <button
                      onClick={() => toggleGroup(item.label)}
                      className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors w-full ${
                        groupActive ? "text-white" : "text-slate-400 hover:text-white hover:bg-slate-800"
                      }`}
                    >
                      <item.icon className="w-4 h-4" />
                      <span className="flex-1 text-left">{item.label}</span>
                      <ChevronDown className={`w-3.5 h-3.5 transition-transform ${isOpen ? "rotate-180" : ""}`} />
                    </button>
                    {isOpen && (
                      <div className="ml-7 mt-1 space-y-1">
                        {item.children.map(child => {
                          const active = pathname === child.href || pathname.startsWith(child.href + "/");
                          return (
                            <Link
                              key={child.href}
                              href={child.href}
                              onClick={() => setSidebarOpen(false)}
                              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                                active ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white hover:bg-slate-800"
                              }`}
                            >
                              <child.icon className="w-3.5 h-3.5" />
                              {child.label}
                            </Link>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              }
              const active = pathname === item.href || pathname.startsWith(item.href + "/");
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setSidebarOpen(false)}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    active ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white hover:bg-slate-800"
                  }`}
                >
                  <item.icon className="w-4 h-4" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <div className="p-4 border-t border-slate-800">
            <button
              onClick={handleLogout}
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-slate-400 hover:text-red-400 hover:bg-red-950/30 w-full transition-colors"
            >
              <LogOut className="w-4 h-4" />
              Sign out
            </button>
          </div>
        </div>
      </aside>

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 bg-black/60 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="bg-slate-900 border-b border-slate-800 px-6 py-4 flex items-center gap-4 lg:hidden">
          <Button variant="ghost" size="icon" onClick={() => setSidebarOpen(true)} className="text-slate-400">
            <Menu className="w-5 h-5" />
          </Button>
          <h1 className="text-white font-semibold">BeMyCa</h1>
        </header>
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
