"use client";

import { useState } from "react";
import Link from "next/link";
import { BookOpen, Plus, Trash2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import {
  useGlossaries,
  useCreateGlossary,
  useDeleteGlossary,
} from "@/lib/api/hooks";
import { SUPPORTED_LANGUAGES } from "@/lib/api/types";

export default function GlossaryPage() {
  const { data, isLoading } = useGlossaries();
  const createGlossary = useCreateGlossary();
  const deleteGlossary = useDeleteGlossary();
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newSrc, setNewSrc] = useState("en");
  const [newTgt, setNewTgt] = useState("vi");

  const list = data?.glossaries || [];

  const handleCreate = async () => {
    if (!newName.trim()) return;
    await createGlossary.mutateAsync({
      name: newName.trim(),
      source_language: newSrc,
      target_language: newTgt,
    });
    setNewName("");
    setShowCreate(false);
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Glossaries</h1>
        <Button onClick={() => setShowCreate(!showCreate)} size="sm">
          <Plus className="w-4 h-4 mr-1" /> New Glossary
        </Button>
      </div>

      {showCreate && (
        <Card className="border-blue-200 bg-blue-50/50">
          <CardContent className="pt-4 space-y-3">
            <input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Glossary name"
              className="w-full border rounded-lg px-3 py-2 text-sm"
              autoFocus
            />
            <div className="grid grid-cols-2 gap-3">
              <select
                value={newSrc}
                onChange={(e) => setNewSrc(e.target.value)}
                className="border rounded-lg px-3 py-2 text-sm"
              >
                {SUPPORTED_LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.name}
                  </option>
                ))}
              </select>
              <select
                value={newTgt}
                onChange={(e) => setNewTgt(e.target.value)}
                className="border rounded-lg px-3 py-2 text-sm"
              >
                {SUPPORTED_LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex gap-2">
              <Button
                onClick={handleCreate}
                loading={createGlossary.isPending}
                size="sm"
              >
                Create
              </Button>
              <Button
                variant="ghost"
                onClick={() => setShowCreate(false)}
                size="sm"
              >
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <div className="animate-pulse space-y-2">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-16 bg-slate-200 rounded-lg" />
          ))}
        </div>
      ) : list.length === 0 ? (
        <EmptyState
          icon={BookOpen}
          title="No glossaries yet"
          description="Create a glossary to ensure consistent terminology"
        />
      ) : (
        <div className="space-y-2">
          {list.map((g) => (
            <Link key={g.id} href={`/glossary/${g.id}`}>
              <Card className="px-5 py-4 hover:shadow-md transition-shadow cursor-pointer">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <BookOpen className="w-5 h-5 text-slate-400" />
                    <div>
                      <p className="font-medium text-sm">{g.name}</p>
                      <p className="text-xs text-slate-500">
                        {g.language_pair} &middot; {g.entry_count} terms
                        {g.project && ` \u00b7 ${g.project}`}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      if (confirm("Delete this glossary?"))
                        deleteGlossary.mutate(g.id);
                    }}
                    className="p-1.5 text-slate-400 hover:text-red-500"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
