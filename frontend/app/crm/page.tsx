"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  Award,
  Kanban,
  ShieldAlert,
  ShieldCheck,
  History,
  ArrowRight,
  User,
  Globe,
  Mail,
  Phone,
  Search,
  Trash2,
  Plus,
  Sparkles,
  Filter,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  RefreshCw,
  Check,
  Clock,
} from "lucide-react";
import { ScoreCard, LeadScoreData } from "@/components/qualification/ScoreCard";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface CampaignItem {
  id: number;
  name: string;
  industry: string;
  city: string;
}

interface PipelineLeadCard {
  id: number;
  campaign_id: number;
  business_name: string;
  industry: string;
  website?: string | null;
  phone?: string | null;
  address?: string | null;
  status: string;
  score?: number | null;
  primary_contact_name?: string | null;
  primary_contact_email?: string | null;
  has_draft: boolean;
  draft_status?: string | null;
  is_suppressed: boolean;
}

interface PipelineData {
  campaign_id: number;
  stages: Record<string, PipelineLeadCard[]>;
  stage_counts: Record<string, number>;
}

interface SuppressionItem {
  id: number;
  email?: string | null;
  domain?: string | null;
  reason: string;
  added_at: string;
}

interface ActivityItem {
  id: number;
  entity_type: string;
  entity_id: number;
  action: string;
  details: Record<string, any>;
  created_at: string;
}

const STAGES = [
  { key: "discovered", label: "Discovered", color: "border-slate-700 bg-slate-900/40 text-slate-300" },
  { key: "researched", label: "Researched", color: "border-cyan-800/60 bg-cyan-950/20 text-cyan-300" },
  { key: "draft_ready", label: "Draft Ready", color: "border-blue-800/60 bg-blue-950/20 text-blue-300" },
  { key: "approved", label: "Approved", color: "border-emerald-800/60 bg-emerald-950/20 text-emerald-300" },
  { key: "contacted", label: "Contacted", color: "border-purple-800/60 bg-purple-950/20 text-purple-300" },
  { key: "replied", label: "Replied / Won", color: "border-amber-800/60 bg-amber-950/20 text-amber-300" },
];

