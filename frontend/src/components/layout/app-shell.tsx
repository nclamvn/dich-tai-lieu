"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  BookOpen,
  BarChart3,
  Settings,
  Upload,
  List,
  Menu,
  X,
  ChevronRight,
  Layers,
} from "lucide-react";
import { useState } from "react";

const NAV_ITEMS = [
  { href: "/translate", label: "Translate", icon: Upload },
  { href: "/jobs", label: "Jobs", icon: List },
  { href: "/glossary", label: "Glossary", icon: BookOpen },
  { href: "/dashboard", label: "Dashboard", icon: BarChart3 },
  { href: "/profiles", label: "Profiles", icon: Layers },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen flex">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 md:hidden"
          style={{ background: "var(--bg-overlay)" }}
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed top-0 left-0 h-screen z-50 flex flex-col",
          "w-[240px] transition-transform duration-200 ease-in-out",
          "md:translate-x-0 md:sticky md:z-auto",
          sidebarOpen ? "translate-x-0" : "-translate-x-full",
        )}
        style={{
          background: "var(--bg-sidebar)",
          borderRight: "1px solid var(--border-default)",
        }}
      >
        {/* Logo */}
        <div
          className="px-3 flex items-center justify-between shrink-0"
          style={{ height: "var(--header-height)" }}
        >
          <Link
            href="/"
            className="flex items-center gap-2 px-2 py-1 no-underline"
            style={{ borderRadius: "var(--radius-sm)" }}
          >
            <div
              className="w-5 h-5 flex items-center justify-center"
              style={{
                borderRadius: "3px",
                background: "var(--fg-primary)",
              }}
            >
              <span className="text-white text-[10px] font-bold">A</span>
            </div>
            <span
              className="text-sm font-medium"
              style={{ color: "var(--fg-primary)" }}
            >
              AI Publisher Pro
            </span>
          </Link>
          <button
            className="md:hidden p-1"
            style={{ borderRadius: "var(--radius-sm)" }}
            onClick={() => setSidebarOpen(false)}
          >
            <X
              className="w-4 h-4"
              style={{ color: "var(--fg-icon)" }}
              strokeWidth={1.5}
            />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-2 py-2 space-y-0.5 overflow-y-auto">
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
            const isActive =
              pathname === href || pathname.startsWith(href + "/");
            return (
              <Link
                key={href}
                href={href}
                onClick={() => setSidebarOpen(false)}
                className={cn(
                  "flex items-center gap-2.5 px-2.5 py-[5px] text-sm no-underline",
                  "transition-colors duration-100",
                )}
                style={{
                  borderRadius: "var(--radius-sm)",
                  background: isActive ? "var(--bg-active)" : "transparent",
                  color: isActive
                    ? "var(--fg-primary)"
                    : "var(--fg-secondary)",
                  fontWeight: isActive ? 500 : 400,
                }}
                onMouseEnter={(e) => {
                  if (!isActive)
                    e.currentTarget.style.background = "var(--bg-hover)";
                }}
                onMouseLeave={(e) => {
                  if (!isActive)
                    e.currentTarget.style.background = "transparent";
                }}
              >
                <Icon
                  className="w-[18px] h-[18px] shrink-0"
                  style={{
                    color: isActive
                      ? "var(--fg-primary)"
                      : "var(--fg-icon)",
                  }}
                  strokeWidth={1.5}
                />
                {label}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div
          className="px-3 py-3 shrink-0"
          style={{ borderTop: "1px solid var(--border-default)" }}
        >
          <p
            className="text-[11px] px-2"
            style={{ color: "var(--fg-tertiary)" }}
          >
            VIBECODE KIT V4
          </p>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-h-screen min-w-0">
        {/* Mobile top bar */}
        <header
          className="md:hidden sticky top-0 z-30 px-4 flex items-center gap-3"
          style={{
            height: "var(--header-height)",
            borderBottom: "1px solid var(--border-default)",
            background: "var(--bg-primary)",
          }}
        >
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-1"
            style={{ borderRadius: "var(--radius-sm)" }}
          >
            <Menu
              className="w-[18px] h-[18px]"
              style={{ color: "var(--fg-icon)" }}
              strokeWidth={1.5}
            />
          </button>
          <div
            className="flex items-center gap-1 text-sm"
            style={{ color: "var(--fg-tertiary)" }}
          >
            <span style={{ color: "var(--fg-secondary)" }}>
              AI Publisher Pro
            </span>
            {pathname !== "/" && (
              <>
                <ChevronRight className="w-3 h-3" />
                <span
                  className="font-medium capitalize"
                  style={{ color: "var(--fg-primary)" }}
                >
                  {pathname.split("/")[1]}
                </span>
              </>
            )}
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          <div
            className="mx-auto px-6 md:px-12 lg:px-16 py-10 md:py-16"
            style={{ maxWidth: "var(--content-width)" }}
          >
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
