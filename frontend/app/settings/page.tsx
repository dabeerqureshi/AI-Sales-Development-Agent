"use client";

import React from "react";
import { SystemStatusSection } from "@/components/dashboard/SystemStatusSection";

export default function SettingsPage() {
  return (
    <div className="max-w-5xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Platform Settings</h1>
        <p className="text-xs text-slate-400 mt-1">
          Configure runtime environment, model endpoints, and service connectivity.
        </p>
      </div>

      <SystemStatusSection />

      <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-6 space-y-4">
        <h3 className="text-sm font-semibold text-slate-200">Environment Details</h3>
        <div className="space-y-3 font-mono text-xs">
          <div className="flex justify-between py-2 border-b border-slate-800">
            <span className="text-slate-400">Backend API URL</span>
            <span className="text-blue-400">{process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}</span>
          </div>
          <div className="flex justify-between py-2 border-b border-slate-800">
            <span className="text-slate-400">Database Engine</span>
            <span className="text-slate-300">SQLite 3 (Local-First file sdr.db)</span>
          </div>
          <div className="flex justify-between py-2 border-b border-slate-800">
            <span className="text-slate-400">Model Configuration</span>
            <span className="text-slate-300">Ollama local instance (default: qwen3:4b)</span>
          </div>
          <div className="flex justify-between py-2">
            <span className="text-slate-400">Security Mode</span>
            <span className="text-emerald-400">Offline/Local first (Zero outbound data sharing)</span>
          </div>
        </div>
      </div>
    </div>
  );
}