export default function CRMHubPage() {
  const [activeTab, setActiveTab] = useState<"pipeline" | "suppression" | "activities">("pipeline");
  const [campaigns, setCampaigns] = useState<CampaignItem[]>([]);
  const [selectedCampaignId, setSelectedCampaignId] = useState<number | null>(null);
  const [pipeline, setPipeline] = useState<PipelineData | null>(null);
  const [suppressions, setSuppressions] = useState<SuppressionItem[]>([]);
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Suppression form state
  const [newEmail, setNewEmail] = useState("");
  const [newDomain, setNewDomain] = useState("");
  const [newReason, setNewReason] = useState("unsubscribed");
  const [suppSearch, setSuppSearch] = useState("");

  // Suppression test state
  const [testEmail, setTestEmail] = useState("");
  const [testResult, setTestResult] = useState<{ is_suppressed: boolean; reason?: string; details?: string } | null>(null);

  // Active lead modal for score view
  const [activeScore, setActiveScore] = useState<LeadScoreData | null>(null);
  const [loadingScore, setLoadingScore] = useState<boolean>(false);

  // Load campaigns
  const loadCampaigns = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/campaigns`);
      if (res.ok) {
        const data = await res.json();
        setCampaigns(data);
        if (data.length > 0 && !selectedCampaignId) {
          setSelectedCampaignId(data[0].id);
        }
      }
    } catch (e) {
      console.error("Failed to load campaigns:", e);
    }
  }, [selectedCampaignId]);

  // Load pipeline
  const loadPipeline = useCallback(async () => {
    if (!selectedCampaignId) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/crm/pipeline?campaign_id=${selectedCampaignId}`);
      if (res.ok) {
        setPipeline(await res.json());
      }
    } catch (e) {
      console.error("Failed to load pipeline:", e);
    } finally {
      setLoading(false);
    }
  }, [selectedCampaignId]);

  // Load suppressions
  const loadSuppressions = useCallback(async () => {
    try {
      const url = suppSearch
        ? `${API_BASE}/api/suppression?search=${encodeURIComponent(suppSearch)}`
        : `${API_BASE}/api/suppression`;
      const res = await fetch(url);
      if (res.ok) {
        setSuppressions(await res.json());
      }
    } catch (e) {
      console.error("Failed to load suppressions:", e);
    }
  }, [suppSearch]);

  // Load activities
  const loadActivities = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/activities?limit=40`);
      if (res.ok) {
        setActivities(await res.json());
      }
    } catch (e) {
      console.error("Failed to load activities:", e);
    }
  }, []);

  useEffect(() => {
    loadCampaigns();
  }, [loadCampaigns]);

  useEffect(() => {
    if (selectedCampaignId) {
      loadPipeline();
    }
  }, [selectedCampaignId, loadPipeline]);

  useEffect(() => {
    if (activeTab === "suppression") {
      loadSuppressions();
    } else if (activeTab === "activities") {
      loadActivities();
    }
  }, [activeTab, loadSuppressions, loadActivities]);

  // Actions
  const handleMoveStage = async (leadId: number, targetStage: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/leads/${leadId}/stage`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ stage: targetStage, notes: `Manual transition to ${targetStage}` }),
      });
      if (res.ok) {
        setStatusMessage(`Lead moved to ${targetStage}!`);
        loadPipeline();
      } else {
        const err = await res.json();
        alert(`Stage transition blocked: ${err.detail || "Validation error"}`);
      }
    } catch {
      alert("Error updating stage.");
    } finally {
      setTimeout(() => setStatusMessage(null), 4000);
    }
  };

  const handleAddSuppression = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newEmail && !newDomain) {
      alert("Please provide an email or domain.");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/api/suppression`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: newEmail || null,
          domain: newDomain || null,
          reason: newReason,
        }),
      });
      if (res.ok) {
        setNewEmail("");
        setNewDomain("");
        setStatusMessage("Suppression rule added successfully!");
        loadSuppressions();
        if (selectedCampaignId) loadPipeline();
      } else {
        const err = await res.json();
        alert(`Failed to add: ${err.detail}`);
      }
    } catch {
      alert("Error adding suppression rule.");
    } finally {
      setTimeout(() => setStatusMessage(null), 4000);
    }
  };

  const handleDeleteSuppression = async (id: number) => {
    if (!confirm("Are you sure you want to remove this suppression rule?")) return;
    try {
      const res = await fetch(`${API_BASE}/api/suppression/${id}`, { method: "DELETE" });
      if (res.ok) {
        setStatusMessage("Suppression rule removed.");
        loadSuppressions();
        if (selectedCampaignId) loadPipeline();
      }
    } catch {
      alert("Error deleting suppression rule.");
    } finally {
      setTimeout(() => setStatusMessage(null), 4000);
    }
  };

  const handleTestSuppression = async () => {
    if (!testEmail) return;
    try {
      const res = await fetch(`${API_BASE}/api/suppression/check?email=${encodeURIComponent(testEmail)}`);
      if (res.ok) {
        setTestResult(await res.json());
      }
    } catch {
      alert("Error testing suppression.");
    }
  };

  const handleInspectScore = async (leadId: number, businessName: string) => {
    setLoadingScore(true);
    try {
      const res = await fetch(`${API_BASE}/api/leads/${leadId}/score`);
      if (res.ok) {
        const data = await res.json();
        setActiveScore({ ...data, business_name: businessName });
      } else {
        alert("No qualification score found for this lead yet.");
      }
    } catch {
      alert("Error loading score.");
    } finally {
      setLoadingScore(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-md bg-purple-500/10 border border-purple-500/20 text-purple-400 text-xs font-mono mb-2">
            <Kanban className="h-3.5 w-3.5" />
            <span>Task 07 — CRM Pipeline & Compliance Gate</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">CRM Pipeline & Suppression Manager</h1>
          <p className="text-xs text-slate-400 mt-1">
            Track leads across sales stages with hard suppression gates to guarantee compliance before outreach.
          </p>
        </div>

        {/* Campaign Selector */}
        {campaigns.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-slate-500">Campaign:</span>
            <select
              value={selectedCampaignId || ""}
              onChange={(e) => setSelectedCampaignId(Number(e.target.value))}
              className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-slate-200 text-xs font-medium focus:outline-none focus:border-blue-500"
            >
              {campaigns.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.city})
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {statusMessage && (
        <div className="p-3 bg-blue-950/80 border border-blue-800/80 rounded-xl text-xs text-blue-200 flex items-center gap-2 font-medium">
          <Sparkles className="h-4 w-4 text-blue-400 shrink-0" />
          <span>{statusMessage}</span>
        </div>
      )}

      {/* Tabs Row */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab("pipeline")}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              activeTab === "pipeline"
                ? "bg-blue-600 text-white"
                : "bg-slate-900 text-slate-400 hover:text-slate-200"
            }`}
          >
            <Kanban className="h-3.5 w-3.5" />
            <span>Kanban Pipeline</span>
          </button>
          <button
            onClick={() => setActiveTab("suppression")}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              activeTab === "suppression"
                ? "bg-purple-600 text-white"
                : "bg-slate-900 text-slate-400 hover:text-slate-200"
            }`}
          >
            <ShieldAlert className="h-3.5 w-3.5" />
            <span>Suppression Blocklist</span>
          </button>
          <button
            onClick={() => setActiveTab("activities")}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              activeTab === "activities"
                ? "bg-slate-700 text-white"
                : "bg-slate-900 text-slate-400 hover:text-slate-200"
            }`}
          >
            <History className="h-3.5 w-3.5" />
            <span>Audit Trail Log</span>
          </button>
        </div>

        {selectedCampaignId && (
          <Link
            href="/email-studio"
            className="inline-flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 font-medium"
          >
            <span>Open Email Studio</span>
            <ArrowRight className="h-3 w-3" />
          </Link>
        )}
      </div>

      {/* TAB 1: KANBAN PIPELINE */}
      {activeTab === "pipeline" && (
        <div className="space-y-4">
          {loading ? (
            <div className="p-16 text-center text-xs text-slate-500 font-mono">Loading sales pipeline...</div>
          ) : !pipeline ? (
            <div className="p-16 text-center text-xs text-slate-500">No pipeline data available.</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3.5 items-start">
              {STAGES.map((col) => {
                const stageLeads = pipeline.stages[col.key] || [];
                return (
                  <div
                    key={col.key}
                    className="flex flex-col bg-slate-900/50 border border-slate-800 rounded-2xl p-3 min-h-[550px] max-h-[800px]"
                  >
                    {/* Column Header */}
                    <div className="flex items-center justify-between pb-2.5 mb-2.5 border-b border-slate-800/80">
                      <div className="flex items-center gap-1.5">
                        <span className={`h-2 w-2 rounded-full ${col.key === "approved" ? "bg-emerald-400" : col.key === "draft_ready" ? "bg-blue-400" : "bg-slate-500"}`} />
                        <h3 className="text-xs font-bold text-slate-200">{col.label}</h3>
                      </div>
                      <span className="text-[11px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                        {stageLeads.length}
                      </span>
                    </div>

                    {/* Leads Container */}
                    <div className="space-y-2.5 overflow-y-auto flex-1 pr-1">
                      {stageLeads.length === 0 ? (
                        <div className="p-6 text-center text-[11px] text-slate-600 font-mono">
                          Empty Stage
                        </div>
                      ) : (
                        stageLeads.map((lead) => (
                          <div
                            key={lead.id}
                            className={`p-3 rounded-xl border bg-slate-950/80 transition-all space-y-2.5 ${
                              lead.is_suppressed
                                ? "border-rose-900/80 bg-rose-950/10"
                                : "border-slate-800/90 hover:border-slate-700"
                            }`}
                          >
                            {/* Card Header: Name & Score */}
                            <div className="flex items-start justify-between gap-1.5">
                              <div className="space-y-0.5">
                                <h4
                                  onClick={() => handleInspectScore(lead.id, lead.business_name)}
                                  className="text-xs font-bold text-slate-100 line-clamp-1 hover:text-blue-400 cursor-pointer"
                                  title="Click to view full 4-quadrant qualification report"
                                >
                                  {lead.business_name}
                                </h4>
                                <div className="text-[10px] text-slate-500 font-mono line-clamp-1">
                                  {lead.industry}
                                </div>
                              </div>

                              {lead.score !== null && lead.score !== undefined && (
                                <span
                                  className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded shrink-0 ${
                                    lead.score >= 75
                                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                      : lead.score >= 50
                                      ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                                      : "bg-slate-800 text-slate-400"
                                  }`}
                                >
                                  {lead.score}/100
                                </span>
                              )}
                            </div>

                            {/* Contact Point */}
                            {lead.primary_contact_name && (
                              <div className="flex items-center gap-1 text-[11px] text-slate-400">
                                <User className="h-3 w-3 text-slate-500 shrink-0" />
                                <span className="line-clamp-1">{lead.primary_contact_name}</span>
                              </div>
                            )}

                            {/* Badges Row: Draft status / Suppression */}
                            <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
                              {lead.is_suppressed && (
                                <span className="inline-flex items-center gap-0.5 px-1.5 py-0.2 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20 font-semibold">
                                  <ShieldAlert className="h-2.5 w-2.5" /> Blocked
                                </span>
                              )}
                              {lead.has_draft && (
                                <span
                                  className={`inline-flex items-center gap-0.5 px-1.5 py-0.2 rounded font-medium ${
                                    lead.draft_status === "approved"
                                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                      : "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                                  }`}
                                >
                                  <Mail className="h-2.5 w-2.5" />
                                  {lead.draft_status === "approved" ? "Draft Approved" : "Draft Ready"}
                                </span>
                              )}
                            </div>

                            {/* Stage Controls Dropdown */}
                            <div className="pt-1.5 border-t border-slate-800/60 flex items-center justify-between">
                              <span className="text-[10px] text-slate-500 font-mono">Move:</span>
                              <select
                                value={col.key}
                                onChange={(e) => handleMoveStage(lead.id, e.target.value)}
                                className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300 text-[10px] focus:outline-none"
                              >
                                {STAGES.map((s) => (
                                  <option key={s.key} value={s.key}>
                                    {s.label}
                                  </option>
                                ))}
                              </select>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: SUPPRESSION & COMPLIANCE */}
      {activeTab === "suppression" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left: Add Suppression Form & Tester (5 cols) */}
          <div className="lg:col-span-5 space-y-6">
            {/* Add Rule Form */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-4">
              <div className="flex items-center gap-2 pb-2 border-b border-slate-800">
                <Plus className="h-4 w-4 text-purple-400" />
                <h3 className="font-bold text-sm text-slate-100">Add Suppression Blocklist Rule</h3>
              </div>
              <form onSubmit={handleAddSuppression} className="space-y-3 text-xs">
                <div>
                  <label className="text-[11px] font-mono text-slate-400">Target Email Address (Optional)</label>
                  <input
                    type="email"
                    placeholder="prospect@company.com"
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    className="w-full mt-1 px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-purple-500"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-mono text-slate-400">Target Domain (Wildcard Block)</label>
                  <input
                    type="text"
                    placeholder="competitor.com or @agency.io"
                    value={newDomain}
                    onChange={(e) => setNewDomain(e.target.value)}
                    className="w-full mt-1 px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-purple-500"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-mono text-slate-400">Block Reason</label>
                  <select
                    value={newReason}
                    onChange={(e) => setNewReason(e.target.value)}
                    className="w-full mt-1 px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-purple-500"
                  >
                    <option value="unsubscribed">Unsubscribed / Opted-out</option>
                    <option value="bounced">Bounced / Bad Address</option>
                    <option value="competitor">Competitor / Internal</option>
                    <option value="manual_block">Manual Operator Block</option>
                  </select>
                </div>
                <button
                  type="submit"
                  className="w-full py-2.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-semibold transition-colors shadow-lg shadow-purple-600/20"
                >
                  Add to Global Blocklist
                </button>
              </form>
            </div>

            {/* Live Suppression Tester */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-3">
              <div className="flex items-center gap-2 pb-2 border-b border-slate-800">
                <ShieldCheck className="h-4 w-4 text-emerald-400" />
                <h3 className="font-bold text-sm text-slate-100">Live Safety Verification Gate</h3>
              </div>
              <p className="text-xs text-slate-400">
                Test any prospect email or domain to verify if outreach dispatch will be hard-blocked.
              </p>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  placeholder="name@domain.com or clinic.com"
                  value={testEmail}
                  onChange={(e) => setTestEmail(e.target.value)}
                  className="flex-1 px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                />
                <button
                  onClick={handleTestSuppression}
                  className="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200"
                >
                  Verify
                </button>
              </div>

              {testResult && (
                <div
                  className={`p-3 rounded-xl border text-xs space-y-1 font-mono ${
                    testResult.is_suppressed
                      ? "bg-rose-950/40 border-rose-800 text-rose-300"
                      : "bg-emerald-950/40 border-emerald-800 text-emerald-300"
                  }`}
                >
                  <div className="font-bold flex items-center gap-1.5">
                    {testResult.is_suppressed ? (
                      <>
                        <ShieldAlert className="h-4 w-4 text-rose-400" />
                        <span>HARD BLOCK ENFORCED</span>
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                        <span>VERIFIED CLEAR FOR OUTREACH</span>
                      </>
                    )}
                  </div>
                  {testResult.details && <p className="text-[11px] opacity-90">{testResult.details}</p>}
                </div>
              )}
            </div>
          </div>

          {/* Right: Active Suppression List Table (7 cols) */}
          <div className="lg:col-span-7 bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-800">
              <h3 className="font-bold text-sm text-slate-100">
                Active Suppression Entries ({suppressions.length})
              </h3>
              <div className="relative">
                <Search className="h-3.5 w-3.5 text-slate-500 absolute left-2.5 top-2.5" />
                <input
                  type="text"
                  placeholder="Filter domain or email..."
                  value={suppSearch}
                  onChange={(e) => setSuppSearch(e.target.value)}
                  className="pl-8 pr-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-purple-500"
                />
              </div>
            </div>

            <div className="overflow-x-auto rounded-xl border border-slate-800/80 bg-slate-950/60">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900 text-slate-400 font-mono text-[11px] uppercase tracking-wider border-b border-slate-800">
                  <tr>
                    <th className="py-2.5 px-3">Type</th>
                    <th className="py-2.5 px-3">Rule Target</th>
                    <th className="py-2.5 px-3">Reason</th>
                    <th className="py-2.5 px-3">Added</th>
                    <th className="py-2.5 px-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-sans">
                  {suppressions.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-slate-500 font-mono">
                        No active suppression rules found.
                      </td>
                    </tr>
                  ) : (
                    suppressions.map((s) => (
                      <tr key={s.id} className="hover:bg-slate-800/30 transition-colors">
                        <td className="py-2.5 px-3 font-mono text-[11px]">
                          {s.email ? (
                            <span className="px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                              Email
                            </span>
                          ) : (
                            <span className="px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20">
                              Domain
                            </span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 font-semibold text-slate-200">
                          {s.email || `@${s.domain}`}
                        </td>
                        <td className="py-2.5 px-3 text-slate-400 capitalize">
                          {s.reason.replace("_", " ")}
                        </td>
                        <td className="py-2.5 px-3 text-slate-500 font-mono text-[11px]">
                          {new Date(s.added_at).toLocaleDateString()}
                        </td>
                        <td className="py-2.5 px-3 text-right">
                          <button
                            onClick={() => handleDeleteSuppression(s.id)}
                            className="p-1 rounded hover:bg-rose-950 text-slate-500 hover:text-rose-400 transition-colors"
                            title="Remove suppression rule"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: AUDIT TRAIL LOG */}
      {activeTab === "activities" && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <History className="h-4 w-4 text-blue-400" />
              <h3 className="font-bold text-sm text-slate-100">Audit Trail Stream ({activities.length})</h3>
            </div>
            <button
              onClick={loadActivities}
              className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-white"
            >
              <RefreshCw className="h-3 w-3" />
              <span>Refresh</span>
            </button>
          </div>

          <div className="space-y-2 max-h-[700px] overflow-y-auto pr-1">
            {activities.length === 0 ? (
              <div className="p-12 text-center text-xs text-slate-500 font-mono">No logged activity yet.</div>
            ) : (
              activities.map((act) => (
                <div
                  key={act.id}
                  className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80 flex items-start justify-between gap-3 text-xs"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[11px] px-1.5 py-0.5 rounded bg-slate-800 text-blue-400 uppercase font-semibold">
                        {act.action.replace("_", " ")}
                      </span>
                      <span className="text-slate-400">
                        {act.entity_type} #{act.entity_id}
                      </span>
                    </div>
                    {act.details && Object.keys(act.details).length > 0 && (
                      <p className="text-slate-300 font-mono text-[11px]">
                        {JSON.stringify(act.details)}
                      </p>
                    )}
                  </div>

                  <span className="text-[11px] text-slate-500 font-mono shrink-0 flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {new Date(act.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Modal for 4-Quadrant Score Report */}
      {activeScore && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
          <div className="relative w-full max-w-3xl max-h-[90vh] overflow-y-auto bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl p-6 space-y-4">
            <button
              onClick={() => setActiveScore(null)}
              className="absolute top-4 right-4 p-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
            >
              <span className="text-slate-400 hover:text-white font-mono text-sm px-1.5">✕</span>
            </button>
            <ScoreCard score={activeScore} />
          </div>
        </div>
      )}
    </div>
  );
}
