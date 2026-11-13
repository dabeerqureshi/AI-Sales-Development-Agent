import React from "react";
import Link from "next/link";
import { SystemStatusSection } from "@/components/dashboard/SystemStatusSection";
import {
  Sparkles,
  ArrowRight,
  ShieldAlert,
  Search,
  CheckCircle,
  FileCode,
  BookOpen
} from "lucide-react";

export default function DashboardPage() {
  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Welcome Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-blue-950/60 via-slate-900 to-slate-900 border border-blue-900/40 p-6 sm:p-8">
        <div className="max-w-2xl relative z-10 space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-xs font-semibold text-blue-400">
            <Sparkles className="h-3.5 w-3.5" />
            Milestone 1 — Foundation Initialized
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            AI Sales Development Agent
          </h1>
          <p className="text-sm text-slate-300 leading-relaxed">
            Local-first, test-driven prospecting engine engineered for Apple Silicon. Discovers real businesses from OpenStreetMap, extracts evidence from public websites, and generates human-reviewed email drafts with zero fabricated data.
          </p>
          <div className="pt-2 flex flex-wrap gap-3">
            <Link
              href="/discover"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition-colors shadow-lg shadow-blue-600/20"
            >
              <Search className="h-3.5 w-3.5" />
              Prepare Task 02 Discovery
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition-colors"
            >
              <FileCode className="h-3.5 w-3.5" />
              FastAPI Swagger Docs
            </a>
          </div>
        </div>
      </div>

      {/* Real-time System Connectivity Status */}
      <SystemStatusSection />

      {/* Engineering & Reliability Rules Banner */}
      <div className="bg-slate-900/40 border border-slate-800/80 rounded-xl p-6 space-y-4">
        <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
          <ShieldAlert className="h-4 w-4 text-amber-400" />
          Reliability & Privacy Guardrails (Active)
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-slate-400">
          <div className="bg-slate-950/60 p-4 rounded-lg border border-slate-800 space-y-1.5">
            <div className="font-medium text-slate-200 flex items-center gap-1.5">
              <CheckCircle className="h-3.5 w-3.5 text-blue-400" />
              Evidence-Based Lead Data
            </div>
            <p>Every lead attribute is linked to an official website or public OpenStreetMap node. Zero invented data.</p>
          </div>
          <div className="bg-slate-950/60 p-4 rounded-lg border border-slate-800 space-y-1.5">
            <div className="font-medium text-slate-200 flex items-center gap-1.5">
              <CheckCircle className="h-3.5 w-3.5 text-blue-400" />
              Local LLM Inference
            </div>
            <p>Runs on local Ollama (Qwen3 4B). Respects local privacy and keeps prospecting prompts on your machine.</p>
          </div>
          <div className="bg-slate-950/60 p-4 rounded-lg border border-slate-800 space-y-1.5">
            <div className="font-medium text-slate-200 flex items-center gap-1.5">
              <CheckCircle className="h-3.5 w-3.5 text-blue-400" />
              Human-in-the-Loop Emailing
            </div>
            <p>All outreach starts as editable drafts. Requires explicit human verification before any transmission.</p>
          </div>
        </div>
      </div>

      {/* Next Milestones Progress */}
      <div className="border border-slate-800 rounded-xl p-6 bg-slate-900/30 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BookOpen className="h-4 w-4 text-blue-400" />
            <h3 className="text-sm font-semibold text-slate-200">Roadmap Progress</h3>
          </div>
          <span className="text-xs font-mono text-blue-400 bg-blue-950/60 px-2.5 py-0.5 rounded border border-blue-900/60">
            Phase 1 of 8 Active
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
          <div className="p-3 rounded-lg bg-emerald-950/20 border border-emerald-800/40 text-emerald-300">
            <div className="font-medium">Task 01: Foundation</div>
            <div className="text-[11px] text-emerald-400/80 mt-1">FastAPI, SQLite, Next.js, Ollama</div>
          </div>
          <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 text-slate-400">
            <div className="font-medium text-slate-300">Task 02: Discovery & MCP</div>
            <div className="text-[11px] text-slate-500 mt-1">OpenStreetMap & Overpass MCP</div>
          </div>
          <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 text-slate-400">
            <div className="font-medium text-slate-300">Task 03: Web Research</div>
            <div className="text-[11px] text-slate-500 mt-1">HTTPX, Trafilatura & Evidence</div>
          </div>
          <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 text-slate-400">
            <div className="font-medium text-slate-300">Task 04: AI Intelligence</div>
            <div className="text-[11px] text-slate-500 mt-1">Scoring & Draft Studio</div>
          </div>
        </div>
      </div>
    </div>
  );
}
