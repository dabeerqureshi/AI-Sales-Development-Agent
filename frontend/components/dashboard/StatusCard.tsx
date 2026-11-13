import React from "react";
import { LucideIcon, CheckCircle2, AlertTriangle, XCircle, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

export type ServiceStatus = "healthy" | "warning" | "error" | "loading";

interface StatusCardProps {
  title: string;
  status: ServiceStatus;
  statusText: string;
  description: string;
  icon: LucideIcon;
  details?: { label: string; value: string | React.ReactNode }[];
  hint?: string;
}

export function StatusCard({
  title,
  status,
  statusText,
  description,
  icon: Icon,
  details = [],
  hint,
}: StatusCardProps) {
  const getStatusBadge = () => {
    switch (status) {
      case "healthy":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="h-3.5 w-3.5" />
            {statusText}
          </span>
        );
      case "warning":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertTriangle className="h-3.5 w-3.5" />
            {statusText}
          </span>
        );
      case "error":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <XCircle className="h-3.5 w-3.5" />
            {statusText}
          </span>
        );
      case "loading":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-500/10 text-slate-400 border border-slate-500/20">
            <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            {statusText}
          </span>
        );
    }
  };

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 hover:border-slate-700/80 transition-all flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div
              className={cn(
                "p-2.5 rounded-lg border",
                status === "healthy" && "bg-emerald-500/10 border-emerald-500/20 text-emerald-400",
                status === "warning" && "bg-amber-500/10 border-amber-500/20 text-amber-400",
                status === "error" && "bg-rose-500/10 border-rose-500/20 text-rose-400",
                status === "loading" && "bg-slate-800 border-slate-700 text-slate-400"
              )}
            >
              <Icon className="h-5 w-5" />
            </div>
            <div>
              <h3 className="font-semibold text-slate-100 text-sm">{title}</h3>
              <p className="text-xs text-slate-400">{description}</p>
            </div>
          </div>
          {getStatusBadge()}
        </div>

        {details.length > 0 && (
          <div className="mt-4 pt-3 border-t border-slate-800/80 space-y-2">
            {details.map((detail, idx) => (
              <div key={idx} className="flex justify-between items-center text-xs">
                <span className="text-slate-400">{detail.label}</span>
                <span className="font-mono text-slate-300 font-medium">{detail.value}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {hint && (
        <div className="mt-4 pt-3 border-t border-slate-800/50">
          <p className="text-[11px] text-slate-400 font-mono bg-slate-950/80 p-2 rounded border border-slate-800">
            {hint}
          </p>
        </div>
      )}
    </div>
  );
}
