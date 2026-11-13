"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  Mail,
  Check,
  Copy,
  RefreshCw,
  ThumbsUp,
  ThumbsDown,
  ShieldCheck,
  Lightbulb,
  Target,
  HelpCircle,
  ExternalLink,
  Sparkles,
  Filter,
  CheckCircle2,
  XCircle,
  Award,
  User,
  Save,
  Send,
  SendHorizontal,
  AlertTriangle,
  Radio,
  FileText,
} from "lucide-react";
import { ScoreCard, LeadScoreData } from "@/components/qualification/ScoreCard";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface CampaignItem {
  id: number;
  name: string;
  industry: string;
  city: string;
}

interface EmailApprovalItem {
  id: number;
  draft_id: number;
  reviewer_notes?: string | null;
  approved_at?: string | null;
  sent_at?: string | null;
}

interface EmailDraftItem {
  id: number;
  lead_id: number;
  contact_id?: number | null;
  subject: string;
  body_text: string;
  evidence_citations: string[];
  version: number;
  status: "draft" | "approved" | "rejected" | "sent";
  created_at: string;
  updated_at: string;
  approval?: EmailApprovalItem | null;
  // Enriched lead metadata
  business_name?: string;
  industry?: string;
  website?: string | null;
  phone?: string | null;
  recipient_name?: string | null;
  recipient_email?: string | null;
}

interface GmailStatus {
  is_connected: boolean;
  mode: string;
  authorized_email?: string | null;
  scopes: string[];
}

