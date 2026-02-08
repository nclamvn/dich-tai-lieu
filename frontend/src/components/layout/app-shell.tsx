"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  FileText,
  BookOpen,
  BarChart3,
  Settings,
  Upload,
  List,
  Menu,
  X,
} from "lucide-react";
import { useState } from "react";

const NAV_ITEMS = [
  { href: "/translate", label: "Translate", icon: Upload },
  { href: "/jobs", label: "Jobs", icon: List },
  { href: "/glossary", label: "Glossary", icon: BookOpen },
  { href: "/dashboard", label: "Dashboard", icon: BarChart3 },
  { href: "/profiles", label: "Profiles", icon: FileText },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-slate-900 text-white sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link
            href="/"
            className="flex items-center gap-2 font-bold text-lg"
          >
            <FileText className="w-5 h-5 text-blue-400" />
            <span>AI Publisher Pro</span>
          </Link>

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center gap-1">
            {NAV_ITEMS.map(({ href, label, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                className={cn(
                  "px-3 py-2 rounded-md text-sm font-medium transition-colors",
                  "hover:bg-slate-800",
                  pathname.startsWith(href)
                    ? "bg-slate-800 text-white"
                    : "text-slate-300",
                )}
              >
                <Icon className="w-4 h-4 inline-block mr-1.5 -mt-0.5" />
                {label}
              </Link>
            ))}
          </nav>

          {/* Mobile Menu Button */}
          <button
            className="md:hidden p-2"
            onClick={() => setMobileOpen(!mobileOpen)}
          >
            {mobileOpen ? (
              <X className="w-5 h-5" />
            ) : (
              <Menu className="w-5 h-5" />
            )}
          </button>
        </div>

        {/* Mobile Nav */}
        {mobileOpen && (
          <nav className="md:hidden border-t border-slate-800 pb-3 px-4">
            {NAV_ITEMS.map(({ href, label, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                onClick={() => setMobileOpen(false)}
                className={cn(
                  "flex items-center gap-2 px-3 py-2.5 rounded-md text-sm",
                  pathname.startsWith(href)
                    ? "bg-slate-800 text-white"
                    : "text-slate-300",
                )}
              >
                <Icon className="w-4 h-4" />
                {label}
              </Link>
            ))}
          </nav>
        )}
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-6">
        {children}
      </main>

      {/* Status Bar */}
      <footer className="bg-white border-t text-xs text-slate-500 px-4 py-2">
        <div className="max-w-7xl mx-auto flex justify-between">
          <span>AI Publisher Pro</span>
          <span>v2.0</span>
        </div>
      </footer>
    </div>
  );
}
