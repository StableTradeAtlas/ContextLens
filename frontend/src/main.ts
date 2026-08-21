import "maplibre-gl/dist/maplibre-gl.css";
import "./style.css";
import type { Candidate, HistoricalMapLayer, InvestigationResult } from "./types";
import type { Map as MapLibreMap } from "maplibre-gl";

type Lang = "zh" | "en";
type View = "identity" | "timeline" | "atlas" | "sources";

const app = document.querySelector<HTMLDivElement>("#app")!;
app.innerHTML = `
<div class="shell">
  <header class="topbar">
    <button class="brand" id="brandBtn" aria-label="ContextLens home"><span class="brand-mark">文</span><span><b>文脉镜 ContextLens</b><small>SHANGHAI ADDRESS DOSSIER</small></span></button>
    <div class="top-actions"><span class="service"><i id="statusDot"></i><span id="serviceText">上海图书馆官方数据</span></span><button class="ghost" id="methodBtn">方法</button><button class="ghost" id="langBtn" aria-label="Switch language">EN</button></div>
  </header>

  <main id="home" class="home">
    <section class="home-copy">
      <p class="kicker">ONE ADDRESS · FOUR ANSWERS</p>
      <h1>一条地址，<br>四个可核查答案。</h1>
      <p class="lead">它过去叫什么？这里发生过什么？今天在哪里？每个答案由哪条上海图书馆记录支撑？</p>
      <form class="search-card" id="searchForm">
        <label><span>上海旧址、路名或门牌</span><input id="addressInput" value="霞飞路436号" autocomplete="off"></label>
        <label class="era"><span>约略年代（可选）</span><input id="eraInput" value="1930年代" autocomplete="off"></label>
        <button class="primary" id="resolveBtn" type="submit">建立地址档案 →</button>
      </form>
      <div class="examples" aria-label="经过人工检查的示例">
        <span>先看一个完整案例</span>
        <button data-address="霞飞路436号" data-era="1930年代">霞飞路436号</button>
        <button data-address="外滩20号" data-era="1930年代">外滩20号</button>
        <button data-address="南京路百货公司" data-era="1940年代">南京路百货</button>
      </div>
      <div class="candidate-box" id="candidateBox"><p id="candidateMessage"></p><div id="candidateList"></div></div>
      <div class="trust-row"><span><b id="officialCount">154</b> 条官方快照记录</span><span><b>0</b> 条演示数据</span><span><b>逐条</b> 返回原始来源</span></div>
    </section>
    <section class="archive-hero" aria-label="1943 Shanghai archival map preview">
      <img src="https://iiif-cloud.princeton.edu/iiif/2/42%2F8a%2F93%2F428a930342fb4c36ae9b4ecdc57eae37%2Fintermediate_file/full/1600,/0/default.jpg" alt="1943 Plan of Shanghai archival map" id="heroArchiveImg">
      <div class="archive-shade"></div>
      <div class="archive-year">1943</div>
      <article><small>ARCHIVAL MAP · PUBLIC IIIF</small><h2>先看见史料，<br>再阅读解释。</h2><p>原图来自 Princeton University Library / AGSL。历史地图只用于辨认街道结构，不制造精确门牌。</p></article>
      <a href="https://geodiscovery.uwm.edu/catalog/princeton-8623j0184" target="_blank" rel="noopener noreferrer">打开原图记录 ↗</a>
    </section>
  </main>

  <main id="dossier" class="dossier" hidden>
    <header class="dossier-head">
      <button class="back" id="backBtn">← 新建调查</button>
      <div><p class="kicker">VERIFIED ADDRESS DOSSIER</p><h1 id="placeTitle"></h1><p id="placeSummary"></p></div>
      <div class="head-actions"><button class="secondary" id="printBtn">打印 / 保存 PDF</button><button class="primary" id="downloadBtn">下载证据档案</button></div>
    </header>
    <nav class="dossier-tabs" aria-label="地址档案四个部分">
      <button class="active" data-view="identity"><b>01</b><span>地址身份<small>旧名 → 今名</small></span></button>
      <button data-view="timeline"><b>02</b><span>发生过什么<small>按时间排列</small></span></button>
      <button data-view="atlas"><b>03</b><span>古今位置<small>原图 + 当代地图</small></span></button>
      <button data-view="sources"><b>04</b><span>证据来源<small>逐条可打开</small></span></button>
    </nav>
    <section class="view-panel" id="viewPanel"></section>
  </main>

  <div class="progress" id="progress" aria-live="polite"><div><span class="spinner"></span><p class="kicker">EVIDENCE COMPILER</p><h2 id="progressTitle">正在核对地址</h2><p id="progressText">先解析旧今路名，再连接事件、建筑和来源。</p><div class="progress-line"><i id="progressBar"></i></div></div></div>
  <div class="modal-backdrop" id="modalBackdrop"></div><aside class="modal" id="modal" aria-hidden="true"><button class="modal-close" id="modalClose" aria-label="关闭">×</button><div id="modalBody"></div></aside>
  <div class="toast" id="toast"></div>
</div>`;

