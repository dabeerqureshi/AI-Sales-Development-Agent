import React from "react";
import Link from "next/link";
import { Target, MapPin, Users, ArrowRight, Play, Globe } from "lucide-react";

export interface CampaignData {
  id: number;
  name: string;
  industry: string;
  country: string;
  region?: string;
  city: string;
  max_leads: number;
  website_required: boolean;
  phone_required: boolean;
  status: string;
  lead_count: number;
  created_at: string;
}

export function CampaignCard({
  campaign,
  onDiscover,
  isDiscovering,
}: {
  campaign: CampaignData;
  onDiscover?: (id: number) => void;
  isDiscovering?: boolean;
}) {
  const getStatusBadge = (status: string) => {
    switch (status) {
      case "completed":
        return <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Completed</span>;
      case "running":
        return <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20 animate-pulse">Running</span>;
      case "failed":
        return <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">Failed</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-500/10 text-slate-400 border border-slate-500/20">Draft</span>;
    }
  };

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-all flex flex-col justify-between">
      <div className="space-y-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h3 className="font-semibold text-slate-100 text-sm">{campaign.name}</h3>
            <div className="flex items-center gap-1.5 text-xs text-blue-400 font-medium mt-0.5">
              <Target className="h-3 w-3" />
              <span>{campaign.industry}</span>
            </div>
          </div>
          {getStatusBadge(campaign.status)}
        </div>

        <div className="space-y-1.5 text-xs text-slate-400 pt-2 border-t border-slate-800/60">
          <div className="flex items-center gap-1.5">
            <MapPin className="h-3.5 w-3.5 text-slate-500" />
            <span>
              {campaign.city}
              {campaign.region ? `, ${campaign.region}` : ""} ({campaign.country})
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <Users className="h-3.5 w-3.5 text-slate-500" />
            <span>
              <strong className="text-slate-200 font-mono">{campaign.lead_count}</strong> of {campaign.max_leads} leads discovered
            </span>
          </div>
          {campaign.website_required && (
            <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
              <Globe className="h-3 w-3 text-blue-400/70" />
              <span>Requires official website</span>
            </div>
          )}
        </div>
      </div>

      <div className="pt-4 mt-4 border-t border-slate-800 flex items-center justify-between gap-2">
        <Link
          href={`/campaigns/${campaign.id}`}
          className="inline-flex items-center gap-1.5 text-xs text-slate-300 hover:text-white font-medium transition-colors"
        >
          View Leads
          <ArrowRight className="h-3.5 w-3.5" />
        </Link>

        {onDiscover && (
          <button
            onClick={() => onDiscover(campaign.id)}
            disabled={isDiscovering || campaign.status === "running"}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-medium transition-colors shadow-sm"
          >
            <Play className={`h-3 w-3 ${isDiscovering ? "animate-spin" : ""}`} />
            {isDiscovering ? "Discovering..." : "Discover Leads"}
          </button>
        )}
      </div>
    </div>
  );
}
