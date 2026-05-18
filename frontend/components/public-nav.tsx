"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Menu, X } from "lucide-react";
import { Button } from "@/components/ui/button";

interface PublicNavProps {
  activePage?: "home" | "pricing";
}

export default function PublicNav({ activePage }: PublicNavProps) {
  const [authed, setAuthed] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    setAuthed(!!localStorage.getItem("bemyca_token"));
  }, []);

  const links = [
    { href: "/", label: "Home", anchor: false },
    { href: "/#how-it-works", label: "How it works", anchor: false },
    { href: "/#features", label: "Features", anchor: false },
    { href: "/pricing", label: "Pricing", anchor: false },
  ];

  return (
    <nav className="sticky top-0 z-50 border-b border-slate-800 bg-slate-950/90 backdrop-blur-sm">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
        <Link href="/">
          <img src="/logo.svg" alt="BeMyCa" className="h-9 w-auto" />
        </Link>

        <div className="hidden md:flex items-center gap-8 text-sm text-slate-400">
          {links.map((l) => (
            <Link
              key={l.label}
              href={l.href}
              className={`hover:text-white transition-colors ${
                (activePage === "home" && l.label === "Home") ||
                (activePage === "pricing" && l.label === "Pricing")
                  ? "text-white"
                  : ""
              }`}
            >
              {l.label}
            </Link>
          ))}
        </div>

        <div className="hidden md:flex items-center gap-3">
          {authed ? (
            <Link href="/dashboard">
              <Button className="bg-blue-600 hover:bg-blue-700 text-sm">
                Dashboard <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </Link>
          ) : (
            <Link href="/login">
              <Button className="bg-blue-600 hover:bg-blue-700 text-sm">Sign In</Button>
            </Link>
          )}
        </div>

        <button
          className="md:hidden text-slate-400 hover:text-white"
          onClick={() => setMenuOpen(!menuOpen)}
        >
          {menuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {menuOpen && (
        <div className="md:hidden border-t border-slate-800 bg-slate-950 px-4 py-4 flex flex-col gap-4 text-sm">
          {links.map((l) => (
            <Link
              key={l.label}
              href={l.href}
              className="text-slate-400 hover:text-white"
              onClick={() => setMenuOpen(false)}
            >
              {l.label}
            </Link>
          ))}
          <div className="pt-2 border-t border-slate-800">
            {authed ? (
              <Link href="/dashboard">
                <Button className="bg-blue-600 hover:bg-blue-700 w-full">Dashboard</Button>
              </Link>
            ) : (
              <Link href="/login">
                <Button className="bg-blue-600 hover:bg-blue-700 w-full">Sign In</Button>
              </Link>
            )}
          </div>
        </div>
      )}
    </nav>
  );
}
