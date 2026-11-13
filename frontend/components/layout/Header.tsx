"use client";

import React from "react";
import { Sparkles, Terminal, ShieldCheck } from "lucide-react";

export function Header() {
  return (
    <header className="h-16 border-b border-slate-800 bg-slate-950/80 backdrop-blur px-8 flex items-center justify-between sticky top-0 z-10">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 text-xs font-medium px-2.5 py-1 rounded-full bg-blue-950/80 border border-blue-800/60 text-blue-300">
          <Sparkles className="h-3.5 w-3.5 text-blue-400" />
          <span>Local Engine Active</span>
        </div>
        <span className="text-xs text-slate-500">•</span>
        <div className="flex items-center gap-1.5 text-xs text-slate-400 font-mono">
          <Terminal className="h-3.5 w-3.5 text-slate-500" />
          <span>FastAPI :8000</span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-xs text-slate-400 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg">
          <ShieldCheck className="h-4 w-4 text-emerald-400" />
          <span>Zero External Paid APIs</span>
        </div>
      </div>
    </header>
  );
}
