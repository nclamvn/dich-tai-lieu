"use client";

import { use, useState } from "react";
import {
  ArrowLeft,
  Plus,
  Trash2,
  Search,
  Download,
  Upload,
} from "lucide-react";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  useGlossary,
  useAddGlossaryEntry,
  useRemoveGlossaryEntry,
  useImportGlossaryEntries,
} from "@/lib/api/hooks";
import { glossaries as glossaryApi } from "@/lib/api/client";
import { useLocale } from "@/lib/i18n";

export default function GlossaryDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data, isLoading } = useGlossary(id);
  const addEntry = useAddGlossaryEntry(id);
  const removeEntry = useRemoveGlossaryEntry(id);
  const importEntries = useImportGlossaryEntries(id);
  const { t } = useLocale();

  const [showAdd, setShowAdd] = useState(false);
  const [srcTerm, setSrcTerm] = useState("");
  const [tgtTerm, setTgtTerm] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  const glossary = data?.glossary;

  if (isLoading)
    return <div className="h-40 skeleton" />;
  if (!glossary)
    return (
      <p style={{ color: "var(--fg-tertiary)" }}>{t.glossary.notFound}</p>
    );

  const filteredEntries = searchQuery
    ? glossary.entries.filter(
        (e) =>
          e.source_term.toLowerCase().includes(searchQuery.toLowerCase()) ||
          e.target_term.toLowerCase().includes(searchQuery.toLowerCase()),
      )
    : glossary.entries;

  const handleAdd = async () => {
    if (!srcTerm.trim() || !tgtTerm.trim()) return;
    await addEntry.mutateAsync({
      source_term: srcTerm,
      target_term: tgtTerm,
    });
    setSrcTerm("");
    setTgtTerm("");
  };

  const handleExport = async () => {
    const exportData = await glossaryApi.exportEntries(id);
    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${glossary.name}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImport = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json";
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      const text = await file.text();
      try {
        const parsed = JSON.parse(text);
        const entries = parsed.entries || parsed;
        await importEntries.mutateAsync(entries);
      } catch {
        alert(t.glossary.invalidJson);
      }
    };
    input.click();
  };

  return (
    <div className="space-y-6">
      <Link
        href="/glossary"
        className="text-sm flex items-center gap-1 no-underline"
        style={{ color: "var(--fg-secondary)" }}
      >
        <ArrowLeft className="w-3 h-3" /> {t.glossary.backToGlossaries}
      </Link>

      <div className="flex items-start justify-between">
        <div>
          <h1>{glossary.name}</h1>
          <p
            className="text-sm"
            style={{ color: "var(--fg-secondary)" }}
          >
            {glossary.language_pair} &middot; {glossary.entry_count} {t.glossary.terms}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={handleImport}>
            <Upload className="w-3 h-3 mr-1" /> {t.glossary.import}
          </Button>
          <Button variant="secondary" size="sm" onClick={handleExport}>
            <Download className="w-3 h-3 mr-1" /> {t.glossary.export}
          </Button>
        </div>
      </div>

      <div className="flex gap-3">
        <div className="flex-1 relative">
          <Search
            className="w-4 h-4 absolute left-3 top-2.5"
            style={{ color: "var(--fg-icon)" }}
            strokeWidth={1.5}
          />
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t.glossary.searchTerms}
            className="w-full pl-9 pr-3 py-2 text-sm"
            style={{
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border-default)",
              background: "var(--bg-primary)",
              color: "var(--fg-primary)",
            }}
          />
        </div>
        <Button size="sm" onClick={() => setShowAdd(!showAdd)}>
          <Plus className="w-4 h-4 mr-1" /> {t.glossary.add}
        </Button>
      </div>

      {showAdd && (
        <Card
          style={{
            borderColor: "var(--color-notion-blue)",
            background: "var(--accent-blue-bg)",
          }}
        >
          <CardContent className="pt-4">
            <div className="grid grid-cols-2 gap-3">
              <input
                value={srcTerm}
                onChange={(e) => setSrcTerm(e.target.value)}
                placeholder={t.glossary.sourceTerm}
                className="px-3 py-2 text-sm"
                style={{
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--border-default)",
                  background: "var(--bg-primary)",
                  color: "var(--fg-primary)",
                }}
                autoFocus
              />
              <input
                value={tgtTerm}
                onChange={(e) => setTgtTerm(e.target.value)}
                placeholder={t.glossary.targetTerm}
                className="px-3 py-2 text-sm"
                style={{
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--border-default)",
                  background: "var(--bg-primary)",
                  color: "var(--fg-primary)",
                }}
                onKeyDown={(e) => e.key === "Enter" && handleAdd()}
              />
            </div>
            <Button
              onClick={handleAdd}
              size="sm"
              className="mt-3"
              loading={addEntry.isPending}
            >
              {t.glossary.addEntry}
            </Button>
          </CardContent>
        </Card>
      )}

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr style={{ background: "var(--bg-secondary)" }}>
                <th
                  className="text-left px-5 py-3 font-medium"
                  style={{ color: "var(--fg-secondary)" }}
                >
                  {t.glossary.source}
                </th>
                <th
                  className="text-left px-5 py-3 font-medium"
                  style={{ color: "var(--fg-secondary)" }}
                >
                  {t.glossary.target}
                </th>
                <th
                  className="text-left px-5 py-3 font-medium"
                  style={{ color: "var(--fg-secondary)" }}
                >
                  {t.glossary.domain}
                </th>
                <th className="w-10"></th>
              </tr>
            </thead>
            <tbody
              style={{
                borderTop: "1px solid var(--border-default)",
              }}
            >
              {filteredEntries.map((entry) => (
                <tr
                  key={entry.id}
                  className="transition-colors duration-100"
                  style={{
                    borderBottom: "1px solid var(--border-default)",
                  }}
                  onMouseEnter={(e) =>
                    (e.currentTarget.style.background =
                      "var(--bg-hover)")
                  }
                  onMouseLeave={(e) =>
                    (e.currentTarget.style.background = "transparent")
                  }
                >
                  <td
                    className="px-5 py-3 font-medium"
                    style={{ color: "var(--fg-primary)" }}
                  >
                    {entry.source_term}
                  </td>
                  <td
                    className="px-5 py-3"
                    style={{ color: "var(--fg-primary)" }}
                  >
                    {entry.target_term}
                  </td>
                  <td
                    className="px-5 py-3"
                    style={{ color: "var(--fg-secondary)" }}
                  >
                    {entry.domain}
                  </td>
                  <td className="px-3 py-3">
                    <button
                      onClick={() => removeEntry.mutate(entry.id)}
                      className="p-1 transition-colors duration-100"
                      style={{ color: "var(--fg-icon)" }}
                      onMouseEnter={(e) =>
                        (e.currentTarget.style.color =
                          "var(--color-notion-red)")
                      }
                      onMouseLeave={(e) =>
                        (e.currentTarget.style.color = "var(--fg-icon)")
                      }
                    >
                      <Trash2 className="w-3.5 h-3.5" strokeWidth={1.5} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
