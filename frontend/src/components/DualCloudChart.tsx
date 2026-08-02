import { useState } from "react"
import { ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine, ResponsiveContainer } from "recharts"
import { useQuery } from "@tanstack/react-query"
type CloudView = "both" | "azure" | "openstack"
type Horizon = 7 | 14 | 30
const COLORS = { azure: "#00A8FF", openstack: "#FF7A3C", budget: "#EF4444", grid: "#1C2B45" }
const fetchForecast = async (cloud: CloudView, horizon: Horizon, budget: number) => {
  const c = cloud === "both" ? "combined" : cloud
  const r = await fetch(`/api/v1/forecast/${c}/${horizon}?budget=${budget}`)
  return r.json()
}
export function DualCloudForecastChart({ budgetUSD = 100_000, className = "" }: { budgetUSD?: number, className?: string }) {
  const [view, setView] = useState<CloudView>("both")
  const [horizon, setHorizon] = useState<Horizon>(30)
  const { data, isLoading } = useQuery({ queryKey: ["forecast", view, horizon, budgetUSD], queryFn: () => fetchForecast(view, horizon, budgetUSD), refetchInterval: 60_000 })
  const chartData = data?.azure?.dates?.map((date: string, i: number) => ({ date, azure_actual: data.azure?.actual?.[i] ?? null, azure_forecast: data.azure?.predicted?.[i] ?? null, azure_upper: data.azure?.upper?.[i] ?? null, os_actual: data.openstack?.actual?.[i] ?? null, os_forecast: data.openstack?.predicted?.[i] ?? null, os_upper: data.openstack?.upper?.[i] ?? null })) ?? []
  return (
    <div className={`rounded-xl border border-gray-800 bg-gray-950 p-6 ${className}`}>
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <h3 className="font-semibold text-white text-lg">Dual-Cloud Cost Forecast</h3>
        <div className="flex gap-2 flex-wrap">
          {(["both","azure","openstack"] as CloudView[]).map(v => <button key={v} onClick={()=>setView(v)} className={`px-3 py-1 rounded text-xs font-mono uppercase ${view===v?"bg-teal-900 text-teal-300 border border-teal-600":"bg-gray-900 text-gray-500 border border-gray-700"}`}>{v}</button>)}
          {([7,14,30] as Horizon[]).map(h => <button key={h} onClick={()=>setHorizon(h)} className={`px-3 py-1 rounded text-xs font-mono ${horizon===h?"bg-blue-900 text-blue-300 border border-blue-600":"bg-gray-900 text-gray-500 border border-gray-700"}`}>{h}d</button>)}
        </div>
      </div>
      {isLoading ? <div className="h-64 flex items-center justify-center text-gray-500">Loading...</div> : (
        <ResponsiveContainer width="100%" height={280}>
          <ComposedChart data={chartData}>
            <CartesianGrid stroke={COLORS.grid} strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{fill:"#6E8AAA",fontSize:10}} tickFormatter={v=>v.slice(5)} />
            <YAxis tick={{fill:"#6E8AAA",fontSize:10}} tickFormatter={v=>`$${(v/1000).toFixed(0)}K`} />
            <Tooltip contentStyle={{background:"#0B1120",border:"1px solid #1C2B45",borderRadius:8}} />
            <Legend iconType="line" wrapperStyle={{fontSize:11}} />
            {(view==="both"||view==="azure") && <><Area dataKey="azure_upper" fill={`${COLORS.azure}15`} stroke="none" legendType="none" /><Line name="Azure Actual" dataKey="azure_actual" stroke={COLORS.azure} strokeWidth={2.5} dot={false} /><Line name="Azure Forecast" dataKey="azure_forecast" stroke={COLORS.azure} strokeWidth={2} strokeDasharray="6 3" dot={false} /></>}
            {(view==="both"||view==="openstack") && <><Area dataKey="os_upper" fill={`${COLORS.openstack}12`} stroke="none" legendType="none" /><Line name="OpenStack Actual" dataKey="os_actual" stroke={COLORS.openstack} strokeWidth={2.5} dot={false} /><Line name="OpenStack Forecast" dataKey="os_forecast" stroke={COLORS.openstack} strokeWidth={2} strokeDasharray="6 3" dot={false} /></>}
            <ReferenceLine y={budgetUSD/30} stroke={COLORS.budget} strokeDasharray="8 4" label={{value:"Budget/day",fill:COLORS.budget,fontSize:10}} />
          </ComposedChart>
        </ResponsiveContainer>
      )}
      {data?.recommendation && <div className="mt-4 rounded-lg border border-teal-800 bg-teal-950/50 p-3 text-teal-300 text-sm">💡 {data.recommendation}</div>}
    </div>
  )
}
