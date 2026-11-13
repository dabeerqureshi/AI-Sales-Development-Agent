"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Activity,
  Play,
  RotateCw,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ShieldAlert,
  Mail,
  User,
  ArrowRight,
  Sparkles,
  Filter,
  Check,
  Send,
  Calendar,
  Layers,
  StopCircle,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface FollowupTaskItem {
  id: number;
  lead_id: number;
  sequence_step: number;
  scheduled_date: string;
  status: "pending" | "executed" | "cancelled";
  cancellation_reason?: string | null;
  created_at: string;
  business_name?: string | null;
  recipient_email?: string | null;
}

interface JobItem {
  id: number;
  campaign_id?: number | null;
  job_type: string;
  status: "queued" | "running" | "completed" | "failed";
  progress_pct: number;
  error_details?: string | null;
  created_at: string;
  completed_at?: string | null;
}

interface ActivityItem {
  id: number;
  entity_type: string;
  entity_id: number;
  action: string;
  details: Record<string, any>;
  created_at: string;
}

export default function LogsPage() {
  const [activeTab, setActiveTab] = useState<"followups" | "jobs" | "activities">("followups");
  const [followups, setFollowups] = useState<FollowupTaskItem[]>([]);
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [runningCycle, setRunningCycle] = useState<boolean>(false);
  const [filterFollowupStatus, setFilterFollowupStatus] = useState<"all" | "pending" | "executed" | "cancelled">("all");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Reply simulation modal state
  const [simLeadId, setSimLeadId] = useState<number | null>(null);
  const [simSnippet, setSimSnippet] = useState("Hi, thanks for following up! We would be interested in seeing a demo call next week.");
  const [simulating, setSimulating] = useState<boolean>(false);

  // Load all monitor data
  const loadMonitorData = useCallback(async () => {
    setLoading(true);
    try {
      const [followupsRes, jobsRes, activitiesRes] = await Promise.all([
        fetch(`${API_BASE}/api/followups`),
        fetch(`${API_BASE}/api/jobs`),
        fetch(`${API_BASE}/api/activities?limit=50`),
      ]);

      if (followupsRes.ok) setFollowups(await followupsRes.json());
      if (jobsRes.ok) setJobs(await jobsRes.json());
      if (activitiesRes.ok) setActivities(await activitiesRes.json());
    } catch (e) {
      console.error("Failed to load worker monitor data:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMonitorData();
  }, [loadMonitorData]);

  // Actions
  const handleRunWorkerCycle = async () => {
    setRunningCycle(true);
    setStatusMessage("Running async worker cycle: scanning due tasks and verifying suppression...");
    try {
      const res = await fetch(`${API_BASE}/api/worker/run-cycle`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        setStatusMessage(
          `Worker cycle complete! Processed ${data.tasks_processed} due tasks, cancelled ${data.tasks_cancelled} suppressed tasks.`
        );
        loadMonitorData();
      } else {
        alert("Worker cycle execution failed.");
      }
    } catch {
      alert("Error contacting worker endpoint.");
    } finally {
      setRunningCycle(false);
      setTimeout(() => setStatusMessage(null), 5000);
    }
  };

  const handleCancelTask = async (taskId: number) => {
    if (!confirm("Are you sure you want to cancel this scheduled follow-up task?")) return;
    try {
      const res = await fetch(`${API_BASE}/api/followups/${taskId}/cancel?reason=manual_cancel`, {
        method: "POST",
      });
      if (res.ok) {
        setStatusMessage("Follow-up task cancelled.");
        loadMonitorData();
      }
    } catch {
      alert("Failed to cancel task.");
    } finally {
      setTimeout(() => setStatusMessage(null), 4000);
    }
  };

  const handleSimulateReply = async () => {
    if (!simLeadId) return;
    setSimulating(true);
    try {
      const res = await fetch(`${API_BASE}/api/leads/${simLeadId}/simulate-reply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ snippet: simSnippet }),
      });
      if (res.ok) {
        const data = await res.json();
        setStatusMessage(
          `Stop Sequence Rule Enforced! Inbound reply received. Automatically cancelled ${data.cancelled_followup_tasks} pending follow-up tasks!`
        );
        setSimLeadId(null);
        loadMonitorData();
      } else {
        alert("Failed to simulate reply.");
      }
    } catch {
      alert("Network error simulating reply.");
    } finally {
      setSimulating(false);
      setTimeout(() => setStatusMessage(null), 6000);
    }
  };

  // Filter calculations
  const filteredFollowups = followups.filter((f) => {
    if (filterFollowupStatus === "all") return true;
    return f.status === filterFollowupStatus;
  });

  const pendingCount = followups.filter((f) => f.status === "pending").length;
  const executedCount = followups.filter((f) => f.status === "executed").length;
  const cancelledCount = followups.filter((f) => f.status === "cancelled").length;

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-mono mb-2">
            <Activity className="h-3.5 w-3.5" />
            <span>Task 09 — Follow-up Engine & Background Worker</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Background Worker & Activity Monitor</h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time execution polling loop, automated multi-step follow-ups, stop-sequence rule enforcement, and audit logs.
          </p>
        </div>

        {/* Worker Controls */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={loadMonitorData}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-xs font-medium text-slate-300 transition-colors"
          >
            <RotateCw className={`h-3 w-3 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
          <button
            onClick={handleRunWorkerCycle}
            disabled={runningCycle}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-semibold transition-colors shadow-lg shadow-emerald-600/20"
          >
            <Play className={`h-3.5 w-3.5 ${runningCycle ? "animate-spin" : ""}`} />
            <span>{runningCycle ? "Running Cycle..." : "Run Worker Cycle"}</span>
          </button>
        </div>
      </div>

      {statusMessage && (
        <div className="p-3 bg-emerald-950/80 border border-emerald-800/80 rounded-xl text-xs text-emerald-200 flex items-center gap-2 font-medium">
          <Sparkles className="h-4 w-4 text-emerald-400 shrink-0" />
          <span>{statusMessage}</span>
        </div>
      )}

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl">
          <div className="text-slate-400">Scheduled Follow-ups</div>
          <div className="text-xl font-bold text-slate-100 font-mono mt-1">{followups.length}</div>
        </div>
        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl">
          <div className="text-slate-400">Pending Execution</div>
          <div className="text-xl font-bold text-amber-400 font-mono mt-1">{pendingCount}</div>
        </div>
        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl">
          <div className="text-slate-400">Stop-Sequence Cancelled</div>
          <div className="text-xl font-bold text-rose-400 font-mono mt-1">{cancelledCount}</div>
        </div>
        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl">
          <div className="text-slate-400">Background Jobs Logged</div>
          <div className="text-xl font-bold text-blue-400 font-mono mt-1">{jobs.length}</div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
        <button
          onClick={() => setActiveTab("followups")}
          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            activeTab === "followups" ? "bg-blue-600 text-white" : "bg-slate-900 text-slate-400 hover:text-slate-200"
          }`}
        >
          <Calendar className="h-3.5 w-3.5" />
          <span>Follow-up Sequence Queue ({followups.length})</span>
        </button>
        <button
          onClick={() => setActiveTab("jobs")}
          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            activeTab === "jobs" ? "bg-purple-600 text-white" : "bg-slate-900 text-slate-400 hover:text-slate-200"
          }`}
        >
          <Layers className="h-3.5 w-3.5" />
          <span>Background Jobs ({jobs.length})</span>
        </button>
        <button
          onClick={() => setActiveTab("activities")}
          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            activeTab === "activities" ? "bg-slate-700 text-white" : "bg-slate-900 text-slate-400 hover:text-slate-200"
          }`}
        >
          <Clock className="h-3.5 w-3.5" />
          <span>Audit Trail ({activities.length})</span>
        </button>
      </div>

      {/* TAB 1: FOLLOW-UP QUEUE */}
      {activeTab === "followups" && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-800">
            <h3 className="font-bold text-sm text-slate-100">
              Automated Follow-up Tasks ({filteredFollowups.length})
            </h3>
            <div className="flex items-center gap-1.5 text-xs">
              <span className="text-slate-500 font-mono text-[11px] mr-1">Filter:</span>
              <button
                onClick={() => setFilterFollowupStatus("all")}
                className={`px-2.5 py-1 rounded-md text-xs font-medium ${
                  filterFollowupStatus === "all" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                All
              </button>
              <button
                onClick={() => setFilterFollowupStatus("pending")}
                className={`px-2.5 py-1 rounded-md text-xs font-medium ${
                  filterFollowupStatus === "pending" ? "bg-amber-600 text-white" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Pending ({pendingCount})
              </button>
              <button
                onClick={() => setFilterFollowupStatus("cancelled")}
                className={`px-2.5 py-1 rounded-md text-xs font-medium ${
                  filterFollowupStatus === "cancelled" ? "bg-rose-600 text-white" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Cancelled ({cancelledCount})
              </button>
              <button
                onClick={() => setFilterFollowupStatus("executed")}
                className={`px-2.5 py-1 rounded-md text-xs font-medium ${
                  filterFollowupStatus === "executed" ? "bg-emerald-600 text-white" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Executed ({executedCount})
              </button>
            </div>
          </div>

          <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/60">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900 text-slate-400 font-mono text-[11px] uppercase tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-3">Lead Account</th>
                  <th className="py-2.5 px-3">Recipient Email</th>
                  <th className="py-2.5 px-3">Sequence Step</th>
                  <th className="py-2.5 px-3">Scheduled Due Date</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Reason / Details</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                {filteredFollowups.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-500 font-mono">
                      No follow-up tasks found in this view.
                    </td>
                  </tr>
                ) : (
                  filteredFollowups.map((task) => (
                    <tr key={task.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-3 px-3 font-semibold text-slate-200">
                        <div className="flex items-center gap-1.5">
                          <span>{task.business_name}</span>
                          <span className="text-[10px] font-mono text-slate-500">#{task.lead_id}</span>
                        </div>
                      </td>
                      <td className="py-3 px-3 text-slate-300 font-mono text-[11px]">
                        {task.recipient_email || "N/A"}
                      </td>
                      <td className="py-3 px-3">
                        <span className="px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
                          Step {task.sequence_step}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-slate-300 font-mono text-[11px]">
                        {new Date(task.scheduled_date).toLocaleString()}
                      </td>
                      <td className="py-3 px-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider ${
                            task.status === "executed"
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                              : task.status === "cancelled"
                              ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                              : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                          }`}
                        >
                          {task.status}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-slate-400 text-[11px]">
                        {task.cancellation_reason ? (
                          <span className="font-mono text-rose-400">
                            Stop: {task.cancellation_reason}
                          </span>
                        ) : (
                          <span className="text-slate-600">None</span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {task.status === "pending" && (
                            <>
                              <button
                                onClick={() => setSimLeadId(task.lead_id)}
                                className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-blue-400 hover:text-blue-300 text-[10px] font-medium transition-colors"
                                title="Simulate prospect replying (triggers Stop Sequence Rule)"
                              >
                                Test Reply
                              </button>
                              <button
                                onClick={() => handleCancelTask(task.id)}
                                className="px-2 py-1 rounded bg-rose-950/60 hover:bg-rose-900 text-rose-300 text-[10px] font-medium transition-colors"
                                title="Cancel scheduled task"
                              >
                                Cancel
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 2: BACKGROUND JOBS HISTORY */}
      {activeTab === "jobs" && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <h3 className="font-bold text-sm text-slate-100">
              Background Job Execution History ({jobs.length})
            </h3>
            <span className="text-xs font-mono text-slate-500">Native Async Worker</span>
          </div>

          <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/60">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900 text-slate-400 font-mono text-[11px] uppercase tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-3">Job ID</th>
                  <th className="py-2.5 px-3">Job Type</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Progress</th>
                  <th className="py-2.5 px-3">Created</th>
                  <th className="py-2.5 px-3">Completed</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                {jobs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-slate-500 font-mono">
                      No background jobs recorded yet.
                    </td>
                  </tr>
                ) : (
                  jobs.map((job) => (
                    <tr key={job.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-3 px-3 font-mono font-bold text-slate-300">
                        #{job.id}
                      </td>
                      <td className="py-3 px-3 font-mono text-slate-200 capitalize">
                        {job.job_type.replace("_", " ")}
                      </td>
                      <td className="py-3 px-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider ${
                            job.status === "completed"
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                              : job.status === "failed"
                              ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                              : "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                          }`}
                        >
                          {job.status}
                        </span>
                      </td>
                      <td className="py-3 px-3 w-40">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                            <div
                              className="h-full bg-emerald-500 rounded-full transition-all"
                              style={{ width: `${job.progress_pct}%` }}
                            />
                          </div>
                          <span className="text-[10px] font-mono text-slate-400">{job.progress_pct}%</span>
                        </div>
                      </td>
                      <td className="py-3 px-3 text-slate-400 font-mono text-[11px]">
                        {new Date(job.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                      </td>
                      <td className="py-3 px-3 text-slate-400 font-mono text-[11px]">
                        {job.completed_at
                          ? new Date(job.completed_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
                          : "In progress"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: AUDIT TRAIL */}
      {activeTab === "activities" && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <h3 className="font-bold text-sm text-slate-100">
              Audit Trail Activity Log ({activities.length})
            </h3>
            <span className="text-xs font-mono text-slate-500">Immutable Compliance Log</span>
          </div>

          <div className="space-y-2 max-h-[700px] overflow-y-auto pr-1">
            {activities.length === 0 ? (
              <div className="p-12 text-center text-xs text-slate-500 font-mono">No logged activity yet.</div>
            ) : (
              activities.map((act) => (
                <div
                  key={act.id}
                  className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80 flex items-start justify-between gap-3 text-xs"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[11px] px-1.5 py-0.5 rounded bg-slate-800 text-blue-400 uppercase font-semibold">
                        {act.action.replace("_", " ")}
                      </span>
                      <span className="text-slate-400">
                        {act.entity_type} #{act.entity_id}
                      </span>
                    </div>
                    {act.details && Object.keys(act.details).length > 0 && (
                      <p className="text-slate-300 font-mono text-[11px]">
                        {JSON.stringify(act.details)}
                      </p>
                    )}
                  </div>

                  <span className="text-[11px] text-slate-500 font-mono shrink-0 flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {new Date(act.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Stop Sequence Inbound Reply Simulator Modal */}
      {simLeadId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-lg bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-2 text-blue-400 pb-2 border-b border-slate-800">
              <Mail className="h-5 w-5" />
              <h3 className="text-base font-bold text-slate-100">Simulate Inbound Prospect Reply</h3>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              When an inbound email is received from this prospect, the application triggers the{" "}
              <strong className="text-rose-400">STOP SEQUENCE RULE</strong>: automatically cancelling all pending
              follow-up emails and moving the lead stage to &quot;replied&quot;.
            </p>

            <div className="space-y-1 text-xs">
              <label className="text-[11px] font-mono text-slate-400">Reply Snippet / Message Content:</label>
              <textarea
                rows={3}
                value={simSnippet}
                onChange={(e) => setSimSnippet(e.target.value)}
                className="w-full p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-blue-500"
              />
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-800">
              <button
                onClick={() => setSimLeadId(null)}
                className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-300"
              >
                Cancel
              </button>
              <button
                onClick={handleSimulateReply}
                disabled={simulating}
                className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-lg shadow-blue-600/20"
              >
                <Send className="h-3 w-3" />
                <span>{simulating ? "Processing..." : "Trigger Inbound Reply"}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
