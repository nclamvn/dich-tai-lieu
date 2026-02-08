"use client";

import { Settings } from "lucide-react";
import { Card, CardHeader, CardContent } from "@/components/ui/card";

export default function SettingsPage() {
  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">Settings</h1>

      <Card>
        <CardHeader>
          <h2 className="font-semibold flex items-center gap-2">
            <Settings className="w-4 h-4" />
            API Configuration
          </h2>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1.5">
              Backend API URL
            </label>
            <input
              type="text"
              defaultValue={
                process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
              }
              disabled
              className="w-full border rounded-lg px-3 py-2 text-sm bg-slate-50 text-slate-500"
            />
            <p className="text-xs text-slate-400 mt-1">
              Set via NEXT_PUBLIC_API_URL environment variable
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1.5">
              Version
            </label>
            <p className="text-sm text-slate-600">
              AI Publisher Pro v2.0 — 15 Sprints, 19 Service Modules
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
