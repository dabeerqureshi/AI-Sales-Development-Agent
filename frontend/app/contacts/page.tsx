"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Users, Mail, Phone, ShieldCheck, Sparkles, RefreshCw, Play, Filter, Search } from "lucide-react";
import { ContactCard, ContactItem } from "@/components/contacts/ContactCard";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface CampaignOption {
  id: number;
  name: string;
  industry: string;
  lead_count: number;
}

export default function ContactsPage() {
  const [campaigns, setCampaigns] = useState<CampaignOption[]>([]);
  const [selectedCampaignId, setSelectedCampaignId] = useState<string>("");
  const [contacts, setContacts] = useState<ContactItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [batchExtracting, setBatchExtracting] = useState<boolean>(false);
  const [notification, setNotification] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [filterMode, setFilterMode] = useState<"all" | "email" | "practitioners">("all");

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
    }
  }, [selectedCampaignId]);

  const loadContacts = useCallback(async (campId: string) => {
    setLoading(true);
    try {
      const url = campId
        ? `${API_BASE}/api/contacts?campaign_id=${campId}`
        : `${API_BASE}/api/contacts`;
      const res = await fetch(url);
      if (res.ok) {
        setContacts(await res.json());
      }
    } catch (e) {
      console.error("Failed to load contacts:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCampaigns();
  }, [fetchCampaigns]);

  useEffect(() => {
    loadContacts(selectedCampaignId);
  }, [selectedCampaignId, loadContacts]);

  const handleBatchExtract = async () => {
    if (!selectedCampaignId) return;
    setBatchExtracting(true);
    setNotification("Extracting public emails, phone lines, and doctors from crawled records...");
    try {
      const res = await fetch(`${API_BASE}/api/campaigns/${selectedCampaignId}/contacts/extract?limit=25`, {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        setNotification(
          `Contacts extracted! Found ${data.stats.contacts_found} verified contacts, ${data.stats.emails_found} emails, and ${data.stats.practitioners_identified} practitioners.`
        );
        loadContacts(selectedCampaignId);
      } else {
        const err = await res.json();
        alert(`Extraction error: ${err.detail || "Error extracting contacts"}`);
      }
    } catch {
      alert("Network error extracting contacts.");
    } finally {
      setBatchExtracting(false);
      setTimeout(() => setNotification(null), 6000);
    }
  };

  const handleSetPrimary = async (contactId: number) => {
    try {
      const res = await fetch(`${API_BASE}/api/contacts/${contactId}/primary`, {
        method: "POST",
      });
      if (res.ok) {
        loadContacts(selectedCampaignId);
      }
    } catch (e) {
      console.error("Failed to set primary contact:", e);
    }
  };

  const filteredContacts = contacts.filter((c) => {
    const matchesSearch =
      (c.full_name || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.business_name || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.email || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.title || "").toLowerCase().includes(searchQuery.toLowerCase());

    if (!matchesSearch) return false;

    if (filterMode === "email") return Boolean(c.email);
    if (filterMode === "practitioners") {
      return Boolean(c.full_name && (c.full_name.includes("Dr.") || (c.title || "").includes("Dentist")));
    }
    return true;
  });

  const totalEmails = contacts.filter((c) => c.email).length;
  const totalPractitioners = contacts.filter((c) => c.full_name && c.full_name.includes("Dr.")).length;
  const highConfidence = contacts.filter((c) => c.confidence_score >= 0.85).length;

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full bg-blue-950 border border-blue-800 text-[11px] font-semibold text-blue-400 mb-2">
            <Users className="h-3 w-3" />
            Milestone 4 Active
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Public Contact Discovery</h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Identify verified emails, telephone lines, and lead practitioners with confidence scoring. Zero guessed emails.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => loadContacts(selectedCampaignId)}
            disabled={loading || batchExtracting}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-xs text-slate-300 font-medium transition-colors"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <button
            onClick={handleBatchExtract}
            disabled={batchExtracting || !selectedCampaignId}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-medium transition-colors shadow-lg shadow-blue-600/20"
          >
            <Play className={`h-3.5 w-3.5 ${batchExtracting ? "animate-spin" : ""}`} />
            {batchExtracting ? "Extracting Contacts..." : "Extract Contacts for Campaign"}
          </button>
        </div>
      </div>

      {notification && (
        <div className="p-3 bg-blue-950/80 border border-blue-800/80 rounded-xl text-xs text-blue-200 flex items-center gap-2 font-medium">
          <Sparkles className="h-4 w-4 text-blue-400 shrink-0" />
          <span>{notification}</span>
        </div>
      )}

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl">
          <div className="text-slate-400 flex items-center gap-1.5">
            <Users className="h-3.5 w-3.5 text-blue-400" />
            <span>Discovered Contacts</span>
          </div>
          <div className="text-xl font-bold text-slate-100 font-mono mt-1">{contacts.length}</div>
        </div>
        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl">
          <div className="text-slate-400 flex items-center gap-1.5">
            <Mail className="h-3.5 w-3.5 text-emerald-400" />
            <span>Verified Emails</span>
          </div>
          <div className="text-xl font-bold text-emerald-400 font-mono mt-1">{totalEmails}</div>
        </div>
        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl">
          <div className="text-slate-400 flex items-center gap-1.5">
            <Users className="h-3.5 w-3.5 text-purple-400" />
            <span>Practitioners / Doctors</span>
          </div>
          <div className="text-xl font-bold text-purple-400 font-mono mt-1">{totalPractitioners}</div>
        </div>
        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl">
          <div className="text-slate-400 flex items-center gap-1.5">
            <ShieldCheck className="h-3.5 w-3.5 text-amber-400" />
            <span>High Confidence (&ge;85%)</span>
          </div>
          <div className="text-xl font-bold text-amber-400 font-mono mt-1">{highConfidence}</div>
        </div>
      </div>

      {/* Campaign Filter & Search Bar */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <span className="text-slate-400 font-semibold shrink-0">Campaign:</span>
          <select
            value={selectedCampaignId}
            onChange={(e) => setSelectedCampaignId(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-blue-500 w-full sm:w-64"
          >
            {campaigns.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} ({c.lead_count} leads)
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-64">
            <Search className="h-3.5 w-3.5 text-slate-500 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search contacts, doctors, business..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500"
            />
          </div>

          <div className="flex items-center gap-1 border border-slate-800 rounded-lg p-0.5 bg-slate-950">
            <button
              onClick={() => setFilterMode("all")}
              className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
                filterMode === "all" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
              }`}
            >
              All
            </button>
            <button
              onClick={() => setFilterMode("email")}
              className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
                filterMode === "email" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
              }`}
            >
              Has Email
            </button>
            <button
              onClick={() => setFilterMode("practitioners")}
              className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
                filterMode === "practitioners" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
              }`}
            >
              Doctors
            </button>
          </div>
        </div>
      </div>

      {/* Contacts List Grid */}
      <div className="space-y-4">
        <h2 className="text-base font-bold text-slate-100 flex items-center justify-between">
          <span>Identified Business Contacts ({filteredContacts.length})</span>
        </h2>

        {loading ? (
          <div className="p-12 text-center text-xs text-slate-500 font-mono">
            Loading contact records...
          </div>
        ) : filteredContacts.length === 0 ? (
          <div className="p-12 text-center rounded-xl bg-slate-900/40 border border-slate-800 space-y-3">
            <Users className="h-8 w-8 text-slate-600 mx-auto" />
            <h3 className="text-sm font-semibold text-slate-200">No contacts found</h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              Run "Extract Contacts for Campaign" to scan public contact pages and research records.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredContacts.map((contact) => (
              <ContactCard
                key={contact.id}
                contact={contact}
                onSetPrimary={handleSetPrimary}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