const state: {lang: Lang; view: View; candidate: Candidate | null; result: InvestigationResult | null; map: MapLibreMap | null; jobId: string} = {lang:"zh", view:"identity", candidate:null, result:null, map:null, jobId:""};
const $ = <T extends HTMLElement>(id:string) => document.getElementById(id) as T;
const esc = (v:unknown) => String(v ?? "").replace(/[&<>'"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]!));
const api = async (path:string, options?:RequestInit) => { const r=await fetch(path, options); const data=await r.json(); if(!r.ok) throw new Error(data.error||"Request failed"); return data; };
const toast = (text:string) => { $("toast").textContent=text; $("toast").classList.add("open"); setTimeout(()=>$("toast").classList.remove("open"),2400); };

function setLanguage() {
  const en=state.lang==="en";
  $("langBtn").textContent=en?"中":"EN";
  $("serviceText").textContent=en?"Official Shanghai Library data":"上海图书馆官方数据";
  $("methodBtn").textContent=en?"Method":"方法";
  $("backBtn").textContent=en?"← New search":"← 新建调查";
  $("printBtn").textContent=en?"Print / save PDF":"打印 / 保存 PDF";
  $("downloadBtn").textContent=en?"Download evidence":"下载证据档案";
  if(state.result) renderView();
}

function openModal(html:string){ $("modalBody").innerHTML=html; $("modal").classList.add("open"); $("modalBackdrop").classList.add("open"); $("modal").setAttribute("aria-hidden","false"); }
function closeModal(){ $("modal").classList.remove("open"); $("modalBackdrop").classList.remove("open"); $("modal").setAttribute("aria-hidden","true"); }
function showProgress(){ $("progressBar").style.width="10%"; $("progress").classList.add("open"); }
function hideProgress(){ $("progress").classList.remove("open"); }

async function resolveAddress(address:string, era:string){
  if(!address.trim()){toast("请输入地址");return;}
  showProgress();
  try{
    const data=await api("/api/place/resolve",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({address,era_hint:era,allow_live:true})});
    hideProgress();
    if(!data.candidates?.length){ $("candidateBox").classList.add("open"); $("candidateMessage").textContent=data.guidance||"没有找到可确认的地点。请补充路名、门牌或年代。"; $("candidateList").innerHTML=""; return; }
    if(data.candidates.length===1){ await investigate(address,era,data.candidates[0]); return; }
    $("candidateBox").classList.add("open"); $("candidateMessage").textContent="这个输入可能对应多个地点，请确认：";
    $("candidateList").innerHTML=data.candidates.map((c:Candidate)=>`<button class="candidate" data-id="${esc(c.candidate_id)}"><span><b>${esc(c.display_name)}</b><small>${esc(c.match_reason)}</small></span><strong>${Math.round(c.confidence*100)}%</strong></button>`).join("");
    $("candidateList").querySelectorAll<HTMLButtonElement>(".candidate").forEach((btn,i)=>btn.onclick=()=>investigate(address,era,data.candidates[i]));
  }catch(e){hideProgress();toast(e instanceof Error?e.message:"地址解析失败");}
}

async function investigate(address:string,era:string,candidate:Candidate){
  state.candidate=candidate; showProgress(); $("progressTitle").textContent="正在建立地址档案"; $("progressText").textContent="只保留与地点直接相关且可返回来源的记录。";
  try{
    const job=await api("/api/investigations",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({address,era_hint:era,candidate,allow_live:true})}); state.jobId=job.id;
    for(let i=0;i<80;i++){
      const current=await api(`/api/investigations/${job.id}`); $("progressBar").style.width=`${Math.max(18,current.progress||i*2)}%`; if(current.message) $("progressText").textContent=current.message;
      if(current.status==="complete"){state.result=current.result;hideProgress();openDossier();return;} if(current.status==="failed") throw new Error(current.error||"调查失败"); await new Promise(r=>setTimeout(r,180));
    }
    throw new Error("调查超时");
  }catch(e){hideProgress();toast(e instanceof Error?e.message:"调查失败");}
}

