"use client";

import React, { useState } from "react";
import { Mail, Phone, ShieldCheck, UserCheck, Copy, Check, ExternalLink, Star } from "lucide-react";

export interface ContactItem {
  id: number;
  lead_id: number;
  full_name?: string | null;
  title?: string | null;
  email?: string | null;
  phone?: string | null;
  confidence_score: number;
  is_primary: boolean;
  business_name?: string | null;
  created_at: string;
  sources?: {
    source_url: string;
    snippet?: string | null;
  }[];
}

export function ContactCard({
  contact,
  onSetPrimary,
}: {
  contact: ContactItem;
  onSetPrimary?: (id: number) => void;
}) {
  const [copiedEmail, setCopiedEmail] = useState(false);
  const [showSource, setShowSource] = useState(false);

  const handleCopyEmail = () => {
    if (contact.email) {
      navigator.clipboard.writeText(contact.email);
      setCopiedEmail(true);
      setTimeout(() => setCopiedEmail(false), 2000);
    }
  };

  const confidencePct = Math.round(contact.confidence_score * 100);
  const primarySource = contact.sources && contact.sources.length > 0 ? contact.sources[0] : null;

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-all space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-slate-100 text-sm">
              {contact.full_name || "Main Office / Reception"}
            </h3>
            {contact.is_primary && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
                <Star className="h-2.5 w-2.5 fill-blue-400" />
                Primary
              </span>
            )}
          </div>
          {contact.title && (
            <div className="text-xs text-blue-400 font-medium mt-0.5">{contact.title}</div>
          )}
          {contact.business_name && (
            <div className="text-[11px] text-slate-400 mt-1 font-mono">
              at <strong className="text-slate-300 font-semibold">{contact.business_name}</strong>
            </div>
          )}
        </div>

        {/* Confidence Badge */}
        <div className="text-right">
          <span
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium border ${
              confidencePct >= 90
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                : confidencePct >= 75
                ? "bg-blue-500/10 text-blue-400 border-blue-500/20"
                : "bg-amber-500/10 text-amber-400 border-amber-500/20"
            }`}
          >
            <ShieldCheck className="h-3 w-3" />
            {confidencePct}% Confidence
          </span>
        </div>
      </div>

      {/* Contact Details */}
      <div className="space-y-2 pt-2 border-t border-slate-800/60 text-xs">
        {contact.email ? (
          <div className="flex items-center justify-between p-2 rounded-lg bg-slate-950/80 border border-slate-800">
            <div className="flex items-center gap-2 text-slate-300 truncate">
              <Mail className="h-3.5 w-3.5 text-blue-400 shrink-0" />
              <span className="font-mono text-[11px] truncate">{contact.email}</span>
            </div>
            <button
              onClick={handleCopyEmail}
              className="text-slate-400 hover:text-white p-1 transition-colors"
              title="Copy Email"
            >
              {copiedEmail ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
            </button>
          </div>
        ) : (
          <div className="text-slate-600 text-[11px] font-mono italic">No direct email published</div>
        )}

        {contact.phone && (
          <div className="flex items-center gap-2 p-2 rounded-lg bg-slate-950/80 border border-slate-800 text-slate-300">
            <Phone className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
            <span className="font-mono text-[11px]">{contact.phone}</span>
          </div>
        )}
      </div>

      {/* Evidence & Action Buttons */}
      <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between gap-2 text-xs">
        {primarySource ? (
          <button
            onClick={() => setShowSource(!showSource)}
            className="text-[11px] text-slate-400 hover:text-slate-200 transition-colors underline"
          >
            {showSource ? "Hide Citation" : "View Source Snippet"}
          </button>
        ) : (
          <span className="text-slate-600 text-[11px]">Direct public citation</span>
        )}

        {!contact.is_primary && onSetPrimary && (
          <button
            onClick={() => onSetPrimary(contact.id)}
            className="inline-flex items-center gap-1 text-[11px] text-slate-400 hover:text-blue-400 font-medium transition-colors"
          >
            <UserCheck className="h-3 w-3" />
            Set as Primary
          </button>
        )}
      </div>

      {/* Expandable Evidence Snippet */}
      {showSource && primarySource && (
        <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1.5 text-[11px]">
          <div className="flex items-center justify-between">
            <span className="text-slate-400 font-semibold">Grounded Evidence Snippet:</span>
            <a
              href={primarySource.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-blue-400 hover:underline"
            >
              <span>Visit Page</span>
              <ExternalLink className="h-2.5 w-2.5" />
            </a>
          </div>
          <p className="text-slate-300 font-mono italic leading-relaxed whitespace-pre-wrap">
            "{primarySource.snippet || "Contact detected in public DOM"}"
          </p>
        </div>
      )}
    </div>
  );
}
