import { useState, useEffect } from "react"

const SI = ({ slug, hex = "ffffff", size = 20 }) => (
  <img src={`https://cdn.simpleicons.org/${slug}/${hex}`} width={size} height={size} alt={slug}
    style={{ display:"block", flexShrink:0 }} onError={e => { e.currentTarget.style.opacity="0" }}/>
)

const VLLMIcon = ({ size=20 }) => (
  <svg width={size} height={size} viewBox="0 0 28 28">
    <rect width="28" height="28" rx="6" fill="#7C3AED"/>
    <path d="M6 20 L14 8 L22 20" stroke="#C4B5FD" strokeWidth="2.5" fill="none" strokeLinejoin="round"/>
    <path d="M10 15 L18 15" stroke="#C4B5FD" strokeWidth="2" strokeLinecap="round"/>
    <circle cx="14" cy="8" r="2" fill="#A78BFA"/>
  </svg>
)

const TimescaleIcon = ({ size=20 }) => (
  <svg width={size} height={size} viewBox="0 0 28 28">
    <ellipse cx="14" cy="8" rx="10" ry="4" fill="#FDB515" stroke="#E5A000" strokeWidth="1"/>
    <path d="M4 8 L4 20 C4 22.2 8.5 24 14 24 C19.5 24 24 22.2 24 20 L24 8" fill="rgba(253,181,21,0.25)" stroke="#E5A000" strokeWidth="1"/>
    <ellipse cx="14" cy="20" rx="10" ry="4" fill="#FDB515" stroke="#E5A000" strokeWidth="1"/>
    <circle cx="14" cy="14" r="6" fill="#100F00" stroke="#E5A000" strokeWidth="1"/>
    <path d="M14 10 L14 14 L17 16" stroke="#FDB515" strokeWidth="1.5" strokeLinecap="round" fill="none"/>
  </svg>
)

const CeilometerIcon = ({ size=20 }) => (
  <svg width={size} height={size} viewBox="0 0 28 28">
    <rect width="28" height="28" rx="6" fill="#4A0080"/>
    <circle cx="14" cy="14" r="8" fill="none" stroke="#C084FC" strokeWidth="1.5"/>
    <circle cx="14" cy="14" r="4" fill="none" stroke="#A855F7" strokeWidth="1"/>
    <circle cx="14" cy="14" r="2" fill="#C084FC"/>
    <path d="M14 6 L14 8 M14 20 L14 22 M6 14 L8 14 M20 14 L22 14" stroke="#C084FC" strokeWidth="1.5" strokeLinecap="round"/>
  </svg>
)

const GnocchiIcon = ({ size=20 }) => (
  <svg width={size} height={size} viewBox="0 0 28 28">
    <rect width="28" height="28" rx="6" fill="#0A4E8C"/>
    <path d="M5 18 C8 12 12 10 14 14 C16 18 20 10 23 13" stroke="#5BB8F5" strokeWidth="2" fill="none" strokeLinecap="round"/>
    <path d="M5 13 C9 7 13 12 14 9 C15 7 20 6 23 9" stroke="#93D3F8" strokeWidth="1.5" fill="none" strokeLinecap="round" opacity="0.7"/>
    <circle cx="23" cy="9" r="2" fill="#5BB8F5"/><circle cx="23" cy="13" r="2" fill="#5BB8F5"/>
  </svg>
)

const HeatIcon = ({ size=20 }) => (
  <svg width={size} height={size} viewBox="0 0 28 28">
    <rect width="28" height="28" rx="6" fill="#7A1500"/>
    <path d="M9 22 C9 16 13 16 13 10 C13 16 17 16 17 22" stroke="#FF6B35" strokeWidth="2.5" fill="none" strokeLinecap="round"/>
    <path d="M5 22 C5 15 9 13 9 8" stroke="#FF4500" strokeWidth="1.5" fill="none" strokeLinecap="round" opacity="0.6"/>
    <path d="M17 22 C17 15 21 13 21 8" stroke="#FF4500" strokeWidth="1.5" fill="none" strokeLinecap="round" opacity="0.6"/>
  </svg>
)

