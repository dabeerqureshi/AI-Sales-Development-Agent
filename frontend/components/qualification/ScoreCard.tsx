"use client";

import React, { useState } from "react";
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Lightbulb,
  HelpCircle,
  Target,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Award,
} from "lucide-react";

export interface ScoreRuleItem {
  name: string;
  points: number;
  max: number;
  passed: boolean;
  details: string;
}

export interface LeadScoreData {
  id: number;
  lead_id: number;
  overall_score: number;
  rule_breakdown: Record<string, ScoreRuleItem>;
  verified_facts: string[];
  potential_opportunity?: string | null;
  unknowns?: string | null;
  recommended_angle?: string | null;
  scored_at: string;
  business_name?: string | null;
}

export function ScoreCard({
  score,
  compact = false,
}: {
  score: LeadScoreData;
  compact?: boolean;
}) {
  const [showBreakdown, setShowBreakdown] = useState(!compact);

  // Score coloring
  const getScoreTheme = (pts: number) => {
    if (pts >= 75) {
      return {
        badge: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
        ring: "border-emerald-500/50 text-emerald-400",
        label: "High Priority Qualified",
      };
    }
    if (pts >= 50) {
      return {
        badge: "bg-amber-500/10 text-amber-400 border-amber-500/30",
        ring: "border-amber-500/50 text-amber-400",
        label: "Moderate Fit",
      };
    }
    return {
      badge: "bg-slate-800 text-slate-400 border-slate-700",
      ring: "border-slate-700 text-slate-500",
      label: "Low Fit / Incomplete Data",
    };
  };

  const theme = getScoreTheme(score.overall_score);

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-all space-y-5">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Award className="h-4 w-4 text-blue-400" />
            <h3 className="font-semibold text-slate-100 text-base">
              {score.business_name || `Lead #${score.lead_id}`}
            </h3>
            <span
              className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${theme.badge}`}
            >
              {theme.label}
            </span>
          </div>
          <p className="text-xs text-slate-500 font-mono">
            Evaluated on {new Date(score.scored_at).toLocaleDateString()} at{" "}
            {new Date(score.scored_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </p>
        </div>

        {/* Score Dial Badge */}
        <div className="flex items-center gap-3">
          <div
            className={`flex flex-col items-center justify-center h-16 w-16 rounded-xl border-2 bg-slate-950 font-mono ${theme.ring}`}
          >
            <span className="text-2xl font-bold leading-none">{score.overall_score}</span>
            <span className="text-[10px] text-slate-500 tracking-wider">/ 100</span>
          </div>

          <button
            onClick={() => setShowBreakdown(!showBreakdown)}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-slate-950 hover:bg-slate-800 border border-slate-800 text-slate-300 text-xs font-medium transition-colors"
          >
            <span>{showBreakdown ? "Hide Rules" : "View Breakdown"}</span>
            {showBreakdown ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>

      {/* Transparent Deterministic Scoring Breakdown */}
      {showBreakdown && (
        <div className="bg-slate-950/80 border border-slate-800/80 rounded-lg p-3.5 space-y-2">
          <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider flex items-center justify-between pb-1 border-b border-slate-800/60">
            <span>Deterministic Scoring Rules</span>
            <span>Points Awarded</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
            {Object.entries(score.rule_breakdown || {}).map(([key, rule]) => (
              <div
                key={key}
                className="flex items-start justify-between gap-2 p-2 rounded bg-slate-900/40 border border-slate-800/40"
              >
                <div className="flex items-start gap-1.5">
                  {rule.passed ? (
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0 mt-0.5" />
                  ) : (
                    <XCircle className="h-3.5 w-3.5 text-slate-600 shrink-0 mt-0.5" />
                  )}
                  <div>
                    <div className="font-medium text-slate-200">{rule.name}</div>
                    <div className="text-[11px] text-slate-400 line-clamp-1">{rule.details}</div>
                  </div>
                </div>
                <div className="font-mono text-[11px] font-semibold text-slate-300 shrink-0">
                  <span className={rule.points > 0 ? "text-emerald-400" : "text-slate-500"}>
                    +{rule.points}
                  </span>{" "}
                  / {rule.max}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* The 4-Quadrant Grounded AI Qualification Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
        {/* Quadrant 1: Verified Facts */}
        <div className="bg-slate-950/60 border border-blue-900/30 rounded-xl p-3.5 space-y-2">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-blue-400">
            <ShieldCheck className="h-3.5 w-3.5" />
            <span>1. Verified Facts (Confirmed by Data)</span>
          </div>
          <ul className="space-y-1 text-xs text-slate-300">
            {score.verified_facts && score.verified_facts.length > 0 ? (
              score.verified_facts.map((fact, idx) => (
                <li key={idx} className="flex items-start gap-1.5">
                  <span className="text-blue-500 font-bold shrink-0">•</span>
                  <span className="line-clamp-2">{fact}</span>
                </li>
              ))
            ) : (
              <li className="text-slate-500 italic">No verified facts recorded.</li>
            )}
          </ul>
        </div>

        {/* Quadrant 2: Potential Opportunity */}
        <div className="bg-slate-950/60 border border-amber-900/30 rounded-xl p-3.5 space-y-2">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-400">
            <Lightbulb className="h-3.5 w-3.5" />
            <span>2. Potential Opportunity</span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            {score.potential_opportunity || "No specific automation opportunity identified."}
          </p>
        </div>

        {/* Quadrant 3: Unknowns (Never assume without proof) */}
        <div className="bg-slate-950/60 border border-purple-900/30 rounded-xl p-3.5 space-y-2">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-purple-400">
            <HelpCircle className="h-3.5 w-3.5" />
            <span>3. Honest Unknowns (Not Assumed)</span>
          </div>
          <div className="text-xs text-slate-400 whitespace-pre-line leading-relaxed">
            {score.unknowns || "Call volume and front desk staffing levels are unconfirmed."}
          </div>
        </div>

        {/* Quadrant 4: Recommended Angle */}
        <div className="bg-slate-950/60 border border-emerald-900/30 rounded-xl p-3.5 space-y-2">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400">
            <Target className="h-3.5 w-3.5" />
            <span>4. Recommended Outreach Hook</span>
          </div>
          <p className="text-xs text-slate-200 font-medium leading-relaxed">
            {score.recommended_angle || "Lead with standard after-hours phone triage introduction."}
          </p>
        </div>
      </div>
    </div>
  );
}
