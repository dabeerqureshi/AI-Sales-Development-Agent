"use client";

import React, { useEffect, useState } from "react";
import { Cpu, Terminal, CheckCircle2, Clock, Wrench } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface MCPTool {
  name: string;
  description?: string;
}

interface MCPServer {
  name: string;
  transport: string;
  status: string;
  available_tools: MCPTool[];
}

interface MCPStatus {
  status: string;
  registered_servers: number;
  available_tools: number;
  servers: MCPServer[];
  last_execution?: {
    tool: string;
    status: string;
    duration_ms: number;
    timestamp: string;
  };
}

export function MCPServerStatus() {
  const [data, setData] = useState<MCPStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadMcp() {
      try {
        const res = await fetch(`${API_BASE}/api/mcp/status`);
        if (res.ok) {
          const statusJson = await res.json();
          setData(statusJson);
        }
      } catch (e) {
        console.error("Failed to load MCP status:", e);
      } finally {
        setLoading(false);
      }
    }
    loadMcp();
  }, []);

  if (loading) {
    return (
      <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-5 text-xs text-slate-400">
        Loading MCP Integration status...
      </div>
    );
  }

  if (!data) {
    return (
      <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-5 text-xs text-slate-400">
        MCP Layer disconnected. Ensure backend is running.
      </div>
    );
  }

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400">
            <Cpu className="h-5 w-5" />
          </div>
          <div>
            <h3 className="font-semibold text-slate-100 text-sm">Model Context Protocol (MCP) Hub</h3>
            <p className="text-xs text-slate-400">Standardized external tool integration layer</p>
          </div>
        </div>
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <CheckCircle2 className="h-3.5 w-3.5" />
          {data.status === "healthy" ? "MCP Ready" : data.status}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
        {data.servers.map((server) => (
          <div key={server.name} className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg space-y-2">
            <div className="flex items-center justify-between font-mono">
              <span className="font-semibold text-slate-200">mcp/{server.name}</span>
              <span className="text-[10px] bg-slate-800 px-1.5 py-0.5 rounded text-slate-300">
                {server.transport}
              </span>
            </div>
            <div className="space-y-1">
              <div className="text-slate-400 text-[11px] flex items-center gap-1">
                <Wrench className="h-3 w-3 text-blue-400" />
                <span>Tools ({server.available_tools.length}):</span>
              </div>
              <ul className="text-slate-300 font-mono text-[11px] list-disc list-inside">
                {server.available_tools.map((t) => (
                  <li key={t.name}>{t.name}</li>
                ))}
              </ul>
            </div>
          </div>
        ))}

        <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg space-y-1">
          <div className="text-slate-400 text-[11px] flex items-center gap-1">
            <Clock className="h-3 w-3 text-emerald-400" />
            <span>Last Tool Execution:</span>
          </div>
          {data.last_execution ? (
            <div className="font-mono text-[11px] space-y-0.5 pt-1">
              <div className="text-blue-400 font-semibold">{data.last_execution.tool}</div>
              <div className="text-slate-400">
                Duration: <span className="text-slate-200">{data.last_execution.duration_ms}ms</span>
              </div>
              <div className="text-slate-400">
                Status: <span className="text-emerald-400">{data.last_execution.status}</span>
              </div>
            </div>
          ) : (
            <div className="text-slate-500 font-mono text-[11px] pt-1">No executions logged yet</div>
          )}
        </div>

        <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg space-y-1">
          <div className="text-slate-400 text-[11px] flex items-center gap-1">
            <Terminal className="h-3 w-3 text-amber-400" />
            <span>Security & Permissions:</span>
          </div>
          <div className="text-[11px] text-slate-400 pt-1 leading-relaxed">
            Strict tool allowlisting active. Arbitrary shell access is disabled.
          </div>
        </div>
      </div>
    </div>
  );
}