const C = {
  az:"#0078D4", az2:"#00A8FF", azBg:"rgba(0,120,212,0.09)", azBd:"rgba(0,120,212,0.38)",
  os:"#ED1944", os2:"#FF6070", osBg:"rgba(237,25,68,0.09)", osBd:"rgba(237,25,68,0.38)",
  teal:"#00C9A7", teal2:"#00F5C9", tBg:"rgba(0,201,167,0.08)", tBd:"rgba(0,201,167,0.30)",
  bg:"#060B14", s1:"#0C1525", s2:"#111E35", bd:"#1A2D48", bd2:"#243A5A",
  txt:"#B8D0E8", muted:"#5A7898",
  kafka:"#FF6B2B", kBg:"rgba(255,107,43,0.10)", kBd:"rgba(255,107,43,0.38)",
}

const FlowDot = ({ color }) => (
  <div style={{ width:6, height:6, borderRadius:"50%", background:color,
    boxShadow:`0 0 6px ${color}`, animation:"blink 1.8s ease-in-out infinite", flexShrink:0 }}/>
)

const Tag = ({ label, color }) => (
  <span style={{ fontFamily:"'Fira Code',monospace", fontSize:8, padding:"2px 5px", borderRadius:3,
    background:color+"22", color:color }}>{label}</span>
)

const Node = ({ icon, label, sub, color, bg, bd, pulse, selected, onClick }) => (
  <div onClick={onClick} style={{
    display:"flex", alignItems:"center", gap:8, padding:"7px 10px",
    borderRadius:9, cursor:"pointer", position:"relative", overflow:"hidden",
    background: selected ? color+"25" : bg,
    border:`1px solid ${selected ? color : bd}`,
    boxShadow: selected ? `0 0 14px ${color}55` : "none",
    transition:"all 0.18s",
  }}>
    {pulse && <div style={{ position:"absolute", top:5, right:5, width:5, height:5,
      borderRadius:"50%", background:color, boxShadow:`0 0 6px ${color}`,
      animation:"blink 1.8s ease-in-out infinite" }}/>}
    <div style={{flexShrink:0}}>{icon}</div>
    <div>
      <div style={{ fontFamily:"'Fira Code',monospace", fontSize:10.5, fontWeight:700,
        color: selected ? color : C.txt, lineHeight:1.2 }}>{label}</div>
      {sub && <div style={{ fontFamily:"'Fira Code',monospace", fontSize:8.5, color:C.muted, lineHeight:1.3, marginTop:1 }}>{sub}</div>}
    </div>
  </div>
)

const BigNode = ({ icon, label, sub, color, bg, bd, selected, onClick, minW=118 }) => (
  <div onClick={onClick} style={{
    padding:"10px 12px", borderRadius:10, cursor:"pointer",
    background: selected ? color+"25" : bg,
    border:`1px solid ${selected ? color : bd}`,
    boxShadow: selected ? `0 0 16px ${color}55` : "none",
    transition:"all 0.18s", display:"flex", flexDirection:"column",
    alignItems:"center", gap:5, minWidth:minW,
  }}>
    {icon}
    <div style={{textAlign:"center"}}>
      <div style={{ fontFamily:"'Fira Code',monospace", fontSize:10, fontWeight:700,
        color: selected ? color : C.txt }}>{label}</div>
      {sub && <div style={{ fontFamily:"'Fira Code',monospace", fontSize:8, color:C.muted, marginTop:1 }}>{sub}</div>}
    </div>
  </div>
)

const Arrow = ({ color=C.teal }) => (
  <div style={{display:"flex",flexDirection:"column",alignItems:"center",margin:"2px 0"}}>
    <div style={{width:1.5,height:16,background:`linear-gradient(180deg,${color}00,${color})`}}/>
    <svg width="8" height="5" viewBox="0 0 8 5"><path d="M0 0 L4 5 L8 0" fill={color}/></svg>
  </div>
)