function openDossier(){
  if(!state.result)return; $("candidateBox").classList.remove("open"); $("home").hidden=true; $("dossier").hidden=false; state.view="identity";
  $("placeTitle").textContent=state.result.candidate.display_name; $("placeSummary").textContent=state.result.summary;
  document.querySelectorAll<HTMLButtonElement>(".dossier-tabs button").forEach(b=>b.classList.toggle("active",b.dataset.view===state.view)); renderView(); window.scrollTo({top:0,behavior:"smooth"});
}

function renderView(){
  if(!state.result)return; if(state.map){state.map.remove();state.map=null;}
  const panel=$("viewPanel");
  if(state.view==="identity") panel.innerHTML=identityView();
  if(state.view==="timeline") panel.innerHTML=timelineView();
  if(state.view==="atlas"){panel.innerHTML=atlasView(); void initMap();}
  if(state.view==="sources") panel.innerHTML=sourcesView();
  wirePanel();
}

function identityView(){
  const r=state.result!, periods=r.candidate.name_periods||[]; const direct=r.claims?.filter((c:any)=>c.support_level==="direct")||[];
  return `<div class="identity-layout"><article class="answer-card hero-answer"><p class="answer-label">ANSWER 01 · ADDRESS IDENTITY</p><h2>${esc(r.candidate.historical_names?.[0]||r.candidate.canonical_name)} <span>→</span> ${esc(r.candidate.modern_names?.[0]||r.candidate.canonical_name)}</h2><p>${esc(r.candidate.match_reason)}</p><div class="confidence"><span>地址解析可信度</span><b>${Math.round(r.candidate.confidence*100)}%</b></div></article><section class="name-ladder"><h3>这条路如何变成今天的名字</h3>${periods.length?periods.map((p:any,i:number)=>`<div class="name-step"><b>${String(i+1).padStart(2,"0")}</b><span><strong>${esc(p.name)}</strong><small>${p.from_year||"年代待考"}${p.to_year?`—${p.to_year}`:"—至今"}</small></span></div>`).join(""):`<div class="empty">官方记录暂未提供完整更名序列。</div>`}</section><aside class="audit-card"><p class="answer-label">WHAT WE CAN SAY</p><h3>${direct.length} 条直接主张</h3>${direct.slice(0,3).map((c:any)=>`<button class="claim-link" data-evidence="${esc(c.evidence_ids?.[0]||"")}">${esc(c.text)}<span>查看证据 ↗</span></button>`).join("")}<p class="boundary">没有来源支撑的内容不会补写为故事。</p></aside></div>`;
}

function timelineView(){
  const r=state.result!, timeline=r.timeline||[];
  return `<div class="section-intro"><p class="answer-label">ANSWER 02 · WHAT HAPPENED HERE</p><h2>${timeline.length} 个可核查地点节点</h2><p>按资料中的年代排列；“年代待考”不会被强行放进确定时间线。</p></div><div class="timeline-list">${timeline.length?timeline.map((item:any,i:number)=>`<article class="timeline-card"><time>${esc(item.time_label||item.date||"年代待考")}</time><div><span class="type">${esc(item.feature_type||item.type||"地点记录")}</span><h3>${esc(item.title)}</h3><p>${esc(item.description||item.address||"")}</p><button data-evidence="${esc(item.feature_id||item.evidence_id||"")}">查看原始证据 →</button></div><b>${String(i+1).padStart(2,"0")}</b></article>`).join(""):`<div class="empty">当前地址没有足够的时间节点。</div>`}</div>${questionBlock()}`;
}

function atlasView(){
  const maps=state.result!.experience?.historical_maps||[]; const active=maps.find((m:HistoricalMapLayer)=>m.map_id==="princeton-1943")||maps[0];
  return `<div class="section-intro"><p class="answer-label">ANSWER 03 · THEN AND NOW</p><h2>历史原图与今天的位置，并排阅读。</h2><p>我们不再把未完成配准的原图伪装成精确叠加。左侧看史料，右侧负责今天的定位。</p></div><div class="atlas-grid"><figure class="archive-map"><div class="map-label"><b>${esc(active?.year||1943)}</b><span>历史原图</span></div><img src="${esc(active?.image_url)}" alt="${esc(active?.title)}"><figcaption><strong>${esc(active?.title)}</strong><span>${esc(active?.provider)} · ${esc(active?.license)}</span><a href="${esc(active?.source_url)}" target="_blank" rel="noopener noreferrer">打开馆藏记录 ↗</a></figcaption></figure><section class="modern-map"><div class="map-label"><b>${new Date().getFullYear()}</b><span>当代定位</span></div><div id="modernMap"></div><div class="map-fail" id="mapFail"><b>在线底图暂不可用</b><span>地址坐标和证据仍保留；请稍后重试底图。</span></div></section></div><div class="map-boundary"><b>使用边界</b><span>历史原图存在配准误差，不能据此声称精确门牌位置。现代地图来自 OpenFreeMap / OpenStreetMap。</span></div>`;
}

