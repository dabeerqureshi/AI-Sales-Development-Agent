"use client";

import React, { useState } from "react";
import { Globe, Calendar, Clock, CheckCircle2, AlertCircle, ChevronDown, ChevronUp, FileText } from "lucide-react";

export interface ResearchItem {
  id: number;
  lead_id: number;
  crawled_url: string;
  page_title?: string | null;
  meta_description?: string | null;
  services_summary?: string | null;
  booking_system_found: boolean;
  booking_system_name?: string | null;
  has_custom_booking_form: boolean;
  after_hours_info?: string | null;
  extracted_text_snippet?: string | null;
  crawled_at: string;
}

export function ResearchCard({
  research,
  businessName,
  industry,
}: {
  research: ResearchItem;
  businessName?: string;
  industry?: string;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-all space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-slate-100 text-sm">{businessName || "Business"}</h3>
            {industry && (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                {industry}
              </span>
            )}
          </div>
          <a
            href={research.crawled_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-xs text-blue-400 hover:underline mt-1 font-mono truncate max-w-md"
          >
            <Globe className="h-3 w-3 shrink-0" />
            <span className="truncate">{research.crawled_url}</span>
          </a>
        </div>

        {/* Booking System Badge */}
        <div>
          {research.booking_system_found ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <Calendar className="h-3.5 w-3.5" />
              {research.booking_system_name || "Online Booking"}
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <AlertCircle className="h-3.5 w-3.5" />
              No Online Booking (Opportunity)
            </span>
          )}
        </div>
      </div>

      {/* Title & Meta Description */}
      {(research.page_title || research.meta_description) && (
        <div className="bg-slate-950/70 border border-slate-800/80 rounded-lg p-3 space-y-1 text-xs">
          {research.page_title && (
            <div className="font-semibold text-slate-200">{research.page_title}</div>
          )}
          {research.meta_description && (
            <div className="text-slate-400 text-[11px] leading-relaxed line-clamp-2">
              {research.meta_description}
            </div>
          )}
        </div>
      )}

      {/* Services Tag Cloud */}
      {research.services_summary && (
        <div className="space-y-1.5">
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Detected Services & Treatments:
          </div>
          <div className="flex flex-wrap gap-1.5">
            {research.services_summary.split(",").map((s, idx) => (
              <span
                key={idx}
                className="px-2 py-0.5 rounded bg-blue-950/60 border border-blue-800/50 text-[11px] text-blue-300 font-medium"
              >
                {s.trim()}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* After-Hours / Emergency Info */}
      {research.after_hours_info && (
        <div className="p-3 bg-amber-950/20 border border-amber-800/40 rounded-lg text-xs space-y-1">
          <div className="flex items-center gap-1.5 font-semibold text-amber-300 text-[11px]">
            <Clock className="h-3.5 w-3.5 text-amber-400" />
            <span>After-Hours / Emergency Policy Detected:</span>
          </div>
          <p className="text-slate-300 text-[11px] italic leading-relaxed">
            "{research.after_hours_info}"
          </p>
        </div>
      )}

      {/* Expandable Raw Text Evidence */}
      {research.extracted_text_snippet && (
        <div className="pt-2 border-t border-slate-800/60">
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors font-medium"
          >
            <FileText className="h-3.5 w-3.5 text-slate-500" />
            <span>{expanded ? "Hide Extracted Evidence" : "View Extracted Text Snippet"}</span>
            {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          </button>

          {expanded && (
            <div className="mt-3 p-3 bg-slate-950 border border-slate-800 rounded-lg text-[11px] font-mono text-slate-300 max-h-48 overflow-y-auto leading-relaxed whitespace-pre-wrap">
              {research.extracted_text_snippet}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