const CloudBox = ({ title, color, bg, bd, logoSlug, logoHex, children }) => (
  <div style={{ borderRadius:14, border:`1.5px solid ${bd}`, background:bg,
    padding:14, flex:1, backdropFilter:"blur(4px)" }}>
    <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:11}}>
      <SI slug={logoSlug} hex={logoHex} size={18}/>
      <span style={{fontFamily:"'Oxanium',sans-serif",fontSize:10,fontWeight:700,
        letterSpacing:2.5,textTransform:"uppercase",color}}>{title}</span>
    </div>
    {children}
  </div>
)

export default function ArchDiagram() {
  const [sel, setSel] = useState(null)
  const [flows, setFlows] = useState([])

  useEffect(() => {
    const id = setInterval(() => {
      const src = Math.random() > 0.5 ? "azure" : "openstack"
      setFlows(f => [...f.slice(-5), {id:Math.random(), src, t:Date.now()}])
    }, 1200)
    return () => clearInterval(id)
  }, [])

  const toggle = k => setSel(s => s===k ? null : k)

  return (
    <div style={{background:C.bg, minHeight:"100vh", fontFamily:"'DM Sans',system-ui,sans-serif", padding:"20px 16px 36px", overflowX:"hidden"}}>

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Oxanium:wght@600;700;800&family=DM+Sans:wght@400;500;600&family=Fira+Code:wght@400;500;600&display=swap');
        @keyframes blink{0%,100%{opacity:1}50%{opacity:0.2}}
        @keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-4px)}}
        * { box-sizing:border-box; }
      `}</style>

      {/* Ambient glows */}
      <div style={{position:"fixed",top:"-10%",left:"20%",width:380,height:380,borderRadius:"50%",background:"radial-gradient(circle,rgba(0,120,212,0.05),transparent 70%)",pointerEvents:"none",zIndex:0}}/>
      <div style={{position:"fixed",top:"40%",right:"5%",width:300,height:300,borderRadius:"50%",background:"radial-gradient(circle,rgba(237,25,68,0.05),transparent 70%)",pointerEvents:"none",zIndex:0}}/>
      <div style={{position:"fixed",inset:0,zIndex:0,pointerEvents:"none",backgroundImage:"radial-gradient(circle,rgba(0,168,255,0.04) 1px,transparent 1px)",backgroundSize:"26px 26px"}}/>

      <div style={{position:"relative",zIndex:1,maxWidth:960,margin:"0 auto"}}>

        {/* HEADER */}
        <div style={{textAlign:"center",marginBottom:24}}>
          <div style={{fontFamily:"'Fira Code',monospace",fontSize:9,letterSpacing:4,color:C.teal,textTransform:"uppercase",marginBottom:6}}>
            Production Architecture · Dual-Cloud · v2.0
          </div>
          <h1 style={{fontFamily:"'Oxanium',sans-serif",fontSize:24,fontWeight:800,color:"#fff",margin:0}}>
            AI FinOps Cost Intelligence Portal
          </h1>
          <div style={{display:"flex",justifyContent:"center",gap:20,marginTop:8,flexWrap:"wrap"}}>
            {[[C.az2,"Azure Cloud — OpenAI · Foundry · ML"],[C.os2,"OpenStack — vLLM · Ceilometer · Nova"],[C.teal,"Shared — Kafka · FastAPI · React"]].map(([clr,lbl])=>(
              <span key={lbl} style={{fontFamily:"'Fira Code',monospace",fontSize:9,color:clr,display:"flex",alignItems:"center",gap:5}}>
                <span style={{width:8,height:8,borderRadius:2,background:clr,display:"inline-block"}}/>
                {lbl}
              </span>
            ))}
          </div>
        </div>

        {/* ROW 1 — CLOUD BOXES */}
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12}}>

          {/* AZURE */}
          <CloudBox title="Azure Cloud" color={C.az2} bg={C.azBg} bd={C.azBd} logoSlug="microsoftazure" logoHex="0078D4">
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:5}}>
              <Node label="Azure OpenAI" sub="GPT-4o · o3-mini · Embeddings" color={C.az2} bg={C.s1} bd={C.azBd} selected={sel==="aoai"} onClick={()=>toggle("aoai")} icon={<SI slug="microsoftazure" hex="00A8FF" size={15}/>}/>
              <Node label="AI Foundry" sub="Agents · Fine-tune · Evals" color={C.az2} bg={C.s1} bd={C.azBd} selected={sel==="foundry"} onClick={()=>toggle("foundry")} icon={<SI slug="microsoftazure" hex="1E90FF" size={15}/>}/>
              <Node label="Azure ML" sub="GPU Clusters · Endpoints" color={C.az2} bg={C.s1} bd={C.azBd} selected={sel==="azml"} onClick={()=>toggle("azml")} icon={<SI slug="microsoftazure" hex="0078D4" size={15}/>}/>
              <Node label="Cognitive SVCs" sub="Vision · Speech · Search" color={C.az2} bg={C.s1} bd={C.azBd} selected={sel==="cog"} onClick={()=>toggle("cog")} icon={<SI slug="microsoftazure" hex="0052A0" size={15}/>}/>
              <Node label="Cost Mgmt API" sub="Daily billing rollups" color={C.az2} bg={C.s1} bd={C.azBd} selected={sel==="costmgmt"} onClick={()=>toggle("costmgmt")} icon={<SI slug="microsoftazure" hex="003D7A" size={15}/>}/>
              <Node label="Azure Monitor" sub="Metrics · Logs · 5min lag" color={C.az2} bg={C.s1} bd={C.azBd} selected={sel==="azmon"} onClick={()=>toggle("azmon")} icon={<SI slug="microsoftazure" hex="4DB8FF" size={15}/>}/>
            </div>
            <div style={{marginTop:8}}>
              <Arrow color={C.az2}/>
              <Node label="azure-ingestor" sub="FastAPI :8001 · APScheduler · 5 min poll" color={C.az2} bg={C.s2} bd={C.azBd} pulse selected={sel==="az-ing"} onClick={()=>toggle("az-ing")} icon={<SI slug="fastapi" hex="00A8FF" size={17}/>}/>
            </div>
          </CloudBox>

          {/* OPENSTACK */}
          <CloudBox title="OpenStack Private Cloud" color={C.os2} bg={C.osBg} bd={C.osBd} logoSlug="openstack" logoHex="ED1944">
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:5}}>
              <Node label="vLLM" sub="OpenAI-compat · :8000/metrics" color={C.os2} bg={C.s1} bd={C.osBd} selected={sel==="vllm"} onClick={()=>toggle("vllm")} icon={<VLLMIcon size={15}/>}/>
              <Node label="Ollama" sub="Local model server · REST" color={C.os2} bg={C.s1} bd={C.osBd} selected={sel==="ollama"} onClick={()=>toggle("ollama")} icon={<SI slug="ollama" hex="FFFFFF" size={15}/>}/>
              <Node label="Ceilometer" sub="Usage metering · Polling" color={C.os2} bg={C.s1} bd={C.osBd} selected={sel==="ceil"} onClick={()=>toggle("ceil")} icon={<CeilometerIcon size={15}/>}/>
              <Node label="Gnocchi" sub="Aggregated metric store" color={C.os2} bg={C.s1} bd={C.osBd} selected={sel==="gnoc"} onClick={()=>toggle("gnoc")} icon={<GnocchiIcon size={15}/>}/>
              <Node label="Nova GPU" sub="DCGM Exporter · Prometheus" color={C.os2} bg={C.s1} bd={C.osBd} selected={sel==="nova"} onClick={()=>toggle("nova")} icon={<SI slug="nvidia" hex="76B900" size={15}/>}/>
              <Node label="Magnum + Heat" sub="K8s on OS · Orchestration" color={C.os2} bg={C.s1} bd={C.osBd} selected={sel==="magnum"} onClick={()=>toggle("magnum")} icon={<HeatIcon size={15}/>}/>
            </div>
            <div style={{marginTop:8}}>
              <Arrow color={C.os2}/>
              <Node label="openstack-ingestor" sub="FastAPI :8002 · openstacksdk · httpx" color={C.os2} bg={C.s2} bd={C.osBd} pulse selected={sel==="os-ing"} onClick={()=>toggle("os-ing")} icon={<SI slug="fastapi" hex="FF6070" size={17}/>}/>
            </div>
          </CloudBox>
        </div>

        {/* KAFKA */}
        <div style={{display:"flex",flexDirection:"column",alignItems:"center",gap:3,marginTop:6}}>
          <div style={{display:"flex",gap:180}}>
            <Arrow color={C.az2}/>
            <Arrow color={C.os2}/>
          </div>
          <div style={{
            background:C.kBg, border:`1.5px solid ${C.kBd}`,
            borderRadius:12, padding:"13px 32px",
            display:"flex", alignItems:"center", gap:14,
            boxShadow:"0 0 28px rgba(255,107,43,0.14)",
            width:"100%", maxWidth:640,
          }}>
            <SI slug="apachekafka" hex="FF6B2B" size={34}/>
            <div style={{flex:1}}>
              <div style={{fontFamily:"'Oxanium',sans-serif",fontSize:17,fontWeight:700,color:C.kafka}}>Apache Kafka</div>
              <div style={{display:"flex",gap:5,marginTop:4,flexWrap:"wrap"}}>
                {[["azure.*",C.az2],["openstack.*",C.os2],["ai.costs.unified",C.teal],["ai.anomalies","#F59E0B"]].map(([t,c])=>(
                  <Tag key={t} label={t} color={c}/>
                ))}
              </div>
              <div style={{display:"flex",gap:4,marginTop:5,alignItems:"center"}}>
                <span style={{fontFamily:"'Fira Code',monospace",fontSize:8,color:C.muted}}>Live:</span>
                {flows.slice(-6).map(f=>(
                  <div key={f.id} style={{width:5,height:5,borderRadius:"50%",background:f.src==="azure"?C.az2:C.os2,boxShadow:`0 0 5px ${f.src==="azure"?C.az2:C.os2}`,animation:"blink 0.5s ease"}}/>
                ))}
              </div>
            </div>
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:8,textAlign:"center"}}>
              {[["17","Topics","#FF6B2B"],["8","Partitions","#F59E0B"],["7d","Retention",C.teal]].map(([v,l,c])=>(
                <div key={l}>
                  <div style={{fontFamily:"'Oxanium',sans-serif",fontSize:17,fontWeight:700,color:c}}>{v}</div>
                  <div style={{fontFamily:"'Fira Code',monospace",fontSize:7,color:C.muted}}>{l}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* PROCESSORS */}
        <div style={{display:"flex",flexDirection:"column",alignItems:"center",gap:3,marginTop:4}}>
          <Arrow color={C.teal}/>
          <div style={{width:"100%",maxWidth:640}}>
            <div style={{fontFamily:"'Fira Code',monospace",fontSize:8,color:C.muted,textAlign:"center",marginBottom:5,letterSpacing:2,textTransform:"uppercase"}}>Stream Processors</div>
            <div style={{display:"flex",gap:6,justifyContent:"center",flexWrap:"wrap"}}>
              {[
                {k:"norm", icon:<SI slug="python" hex="00C9A7" size={26}/>, label:"cost-normaliser", sub:"aiokafka · Pydantic v2", color:C.teal, bg:C.tBg, bd:C.tBd},
                {k:"token",icon:<SI slug="python" hex="00F5C9" size={26}/>, label:"token-tracker",   sub:"tiktoken · HuggingFace",color:C.teal, bg:C.tBg, bd:C.tBd},
                {k:"anom", icon:<SI slug="python" hex="00E8BB" size={26}/>, label:"anomaly-detector",sub:"Z-score · 6 rule types", color:C.teal, bg:C.tBg, bd:C.tBd},
                {k:"fore", icon:<SI slug="python" hex="00B899" size={26}/>, label:"forecast-engine", sub:"Prophet · LightGBM",     color:C.teal, bg:C.tBg, bd:C.tBd},
                {k:"rec",  icon:<SI slug="python" hex="009A80" size={26}/>, label:"recommendation", sub:"ranked · migration ROI",  color:C.teal, bg:C.tBg, bd:C.tBd},
              ].map(n=>(
                <BigNode key={n.k} {...n} selected={sel===n.k} onClick={()=>toggle(n.k)} minW={108}/>
              ))}
            </div>
          </div>
        </div>

        {/* STORAGE */}
        <div style={{display:"flex",flexDirection:"column",alignItems:"center",gap:3,marginTop:4}}>
          <Arrow color={C.teal}/>
          <div style={{width:"100%",maxWidth:640}}>
            <div style={{fontFamily:"'Fira Code',monospace",fontSize:8,color:C.muted,textAlign:"center",marginBottom:5,letterSpacing:2,textTransform:"uppercase"}}>Persistent Storage</div>
            <div style={{display:"flex",gap:8,justifyContent:"center"}}>
              <BigNode k="ts" icon={<TimescaleIcon size={30}/>} label="TimescaleDB" sub="Hypertable · Cont. Aggregates" color="#FDB515" bg="rgba(253,181,21,0.08)" bd="rgba(253,181,21,0.32)" selected={sel==="ts"} onClick={()=>toggle("ts")} minW={140}/>
              <BigNode k="ch" icon={<SI slug="clickhouse" hex="FFCC01" size={30}/>} label="ClickHouse" sub="Column store · Analytics" color="#FFCC01" bg="rgba(255,204,1,0.08)" bd="rgba(255,204,1,0.3)" selected={sel==="ch"} onClick={()=>toggle("ch")} minW={130}/>
              <BigNode k="rd" icon={<SI slug="redis" hex="FF4438" size={30}/>} label="Redis" sub="Semantic cache · 1hr TTL" color="#FF4438" bg="rgba(255,68,56,0.08)" bd="rgba(255,68,56,0.3)" selected={sel==="rd"} onClick={()=>toggle("rd")} minW={120}/>
            </div>
          </div>
        </div>

        {/* LLM GATEWAY LAYER */}
        <div style={{display:"flex",flexDirection:"column",alignItems:"center",gap:3,marginTop:6}}>
          <div style={{width:"100%",maxWidth:640}}>
            <div style={{fontFamily:"'Fira Code',monospace",fontSize:8,color:C.muted,textAlign:"center",marginBottom:5,letterSpacing:2,textTransform:"uppercase"}}>Gateway & Routing</div>
            <div style={{display:"flex",gap:6,justifyContent:"center"}}>
              <BigNode k="gw" icon={<SI slug="openai" hex="74AA9C" size={26}/>} label="llm-gateway" sub="LiteLLM · :8010" color="#74AA9C" bg="rgba(116,170,156,0.08)" bd="rgba(116,170,156,0.3)" selected={sel==="gw"} onClick={()=>toggle("gw")} minW={120}/>
              <BigNode k="mr" icon={<SI slug="fastapi" hex="A78BFA" size={26}/>} label="model-router" sub=":8011 · routing rules" color="#A78BFA" bg="rgba(167,139,250,0.08)" bd="rgba(167,139,250,0.3)" selected={sel==="mr"} onClick={()=>toggle("mr")} minW={120}/>
              <BigNode k="sc" icon={<SI slug="redis" hex="FB923C" size={26}/>} label="semantic-cache" sub=":8012 · cosine-sim" color="#FB923C" bg="rgba(251,146,60,0.08)" bd="rgba(251,146,60,0.3)" selected={sel==="sc"} onClick={()=>toggle("sc")} minW={120}/>
            </div>
          </div>
        </div>

        {/* FASTAPI BFF */}
        <div style={{display:"flex",flexDirection:"column",alignItems:"center",gap:3,marginTop:4}}>
          <Arrow color={C.teal}/>
          <div style={{
            background:C.tBg, border:`1.5px solid ${C.tBd}`,
            borderRadius:12, padding:"12px 28px",
            display:"flex", alignItems:"center", gap:14,
            boxShadow:"0 0 20px rgba(0,201,167,0.10)",
            width:"100%", maxWidth:560,
          }}>
            <SI slug="fastapi" hex="00C9A7" size={32}/>
            <div style={{flex:1}}>
              <div style={{fontFamily:"'Oxanium',sans-serif",fontSize:16,fontWeight:700,color:C.teal}}>
                FastAPI BFF <span style={{fontSize:11,fontWeight:400,color:C.muted}}>:8000</span>
              </div>
              <div style={{display:"flex",gap:4,marginTop:5,flexWrap:"wrap"}}>
                {[["GET",C.teal],["POST","#60A5FA"],["WS","#A78BFA"],["asyncpg","#FDB515"],["12 endpoints",C.teal],["REST + WebSocket",C.teal2]].map(([t,c])=>(
                  <Tag key={t} label={t} color={c}/>
                ))}
              </div>
            </div>
            <div style={{textAlign:"right",fontFamily:"'Fira Code',monospace",fontSize:8,color:C.muted}}>
              <div style={{marginBottom:2}}>uvicorn · 4 workers</div>
              <div style={{marginBottom:2}}>CORS enabled</div>
              <div>lifespan context</div>
            </div>
          </div>
        </div>

        {/* REACT DASHBOARD */}
        <div style={{display:"flex",flexDirection:"column",alignItems:"center",gap:3,marginTop:4}}>
          <Arrow color={C.teal}/>
          <div style={{
            background:"rgba(97,218,251,0.07)", border:"1.5px solid rgba(97,218,251,0.28)",
            borderRadius:12, padding:"12px 28px",
            display:"flex", alignItems:"center", gap:14,
            boxShadow:"0 0 20px rgba(97,218,251,0.08)",
            width:"100%", maxWidth:560,
          }}>
            <SI slug="react" hex="61DAFB" size={32}/>
            <div style={{flex:1}}>
              <div style={{fontFamily:"'Oxanium',sans-serif",fontSize:16,fontWeight:700,color:"#61DAFB"}}>
                React Dashboard <span style={{fontSize:11,fontWeight:400,color:C.muted}}>:5173</span>
              </div>
              <div style={{display:"flex",gap:4,marginTop:5,flexWrap:"wrap"}}>
                {[["React 18","61DAFB"],["TypeScript","3178C6"],["Recharts","61DAFB"],
                  ["TanStack","FF4154"],["Zustand","433E38"],
                  ["Tailwind","06B6D4"],["Vite","646CFF"],["shadcn/ui","18181B"]].map(([t,c])=>(
                  <Tag key={t} label={t} color={"#"+c}/>
                ))}
              </div>
            </div>
            <div style={{textAlign:"right"}}>
              <div style={{fontFamily:"'Fira Code',monospace",fontSize:9,color:C.muted,marginBottom:3}}>9 screens</div>
              <div style={{fontFamily:"'Fira Code',monospace",fontSize:9,color:C.muted,marginBottom:3}}>Live WS feed</div>
              <div style={{fontFamily:"'Fira Code',monospace",fontSize:9,color:C.muted}}>Dual-cloud toggle</div>
            </div>
          </div>
        </div>

        {/* DEPLOYMENT ROW */}
        <div style={{display:"flex",flexDirection:"column",alignItems:"center",gap:3,marginTop:6}}>
          <div style={{fontFamily:"'Fira Code',monospace",fontSize:8,color:C.muted,textAlign:"center",letterSpacing:2,textTransform:"uppercase"}}>Deployment Targets</div>
          <div style={{display:"flex",gap:8,justifyContent:"center",marginTop:4,flexWrap:"wrap"}}>
            {[
              {k:"aks",  icon:<SI slug="microsoftazure" hex="0078D4" size={24}/>, label:"AKS",          sub:"Azure Kubernetes",  color:C.az2, bg:C.azBg, bd:C.azBd},
              {k:"helm", icon:<SI slug="helm" hex="326CE5" size={24}/>,           label:"Helm Charts",  sub:"values-azure / os", color:"#326CE5", bg:"rgba(50,108,229,0.08)", bd:"rgba(50,108,229,0.3)"},
              {k:"k3s",  icon:<SI slug="openstack" hex="ED1944" size={24}/>,      label:"Magnum / k3s", sub:"OpenStack K8s",     color:C.os2, bg:C.osBg, bd:C.osBd},
              {k:"docker",icon:<SI slug="docker" hex="2496ED" size={24}/>,        label:"Docker",       sub:"12 images",         color:"#2496ED", bg:"rgba(36,150,237,0.08)", bd:"rgba(36,150,237,0.3)"},
              {k:"k8s",  icon:<SI slug="kubernetes" hex="326CE5" size={24}/>,     label:"Kubernetes",   sub:"namespaced · HPA",  color:"#326CE5", bg:"rgba(50,108,229,0.08)", bd:"rgba(50,108,229,0.3)"},
            ].map(n=>(
              <BigNode key={n.k} {...n} selected={sel===n.k} onClick={()=>toggle(n.k)} minW={100}/>
            ))}
          </div>
        </div>

        {/* STATS FOOTER */}
        <div style={{
          display:"grid", gridTemplateColumns:"repeat(6,1fr)", gap:8, marginTop:20,
          background:C.s1, border:`1px solid ${C.bd}`, borderRadius:12, padding:"14px 20px",
        }}>
          {[
            ["12","Microservices","#fff"],
            ["2","Clouds",C.teal],
            ["17","Kafka Topics","#FF6B2B"],
            ["3","DBs + Cache","#FDB515"],
            ["65%","Avg Savings","#36C758"],
            ["30d","Forecast","#A78BFA"],
          ].map(([v,l,c])=>(
            <div key={l} style={{textAlign:"center"}}>
              <div style={{fontFamily:"'Oxanium',sans-serif",fontSize:20,fontWeight:800,color:c}}>{v}</div>
              <div style={{fontFamily:"'Fira Code',monospace",fontSize:8,color:C.muted,marginTop:2}}>{l}</div>
            </div>
          ))}
        </div>

      </div>

      {/* SELECTED TOOLTIP */}
      {sel && (
        <div style={{
          position:"fixed",bottom:16,right:16,background:C.s1,border:`1px solid ${C.tBd}`,
          borderRadius:10,padding:"10px 14px",zIndex:200,maxWidth:220,
          boxShadow:"0 8px 32px rgba(0,0,0,0.6)",
        }}>
          <div style={{fontFamily:"'Fira Code',monospace",fontSize:9,color:C.teal,marginBottom:4}}>▸ SELECTED</div>
          <div style={{fontFamily:"'Oxanium',sans-serif",fontSize:13,fontWeight:700,color:"#fff"}}>{sel}</div>
          <button onClick={()=>setSel(null)}
            style={{position:"absolute",top:8,right:10,background:"none",border:"none",color:C.muted,cursor:"pointer",fontSize:13}}>✕</button>
        </div>
      )}
    </div>
  )
}
