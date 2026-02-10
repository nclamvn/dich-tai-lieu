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
  ChevronLeft,
  Layers,
  PanelLeftClose,
  PanelLeft,
  PenTool,
  Wand2,
  Database,
  FolderUp,
  FileEdit,
} from "lucide-react";
import { useState, useEffect } from "react";
import { useLocale } from "@/lib/i18n";
import { LocaleToggle } from "@/components/ui/locale-toggle";
import { ThemeToggle } from "@/components/ui/theme-toggle";

const NAV_KEYS = [
  { href: "/translate", key: "translate" as const, icon: Upload },
  { href: "/write", key: "write" as const, icon: PenTool },
  { href: "/write-v2", key: "writeV2" as const, icon: Wand2 },
  { href: "/jobs", key: "jobs" as const, icon: List },
  { href: "/glossary", key: "glossary" as const, icon: BookOpen },
  { href: "/tm", key: "tm" as const, icon: Database },
  { href: "/batch", key: "batch" as const, icon: FolderUp },
  { href: "/dashboard", key: "dashboard" as const, icon: BarChart3 },
  { href: "/profiles", key: "profiles" as const, icon: Layers },
  { href: "/settings", key: "settings" as const, icon: Settings },
];

const STORAGE_KEY = "aipub-sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const { t } = useLocale();

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "collapsed") setCollapsed(true);
  }, []);

  const toggleCollapsed = () => {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem(STORAGE_KEY, next ? "collapsed" : "expanded");
  };

  const sidebarWidth = collapsed ? "w-[56px]" : "w-[240px]";

  return (
    <div className="min-h-screen flex">
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 md:hidden"
          style={{ background: "var(--bg-overlay)" }}
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed top-0 left-0 h-screen z-50 flex flex-col",
          "transition-all duration-200 ease-in-out",
          "md:translate-x-0 md:sticky md:z-auto",
          mobileOpen ? "translate-x-0 w-[240px]" : "-translate-x-full",
          !mobileOpen && sidebarWidth,
        )}
        style={{
          background: "var(--bg-sidebar)",
          borderRight: "1px solid var(--border-default)",
        }}
      >
        {/* Logo + collapse toggle */}
        <div
          className={cn(
            "flex items-center shrink-0",
            collapsed ? "px-2 justify-center" : "px-3 justify-between",
          )}
          style={{ height: "var(--header-height)" }}
        >
          {collapsed ? (
            /* Collapsed: only expand icon */
            <button
              onClick={toggleCollapsed}
              className="hidden md:flex p-1.5 transition-colors duration-100 items-center justify-center"
              style={{
                borderRadius: "var(--radius-sm)",
                color: "var(--fg-icon)",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = "var(--fg-primary)")}
              onMouseLeave={(e) => (e.currentTarget.style.color = "var(--fg-icon)")}
            >
              <PanelLeft className="w-4 h-4" strokeWidth={1.5} />
            </button>
          ) : (
            <>
              <Link
                href="/"
                className="flex items-center py-1 px-2 no-underline"
                style={{ borderRadius: "var(--radius-sm)" }}
              >
                <span
                  className="text-sm font-medium"
                  style={{ color: "var(--fg-primary)" }}
                >
                  AI Publisher Pro
                </span>
              </Link>
              <div className="flex items-center gap-0.5">
                {/* Collapse toggle (desktop) */}
                <button
                  onClick={toggleCollapsed}
                  className="hidden md:flex p-1 transition-colors duration-100 items-center justify-center"
                  style={{
                    borderRadius: "var(--radius-sm)",
                    color: "var(--fg-icon)",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.color = "var(--fg-primary)")}
                  onMouseLeave={(e) => (e.currentTarget.style.color = "var(--fg-icon)")}
                >
                  <PanelLeftClose className="w-4 h-4" strokeWidth={1.5} />
                </button>
                {/* Mobile close */}
                <button
                  className="md:hidden p-1"
                  style={{ borderRadius: "var(--radius-sm)" }}
                  onClick={() => setMobileOpen(false)}
                >
                  <X
                    className="w-4 h-4"
                    style={{ color: "var(--fg-icon)" }}
                    strokeWidth={1.5}
                  />
                </button>
              </div>
            </>
          )}
        </div>

        {/* Nav */}
        <nav className={cn("flex-1 py-2 space-y-0.5 overflow-y-auto", collapsed ? "px-1.5" : "px-2")}>
          {NAV_KEYS.map(({ href, key, icon: Icon }) => {
            const isActive =
              pathname === href || pathname.startsWith(href + "/");
            return (
              <Link
                key={href}
                href={href}
                onClick={() => setMobileOpen(false)}
                title={collapsed ? t.nav[key] : undefined}
                className={cn(
                  "flex items-center text-sm no-underline transition-colors duration-100",
                  collapsed
                    ? "justify-center px-0 py-1.5"
                    : "gap-2.5 px-2.5 py-[5px]",
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
                {!collapsed && t.nav[key]}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div
          className={cn(
            "shrink-0 flex items-center",
            collapsed ? "flex-col gap-2 px-1.5 pt-3 pb-12" : "justify-between px-3 py-3",
          )}
          style={{ borderTop: "1px solid var(--border-default)" }}
        >
          {!collapsed && (
            <p
              className="text-[11px] px-2"
              style={{ color: "var(--fg-tertiary)" }}
            >
              VIBECODE KIT V4
            </p>
          )}
          <div className={cn("flex items-center", collapsed ? "flex-col gap-2" : "gap-1.5")}>
            <ThemeToggle collapsed={collapsed} />
            <LocaleToggle collapsed={collapsed} />
          </div>
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
            onClick={() => setMobileOpen(true)}
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
            className="flex-1 flex items-center gap-1 text-sm"
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
          <ThemeToggle />
          <LocaleToggle />
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          <div
            className="mx-auto px-6 md:px-12 lg:px-16 py-5 md:py-8"
            style={{ maxWidth: "var(--content-width)" }}
          >
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
