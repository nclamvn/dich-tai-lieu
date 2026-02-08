"use client";

import { use, useState } from "react";
import { ArrowLeft, Plus, Trash2, Search, Download, Upload } from "lucide-react";
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

  const [showAdd, setShowAdd] = useState(false);
  const [srcTerm, setSrcTerm] = useState("");
  const [tgtTerm, setTgtTerm] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  const glossary = data?.glossary;

  if (isLoading)
    return <div className="animate-pulse h-40 bg-slate-200 rounded-lg" />;
  if (!glossary) return <p>Glossary not found</p>;

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
        alert("Invalid JSON file");
      }
    };
    input.click();
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <Link
        href="/glossary"
        className="text-sm text-slate-500 hover:text-slate-700 flex items-center gap-1"
      >
        <ArrowLeft className="w-3 h-3" /> Back to Glossaries
      </Link>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">{glossary.name}</h1>
          <p className="text-slate-500 text-sm">
            {glossary.language_pair} &middot; {glossary.entry_count} terms
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={handleImport}>
            <Upload className="w-3 h-3 mr-1" /> Import
          </Button>
          <Button variant="secondary" size="sm" onClick={handleExport}>
            <Download className="w-3 h-3 mr-1" /> Export
          </Button>
        </div>
      </div>

      <div className="flex gap-3">
        <div className="flex-1 relative">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search terms..."
            className="w-full border rounded-lg pl-9 pr-3 py-2 text-sm"
          />
        </div>
        <Button size="sm" onClick={() => setShowAdd(!showAdd)}>
          <Plus className="w-4 h-4 mr-1" /> Add
        </Button>
      </div>

      {showAdd && (
        <Card className="border-blue-200 bg-blue-50/50">
          <CardContent className="pt-4">
            <div className="grid grid-cols-2 gap-3">
              <input
                value={srcTerm}
                onChange={(e) => setSrcTerm(e.target.value)}
                placeholder="Source term"
                className="border rounded-lg px-3 py-2 text-sm"
                autoFocus
              />
              <input
                value={tgtTerm}
                onChange={(e) => setTgtTerm(e.target.value)}
                placeholder="Target term"
                className="border rounded-lg px-3 py-2 text-sm"
                onKeyDown={(e) => e.key === "Enter" && handleAdd()}
              />
            </div>
            <Button
              onClick={handleAdd}
              size="sm"
              className="mt-3"
              loading={addEntry.isPending}
            >
              Add Entry
            </Button>
          </CardContent>
        </Card>
      )}

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="text-left px-5 py-3 font-medium text-slate-600">
                  Source
                </th>
                <th className="text-left px-5 py-3 font-medium text-slate-600">
                  Target
                </th>
                <th className="text-left px-5 py-3 font-medium text-slate-600">
                  Domain
                </th>
                <th className="w-10"></th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {filteredEntries.map((entry) => (
                <tr key={entry.id} className="hover:bg-slate-50">
                  <td className="px-5 py-3 font-medium">
                    {entry.source_term}
                  </td>
                  <td className="px-5 py-3">{entry.target_term}</td>
                  <td className="px-5 py-3 text-slate-500">
                    {entry.domain}
                  </td>
                  <td className="px-3 py-3">
                    <button
                      onClick={() => removeEntry.mutate(entry.id)}
                      className="p-1 text-slate-400 hover:text-red-500"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
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
