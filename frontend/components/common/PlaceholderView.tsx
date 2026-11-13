import React from "react";
import Link from "next/link";
import { ArrowLeft, Clock } from "lucide-react";

export function PlaceholderView({
  title,
  milestone,
  description,
}: {
  title: string;
  milestone: string;
  description: string;
}) {
  return (
    <div className="max-w-4xl mx-auto py-12 px-4 text-center space-y-6">
      <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-xs text-slate-400 font-mono">
        <Clock className="h-3.5 w-3.5 text-blue-400" />
        Scheduled for {milestone}
      </div>
      <h1 className="text-3xl font-bold text-white tracking-tight">{title}</h1>
      <p className="text-sm text-slate-400 max-w-lg mx-auto leading-relaxed">
        {description}
      </p>
      <div className="pt-4">
        <Link
          href="/"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-xs font-medium text-slate-200 border border-slate-800 transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Dashboard
        </Link>
      </div>
    </div>
  );
}
