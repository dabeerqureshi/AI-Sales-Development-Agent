"use client";

import React, { useState } from "react";
import {
  ExternalLink,
  Globe,
  Phone,
  MapPin,
  ShieldCheck,
  Sparkles,
  CheckCircle2,
  Award,
  X,
} from "lucide-react";
import { ScoreCard, LeadScoreData } from "@/components/qualification/ScoreCard";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface LeadItem {
  id: number;
  campaign_id: number;
  business_name: string;
  industry: string;
  website?: string | null;
  phone?: string | null;
  address?: string | null;
  external_id: string;
  source: string;
  status: string;
  created_at: string;
  sources?: {
    source_name: string;
    source_url: string;
  }[];
}

export function LeadTable({
  leads,
  onLeadResearched,
}: {
  leads: LeadItem[];
  onLeadResearched?: () => void;
}) {
  const [researchingId, setResearchingId] = useState<number | null>(null);
  const [qualifyingId, setQualifyingId] = useState<number | null>(null);
  const [activeScore, setActiveScore] = useState<LeadScoreData | null>(null);
  const [loadingScore, setLoadingScore] = useState<boolean>(false);

  const handleResearchSingle = async (leadId: number) => {
    setResearchingId(leadId);
    try {
      const res = await fetch(`${API_BASE}/api/leads/${leadId}/research`, {
        method: "POST",
      });
      if (res.ok) {
        if (onLeadResearched) onLeadResearched();
      } else {
        const err = await res.json();
        alert(`Research failed: ${err.detail || "Error crawling website"}`);
      }
    } catch {
      alert("Network error crawling website.");
    } finally {
      setResearchingId(null);
    }
  };

  const handleQualifySingle = async (leadId: number, businessName: string) => {
    setQualifyingId(leadId);
    try {
      const res = await fetch(`${API_BASE}/api/leads/${leadId}/qualify`, {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        setActiveScore({ ...data, business_name: businessName });
        if (onLeadResearched) onLeadResearched();
      } else {
        const err = await res.json();
        alert(`Qualification failed: ${err.detail || "Error scoring lead"}`);
      }
    } catch {
      alert("Network error qualifying lead.");
    } finally {
      setQualifyingId(null);
    }
  };

  const handleViewScore = async (leadId: number, businessName: string) => {
    setLoadingScore(true);
    try {
      const res = await fetch(`${API_BASE}/api/leads/${leadId}/score`);
      if (res.ok) {
        const data = await res.json();
        setActiveScore({ ...data, business_name: businessName });
      } else {
        // Run qualify if not yet scored
        handleQualifySingle(leadId, businessName);
      }
    } catch {
      alert("Error fetching lead score.");
    } finally {
      setLoadingScore(false);
    }
  };

  if (leads.length === 0) {
    return (
      <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-12 text-center space-y-2">
        <p className="text-sm font-semibold text-slate-300">No leads discovered yet</p>
        <p className="text-xs text-slate-500">
          Run the Business Discovery tool to search real OpenStreetMap records.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Modal for 4-Quadrant Score Report */}
      {activeScore && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
          <div className="relative w-full max-w-3xl max-h-[90vh] overflow-y-auto bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl p-6 space-y-4">
            <button
              onClick={() => setActiveScore(null)}
              className="absolute top-4 right-4 p-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
            <ScoreCard score={activeScore} />
          </div>
        </div>
      )}

      <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/40">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-950/80 text-slate-400 font-mono text-[11px] uppercase tracking-wider border-b border-slate-800">
            <tr>
              <th className="py-3 px-4">Business Name</th>
              <th className="py-3 px-4">Category</th>
              <th className="py-3 px-4">Website</th>
              <th className="py-3 px-4">Phone</th>
              <th className="py-3 px-4">Physical Address</th>
              <th className="py-3 px-4">Qualification</th>
              <th className="py-3 px-4">Research & Actions</th>
              <th className="py-3 px-4">Source</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-sans">
            {leads.map((lead) => {
              const primarySourceUrl =
                lead.sources && lead.sources.length > 0
                  ? lead.sources[0].source_url
                  : `https://www.openstreetmap.org/${lead.external_id}`;
              const isResearched = lead.status === "researched" || lead.status === "qualified";
              const isQualified = lead.status === "qualified";

              return (
                <tr key={lead.id} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-3.5 px-4 font-semibold text-slate-200">
                    <div className="flex items-center gap-2">
                      <span>{lead.business_name}</span>
                      <span className="text-[10px] text-slate-500 font-mono font-normal">#{lead.id}</span>
                    </div>
                  </td>
                  <td className="py-3.5 px-4 text-slate-300 font-mono text-[11px]">
                    {lead.industry}
                  </td>
                  <td className="py-3.5 px-4">
                    {lead.website ? (
                      <a
                        href={lead.website}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-blue-400 hover:text-blue-300 hover:underline max-w-[160px] truncate"
                        title={lead.website}
                      >
                        <Globe className="h-3 w-3 shrink-0" />
                        <span className="truncate">{lead.website.replace(/^https?:\/\/(www\.)?/, "")}</span>
                        <ExternalLink className="h-2.5 w-2.5 shrink-0" />
                      </a>
                    ) : (
                      <span className="text-slate-600 font-mono text-[11px]">N/A</span>
                    )}
                  </td>
                  <td className="py-3.5 px-4 text-slate-300 font-mono text-[11px]">
                    {lead.phone ? (
                      <span className="inline-flex items-center gap-1">
                        <Phone className="h-3 w-3 text-slate-500" />
                        {lead.phone}
                      </span>
                    ) : (
                      <span className="text-slate-600">N/A</span>
                    )}
                  </td>
                  <td className="py-3.5 px-4 text-slate-400 max-w-xs truncate" title={lead.address || "N/A"}>
                    {lead.address ? (
                      <div className="flex items-center gap-1 truncate">
                        <MapPin className="h-3 w-3 text-slate-500 shrink-0" />
                        <span className="truncate">{lead.address}</span>
                      </div>
                    ) : (
                      <span className="text-slate-600 font-mono">N/A</span>
                    )}
                  </td>

                  {/* AI Qualification Column */}
                  <td className="py-3.5 px-4">
                    {isQualified ? (
                      <button
                        onClick={() => handleViewScore(lead.id, lead.business_name)}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 transition-colors"
                      >
                        <Award className="h-3 w-3" />
                        <span>Qualified</span>
                      </button>
                    ) : (
                      <button
                        onClick={() => handleQualifySingle(lead.id, lead.business_name)}
                        disabled={qualifyingId === lead.id}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-900 hover:bg-slate-800 border border-slate-700 text-[11px] font-medium text-slate-200 transition-colors disabled:opacity-50"
                      >
                        <Award className={`h-3 w-3 text-purple-400 ${qualifyingId === lead.id ? "animate-spin" : ""}`} />
                        {qualifyingId === lead.id ? "Scoring..." : "Qualify"}
                      </button>
                    )}
                  </td>

                  <td className="py-3.5 px-4">
                    {lead.website ? (
                      isResearched ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          <CheckCircle2 className="h-3 w-3" />
                          Researched
                        </span>
                      ) : (
                        <button
                          onClick={() => handleResearchSingle(lead.id)}
                          disabled={researchingId === lead.id}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-900 hover:bg-slate-800 border border-slate-700 text-[11px] font-medium text-slate-200 transition-colors disabled:opacity-50"
                        >
                          <Sparkles className={`h-3 w-3 text-blue-400 ${researchingId === lead.id ? "animate-spin" : ""}`} />
                          {researchingId === lead.id ? "Crawling..." : "Research Site"}
                        </button>
                      )
                    ) : (
                      <span className="text-slate-600 text-[11px] font-mono">No Website</span>
                    )}
                  </td>
                  <td className="py-3.5 px-4">
                    <a
                      href={primarySourceUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-950 border border-slate-800 text-[11px] font-mono text-emerald-400 hover:border-emerald-600/60 transition-colors"
                    >
                      <ShieldCheck className="h-3 w-3" />
                      <span>OSM: {lead.external_id}</span>
                      <ExternalLink className="h-2.5 w-2.5 text-slate-500" />
                    </a>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
