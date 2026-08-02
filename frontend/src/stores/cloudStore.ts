import { create } from "zustand"
type Cloud = "azure" | "openstack" | "all"
type Period = "MTD" | "7d" | "30d" | "YTD"
interface CloudStore { cloud: Cloud; period: Period; team: string | null; setCloud: (c: Cloud) => void; setPeriod: (p: Period) => void; setTeam: (t: string | null) => void }
export const useCloudStore = create<CloudStore>((set) => ({ cloud: "all", period: "MTD", team: null, setCloud: (cloud) => set({ cloud }), setPeriod: (period) => set({ period }), setTeam: (team) => set({ team }) }))
