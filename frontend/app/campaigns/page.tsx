"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Plus, Target, RefreshCw, Sparkles, Filter } from "lucide-react";
import { CampaignCard, CampaignData } from "@/components/campaigns/CampaignCard";
import { MCPServerStatus } from "@/components/mcp/MCPServerStatus";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<CampaignData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [discoveringId, setDiscoveringId] = useState<number | null>(null);
  const [notification, setNotification] = useState<string | null>(null);

  // Form fields
  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("Dentist");
  const [country, setCountry] = useState("United States");
  const [region, setRegion] = useState("Texas");
  const [city, setCity] = useState("Austin");
  const [maxLeads, setMaxLeads] = useState(25);
  const [websiteRequired, setWebsiteRequired] = useState(false);
  const [phoneRequired, setPhoneRequired] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const fetchCampaigns = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/campaigns`);
      if (res.ok) {
        const data = await res.json();
        setCampaigns(data);
      }
    } catch (e) {
      console.error("Failed to load campaigns:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCampaigns();
  }, [fetchCampaigns]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/api/campaigns`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          industry,
          country,
          region,
          city,
          max_leads: Number(maxLeads),
          website_required: websiteRequired,
          phone_required: phoneRequired,
        }),
      });
      if (res.ok) {
        setShowCreateModal(false);
        setName("");
        fetchCampaigns();
        setNotification("Campaign created successfully!");
        setTimeout(() => setNotification(null), 4000);
      } else {
        const err = await res.json();
        alert(`Failed to create campaign: ${err.detail || "Validation error"}`);
      }
    } catch {
      alert("Error connecting to backend API.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDiscover = async (campaignId: number) => {
    setDiscoveringId(campaignId);
    setNotification("Executing OpenStreetMap discovery via MCP...");
    try {
      const res = await fetch(`${API_BASE}/api/campaigns/${campaignId}/discover`, {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        setNotification(
          `Discovery complete! Found ${data.stats.total_found}, saved ${data.stats.new_leads_saved} new leads.`
        );
        fetchCampaigns();
      } else {
        const err = await res.json();
        alert(`Discovery failed: ${err.detail || "Error from Overpass/MCP"}`);
      }
    } catch {
      alert("Network error executing discovery.");
    } finally {
      setDiscoveringId(null);
      setTimeout(() => setNotification(null), 5000);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full bg-blue-950 border border-blue-800 text-[11px] font-semibold text-blue-400 mb-2">
            <Target className="h-3 w-3" />
            Milestone 2 Active
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Campaign Manager</h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Create prospecting campaigns, target industries, and execute verified OpenStreetMap discovery.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchCampaigns}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-xs text-slate-300 font-medium transition-colors"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition-colors shadow-lg shadow-blue-600/20"
          >
            <Plus className="h-4 w-4" />
            New Campaign
          </button>
        </div>
      </div>

      {/* Notification Banner */}
      {notification && (
        <div className="p-3 bg-blue-950/80 border border-blue-800/80 rounded-xl text-xs text-blue-200 flex items-center gap-2 animate-fade-in font-medium">
          <Sparkles className="h-4 w-4 text-blue-400 shrink-0" />
          <span>{notification}</span>
        </div>
      )}

      {/* MCP Integration Subsystem Status Card */}
      <MCPServerStatus />

      {/* Campaigns Grid */}
      <div className="space-y-4">
        <h2 className="text-base font-bold text-slate-200 flex items-center justify-between">
          <span>Active Prospecting Campaigns ({campaigns.length})</span>
        </h2>

        {loading ? (
          <div className="p-12 text-center text-xs text-slate-500 font-mono">Loading campaigns...</div>
        ) : campaigns.length === 0 ? (
          <div className="p-12 text-center rounded-xl bg-slate-900/40 border border-slate-800 space-y-3">
            <Target className="h-8 w-8 text-slate-600 mx-auto" />
            <h3 className="text-sm font-semibold text-slate-200">No campaigns yet</h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              Create your first campaign (e.g. Austin Dental Clinics) to start discovering real businesses.
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium"
            >
              <Plus className="h-3.5 w-3.5" />
              Create First Campaign
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {campaigns.map((camp) => (
              <CampaignCard
                key={camp.id}
                campaign={camp}
                onDiscover={handleDiscover}
                isDiscovering={discoveringId === camp.id}
              />
            ))}
          </div>
        )}
      </div>

      {/* Create Campaign Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div>
                <h3 className="text-base font-bold text-white">Create Prospecting Campaign</h3>
                <p className="text-xs text-slate-400 mt-0.5">Define target market and discovery parameters</p>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreate} className="space-y-4 text-xs">
              <div className="space-y-1">
                <label className="text-slate-300 font-medium">Campaign Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Texas Dental Automation"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-slate-300 font-medium">Industry / Category</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Dentist, Clinic"
                    value={industry}
                    onChange={(e) => setIndustry(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-slate-300 font-medium">Target City</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Austin"
                    value={city}
                    onChange={(e) => setCity(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-slate-300 font-medium">State / Region (Optional)</label>
                  <input
                    type="text"
                    placeholder="e.g. Texas"
                    value={region}
                    onChange={(e) => setRegion(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
                  />
                </div>
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
              </div>

              <div className="space-y-1">
                <label className="text-slate-300 font-medium">Maximum Leads to Discover: {maxLeads}</label>
                <input
                  type="range"
                  min="5"
                  max="100"
                  step="5"
                  value={maxLeads}
                  onChange={(e) => setMaxLeads(Number(e.target.value))}
                  className="w-full accent-blue-600"
                />
              </div>

              <div className="pt-2 border-t border-slate-800 space-y-2">
                <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1">
                  <Filter className="h-3 w-3" />
                  <span>Quality Filters</span>
                </div>
                <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={websiteRequired}
                    onChange={(e) => setWebsiteRequired(e.target.checked)}
                    className="rounded bg-slate-950 border-slate-800 text-blue-600 focus:ring-0"
                  />
                  <span>Website required (skip businesses without online URL)</span>
                </label>
                <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={phoneRequired}
                    onChange={(e) => setPhoneRequired(e.target.checked)}
                    className="rounded bg-slate-950 border-slate-800 text-blue-600 focus:ring-0"
                  />
                  <span>Phone number required</span>
                </label>
              </div>

              <div className="pt-4 border-t border-slate-800 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium transition-colors shadow-lg shadow-blue-600/20 disabled:opacity-50"
                >
                  {submitting ? "Creating..." : "Save Campaign"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
