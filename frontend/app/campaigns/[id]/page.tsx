"use client";

import React, { useState, useEffect, useCallback, use } from "react";
import Link from "next/link";
import { ArrowLeft, Play, Globe, Phone, MapPin, Target, Sparkles, Filter, BookOpen, Users, Award } from "lucide-react";
import { LeadTable, LeadItem } from "@/components/campaigns/LeadTable";
import { CampaignData } from "@/components/campaigns/CampaignCard";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function CampaignDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const resolvedParams = use(params);
  const campaignId = resolvedParams.id;

  const [campaign, setCampaign] = useState<CampaignData | null>(null);
  const [leads, setLeads] = useState<LeadItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [discovering, setDiscovering] = useState<boolean>(false);
  const [researching, setResearching] = useState<boolean>(false);
  const [extractingContacts, setExtractingContacts] = useState<boolean>(false);
  const [qualifying, setQualifying] = useState<boolean>(false);
  const [filterMode, setFilterMode] = useState<"all" | "website" | "phone">("all");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [campRes, leadsRes] = await Promise.all([
        fetch(`${API_BASE}/api/campaigns/${campaignId}`),
        fetch(`${API_BASE}/api/campaigns/${campaignId}/leads`),
      ]);

      if (campRes.ok) {
        setCampaign(await campRes.json());
      }
      if (leadsRes.ok) {
        setLeads(await leadsRes.json());
      }
    } catch (e) {
      console.error("Failed to load campaign data:", e);
    } finally {
      setLoading(false);
    }
  }, [campaignId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleStartDiscovery = async () => {
    setDiscovering(true);
    setStatusMessage("Running OpenStreetMap business discovery...");
    try {
      const res = await fetch(`${API_BASE}/api/campaigns/${campaignId}/discover`, {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        setStatusMessage(
          `Discovery finished! Found ${data.stats.total_found} OSM nodes, added ${data.stats.new_leads_saved} new leads.`
        );
        loadData();
      } else {
        const err = await res.json();
        alert(`Discovery error: ${err.detail || "Failed to query Overpass/Nominatim"}`);
      }
    } catch {
      alert("Error triggering discovery.");
    } finally {
      setDiscovering(false);
      setTimeout(() => setStatusMessage(null), 6000);
    }
  };

  const handleBatchResearch = async () => {
    setResearching(true);
    setStatusMessage("Analyzing prospect websites for booking systems and service evidence...");
    try {
      const res = await fetch(`${API_BASE}/api/campaigns/${campaignId}/research?limit=25`, {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        setStatusMessage(
          `Website research complete! Crawled ${data.stats.successfully_researched} sites, found ${data.stats.booking_systems_detected} booking systems.`
        );
        loadData();
      } else {
        const err = await res.json();
        alert(`Research error: ${err.detail || "Error crawling websites"}`);
      }
    } catch {
      alert("Error triggering website research.");
    } finally {
      setResearching(false);
      setTimeout(() => setStatusMessage(null), 6000);
    }
  };

  const handleBatchExtractContacts = async () => {
    setExtractingContacts(true);
    setStatusMessage("Extracting public business emails, phone lines, and practitioners...");
    try {
      const res = await fetch(`${API_BASE}/api/campaigns/${campaignId}/contacts/extract?limit=25`, {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        setStatusMessage(
          `Contact extraction finished! Found ${data.stats.contacts_found} contacts (${data.stats.emails_found} emails, ${data.stats.practitioners_identified} doctors).`
        );
        loadData();
      } else {
        const err = await res.json();
        alert(`Contact extraction error: ${err.detail || "Error extracting contacts"}`);
      }
    } catch {
      alert("Error triggering contact extraction.");
    } finally {
      setExtractingContacts(false);
      setTimeout(() => setStatusMessage(null), 6000);
    }
  };

  const handleBatchQualify = async () => {
    setQualifying(true);
    setStatusMessage("Scoring leads & synthesizing 4-quadrant qualification reports...");
    try {
      const res = await fetch(`${API_BASE}/api/campaigns/${campaignId}/qualify?limit=50`, {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        setStatusMessage(
          `AI Qualification completed! Qualified ${data.stats.qualified_count} leads (Average Score: ${data.stats.average_score}/100).`
        );
        loadData();
      } else {
        const err = await res.json();
        alert(`Qualification error: ${err.detail || "Error qualifying leads"}`);
      }
    } catch {
      alert("Error triggering qualification.");
    } finally {
      setQualifying(false);
      setTimeout(() => setStatusMessage(null), 6000);
    }
  };

  const filteredLeads = leads.filter((l) => {
    if (filterMode === "website") return Boolean(l.website);
    if (filterMode === "phone") return Boolean(l.phone);
    return true;
  });

  if (loading) {
    return <div className="p-12 text-center text-xs text-slate-500 font-mono">Loading campaign...</div>;
  }

  if (!campaign) {
    return (
      <div className="p-12 text-center text-xs text-slate-400">
        Campaign not found.{" "}
        <Link href="/campaigns" className="text-blue-400 underline">
          Back to campaigns
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Top Breadcrumb & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <Link
            href="/campaigns"
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Campaigns
          </Link>
          <h1 className="text-2xl font-bold text-white tracking-tight">{campaign.name}</h1>
          <div className="flex items-center gap-2 text-xs text-slate-400 font-medium">
            <span className="flex items-center gap-1 text-blue-400">
              <Target className="h-3.5 w-3.5" />
              {campaign.industry}
            </span>
            <span>•</span>
            <span className="flex items-center gap-1">
              <MapPin className="h-3.5 w-3.5 text-slate-500" />
              {campaign.city}
              {campaign.region ? `, ${campaign.region}` : ""} ({campaign.country})
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleBatchQualify}
            disabled={qualifying || leads.length === 0}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white text-xs font-medium transition-colors shadow-lg shadow-purple-600/20"
          >
            <Award className={`h-3.5 w-3.5 ${qualifying ? "animate-spin" : ""}`} />
            {qualifying ? "Scoring..." : "Qualify All Leads"}
          </button>
          <button
            onClick={handleBatchExtractContacts}
            disabled={extractingContacts}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 disabled:opacity-50 text-slate-200 text-xs font-medium transition-colors"
          >
            <Users className={`h-3.5 w-3.5 text-purple-400 ${extractingContacts ? "animate-spin" : ""}`} />
            {extractingContacts ? "Extracting..." : "Extract Contacts"}
          </button>
          <button
            onClick={handleBatchResearch}
            disabled={researching || leads.filter((l) => l.website).length === 0}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 disabled:opacity-50 text-slate-200 text-xs font-medium transition-colors"
          >
            <BookOpen className={`h-3.5 w-3.5 text-blue-400 ${researching ? "animate-spin" : ""}`} />
            {researching ? "Researching..." : "Research Websites"}
          </button>
          <button
            onClick={handleStartDiscovery}
            disabled={discovering}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-medium transition-colors shadow-lg shadow-blue-600/20"
          >
            <Play className={`h-3.5 w-3.5 ${discovering ? "animate-spin" : ""}`} />
            {discovering ? "Discovering..." : "Execute MCP Discovery"}
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
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-xs">
        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl">
          <div className="text-slate-400">Discovered Leads</div>
          <div className="text-xl font-bold text-slate-100 font-mono mt-1">{leads.length}</div>
        </div>
        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl">
          <div className="text-slate-400">With Website</div>
          <div className="text-xl font-bold text-emerald-400 font-mono mt-1">
            {leads.filter((l) => l.website).length}
          </div>
        </div>
        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl">
          <div className="text-slate-400">With Phone</div>
          <div className="text-xl font-bold text-blue-400 font-mono mt-1">
            {leads.filter((l) => l.phone).length}
          </div>
        </div>
        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl">
          <div className="text-slate-400">Researched Sites</div>
          <div className="text-xl font-bold text-cyan-400 font-mono mt-1">
            {leads.filter((l) => l.status === "researched" || l.status === "qualified").length}
          </div>
        </div>
        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl">
          <div className="text-slate-400">AI Qualified</div>
          <div className="text-xl font-bold text-purple-400 font-mono mt-1">
            {leads.filter((l) => l.status === "qualified").length}
          </div>
        </div>
      </div>

      {/* Leads Table Card */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <h2 className="text-base font-bold text-slate-100">
            Discovered Business Records ({filteredLeads.length})
          </h2>

          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-500 flex items-center gap-1 font-mono text-[11px]">
              <Filter className="h-3 w-3" /> Filter:
            </span>
            <button
              onClick={() => setFilterMode("all")}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                filterMode === "all"
                  ? "bg-blue-600 text-white"
                  : "bg-slate-900 text-slate-400 hover:text-slate-200"
              }`}
            >
              All ({leads.length})
            </button>
            <button
              onClick={() => setFilterMode("website")}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                filterMode === "website"
                  ? "bg-blue-600 text-white"
                  : "bg-slate-900 text-slate-400 hover:text-slate-200"
              }`}
            >
              Has Website ({leads.filter((l) => l.website).length})
            </button>
            <button
              onClick={() => setFilterMode("phone")}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                filterMode === "phone"
                  ? "bg-blue-600 text-white"
                  : "bg-slate-900 text-slate-400 hover:text-slate-200"
              }`}
            >
              Has Phone ({leads.filter((l) => l.phone).length})
            </button>
          </div>
        </div>

        <LeadTable leads={filteredLeads} onLeadResearched={loadData} />
      </div>
    </div>
  );
}
