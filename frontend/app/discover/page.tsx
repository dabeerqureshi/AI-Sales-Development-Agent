"use client";

import React, { useState, useEffect } from "react";
import { Search, Play, Sparkles, Filter, Globe, Phone, MapPin, Database } from "lucide-react";
import { LeadTable, LeadItem } from "@/components/campaigns/LeadTable";
import { MCPServerStatus } from "@/components/mcp/MCPServerStatus";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface CampaignOption {
  id: number;
  name: string;
  industry: string;
  city: string;
  region?: string;
  lead_count: number;
}

export default function DiscoverPage() {
  const [campaigns, setCampaigns] = useState<CampaignOption[]>([]);
  const [selectedCampaignId, setSelectedCampaignId] = useState<string>("");
  
  // Custom search inputs
  const [industry, setIndustry] = useState("Dentist");
  const [city, setCity] = useState("Austin");
  const [region, setRegion] = useState("Texas");
  const [country, setCountry] = useState("United States");
  const [limit, setLimit] = useState(15);
  const [websiteRequired, setWebsiteRequired] = useState(false);
  const [phoneRequired, setPhoneRequired] = useState(false);

  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<LeadItem[]>([]);
  const [stats, setStats] = useState<{
    found: number;
    saved: number;
    duplicates: number;
    duration: number;
  } | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    async function loadCampaigns() {
      try {
        const res = await fetch(`${API_BASE}/api/campaigns`);
        if (res.ok) {
          const data = await res.json();
          setCampaigns(data);
          if (data.length > 0) {
            setSelectedCampaignId(String(data[0].id));
          }
        }
      } catch (e) {
        console.error("Failed to load campaigns:", e);
      }
    }
    loadCampaigns();
  }, []);

  const handleRunDiscovery = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg(null);
    setStats(null);

    let targetCampId = selectedCampaignId;

    try {
      // If no campaign selected or user chose to create a new one:
      if (!targetCampId || targetCampId === "new") {
        const campRes = await fetch(`${API_BASE}/api/campaigns`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: `${city} ${industry} Prospecting`,
            industry,
            city,
            region,
            country,
            max_leads: limit,
            website_required: websiteRequired,
            phone_required: phoneRequired,
          }),
        });

        if (!campRes.ok) {
          const err = await campRes.json();
          throw new Error(err.detail || "Failed to create campaign container.");
        }
        const createdCamp = await campRes.json();
        targetCampId = String(createdCamp.id);
        setSelectedCampaignId(targetCampId);
      }

      // Execute discovery
      const discRes = await fetch(
        `${API_BASE}/api/campaigns/${targetCampId}/discover?limit=${limit}`,
        { method: "POST" }
      );

      if (!discRes.ok) {
        const err = await discRes.json();
        throw new Error(err.detail || "Discovery execution failed.");
      }

      const discData = await discRes.json();
      setStats({
        found: discData.stats.total_found,
        saved: discData.stats.new_leads_saved,
        duplicates: discData.stats.duplicates_skipped,
        duration: discData.stats.execution_time_seconds,
      });

      // Load all leads for this campaign
      const leadsRes = await fetch(`${API_BASE}/api/campaigns/${targetCampId}/leads`);
      if (leadsRes.ok) {
        setResults(await leadsRes.json());
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to execute business discovery.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full bg-blue-950 border border-blue-800 text-[11px] font-semibold text-blue-400 mb-2">
          <Search className="h-3 w-3" />
          Live Lead Discovery Studio
        </div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Discover Businesses</h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Standardized OpenStreetMap discovery via Model Context Protocol (MCP). Zero fabricated data.
        </p>
      </div>

      <MCPServerStatus />

      {/* Discovery Form Card */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-6">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
          <div className="flex items-center gap-2">
            <Search className="h-4 w-4 text-blue-400" />
            <h3 className="text-sm font-semibold text-slate-200">Search Parameters</h3>
          </div>
          <span className="text-xs text-slate-400 font-mono">MCP Tool: search_businesses</span>
        </div>

        <form onSubmit={handleRunDiscovery} className="space-y-4 text-xs">
          {campaigns.length > 0 && (
            <div className="space-y-1">
              <label className="text-slate-300 font-medium">Assign to Campaign</label>
              <select
                value={selectedCampaignId}
                onChange={(e) => {
                  setSelectedCampaignId(e.target.value);
                  const selected = campaigns.find((c) => String(c.id) === e.target.value);
                  if (selected) {
                    setIndustry(selected.industry);
                    setCity(selected.city);
                    if (selected.region) setRegion(selected.region);
                  }
                }}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
              >
                {campaigns.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.city}, {c.industry}) — {c.lead_count} leads
                  </option>
                ))}
                <option value="new">+ Create a new campaign on discovery</option>
              </select>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="space-y-1">
              <label className="text-slate-300 font-medium">Industry / Amenity</label>
              <input
                type="text"
                required
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
                placeholder="e.g. Dentist, Clinic"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
              />
            </div>

            <div className="space-y-1">
              <label className="text-slate-300 font-medium">City</label>
              <input
                type="text"
                required
                value={city}
                onChange={(e) => setCity(e.target.value)}
                placeholder="e.g. Austin"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
              />
            </div>

            <div className="space-y-1">
              <label className="text-slate-300 font-medium">State / Region</label>
              <input
                type="text"
                value={region}
                onChange={(e) => setRegion(e.target.value)}
                placeholder="e.g. Texas"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
            <div className="space-y-1">
              <label className="text-slate-300 font-medium">Country</label>
              <input
                type="text"
                required
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
              />
            </div>
            <div className="space-y-1">
              <label className="text-slate-300 font-medium">Max Leads to Discover: {limit}</label>
              <input
                type="range"
                min="5"
                max="50"
                step="5"
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
                className="w-full accent-blue-600 mt-2"
              />
            </div>
          </div>

          <div className="pt-2 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 text-slate-300 cursor-pointer text-xs">
                <input
                  type="checkbox"
                  checked={websiteRequired}
                  onChange={(e) => setWebsiteRequired(e.target.checked)}
                  className="rounded bg-slate-950 border-slate-800 text-blue-600 focus:ring-0"
                />
                <span>Must have official website</span>
              </label>
              <label className="flex items-center gap-2 text-slate-300 cursor-pointer text-xs">
                <input
                  type="checkbox"
                  checked={phoneRequired}
                  onChange={(e) => setPhoneRequired(e.target.checked)}
                  className="rounded bg-slate-950 border-slate-800 text-blue-600 focus:ring-0"
                />
                <span>Must have phone</span>
              </label>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-medium text-xs transition-colors shadow-lg shadow-blue-600/25"
            >
              <Play className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
              {loading ? "Searching OpenStreetMap via MCP..." : "Start Discovery Search"}
            </button>
          </div>
        </form>
      </div>

      {/* Error Banner */}
      {errorMsg && (
        <div className="p-4 bg-rose-950/60 border border-rose-800/80 rounded-xl text-xs text-rose-300">
          <strong>Discovery Error:</strong> {errorMsg}
        </div>
      )}

      {/* Stats Summary Banner */}
      {stats && (
        <div className="p-4 bg-blue-950/40 border border-blue-900/60 rounded-xl grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div>
            <span className="text-slate-400">Total Found:</span>
            <div className="text-lg font-bold text-slate-100 font-mono">{stats.found}</div>
          </div>
          <div>
            <span className="text-slate-400">New Leads Saved:</span>
            <div className="text-lg font-bold text-emerald-400 font-mono">+{stats.saved}</div>
          </div>
          <div>
            <span className="text-slate-400">Duplicates Skipped:</span>
            <div className="text-lg font-bold text-amber-400 font-mono">{stats.duplicates}</div>
          </div>
          <div>
            <span className="text-slate-400">Execution Time:</span>
            <div className="text-lg font-bold text-blue-400 font-mono">{stats.duration}s</div>
          </div>
        </div>
      )}

      {/* Leads Result Table */}
      <div className="space-y-3">
        <h2 className="text-base font-bold text-slate-100 flex items-center justify-between">
          <span>Discovered Business Leads ({results.length})</span>
          {results.length > 0 && (
            <span className="text-xs text-slate-500 font-normal">
              Stored in SQLite • Linked to verified OpenStreetMap node IDs
            </span>
          )}
        </h2>
        <LeadTable leads={results} />
      </div>
    </div>
  );
}