function sourcesView(){
  const evidence=state.result!.evidence||[];
    return `<div class="section-intro source-intro"><div><p class="answer-label">ANSWER 04 · SOURCE RECEIPT</p><h2>${evidence.length} 条证据，每条都能回到来源。</h2><p>官方记录与辅助公开来源分开标识；查询规模不冒充本次命中数量。</p></div><div class="source-score"><b>${state.result!.quality?.source_count||0}</b><span>可打开来源</span></div></div><div class="source-table"><div class="source-row source-head"><span>记录</span><span>数据集 / 年代</span><span>来源状态</span><span></span></div>${evidence.map((e:any)=>`<article class="source-row"><span><b>${esc(e.source_title||e.title)}</b><small>${esc(e.description||e.snippet||"")}</small></span><span>${esc(e.dataset_label||e.dataset||e.source_title||"开放数据")}<small>${esc(e.time_label||e.date||"年代待考")}</small></span><span><i></i>${e.source_mode==="live_api"?"实时官方接口":e.source_mode==="reviewed_official_snapshot"?"已核验官方快照":"公开辅助来源"}</span><button data-evidence="${esc(e.evidence_id||e.record_id)}">来源护照 →</button></article>`).join("")}</div>`;
}

function questionBlock(){return `<section class="questions"><div><p class="answer-label">THREE USEFUL QUESTIONS</p><h2>问题由当前档案决定，<br>不是泛泛聊天。</h2></div><div><button data-question="names"><b>01</b><span>这条路为什么改名？<small>只使用道路身份和名称年代回答</small></span></button><button data-question="event"><b>02</b><span>这个门牌发生过什么？<small>只使用直接地点事件回答</small></span></button><button data-question="limits"><b>03</b><span>哪些内容仍然不知道？<small>显示时间、空间和来源空白</small></span></button></div></section>`;}

function wirePanel(){
  $("viewPanel").querySelectorAll<HTMLButtonElement>("[data-evidence]").forEach(b=>b.onclick=()=>openEvidence(b.dataset.evidence||""));
  $("viewPanel").querySelectorAll<HTMLButtonElement>("[data-question]").forEach(b=>b.onclick=()=>answerQuestion(b.dataset.question||""));
}

function openEvidence(id:string){
  const r=state.result!; const e=(r.evidence||[]).find((x:any)=>x.evidence_id===id||x.record_id===id)||(r.evidence||[])[0]; if(!e){toast("没有找到对应证据");return;}
  const lineage=e.lineage||{}; openModal(`<p class="answer-label">SOURCE PASSPORT</p><h2>${esc(e.source_title||e.title)}</h2><p class="modal-lead">${esc(e.description||e.snippet||"")}</p><dl><dt>来源状态</dt><dd>${e.source_mode==="live_api"?"实时官方接口":e.source_mode==="reviewed_official_snapshot"?"已核验官方快照":"公开辅助来源"}</dd><dt>数据提供方</dt><dd>${esc(lineage.provider||e.provider||"上海图书馆")}</dd><dt>数据集</dt><dd>${esc(e.dataset_label||e.dataset||lineage.dataset||e.source_title||"开放数据")}</dd><dt>年代</dt><dd>${esc(e.time_label||e.date||"年代待考")}</dd><dt>证据编号</dt><dd>${esc(e.evidence_id||e.record_id)}</dd><dt>标准化</dt><dd>${esc(lineage.normalization||"ContextLens place investigation v1")}</dd></dl><a class="primary modal-link" href="${esc(e.source_uri||lineage.official_uri||"#")}" target="_blank" rel="noopener noreferrer">打开原始来源 ↗</a>`);
}

