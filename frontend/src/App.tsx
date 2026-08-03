import { useState } from "react"
import { useCloudStore } from "./stores/cloudStore"
import { DualCloudForecastChart } from "./components/DualCloudChart"
import { useLiveCosts, useLiveAnomalies } from "./hooks/useLiveStream"
import { useQuery } from "@tanstack/react-query"

type Page = "overview" | "forecast" | "anomalies" | "gpu" | "savings"

const CLOUD_COLORS = { azure: "text-blue-400", openstack: "text-orange-400", all: "text-teal-400" }

export default function App() {
  const [page, setPage] = useState<Page>("overview")
  const { cloud, setCloud, period, setPeriod } = useCloudStore()
  const { items: liveCosts, connected: costsConnected } = useLiveCosts()
  const { items: liveAnomalies } = useLiveAnomalies()

  const { data: summary } = useQuery({
    queryKey: ["summary", cloud, period],
    queryFn:  () => fetch(`/api/v1/costs/summary?cloud=${cloud}&period=${period}`).then(r => r.json()),
    refetchInterval: 60_000,
  })

  const totalCost = summary?.data?.reduce((s: number, r: any) => s + (r.total_usd || 0), 0) ?? 0
  const azureCost = summary?.data?.filter((r: any) => r.cloud === "azure")
                              .reduce((s: number, r: any) => s + (r.total_usd || 0), 0) ?? 0
  const osCost    = totalCost - azureCost

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/80 backdrop-blur px-6 py-3 flex items-center gap-4 sticky top-0 z-50">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-orange-600 flex items-center justify-center text-white font-bold text-xs">AI</div>
          <span className="font-semibold text-white">FinOps Portal</span>
          <span className="text-gray-500 text-xs font-mono">Azure + OpenStack</span>
        </div>
        <div className="flex gap-1 ml-4">
          {(["all","azure","openstack"] as const).map(c => (
            <button key={c} onClick={() => setCloud(c)}
              className={`px-3 py-1 rounded text-xs font-mono uppercase transition-colors
                ${cloud === c ? "bg-gray-700 text-white" : "text-gray-500 hover:text-gray-300"}`}>
              {c}
            </button>
          ))}
        </div>
        <div className="ml-auto flex items-center gap-4 text-xs font-mono text-gray-500">
          <span className={costsConnected ? "text-green-400" : "text-red-400"}>
            {costsConnected ? "● LIVE" : "○ DISCONNECTED"}
          </span>
          {liveAnomalies.length > 0 && (
            <span className="text-red-400 animate-pulse">⚠ {liveAnomalies.length} anomalies</span>
          )}
        </div>
      </header>

      <div className="flex flex-1">
        {/* Sidebar */}
        <nav className="w-52 border-r border-gray-800 bg-gray-900/50 flex flex-col gap-1 p-3">
          {([
            ["overview",  "📊", "Overview"],
            ["forecast",  "📈", "Forecast"],
            ["anomalies", "⚠️", "Anomalies"],
            ["gpu",       "🖥️", "GPU Grid"],
            ["savings",   "💰", "Savings Lab"],
          ] as [Page, string, string][]).map(([p, icon, label]) => (
            <button key={p} onClick={() => setPage(p)}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-left transition-colors
                ${page === p ? "bg-gray-800 text-white" : "text-gray-500 hover:text-gray-300 hover:bg-gray-800/50"}`}>
              <span>{icon}</span> {label}
            </button>
          ))}
        </nav>

        {/* Main */}
        <main className="flex-1 p-6 overflow-auto">
          {page === "overview" && (
            <div className="space-y-6">
              <h1 className="text-2xl font-bold text-white">Overview — {period}</h1>
              {/* KPI Row */}
              <div className="grid grid-cols-4 gap-4">
                {[
                  { label: "Total Spend", value: `$${totalCost.toLocaleString(undefined,{maximumFractionDigits:0})}`, color: "text-white" },
                  { label: "Azure Spend",  value: `$${azureCost.toLocaleString(undefined,{maximumFractionDigits:0})}`, color: "text-blue-400" },
                  { label: "OpenStack",    value: `$${osCost.toLocaleString(undefined,{maximumFractionDigits:0})}`,    color: "text-orange-400" },
                  { label: "Live Events",  value: liveCosts.length.toString(), color: "text-teal-400" },
                ].map(kpi => (
                  <div key={kpi.label} className="rounded-xl border border-gray-800 bg-gray-900 p-4">
                    <div className={`text-2xl font-bold font-mono ${kpi.color}`}>{kpi.value}</div>
                    <div className="text-xs text-gray-500 mt-1">{kpi.label}</div>
                  </div>
                ))}
              </div>
              {/* Live feed */}
              <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
                <h3 className="font-semibold text-white mb-3 text-sm">🔴 Live Cost Events</h3>
                <div className="space-y-1 max-h-48 overflow-auto">
                  {liveCosts.slice(0, 20).map((e, i) => (
                    <div key={i} className="flex items-center gap-3 text-xs font-mono text-gray-400 border-b border-gray-800 pb-1">
                      <span className={e.cloud === "azure" ? "text-blue-400" : "text-orange-400"}>{e.cloud.toUpperCase()}</span>
                      <span className="text-gray-300">{e.team}</span>
                      <span>{e.model}</span>
                      <span className="ml-auto text-teal-400">${e.cost_usd?.toFixed(6)}</span>
                    </div>
                  ))}
                  {liveCosts.length === 0 && <p className="text-gray-600 text-xs">Waiting for events…</p>}
                </div>
              </div>
            </div>
          )}

          {page === "forecast" && (
            <div className="space-y-6">
              <h1 className="text-2xl font-bold text-white">Cost Forecast</h1>
              <DualCloudForecastChart budgetUSD={100_000} />
            </div>
          )}

          {page === "anomalies" && (
            <div className="space-y-6">
              <h1 className="text-2xl font-bold text-white">Anomaly Detection</h1>
              <div className="space-y-3">
                {liveAnomalies.map((a, i) => (
                  <div key={i} className={`rounded-lg border p-4 text-sm
                    ${a.severity === "critical" ? "border-red-700 bg-red-950/30" :
                      a.severity === "high" ? "border-orange-700 bg-orange-950/30" :
                      "border-yellow-700 bg-yellow-950/20"}`}>
                    <div className="flex items-start justify-between">
                      <div>
                        <span className="font-semibold text-white">{a.type}</span>
                        <span className={`ml-2 text-xs px-2 py-0.5 rounded font-mono
                          ${a.cloud === "azure" ? "bg-blue-900 text-blue-300" : "bg-orange-900 text-orange-300"}`}>
                          {a.cloud}
                        </span>
                      </div>
                      <span className="text-xs text-gray-500 font-mono">{a.severity?.toUpperCase()}</span>
                    </div>
                    <p className="text-gray-400 mt-1">{a.message}</p>
                  </div>
                ))}
                {liveAnomalies.length === 0 && (
                  <div className="rounded-xl border border-gray-800 p-8 text-center text-gray-500">
                    ✅ No active anomalies
                  </div>
                )}
              </div>
            </div>
          )}

          {(page === "gpu" || page === "savings") && (
            <div className="rounded-xl border border-gray-800 p-8 text-center text-gray-500">
              <p className="text-lg">🚧 {page === "gpu" ? "GPU Grid" : "Savings Lab"}</p>
              <p className="text-sm mt-2">Connect to the API endpoints:<br/>
                <code className="font-mono text-teal-400">
                  {page === "gpu" ? "/api/v1/gpu/utilisation" : "/api/v1/recommendations"}
                </code>
              </p>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