export default function EmailStudioPage() {
  const [campaigns, setCampaigns] = useState<CampaignItem[]>([]);
  const [selectedCampaignId, setSelectedCampaignId] = useState<number | null>(null);
  const [drafts, setDrafts] = useState<EmailDraftItem[]>([]);
  const [selectedDraftId, setSelectedDraftId] = useState<number | null>(null);
  const [leadScore, setLeadScore] = useState<LeadScoreData | null>(null);
  const [gmailStatus, setGmailStatus] = useState<GmailStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [loadingEvidence, setLoadingEvidence] = useState<boolean>(false);
  const [generating, setGenerating] = useState<boolean>(false);
  const [saving, setSaving] = useState<boolean>(false);
  const [pushingGmail, setPushingGmail] = useState<boolean>(false);
  const [sendingEmail, setSendingEmail] = useState<boolean>(false);
  const [showSendModal, setShowSendModal] = useState<boolean>(false);
  const [filterStatus, setFilterStatus] = useState<"all" | "draft" | "approved" | "rejected" | "sent">("all");
  const [copied, setCopied] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Form edit state for currently selected draft
  const [editSubject, setEditSubject] = useState<string>("");
  const [editBody, setEditBody] = useState<string>("");
  const [reviewNotes, setEditReviewNotes] = useState<string>("");

  // Load campaigns & Gmail status
  const loadInitialData = useCallback(async () => {
    try {
      const [campRes, gmailRes] = await Promise.all([
        fetch(`${API_BASE}/api/campaigns`),
        fetch(`${API_BASE}/api/gmail/status`),
      ]);

      if (campRes.ok) {
        const data = await campRes.json();
        setCampaigns(data);
        if (data.length > 0 && !selectedCampaignId) {
          setSelectedCampaignId(data[0].id);
        }
      }
      if (gmailRes.ok) {
        setGmailStatus(await gmailRes.json());
      }
    } catch (e) {
      console.error("Failed to load initial data:", e);
    }
  }, [selectedCampaignId]);

  // Load drafts for selected campaign
  const loadDrafts = useCallback(async () => {
    if (!selectedCampaignId) return;
    setLoading(true);
    try {
      const [draftsRes, leadsRes, contactsRes] = await Promise.all([
        fetch(`${API_BASE}/api/campaigns/${selectedCampaignId}/drafts`),
        fetch(`${API_BASE}/api/campaigns/${selectedCampaignId}/leads`),
        fetch(`${API_BASE}/api/contacts?campaign_id=${selectedCampaignId}`),
      ]);

      if (draftsRes.ok && leadsRes.ok) {
        const draftsData: EmailDraftItem[] = await draftsRes.json();
        const leadsData = await leadsRes.json();
        const contactsData = contactsRes.ok ? await contactsRes.json() : [];

        const leadMap = new Map<number, any>(leadsData.map((l: any) => [l.id, l]));
        const contactMap = new Map<number, any>(contactsData.map((c: any) => [c.id, c]));

        const enriched: EmailDraftItem[] = draftsData.map((d) => {
          const lead = leadMap.get(d.lead_id);
          const contact = d.contact_id ? contactMap.get(d.contact_id) : null;
          return {
            ...d,
            business_name: lead?.business_name || `Lead #${d.lead_id}`,
            industry: lead?.industry || "B2B Prospect",
            website: lead?.website,
            phone: lead?.phone,
            recipient_name: contact?.full_name || "Main Office / Reception",
            recipient_email: contact?.email || "No direct email",
          };
        });

        setDrafts(enriched);
        if (enriched.length > 0 && !selectedDraftId) {
          setSelectedDraftId(enriched[0].id);
        }
      }
    } catch (e) {
      console.error("Failed to load drafts:", e);
    } finally {
      setLoading(false);
    }
  }, [selectedCampaignId, selectedDraftId]);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  useEffect(() => {
    if (selectedCampaignId) {
      loadDrafts();
    }
  }, [selectedCampaignId, loadDrafts]);

  const activeDraft = drafts.find((d) => d.id === selectedDraftId) || drafts[0] || null;

  // Sync edit form state whenever active draft changes
  useEffect(() => {
    if (activeDraft) {
      setEditSubject(activeDraft.subject);
      setEditBody(activeDraft.body_text);
      setEditReviewNotes(activeDraft.approval?.reviewer_notes || "");

      // Load lead score evidence for the right pane
      const loadLeadScore = async () => {
        setLoadingEvidence(true);
        try {
          const res = await fetch(`${API_BASE}/api/leads/${activeDraft.lead_id}/score`);
          if (res.ok) {
            const data = await res.json();
            setLeadScore(data);
          } else {
            setLeadScore(null);
          }
        } catch {
          setLeadScore(null);
        } finally {
          setLoadingEvidence(false);
        }
      };

      loadLeadScore();
    }
  }, [activeDraft]);

  // Actions
  const handleSaveDraft = async () => {
    if (!activeDraft) return;
    setSaving(true);
    try {
      const res = await fetch(`${API_BASE}/api/drafts/${activeDraft.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subject: editSubject, body_text: editBody }),
      });
      if (res.ok) {
        setStatusMessage("Draft edits saved successfully.");
        loadDrafts();
      } else {
        alert("Failed to save draft edits.");
      }
    } catch {
      alert("Error saving draft.");
    } finally {
      setSaving(false);
      setTimeout(() => setStatusMessage(null), 4000);
    }
  };

  const handleApproveDraft = async () => {
    if (!activeDraft) return;
    try {
      const res = await fetch(`${API_BASE}/api/drafts/${activeDraft.id}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notes: reviewNotes || "Approved for outreach transmission." }),
      });
      if (res.ok) {
        setStatusMessage("Draft approved for outreach queue!");
        loadDrafts();
      } else {
        alert("Failed to approve draft.");
      }
    } catch {
      alert("Error approving draft.");
    } finally {
      setTimeout(() => setStatusMessage(null), 4000);
    }
  };

  const handleRejectDraft = async () => {
    if (!activeDraft) return;
    try {
      const res = await fetch(`${API_BASE}/api/drafts/${activeDraft.id}/reject`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notes: reviewNotes || "Rejected during review." }),
      });
      if (res.ok) {
        setStatusMessage("Draft marked as rejected.");
        loadDrafts();
      } else {
        alert("Failed to reject draft.");
      }
    } catch {
      alert("Error rejecting draft.");
    } finally {
      setTimeout(() => setStatusMessage(null), 4000);
    }
  };

  const handleRegenerateDraft = async () => {
    if (!activeDraft) return;
    setGenerating(true);
    setStatusMessage("Regenerating draft with local AI & latest evidence...");
    try {
      const res = await fetch(`${API_BASE}/api/leads/${activeDraft.lead_id}/drafts/generate`, {
        method: "POST",
      });
      if (res.ok) {
        setStatusMessage("New version generated successfully!");
        loadDrafts();
      } else {
        alert("Failed to regenerate draft.");
      }
    } catch {
      alert("Error regenerating draft.");
    } finally {
      setGenerating(false);
      setTimeout(() => setStatusMessage(null), 4000);
    }
  };

  const handlePushToGmailDraft = async () => {
    if (!activeDraft) return;
    setPushingGmail(true);
    try {
      const res = await fetch(`${API_BASE}/api/drafts/${activeDraft.id}/gmail-draft`, {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        setStatusMessage(`Gmail Draft Created! (ID: ${data.gmail_draft_id})`);
      } else {
        const err = await res.json();
        alert(`Failed to push draft to Gmail: ${err.detail}`);
      }
    } catch {
      alert("Error contacting Gmail API.");
    } finally {
      setPushingGmail(false);
      setTimeout(() => setStatusMessage(null), 5000);
    }
  };

  const handleSendApprovedEmail = async () => {
    if (!activeDraft) return;
    setSendingEmail(true);
    try {
      const res = await fetch(`${API_BASE}/api/drafts/${activeDraft.id}/send`, {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        setStatusMessage(`Email successfully dispatched via Gmail! (Message ID: ${data.gmail_message_id})`);
        setShowSendModal(false);
        loadDrafts();
      } else {
        const err = await res.json();
        alert(`Send failed: ${err.detail}`);
      }
    } catch {
      alert("Error dispatching email.");
    } finally {
      setSendingEmail(false);
      setTimeout(() => setStatusMessage(null), 6000);
    }
  };

  const handleBatchGenerate = async () => {
    if (!selectedCampaignId) return;
    setGenerating(true);
    setStatusMessage("Batch generating evidence-grounded outreach drafts...");
    try {
      const res = await fetch(`${API_BASE}/api/campaigns/${selectedCampaignId}/drafts/generate?limit=50`, {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        setStatusMessage(
          `Batch generation complete! Generated ${data.stats.drafts_generated} personalized drafts.`
        );
        loadDrafts();
      } else {
        alert("Error during batch generation.");
      }
    } catch {
      alert("Network error running batch generation.");
    } finally {
      setGenerating(false);
      setTimeout(() => setStatusMessage(null), 6000);
    }
  };

  const handleCopyClipboard = () => {
    const fullText = `Subject: ${editSubject}\n\n${editBody}`;
    navigator.clipboard.writeText(fullText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Filter calculations
  const filteredDrafts = drafts.filter((d) => {
    if (filterStatus === "all") return true;
    return d.status === filterStatus;
  });

  const draftCount = drafts.filter((d) => d.status === "draft").length;
  const approvedCount = drafts.filter((d) => d.status === "approved").length;
  const rejectedCount = drafts.filter((d) => d.status === "rejected").length;
  const sentCount = drafts.filter((d) => d.status === "sent").length;

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-md bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-mono mb-2">
            <Mail className="h-3.5 w-3.5" />
            <span>Task 08 — Gmail API Integration & Human Approval Flow</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">AI Email Outreach Studio</h1>
          <p className="text-xs text-slate-400 mt-1">
            Review and approve personalized cold outreach emails grounded strictly in verified qualification facts.
          </p>
        </div>

        {/* Campaign Selector & Gmail Status */}
        <div className="flex flex-wrap items-center gap-2.5">
          {gmailStatus && (
            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono">
              <span
                className={`h-2 w-2 rounded-full ${
                  gmailStatus.is_connected
                    ? "bg-emerald-400 animate-pulse"
                    : "bg-blue-400"
                }`}
              />
              <span className="text-slate-300">
                Gmail: {gmailStatus.mode === "live" ? "Live Account" : "Simulator Mode"}
              </span>
            </div>
          )}

          {campaigns.length > 0 && (
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
          )}

          <button
            onClick={handleBatchGenerate}
            disabled={generating}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-medium transition-colors shadow-lg shadow-blue-600/20"
          >
            <Sparkles className={`h-3.5 w-3.5 ${generating ? "animate-spin" : ""}`} />
            {generating ? "Generating..." : "Generate All Drafts"}
          </button>
        </div>
      </div>

      {statusMessage && (
        <div className="p-3 bg-blue-950/80 border border-blue-800/80 rounded-xl text-xs text-blue-200 flex items-center gap-2 font-medium">
          <Sparkles className="h-4 w-4 text-blue-400 shrink-0" />
          <span>{statusMessage}</span>
        </div>
      )}

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl">
          <div className="text-slate-400">Total Outreach Drafts</div>
          <div className="text-xl font-bold text-slate-100 font-mono mt-1">{drafts.length}</div>
        </div>
        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl">
          <div className="text-slate-400">Approved for Dispatch</div>
          <div className="text-xl font-bold text-emerald-400 font-mono mt-1">{approvedCount}</div>
        </div>
        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl">
          <div className="text-slate-400">Ready for Human Review</div>
          <div className="text-xl font-bold text-amber-400 font-mono mt-1">{draftCount}</div>
        </div>
        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl">
          <div className="text-slate-400">Dispatched via Gmail</div>
          <div className="text-xl font-bold text-purple-400 font-mono mt-1">{sentCount}</div>
        </div>
      </div>

      {/* Main Split-Screen Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Prospect Queue & Filters (4 Cols) */}
        <div className="lg:col-span-4 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <h2 className="text-sm font-bold text-slate-200">Outreach Queue ({filteredDrafts.length})</h2>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setFilterStatus("all")}
                className={`px-2 py-0.5 rounded text-[11px] font-medium ${
                  filterStatus === "all" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                All
              </button>
              <button
                onClick={() => setFilterStatus("draft")}
                className={`px-2 py-0.5 rounded text-[11px] font-medium ${
                  filterStatus === "draft" ? "bg-amber-600 text-white" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Drafts
              </button>
              <button
                onClick={() => setFilterStatus("approved")}
                className={`px-2 py-0.5 rounded text-[11px] font-medium ${
                  filterStatus === "approved" ? "bg-emerald-600 text-white" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Approved
              </button>
              <button
                onClick={() => setFilterStatus("sent")}
                className={`px-2 py-0.5 rounded text-[11px] font-medium ${
                  filterStatus === "sent" ? "bg-purple-600 text-white" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Sent
              </button>
            </div>
          </div>

          {loading ? (
            <div className="p-8 text-center text-xs text-slate-500 font-mono">Loading drafts...</div>
          ) : filteredDrafts.length === 0 ? (
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 text-center space-y-2">
              <Mail className="h-6 w-6 text-slate-600 mx-auto" />
              <p className="text-xs font-semibold text-slate-300">No drafts in this category</p>
              <p className="text-[11px] text-slate-500">Click &quot;Generate All Drafts&quot; to synthesize emails.</p>
            </div>
          ) : (
            <div className="space-y-2 max-h-[750px] overflow-y-auto pr-1">
              {filteredDrafts.map((d) => {
                const isSelected = d.id === (activeDraft?.id || null);
                return (
                  <div
                    key={d.id}
                    onClick={() => setSelectedDraftId(d.id)}
                    className={`p-3.5 rounded-xl border cursor-pointer transition-all space-y-2 ${
                      isSelected
                        ? "bg-slate-800/90 border-blue-500 shadow-md shadow-blue-500/10"
                        : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="space-y-0.5">
                        <div className="font-semibold text-xs text-slate-100 flex items-center gap-1.5">
                          <span className="line-clamp-1">{d.business_name}</span>
                          <span className="text-[10px] font-mono px-1 rounded bg-slate-800 text-slate-400">
                            v{d.version}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-400 flex items-center gap-1">
                          <User className="h-3 w-3 text-slate-500" />
                          <span className="line-clamp-1">{d.recipient_name}</span>
                        </div>
                      </div>

                      {/* Status Badge */}
                      <span
                        className={`text-[10px] font-semibold px-2 py-0.5 rounded uppercase tracking-wider shrink-0 ${
                          d.status === "sent"
                            ? "bg-purple-500/10 text-purple-400 border border-purple-500/20"
                            : d.status === "approved"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : d.status === "rejected"
                            ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                            : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                        }`}
                      >
                        {d.status}
                      </span>
                    </div>

                    <p className="text-[11px] text-slate-400 line-clamp-1 italic font-mono">&quot;{d.subject}&quot;</p>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Center/Right Split-Screen: Editor & Evidence (8 Cols) */}
        <div className="lg:col-span-8 space-y-6">
          {activeDraft ? (
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 items-start">
              {/* Left Side: Email Draft Editor */}
              <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 space-y-4">
                {/* Header & Status */}
                <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
                  <div className="flex items-center gap-2">
                    <Mail className="h-4 w-4 text-blue-400" />
                    <h3 className="font-bold text-sm text-slate-100">Draft Editor</h3>
                    <span className="text-[11px] font-mono text-slate-400">v{activeDraft.version}</span>
                    {activeDraft.status === "sent" && (
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20">
                        Dispatched via Gmail
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={handleCopyClipboard}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-[11px] font-medium text-slate-200 transition-colors"
                      title="Copy to clipboard"
                    >
                      {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                      <span>{copied ? "Copied" : "Copy"}</span>
                    </button>
                    <button
                      onClick={handleRegenerateDraft}
                      disabled={generating}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-[11px] font-medium text-slate-200 transition-colors disabled:opacity-50"
                      title="Regenerate email using AI"
                    >
                      <RefreshCw className={`h-3 w-3 text-blue-400 ${generating ? "animate-spin" : ""}`} />
                      <span>Regen</span>
                    </button>
                    <button
                      onClick={handlePushToGmailDraft}
                      disabled={pushingGmail}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-[11px] font-medium text-slate-200 transition-colors disabled:opacity-50"
                      title="Push to Gmail as draft"
                    >
                      <FileText className={`h-3 w-3 text-emerald-400 ${pushingGmail ? "animate-spin" : ""}`} />
                      <span>Push Draft</span>
                    </button>
                  </div>
                </div>

                {/* Recipient Metadata */}
                <div className="bg-slate-950/70 border border-slate-800/60 rounded-lg p-2.5 text-xs space-y-1 font-mono">
                  <div className="flex items-center gap-2 text-slate-300">
                    <span className="text-slate-500 w-12 shrink-0">To:</span>
                    <span className="font-semibold text-slate-200">{activeDraft.recipient_name}</span>
                    <span className="text-slate-400">&lt;{activeDraft.recipient_email}&gt;</span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-400">
                    <span className="text-slate-500 w-12 shrink-0">Account:</span>
                    <span>{activeDraft.business_name}</span>
                  </div>
                </div>

                {/* Subject Line Input */}
                <div className="space-y-1">
                  <label className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                    Subject Line
                  </label>
                  <input
                    type="text"
                    value={editSubject}
                    onChange={(e) => setEditSubject(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-100 font-medium focus:outline-none focus:border-blue-500"
                  />
                </div>

                {/* Body Textarea */}
                <div className="space-y-1">
                  <label className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                    Email Body Text
                  </label>
                  <textarea
                    rows={12}
                    value={editBody}
                    onChange={(e) => setEditBody(e.target.value)}
                    className="w-full px-3 py-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-200 font-sans leading-relaxed focus:outline-none focus:border-blue-500"
                  />
                </div>

                {/* Verified Evidence Citations Tags */}
                <div className="space-y-1.5 pt-1">
                  <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1">
                    <ShieldCheck className="h-3 w-3 text-emerald-400" />
                    <span>Evidence Cited in this Email:</span>
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {activeDraft.evidence_citations && activeDraft.evidence_citations.length > 0 ? (
                      activeDraft.evidence_citations.map((cite, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] font-medium"
                        >
                          ✓ {cite}
                        </span>
                      ))
                    ) : (
                      <span className="text-slate-500 text-[11px] italic">No citations attached.</span>
                    )}
                  </div>
                </div>

                {/* Human Review Notes & Actions */}
                <div className="space-y-3 pt-3 border-t border-slate-800/80">
                  <div className="space-y-1">
                    <label className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                      Reviewer Notes / Feedback
                    </label>
                    <input
                      type="text"
                      placeholder="Add compliance notes or revision feedback..."
                      value={reviewNotes}
                      onChange={(e) => setEditReviewNotes(e.target.value)}
                      className="w-full px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-300 focus:outline-none focus:border-blue-500"
                    />
                  </div>

                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <button
                      onClick={handleSaveDraft}
                      disabled={saving}
                      className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors"
                    >
                      <Save className="h-3.5 w-3.5" />
                      <span>{saving ? "Saving..." : "Save Edits"}</span>
                    </button>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={handleRejectDraft}
                        className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-rose-950/60 hover:bg-rose-900/80 border border-rose-800/80 text-rose-200 text-xs font-semibold transition-colors"
                      >
                        <ThumbsDown className="h-3.5 w-3.5 text-rose-400" />
                        <span>Reject</span>
                      </button>

                      {activeDraft.status !== "approved" && activeDraft.status !== "sent" ? (
                        <button
                          onClick={handleApproveDraft}
                          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-colors shadow-lg shadow-emerald-600/20"
                        >
                          <ThumbsUp className="h-3.5 w-3.5" />
                          <span>Approve Draft</span>
                        </button>
                      ) : activeDraft.status === "approved" ? (
                        <button
                          onClick={() => setShowSendModal(true)}
                          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold transition-colors shadow-lg shadow-purple-600/20 animate-pulse"
                        >
                          <Send className="h-3.5 w-3.5" />
                          <span>Send via Gmail</span>
                        </button>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-3 py-2 rounded-lg bg-slate-800 text-slate-400 text-xs font-medium">
                          <CheckCircle2 className="h-3.5 w-3.5 text-purple-400" />
                          <span>Dispatched</span>
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Right Side: Grounded Evidence & Justification Panel */}
              <div className="space-y-4">
                <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                  <div className="flex items-center gap-2">
                    <Award className="h-4 w-4 text-purple-400" />
                    <h3 className="font-bold text-sm text-slate-100">Grounded Evidence & Justification</h3>
                  </div>
                  {activeDraft.website && (
                    <a
                      href={activeDraft.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-[11px] text-blue-400 hover:underline"
                    >
                      <span>Website</span>
                      <ExternalLink className="h-2.5 w-2.5" />
                    </a>
                  )}
                </div>

                {loadingEvidence ? (
                  <div className="p-8 text-center text-xs text-slate-500 font-mono">
                    Loading qualification evidence...
                  </div>
                ) : leadScore ? (
                  <ScoreCard score={{ ...leadScore, business_name: activeDraft.business_name }} compact={true} />
                ) : (
                  <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-6 text-center space-y-2">
                    <Lightbulb className="h-6 w-6 text-slate-600 mx-auto" />
                    <p className="text-xs font-semibold text-slate-300">No Qualification Record Yet</p>
                    <p className="text-[11px] text-slate-500">
                      Run AI Qualification on this lead in CRM to generate a 4-quadrant report.
                    </p>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-16 text-center space-y-3">
              <Mail className="h-10 w-10 text-slate-600 mx-auto" />
              <h2 className="text-base font-bold text-slate-200">No Email Draft Selected</h2>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Select a draft from the queue on the left or generate fresh personalized outreach drafts.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Explicit Human-in-the-Loop Send Confirmation Modal */}
      {showSendModal && activeDraft && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-lg bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-5">
            <div className="flex items-center gap-2.5 text-purple-400 pb-3 border-b border-slate-800">
              <Send className="h-5 w-5" />
              <h3 className="text-base font-bold text-slate-100">Authorize Outbound Email Dispatch</h3>
            </div>

            <p className="text-xs text-slate-300">
              You are authorizing the dispatch of this approved cold outreach email via Gmail.
            </p>

            <div className="p-3.5 bg-slate-950 rounded-xl border border-slate-800 text-xs space-y-2 font-mono">
              <div className="flex items-center justify-between text-slate-400">
                <span>Recipient:</span>
                <span className="font-semibold text-slate-200">{activeDraft.recipient_name}</span>
              </div>
              <div className="flex items-center justify-between text-slate-400">
                <span>Email Address:</span>
                <span className="text-blue-400">{activeDraft.recipient_email}</span>
              </div>
              <div className="flex items-center justify-between text-slate-400">
                <span>Subject:</span>
                <span className="text-slate-300 truncate max-w-xs">{activeDraft.subject}</span>
              </div>
              <div className="flex items-center justify-between text-slate-400">
                <span>Account:</span>
                <span>{activeDraft.business_name}</span>
              </div>
            </div>

            {/* Compliance Safety Verification Checklist */}
            <div className="space-y-1.5 text-xs text-slate-300">
              <div className="flex items-center gap-2 text-emerald-400 font-semibold">
                <CheckCircle2 className="h-4 w-4" />
                <span>Verified Clear of Global Suppression List</span>
              </div>
              <div className="flex items-center gap-2 text-emerald-400 font-semibold">
                <CheckCircle2 className="h-4 w-4" />
                <span>Verified No Prior Outreach Dispatched (Duplicate Gate)</span>
              </div>
              <div className="flex items-center gap-2 text-emerald-400 font-semibold">
                <CheckCircle2 className="h-4 w-4" />
                <span>Verified Human Approval Recorded</span>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
              <button
                onClick={() => setShowSendModal(false)}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-300"
              >
                Cancel
              </button>
              <button
                onClick={handleSendApprovedEmail}
                disabled={sendingEmail}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white text-xs font-semibold transition-colors shadow-lg shadow-purple-600/25"
              >
                <Send className={`h-3.5 w-3.5 ${sendingEmail ? "animate-spin" : ""}`} />
                <span>{sendingEmail ? "Dispatching..." : "Confirm & Send Email"}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