function answerQuestion(kind:string){
  const r=state.result!, direct=(r.claims||[]).filter((c:any)=>c.support_level==="direct"); let title="",body="";
  if(kind==="names"){title="这条路为什么改名？"; body=`官方道路实体记录显示名称经历：${(r.candidate.name_periods||[]).map((p:any)=>p.name).join(" → ")||"尚无完整序列"}。名称变化是可核查事实；具体政治或制度原因若无直接来源，不在本档案中推断。`;}
  if(kind==="event"){title="这个门牌发生过什么？"; body=direct[0]?.text||r.finding;}
  if(kind==="limits"){title="哪些内容仍然不知道？"; body=`当前空间精度：${r.quality?.uncertainty==="bounded"?"来源坐标可用":"道路范围或近似位置"}。${(r.timeline||[]).some((x:any)=>!x.start_year&&!x.date)?"部分节点年代待考。":"现有节点均有年代线索。"} 原图不用于证明精确门牌。`;}
  openModal(`<p class="answer-label">GROUNDED ANSWER</p><h2>${esc(title)}</h2><p class="modal-lead">${esc(body)}</p><p class="boundary">回答只使用当前地址档案中的记录；点击“证据来源”可逐条复核。</p>`);
}

async function initMap(){
  const container=document.getElementById("modernMap"); if(!container||!state.result)return;
  try{const maplibre=await import("maplibre-gl"); const center=state.result.map?.center||[121.4737,31.2304]; state.map=new maplibre.Map({container,style:"https://tiles.openfreemap.org/styles/liberty",center,zoom:14,attributionControl:{compact:true}}); state.map.on("load",()=>{const fc=state.result!.feature_collection; state.map!.addSource("evidence",{type:"geojson",data:fc}); state.map!.addLayer({id:"evidence-points",type:"circle",source:"evidence",paint:{"circle-radius":8,"circle-color":"#b64b38","circle-stroke-width":3,"circle-stroke-color":"#fffaf0"}}); if(state.result!.map?.bounds?.length===4){const b=state.result!.map.bounds;state.map!.fitBounds([[b[0],b[1]],[b[2],b[3]]],{padding:70,maxZoom:15});}}); state.map.on("error",()=>$("mapFail").classList.add("open"));}
  catch{$("mapFail").classList.add("open");}
}

function downloadEvidence(){if(!state.result)return;const blob=new Blob([JSON.stringify(state.result,null,2)],{type:"application/json"});const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=`ContextLens-${state.result.candidate.canonical_name}-evidence.json`;a.click();URL.revokeObjectURL(a.href);}

$("searchForm").addEventListener("submit",e=>{e.preventDefault();void resolveAddress(($("addressInput") as HTMLInputElement).value,($("eraInput") as HTMLInputElement).value);});
document.querySelectorAll<HTMLButtonElement>("[data-address]").forEach(b=>b.onclick=()=>{($("addressInput") as HTMLInputElement).value=b.dataset.address||"";($("eraInput") as HTMLInputElement).value=b.dataset.era||"";void resolveAddress(b.dataset.address||"",b.dataset.era||"");});
document.querySelectorAll<HTMLButtonElement>(".dossier-tabs button").forEach(b=>b.onclick=()=>{state.view=b.dataset.view as View;document.querySelectorAll(".dossier-tabs button").forEach(x=>x.classList.toggle("active",x===b));renderView();});
$("backBtn").onclick=()=>{$("dossier").hidden=true;$("home").hidden=false;if(state.map){state.map.remove();state.map=null;}};
$("brandBtn").onclick=()=>$("backBtn").click(); $("langBtn").onclick=()=>{state.lang=state.lang==="zh"?"en":"zh";setLanguage();};
$("methodBtn").onclick=()=>openModal(`<p class="answer-label">PRODUCT METHOD</p><h2>一个地址，四个答案。</h2><ol class="method-list"><li><b>地址身份</b><span>拆分旧路名、门牌与年代，并保留歧义。</span></li><li><b>地点事件</b><span>只连接直接出现该地点的事件和建筑。</span></li><li><b>古今位置</b><span>历史原图与现代地图并排，不伪造精确叠加。</span></li><li><b>来源护照</b><span>每条主张返回提供方、数据集、URI与标准化记录。</span></li></ol>`);
$("printBtn").onclick=()=>window.print(); $("downloadBtn").onclick=downloadEvidence; $("modalClose").onclick=closeModal; $("modalBackdrop").onclick=closeModal;
$("heroArchiveImg").addEventListener("error",()=>document.querySelector(".archive-hero")?.classList.add("image-failed"));
fetch("/api/health").then(r=>r.json()).then(h=>{$("officialCount").textContent=String(h.official_records||0);$("statusDot").classList.toggle("ok",h.ok&&!h.demo_seed_active);}).catch(()=>$("serviceText").textContent="证据服务离线");
