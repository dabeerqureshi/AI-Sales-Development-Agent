"use client";

import React, { useState, useEffect, useCallback } from "react";
import { BookOpen, Sparkles, RefreshCw, Calendar, Globe, AlertCircle, Play } from "lucide-react";
import { ResearchCard, ResearchItem } from "@/components/research/ResearchCard";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface CampaignOption {
  id: number;
  name: string;
  industry: string;
  city: string;
  lead_count: number;
}

interface LeadWithResearch {
  id: number;
  business_name: string;
  industry: string;
  website: string | null;
  status: string;
  research?: ResearchItem;
}

export default function ResearchPage() {
  const [campaigns, setCampaigns] = useState<CampaignOption[]>([]);
  const [selectedCampaignId, setSelectedCampaignId] = useState<string>("");
  const [leadsWithResearch, setLeadsWithResearch] = useState<LeadWithResearch[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [batchResearching, setBatchResearching] = useState<boolean>(false);
  const [notification, setNotification] = useState<string | null>(null);

  const fetchCampaigns = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/campaigns`);
      if (res.ok) {
        const data = await res.json();
        setCampaigns(data);
        if (data.length > 0 && !selectedCampaignId) {
          setSelectedCampaignId(String(data[0].id));
        }
      }
    } catch (e) {
      console.error("Failed to load campaigns:", e);
    } finally {
      setLoading(false);
    }
  }, [selectedCampaignId]);

  const loadResearchForCampaign = useCallback(async (campId: string) => {
    if (!campId) return;
    setLoading(true);
    try {
      const [leadsRes, researchRes] = await Promise.all([
        fetch(`${API_BASE}/api/campaigns/${campId}/leads`),
        fetch(`${API_BASE}/api/campaigns/${campId}/research`),
      ]);

      if (leadsRes.ok && researchRes.ok) {
        const leads = await leadsRes.json();
        const researchRecords: ResearchItem[] = await researchRes.json();

        const researchMap = new Map<number, ResearchItem>();
        researchRecords.forEach((r) => researchMap.set(r.lead_id, r));

        const merged: LeadWithResearch[] = leads
          .filter((l: any) => Boolean(l.website))
          .map((l: any) => ({
            id: l.id,
            business_name: l.business_name,
            industry: l.industry,
            website: l.website,
            status: l.status,
            research: researchMap.get(l.id),
          }));

        setLeadsWithResearch(merged);
      }
    } catch (e) {
      console.error("Failed to load research data:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCampaigns();
  }, [fetchCampaigns]);

  useEffect(() => {
    if (selectedCampaignId) {
      loadResearchForCampaign(selectedCampaignId);
    }
  }, [selectedCampaignId, loadResearchForCampaign]);

  const handleBatchResearch = async () => {
    if (!selectedCampaignId) return;
    setBatchResearching(true);
    setNotification("Autonomous crawler is analyzing prospect websites and booking systems...");
    try {
      const res = await fetch(`${API_BASE}/api/campaigns/${selectedCampaignId}/research?limit=25`, {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        setNotification(
          `Research finished! Successfully crawled ${data.stats.successfully_researched} websites. Found ${data.stats.booking_systems_detected} online booking systems.`
        );
        loadResearchForCampaign(selectedCampaignId);
      } else {
        const err = await res.json();
        alert(`Batch research error: ${err.detail || "Crawler error"}`);
      }
    } catch {
      alert("Network error executing batch research.");
    } finally {
      setBatchResearching(false);
      setTimeout(() => setNotification(null), 6000);
    }
  };

  const researchedCount = leadsWithResearch.filter((l) => Boolean(l.research)).length;
  const bookingFoundCount = leadsWithResearch.filter((l) => l.research?.booking_system_found).length;
  const opportunityCount = researchedCount - bookingFoundCount;

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full bg-blue-950 border border-blue-800 text-[11px] font-semibold text-blue-400 mb-2">
            <BookOpen className="h-3 w-3" />
            Milestone 3 Active
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Website Research Engine</h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Autonomous web extraction using HTTPX, Trafilatura, and BeautifulSoup. Identifies booking systems, treatments, and operational evidence.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => loadResearchForCampaign(selectedCampaignId)}
            disabled={loading || batchResearching}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-xs text-slate-300 font-medium transition-colors"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <button
            onClick={handleBatchResearch}
            disabled={batchResearching || leadsWithResearch.length === 0}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-medium transition-colors shadow-lg shadow-blue-600/20"
          >
            <Play className={`h-3.5 w-3.5 ${batchResearching ? "animate-spin" : ""}`} />
            {batchResearching ? "Crawling Websites..." : "Research All Campaign Sites"}
          </button>
        </div>
      </div>

      {notification && (
        <div className="p-3 bg-blue-950/80 border border-blue-800/80 rounded-xl text-xs text-blue-200 flex items-center gap-2 font-medium">
          <Sparkles className="h-4 w-4 text-blue-400 shrink-0" />
          <span>{notification}</span>
        </div>
      )}

      {/* Campaign Selector & Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="md:col-span-1 bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-2 flex flex-col justify-between">
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-300">Select Campaign</label>
            <select
              value={selectedCampaignId}
              onChange={(e) => setSelectedCampaignId(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
            >
              {campaigns.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.lead_count} leads)
                </option>
              ))}
            </select>
          </div>
          <div className="text-[11px] text-slate-500 font-mono">
            Targeting businesses with active online websites
          </div>
        </div>

        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400">
            <Globe className="h-5 w-5" />
          </div>
          <div>
            <div className="text-xs text-slate-400">Websites Ready</div>
            <div className="text-xl font-bold text-slate-100 font-mono">
              {researchedCount} / {leadsWithResearch.length}
            </div>
          </div>
        </div>

        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
            <Calendar className="h-5 w-5" />
          </div>
          <div>
            <div className="text-xs text-slate-400">Booking Tool Detected</div>
            <div className="text-xl font-bold text-emerald-400 font-mono">
              {bookingFoundCount}
            </div>
          </div>
        </div>

        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400">
            <AlertCircle className="h-5 w-5" />
          </div>
          <div>
            <div className="text-xs text-slate-400">No Booking (Prime Offer)</div>
            <div className="text-xl font-bold text-amber-400 font-mono">
              {opportunityCount}
            </div>
          </div>
        </div>
      </div>

      {/* Research Records Grid */}
      <div className="space-y-4">
        <h2 className="text-base font-bold text-slate-100 flex items-center justify-between">
          <span>Website Intelligence & Grounded Evidence ({leadsWithResearch.length})</span>
        </h2>

        {loading ? (
          <div className="p-12 text-center text-xs text-slate-500 font-mono">
            Loading extracted intelligence...
          </div>
        ) : leadsWithResearch.length === 0 ? (
          <div className="p-12 text-center rounded-xl bg-slate-900/40 border border-slate-800 space-y-3">
            <Globe className="h-8 w-8 text-slate-600 mx-auto" />
            <h3 className="text-sm font-semibold text-slate-200">No websites found in this campaign</h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              Run business discovery with "Website required" enabled to find businesses with digital footprints.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {leadsWithResearch.map((item) => {
              if (item.research) {
                return (
                  <ResearchCard
                    key={item.id}
                    research={item.research}
                    businessName={item.business_name}
                    industry={item.industry}
                  />
                );
              } else {
                return (
                  <div
                    key={item.id}
                    className="p-5 rounded-xl bg-slate-900/40 border border-slate-800 flex items-center justify-between gap-4"
                  >
                    <div>
                      <h4 className="font-semibold text-slate-200 text-sm">{item.business_name}</h4>
                      <p className="text-xs text-slate-400 font-mono truncate max-w-xs">{item.website}</p>
                      <span className="text-[11px] text-slate-500 mt-1 inline-block">Not yet crawled</span>
                    </div>
                    <button
                      onClick={async () => {
                        await fetch(`${API_BASE}/api/leads/${item.id}/research`, { method: "POST" });
                        loadResearchForCampaign(selectedCampaignId);
                      }}
                      className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium shrink-0"
                    >
                      Research Site
                    </button>
                  </div>
                );
              }
            })}
          </div>
        )}
      </div>
    </div>
  );
}
