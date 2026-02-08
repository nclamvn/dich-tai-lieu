"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Upload, FileText, Sparkles, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { useCreateJob, useProfiles, useGlossaries } from "@/lib/api/hooks";
import {
  SUPPORTED_LANGUAGES,
  OUTPUT_FORMATS,
  type TranslateRequest,
} from "@/lib/api/types";
import { cn } from "@/lib/utils";

export default function TranslatePage() {
  const router = useRouter();
  const createJob = useCreateJob();

  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [sourceLang, setSourceLang] = useState("en");
  const [targetLang, setTargetLang] = useState("vi");
  const [outputFormat, setOutputFormat] = useState("docx");
  const [profileId, setProfileId] = useState("");
  const [selectedGlossaries, setSelectedGlossaries] = useState<string[]>([]);

  const { data: profilesData } = useProfiles();
  const { data: glossaryData } = useGlossaries(sourceLang, targetLang);

  const profileList = profilesData?.profiles || [];
  const glossaryList = glossaryData?.glossaries || [];

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) setFile(droppedFile);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setDragOver(false);
  }, []);

  const handleSubmit = async () => {
    if (!file) return;

    const request: TranslateRequest = {
      source_language: sourceLang,
      target_language: targetLang,
      output_format: outputFormat,
      profile_id: profileId || undefined,
      glossary_ids:
        selectedGlossaries.length > 0 ? selectedGlossaries : undefined,
    };

    try {
      const job = await createJob.mutateAsync({ file, request });
      router.push(`/jobs/${job.id}`);
    } catch {
      // Error handled by mutation state
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Translate Document</h1>
        <p className="text-slate-500 mt-1">
          Upload a document and configure translation settings
        </p>
      </div>

      {/* File Upload */}
      <Card>
        <CardHeader>
          <h2 className="font-semibold flex items-center gap-2">
            <Upload className="w-4 h-4" />
            Upload Document
          </h2>
        </CardHeader>
        <CardContent>
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            className={cn(
              "border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer",
              dragOver
                ? "border-blue-400 bg-blue-50"
                : file
                  ? "border-green-300 bg-green-50"
                  : "border-slate-300 hover:border-slate-400",
            )}
            onClick={() => document.getElementById("file-input")?.click()}
          >
            <input
              id="file-input"
              type="file"
              className="hidden"
              accept=".pdf,.docx,.txt,.md,.epub"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
            {file ? (
              <div className="flex items-center justify-center gap-3">
                <FileText className="w-8 h-8 text-green-600" />
                <div className="text-left">
                  <p className="font-medium text-green-900">{file.name}</p>
                  <p className="text-sm text-green-600">
                    {(file.size / 1024).toFixed(1)} KB — Click to change
                  </p>
                </div>
              </div>
            ) : (
              <>
                <Upload className="w-10 h-10 text-slate-400 mx-auto mb-3" />
                <p className="font-medium">
                  Drop file here or click to browse
                </p>
                <p className="text-sm text-slate-400 mt-1">
                  PDF, DOCX, TXT, Markdown, EPUB
                </p>
              </>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Translation Settings */}
      <Card>
        <CardHeader>
          <h2 className="font-semibold flex items-center gap-2">
            <Sparkles className="w-4 h-4" />
            Translation Settings
          </h2>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Language Selection */}
          <div className="grid grid-cols-[1fr_auto_1fr] gap-3 items-end">
            <div>
              <label className="block text-sm font-medium mb-1.5">
                Source Language
              </label>
              <select
                value={sourceLang}
                onChange={(e) => setSourceLang(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm bg-white"
              >
                {SUPPORTED_LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.native_name} ({l.name})
                  </option>
                ))}
              </select>
            </div>

            <ArrowRight className="w-5 h-5 text-slate-400 mb-2" />

            <div>
              <label className="block text-sm font-medium mb-1.5">
                Target Language
              </label>
              <select
                value={targetLang}
                onChange={(e) => setTargetLang(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm bg-white"
              >
                {SUPPORTED_LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.native_name} ({l.name})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Output Format */}
          <div>
            <label className="block text-sm font-medium mb-1.5">
              Output Format
            </label>
            <div className="flex gap-2 flex-wrap">
              {OUTPUT_FORMATS.map((f) => (
                <button
                  key={f.value}
                  onClick={() => setOutputFormat(f.value)}
                  className={cn(
                    "px-3 py-1.5 rounded-lg text-sm border transition-colors",
                    outputFormat === f.value
                      ? "border-blue-500 bg-blue-50 text-blue-700 font-medium"
                      : "border-slate-200 hover:border-slate-300",
                  )}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>

          {/* Profile */}
          {profileList.length > 0 && (
            <div>
              <label className="block text-sm font-medium mb-1.5">
                Publishing Profile (optional)
              </label>
              <select
                value={profileId}
                onChange={(e) => setProfileId(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm bg-white"
              >
                <option value="">Auto (QAPR routing)</option>
                {profileList.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} — {p.language_pair}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Glossaries */}
          {glossaryList.length > 0 && (
            <div>
              <label className="block text-sm font-medium mb-1.5">
                Glossaries ({sourceLang}&rarr;{targetLang})
              </label>
              <div className="space-y-1.5">
                {glossaryList.map((g) => (
                  <label
                    key={g.id}
                    className="flex items-center gap-2 text-sm"
                  >
                    <input
                      type="checkbox"
                      checked={selectedGlossaries.includes(g.id)}
                      onChange={(e) => {
                        setSelectedGlossaries((prev) =>
                          e.target.checked
                            ? [...prev, g.id]
                            : prev.filter((id) => id !== g.id),
                        );
                      }}
                      className="rounded border-slate-300"
                    />
                    {g.name}
                    <span className="text-slate-400">
                      ({g.entry_count} terms)
                    </span>
                  </label>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Submit */}
      <div className="flex justify-end gap-3">
        <Button
          variant="primary"
          size="lg"
          onClick={handleSubmit}
          disabled={!file}
          loading={createJob.isPending}
        >
          <Upload className="w-4 h-4 mr-2" />
          Start Translation
        </Button>
      </div>

      {createJob.isError && (
        <p className="text-red-600 text-sm">
          Error: {(createJob.error as Error).message}
        </p>
      )}
    </div>
  );
}
