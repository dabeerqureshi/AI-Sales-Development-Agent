"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Server, Database, Cpu, Sparkles, RefreshCw } from "lucide-react";
import { StatusCard, ServiceStatus } from "./StatusCard";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface BackendHealth {
  status: string;
  app_name: string;
  environment: string;
  version: string;
}

interface DatabaseHealth {
  status: string;
  connected: boolean;
  database_type: string;
  latency_ms?: number;
  error?: string;
}

interface OllamaHealth {
  status: string;
  ollama_reachable: boolean;
  configured_model: string;
  model_available: boolean;
  available_models: string[];
  error?: string;
}

export function SystemStatusSection() {
  const [loading, setLoading] = useState<boolean>(true);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const [backendState, setBackendState] = useState<{
    status: ServiceStatus;
    data: BackendHealth | null;
    error: string | null;
  }>({ status: "loading", data: null, error: null });

  const [dbState, setDbState] = useState<{
    status: ServiceStatus;
    data: DatabaseHealth | null;
    error: string | null;
  }>({ status: "loading", data: null, error: null });

  const [ollamaState, setOllamaState] = useState<{
    status: ServiceStatus;
    data: OllamaHealth | null;
    error: string | null;
  }>({ status: "loading", data: null, error: null });

  const fetchHealth = useCallback(async () => {
    setLoading(true);

    // 1. Fetch Backend Health
    try {
      const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
      if (res.ok) {
        const data: BackendHealth = await res.json();
        setBackendState({ status: "healthy", data, error: null });
      } else {
        setBackendState({
          status: "error",
          data: null,
          error: `HTTP ${res.status}: Failed to reach FastAPI`,
        });
      }
    } catch {
      setBackendState({
        status: "error",
        data: null,
        error: "Backend offline. Run: uvicorn app.main:app --port 8000",
      });
    }

    // 2. Fetch Database Health
    try {
      const res = await fetch(`${API_BASE}/health/database`, { cache: "no-store" });
      if (res.ok) {
        const data: DatabaseHealth = await res.json();
        setDbState({
          status: data.connected ? "healthy" : "error",
          data,
          error: data.error || null,
        });
      } else {
        const errData = await res.json().catch(() => null);
        setDbState({
          status: "error",
          data: errData,
          error: errData?.error || "Database query failed",
        });
      }
    } catch {
      setDbState({
        status: "error",
        data: null,
        error: "Cannot check database (backend unreachable)",
      });
    }

    // 3. Fetch Ollama Health
    try {
      const res = await fetch(`${API_BASE}/health/ollama`, { cache: "no-store" });
      const data: OllamaHealth = await res.json();
      if (data.status === "ok") {
        setOllamaState({ status: "healthy", data, error: null });
      } else if (data.status === "model_missing") {
        setOllamaState({
          status: "warning",
          data,
          error: data.error || `Model ${data.configured_model} not installed`,
        });
      } else {
        setOllamaState({
          status: "error",
          data,
          error: data.error || "Ollama server offline",
        });
      }
    } catch {
      setOllamaState({
        status: "error",
        data: null,
        error: "Cannot reach Ollama endpoint (backend offline)",
      });
    }

    setLastChecked(new Date());
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchHealth();
  }, [fetchHealth]);

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <span>System Runtime & Services</span>
            <span className="text-xs px-2 py-0.5 rounded bg-blue-950 text-blue-400 border border-blue-800/60 font-normal">
              Foundation
            </span>
          </h2>
          <p className="text-xs text-slate-400">
            Real service health and local model detection for this session.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {lastChecked && (
            <span className="text-xs text-slate-500 font-mono">
              Updated {lastChecked.toLocaleTimeString()}
            </span>
          )}
          <button
            onClick={fetchHealth}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700/80 text-xs font-medium text-slate-200 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* FastAPI Backend */}
        <StatusCard
          title="FastAPI Backend"
          description="Python REST API Gateway"
          icon={Server}
          status={backendState.status}
          statusText={
            backendState.status === "healthy"
              ? "Online"
              : backendState.status === "loading"
              ? "Connecting..."
              : "Offline"
          }
          details={[
            {
              label: "Environment",
              value: backendState.data?.environment || "development",
            },
            {
              label: "Port",
              value: "8000",
            },
            {
              label: "Version",
              value: backendState.data?.version || "0.1.0",
            },
          ]}
          hint={backendState.error || undefined}
        />

        {/* SQLite Database */}
        <StatusCard
          title="SQLite Database"
          description="Local-first persistence"
          icon={Database}
          status={dbState.status}
          statusText={
            dbState.status === "healthy"
              ? "Connected"
              : dbState.status === "loading"
              ? "Connecting..."
              : "Disconnected"
          }
          details={[
            {
              label: "Engine",
              value: "SQLite 3",
            },
            {
              label: "Path",
              value: "sdr.db",
            },
            {
              label: "Ping Latency",
              value:
                dbState.data?.latency_ms !== undefined
                  ? `${dbState.data.latency_ms} ms`
                  : "N/A",
            },
          ]}
          hint={dbState.error || undefined}
        />

        {/* Ollama Local AI */}
        <StatusCard
          title="Ollama Local AI"
          description="Local LLM Inference Engine"
          icon={Cpu}
          status={ollamaState.status}
          statusText={
            ollamaState.status === "healthy"
              ? "Model Ready"
              : ollamaState.status === "warning"
              ? "Model Needed"
              : ollamaState.status === "loading"
              ? "Checking..."
              : "Offline"
          }
          details={[
            {
              label: "Configured Model",
              value: ollamaState.data?.configured_model || "qwen3:4b",
            },
            {
              label: "Model Installed",
              value: ollamaState.data?.model_available ? "Yes (Detected)" : "No",
            },
            {
              label: "Available Models",
              value:
                ollamaState.data?.available_models && ollamaState.data.available_models.length > 0
                  ? ollamaState.data.available_models.slice(0, 2).join(", ")
                  : "None",
            },
          ]}
          hint={
            ollamaState.error ||
            (!ollamaState.data?.model_available && ollamaState.data?.ollama_reachable
              ? `Run: ollama pull ${ollamaState.data?.configured_model || "qwen3:4b"}`
              : undefined)
          }
        />
      </div>
    </div>
  );
}
