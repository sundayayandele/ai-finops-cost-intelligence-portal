import { useEffect, useState, useRef, useCallback } from "react"
interface StreamOptions { url: string; maxItems?: number; enabled?: boolean }
export function useWebSocketStream<T>({ url, maxItems = 200, enabled = true }: StreamOptions) {
  const [items, setItems] = useState<T[]>([])
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const connect = useCallback(() => {
    if (!enabled) return
    const ws = new WebSocket(url.startsWith("ws") ? url : `ws://${window.location.host}${url}`)
    wsRef.current = ws
    ws.onopen = () => setConnected(true)
    ws.onclose = () => { setConnected(false); setTimeout(connect, 3000) }
    ws.onmessage = (e) => { try { setItems(p => [JSON.parse(e.data) as T, ...p].slice(0, maxItems)) } catch {} }
    return () => ws.close()
  }, [url, maxItems, enabled])
  useEffect(() => { return connect() }, [connect])
  return { items, connected }
}
export const useLiveCosts = (enabled = true) => useWebSocketStream<{cloud:string;cost_usd:number;team:string;model:string}>({ url: "/ws/costs/live", enabled })
export const useLiveAnomalies = (enabled = true) => useWebSocketStream<{type:string;severity:string;message:string;cloud:string}>({ url: "/ws/anomalies", enabled })
