from __future__ import annotations

import json
import mimetypes
import os
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from app.agent import answer_question
from app.config import LOG_DIR, PROJECT_ROOT, get_settings
from app.deepseek_client import interpret_place_archive
from app.place_investigation import INVESTIGATION_STORE, hash_private_query, resolve_place
from app.storage import count_records_by_source


HOST = "127.0.0.1"
VERSION = "contextlens-memory-wormhole-1.0"
MAX_BODY = 24_000
VENDOR_DIR = PROJECT_ROOT / "vendor" / "maplibre-gl"
OHM_DATES_PATH = PROJECT_ROOT / "vendor" / "maplibre-gl-dates" / "index.js"
STATIC_DIR = PROJECT_ROOT / "app" / "static"


HTML = r'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="从一条上海旧址出发，沿时间轴重建建筑、人物与事件，并让每个结论回到真实来源。">
  <title>文脉镜 · 我的上海旧址</title>
  <link rel="stylesheet" href="/vendor/maplibre-gl.css">
  <style>
    :root {
      --paper:#f3efe5; --paper-2:#faf8f1; --ink:#11263b; --ink-2:#183b55;
      --vermillion:#a33a2b; --gold:#b18a45; --jade:#3c7168; --line:rgba(17,38,59,.16);
      --shadow:0 24px 70px rgba(21,38,53,.15); --serif:"Songti SC","STSong","Noto Serif SC",serif;
      --sans:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
    }
    *{box-sizing:border-box} html{scroll-behavior:smooth} body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans)}
    button,input,textarea,select{font:inherit} button{cursor:pointer} a{color:inherit}
    .noise{position:fixed;inset:0;pointer-events:none;z-index:40;opacity:.22;background-image:radial-gradient(rgba(17,38,59,.12) .45px,transparent .45px);background-size:5px 5px;mix-blend-mode:multiply}
    .topbar{height:74px;padding:0 clamp(20px,5vw,72px);display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line);background:rgba(250,248,241,.86);backdrop-filter:blur(16px);position:sticky;top:0;z-index:30}
    .brand{display:flex;align-items:center;gap:12px;font-weight:850}.brand-mark{width:35px;height:35px;border-radius:50%;background:conic-gradient(from 210deg,var(--ink),var(--jade),var(--gold),var(--ink));box-shadow:inset 0 0 0 7px var(--paper-2)}
    .brand small{display:block;font-size:10px;letter-spacing:.18em;color:var(--vermillion);margin-top:3px}.top-actions{display:flex;gap:8px;align-items:center}.status-dot{width:8px;height:8px;border-radius:50%;background:#78918b;box-shadow:0 0 0 5px rgba(60,113,104,.1)}
    .ghost,.primary,.secondary,.chip{border:0;border-radius:999px;padding:11px 17px;font-weight:760}.ghost{background:transparent;color:var(--ink)}.ghost:hover{background:rgba(17,38,59,.06)}
    .primary{background:var(--ink);color:#fff;box-shadow:0 9px 25px rgba(17,38,59,.2)}.primary:hover{background:#1a3e5b;transform:translateY(-1px)}.primary:disabled{opacity:.45;transform:none}
    .secondary{background:var(--paper-2);border:1px solid var(--line);color:var(--ink)}
    .hero{min-height:calc(100vh - 74px);display:grid;grid-template-columns:minmax(460px,.92fr) minmax(500px,1.08fr);overflow:hidden}
    .hero-copy{padding:clamp(44px,7vw,104px) clamp(28px,6vw,94px);display:flex;flex-direction:column;justify-content:center;position:relative}
    .kicker{font-size:12px;letter-spacing:.22em;text-transform:uppercase;color:var(--vermillion);font-weight:850;display:flex;gap:10px;align-items:center}.kicker:before{content:"";width:28px;height:1px;background:var(--vermillion)}
    h1{font-family:var(--serif);font-size:clamp(48px,6.2vw,92px);line-height:.98;letter-spacing:-.045em;margin:26px 0 22px;max-width:730px;font-weight:760}
    .lead{font-size:clamp(17px,1.4vw,21px);line-height:1.8;color:#51606b;max-width:650px;margin:0 0 34px}.lead strong{color:var(--ink)}
    .intake{background:rgba(250,248,241,.92);border:1px solid rgba(177,138,69,.36);box-shadow:var(--shadow);padding:19px;border-radius:22px;max-width:690px;position:relative;z-index:4}
    .address-row{display:grid;grid-template-columns:1fr 124px;gap:10px}.field{display:flex;flex-direction:column;gap:7px}.field label{font-size:11px;letter-spacing:.09em;color:#6e6b63;font-weight:800;text-transform:uppercase}.field input,.field textarea{width:100%;border:1px solid var(--line);background:#fffdf8;color:var(--ink);border-radius:13px;padding:15px 16px;outline:none}.field input:focus,.field textarea:focus{border-color:var(--gold);box-shadow:0 0 0 3px rgba(177,138,69,.13)}
    .memory-field{margin-top:10px}.memory-field textarea{min-height:68px;resize:vertical}.privacy{font-size:11px;color:#6e6b63;margin:7px 2px 0;display:flex;gap:6px;align-items:center}.privacy:before{content:"";width:7px;height:7px;border-radius:50%;background:var(--jade)}
    .intake-footer{display:flex;align-items:center;justify-content:space-between;gap:14px;margin-top:15px}.examples{display:flex;flex-wrap:wrap;gap:7px}.chip{padding:8px 11px;font-size:12px;background:rgba(17,38,59,.06);color:var(--ink)}.chip:hover{background:rgba(163,58,43,.11);color:var(--vermillion)}
    .hero-visual{position:relative;background:#152d42;min-height:690px;overflow:hidden}.hero-visual:before{content:"";position:absolute;inset:0;background:radial-gradient(circle at 45% 40%,rgba(177,138,69,.16),transparent 30%),linear-gradient(135deg,#0d2133,#183b55 65%,#243d49)}
    .contour{position:absolute;border:1px solid rgba(241,225,188,.18);border-radius:45% 55% 58% 42%;transform:rotate(-12deg)}.c1{width:78%;height:62%;left:6%;top:14%}.c2{width:62%;height:48%;left:15%;top:22%}.c3{width:46%;height:34%;left:23%;top:29%}.river{position:absolute;width:18%;height:130%;right:15%;top:-15%;border:1px solid rgba(123,191,187,.28);border-width:0 0 0 34px;transform:rotate(16deg);border-radius:50%}
    .hero-pin{position:absolute;left:47%;top:47%;width:22px;height:22px;border-radius:50%;background:var(--vermillion);box-shadow:0 0 0 13px rgba(163,58,43,.18),0 0 0 28px rgba(163,58,43,.08);animation:pulse 2.8s ease-out infinite}.hero-pin:after{content:"霞飞路 · 1934";position:absolute;left:34px;top:-8px;color:#f8edda;white-space:nowrap;font-family:var(--serif);font-size:18px}
    @keyframes pulse{50%{box-shadow:0 0 0 18px rgba(163,58,43,.12),0 0 0 42px transparent}}
    .archive-note{position:absolute;right:7%;bottom:9%;width:min(320px,38%);padding:22px;background:rgba(247,240,221,.92);color:var(--ink);transform:rotate(-2deg);box-shadow:0 20px 55px rgba(0,0,0,.28)}.archive-note small{color:var(--vermillion);font-weight:850;letter-spacing:.12em}.archive-note p{font-family:var(--serif);font-size:18px;line-height:1.65;margin:12px 0 0}
    .candidate-panel{display:none;max-width:690px;margin-top:16px;background:var(--paper-2);border:1px solid var(--line);border-radius:18px;padding:15px;position:relative;z-index:5}.candidate-panel.open{display:block}.candidate-head{display:flex;justify-content:space-between;gap:12px;align-items:center}.candidate-list{display:grid;gap:8px;margin-top:11px}.candidate{width:100%;text-align:left;background:#fff;border:1px solid var(--line);border-radius:13px;padding:13px;display:grid;grid-template-columns:22px 1fr auto;gap:10px;align-items:start}.candidate.selected{border-color:var(--vermillion);box-shadow:0 0 0 2px rgba(163,58,43,.1)}.candidate input{margin-top:4px}.candidate strong{display:block}.candidate span{font-size:12px;color:#6a737a;line-height:1.5}.confidence{font-size:11px!important;color:var(--jade)!important;font-weight:850}
    .result-page{display:none;min-height:100vh;background:#e9e5db}.result-page.open{display:block}.result-head{padding:24px clamp(18px,4vw,56px);background:var(--paper-2);display:flex;gap:20px;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line)}.result-title{display:flex;gap:17px;align-items:center}.result-title h2{font-family:var(--serif);font-size:clamp(26px,3vw,42px);margin:0}.result-title p{margin:5px 0 0;color:#64717a}.result-actions{display:flex;gap:8px;flex-wrap:wrap}
    .workspace{height:calc(100vh - 108px);min-height:760px;display:grid;grid-template-columns:minmax(0,1.62fr) minmax(380px,.62fr);position:relative}.map-shell{--compare:52%;position:relative;background:#183b55;overflow:hidden}.map{position:absolute;inset:0}.history-map{z-index:1}.modern-map{z-index:2;clip-path:inset(0 0 0 var(--compare));pointer-events:none}.map-shell.history-only .modern-map{clip-path:inset(0 0 0 100%)}.map-shell.modern-only .modern-map{clip-path:inset(0);pointer-events:auto}.map-shell.modern-only .history-map{pointer-events:none}.compare-divider{position:absolute;z-index:7;top:0;bottom:0;left:var(--compare);width:2px;background:rgba(255,248,231,.9);box-shadow:0 0 0 1px rgba(17,38,59,.15),0 0 30px rgba(17,38,59,.3);pointer-events:none}.compare-divider:before{content:"古";position:absolute;top:50%;left:-31px;width:29px;padding:8px 0;text-align:center;border-radius:16px 0 0 16px;background:var(--ink);color:#fff;font:800 11px var(--serif)}.compare-divider:after{content:"今";position:absolute;top:50%;left:2px;width:29px;padding:8px 0;text-align:center;border-radius:0 16px 16px 0;background:#f7f1e2;color:var(--ink);font:800 11px var(--serif)}.map-shell.history-only .compare-divider,.map-shell.modern-only .compare-divider{display:none}.map-fallback{position:absolute;z-index:3;inset:0;display:none;background:radial-gradient(circle at 50% 48%,rgba(177,138,69,.16),transparent 28%),linear-gradient(145deg,#102a3e,#24495c)}.map-fallback.open{display:block}.fallback-grid{position:absolute;inset:0;background-image:linear-gradient(rgba(242,230,203,.08) 1px,transparent 1px),linear-gradient(90deg,rgba(242,230,203,.08) 1px,transparent 1px);background-size:54px 54px}.fallback-river{position:absolute;width:22%;height:120%;right:17%;top:-10%;border-left:38px solid rgba(95,159,164,.2);transform:rotate(15deg);border-radius:50%}.fallback-pins{position:absolute;inset:0}.fallback-pin{position:absolute;width:18px;height:18px;border:3px solid #f7edda;border-radius:50%;background:var(--vermillion);transform:translate(-50%,-50%);box-shadow:0 0 0 9px rgba(163,58,43,.16)}
    .map-overlay{position:absolute;left:20px;right:20px;top:20px;z-index:8;display:flex;justify-content:space-between;align-items:flex-start;pointer-events:none}.map-card{pointer-events:auto;background:rgba(250,248,241,.93);backdrop-filter:blur(13px);border:1px solid rgba(255,255,255,.5);box-shadow:0 16px 45px rgba(0,0,0,.2);border-radius:16px;padding:15px 17px;max-width:min(490px,62%)}.map-card small{color:var(--vermillion);font-weight:850;letter-spacing:.11em}.map-card strong{font-family:var(--serif);display:block;font-size:23px;margin:5px 0}.map-card p{margin:0;color:#5f696e;line-height:1.55;font-size:13px}.lens{pointer-events:auto;display:flex;background:rgba(250,248,241,.92);padding:4px;border-radius:999px;box-shadow:0 12px 32px rgba(0,0,0,.16)}.lens button{border:0;background:transparent;border-radius:999px;padding:9px 13px;font-weight:800;color:#5e696f}.lens button.active{background:var(--ink);color:#fff}
    .time-control{position:absolute;left:22px;right:22px;bottom:22px;z-index:9;background:rgba(250,248,241,.95);border:1px solid rgba(255,255,255,.6);border-radius:19px;padding:12px 15px;display:grid;grid-template-columns:auto 1fr auto;gap:13px;align-items:center;box-shadow:0 16px 45px rgba(0,0,0,.22)}.time-title{min-width:132px}.time-title strong{font-family:var(--serif);font-size:17px;display:block}.time-title small{color:#756d63;font-size:10px}.time-slider input{accent-color:var(--vermillion);width:100%}.time-slider{display:grid;gap:6px}.era-shortcuts{display:flex;gap:5px;justify-content:space-between}.era-shortcuts button{border:0;background:transparent;color:#7e766c;font-size:9px;padding:2px 4px}.era-shortcuts button:hover{color:var(--vermillion)}.year-tools{display:flex;align-items:center;gap:6px}.year-input{width:76px;border:1px solid var(--line);background:#fffdf8;border-radius:10px;padding:8px;color:var(--ink);font-weight:850;text-align:center}.play-time{width:34px;height:34px;border-radius:50%;border:0;background:var(--ink);color:white}.compare-range{position:absolute;z-index:9;right:22px;bottom:102px;width:150px;padding:8px 11px;background:rgba(17,38,59,.86);border-radius:999px;color:white;display:flex;gap:8px;align-items:center;font-size:9px}.compare-range input{width:90px;accent-color:#f2dcc0}.map-status{position:absolute;z-index:9;left:22px;bottom:102px;max-width:420px;padding:9px 12px;border-radius:11px;background:rgba(17,38,59,.86);color:#f7edda;font-size:10px;letter-spacing:.03em}.map-status strong{color:#e4c688}.year-badge{background:var(--vermillion);color:#fff;border-radius:999px;text-align:center;padding:8px;font-weight:850}
    .story-panel{background:var(--paper-2);border-left:1px solid var(--line);overflow:auto;padding:24px 23px 80px}.story-kicker{font-size:11px;letter-spacing:.14em;color:var(--vermillion);font-weight:850}.finding{font-family:var(--serif);font-size:22px;line-height:1.55;margin:10px 0 22px}.metrics{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:23px}.metric{border:1px solid var(--line);border-radius:999px;padding:7px 10px;font-size:11px;color:#58656d}.metric strong{color:var(--ink)}
    .era-card{padding:15px;border:1px solid var(--line);border-radius:15px;margin:0 0 21px;background:linear-gradient(135deg,rgba(177,138,69,.1),rgba(60,113,104,.05))}.era-card small{color:var(--vermillion);font-weight:850}.era-card strong{font-family:var(--serif);font-size:20px;display:block;margin:5px 0}.era-card p{margin:0;color:#657078;font-size:12px;line-height:1.55}.timeline-empty{padding:18px;border:1px dashed var(--line);color:#6a7479;border-radius:13px;font-size:12px;line-height:1.6}.timeline{position:relative;padding-left:24px}.timeline:before{content:"";position:absolute;left:6px;top:10px;bottom:10px;width:1px;background:linear-gradient(var(--gold),rgba(177,138,69,.14))}.event-card{border:0;background:transparent;width:100%;text-align:left;padding:0 0 23px;position:relative;color:var(--ink)}.event-card:before{content:"";position:absolute;left:-23px;top:7px;width:10px;height:10px;border-radius:50%;background:var(--paper-2);border:2px solid var(--gold)}.event-card.hidden-era{display:none}.event-card.active:before{background:var(--vermillion);border-color:var(--vermillion);box-shadow:0 0 0 5px rgba(163,58,43,.1)}.event-card time{font-size:11px;color:var(--vermillion);font-weight:850}.event-card h3{font-family:var(--serif);font-size:18px;margin:4px 0 5px}.event-card p{font-size:12px;color:#667177;line-height:1.55;margin:0}.event-meta{display:flex;gap:7px;margin-top:8px;font-size:10px;color:#6c7479}.precision{border-radius:99px;padding:4px 7px;background:rgba(60,113,104,.1);color:var(--jade)}
    .model-section{margin:4px 0 24px;padding-top:19px;border-top:1px solid var(--line)}.model-section h3{font-family:var(--serif);font-size:20px;margin:5px 0}.model-section>p{font-size:11px;color:#72797d;line-height:1.5}.model-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.model-card{border:1px solid var(--line);border-radius:14px;background:#ebe5d8;padding:10px;min-height:166px;position:relative;overflow:hidden}.model-stage{height:102px;display:grid;place-items:end center;perspective:500px;background:radial-gradient(ellipse at 50% 88%,rgba(17,38,59,.16),transparent 50%)}.model-obj{--h:70px;width:42px;height:var(--h);position:relative;transform:rotateX(-8deg) rotateY(-26deg);transform-style:preserve-3d;background:linear-gradient(90deg,#9f8053,#d3b77e);box-shadow:14px 13px 18px rgba(17,38,59,.18);animation:modelFloat 5s ease-in-out infinite}.model-obj:before{content:"";position:absolute;inset:0;transform:translateZ(-12px);background:#765e3e}.model-obj:after{content:"";position:absolute;left:0;right:0;top:-10px;height:10px;background:#d9c08c;clip-path:polygon(50% 0,100% 100%,0 100%)}.clock-tower{--h:76px;width:34px}.clock-tower:before{border-top:18px solid #675033}.pyramid-roof{--h:62px;width:52px}.pyramid-roof:after{top:-26px;height:27px}.pearl-tower{--h:82px;width:7px;border-radius:5px;background:#9f3150;box-shadow:none}.pearl-tower:after{width:35px;height:35px;border-radius:50%;clip-path:none;left:-14px;top:24px;background:radial-gradient(circle at 32% 25%,#f3a0ad,#9f3150 55%,#5d263e)}.tiered-tower{--h:88px;width:34px;clip-path:polygon(23% 0,77% 0,100% 100%,0 100%)}.portal-tower{--h:91px;width:40px;clip-path:polygon(0 0,100% 0,100% 100%,0 100%,0 18%,29% 18%,29% 8%,71% 8%,71% 18%,0 18%)}.twist-tower{--h:96px;width:36px;border-radius:14px 3px 10px 3px;transform:rotateX(-8deg) rotateY(-26deg) rotate(-4deg);background:linear-gradient(90deg,#638493,#c1d6d4)}.model-card strong{font-family:var(--serif);display:block;font-size:13px}.model-card small{font-size:9px;color:#756d63}.concept-tag{position:absolute;right:7px;top:7px;background:rgba(17,38,59,.82);color:#fff!important;padding:4px 6px;border-radius:99px}@keyframes modelFloat{50%{transform:rotateX(-8deg) rotateY(-18deg) translateY(-3px)}}
    .drawer-backdrop{position:fixed;inset:0;background:rgba(11,25,37,.35);z-index:48;opacity:0;pointer-events:none;transition:.25s}.drawer-backdrop.open{opacity:1;pointer-events:auto}.drawer{position:fixed;right:0;top:0;bottom:0;width:min(520px,94vw);background:var(--paper-2);z-index:50;transform:translateX(102%);transition:.3s ease;box-shadow:-25px 0 70px rgba(0,0,0,.22);padding:28px;overflow:auto}.drawer.open{transform:none}.drawer-top{display:flex;justify-content:space-between;align-items:center}.drawer h2{font-family:var(--serif);font-size:30px}.drawer-close{border:0;background:rgba(17,38,59,.08);width:37px;height:37px;border-radius:50%;font-size:20px}.evidence-source{display:inline-flex;margin:12px 0;padding:9px 12px;border-radius:9px;background:var(--ink);color:#fff;text-decoration:none;font-size:12px;font-weight:800}.detail-table{border-top:1px solid var(--line);margin-top:18px}.detail-row{padding:13px 0;border-bottom:1px solid var(--line)}.detail-row small{display:block;color:#82786c;margin-bottom:4px}.detail-row div{line-height:1.6}.research-section{padding:14px 0;border-bottom:1px solid var(--line)}.research-section strong{font-family:var(--serif);font-size:18px}.research-section p{color:#5f696f;line-height:1.65}
    .progress-layer{position:fixed;inset:0;background:rgba(15,34,49,.88);z-index:60;display:none;place-items:center;color:#fff;backdrop-filter:blur(13px)}.progress-layer.open{display:grid}.progress-box{width:min(620px,88vw)}.progress-box h2{font-family:var(--serif);font-size:38px;margin:0 0 8px}.progress-box p{color:#cdd6d9}.bar{height:5px;background:rgba(255,255,255,.14);margin:27px 0;border-radius:9px;overflow:hidden}.bar span{display:block;height:100%;background:linear-gradient(90deg,var(--gold),#e5c789);width:5%;transition:.4s}.steps{display:grid;grid-template-columns:repeat(5,1fr);gap:8px}.step{font-size:11px;color:#8da0aa;border-top:1px solid rgba(255,255,255,.18);padding-top:9px}.step.done{color:#f7ecd4;border-color:var(--gold)}
    .toast{position:fixed;left:50%;bottom:24px;transform:translate(-50%,20px);opacity:0;background:var(--ink);color:#fff;border-radius:999px;padding:11px 16px;z-index:70;transition:.25s;pointer-events:none}.toast.open{transform:translate(-50%,0);opacity:1}
    @media(max-width:980px){.hero{grid-template-columns:1fr}.hero-visual{min-height:420px}.hero-copy{padding:52px 25px}.workspace{height:auto;grid-template-columns:1fr}.map-shell{height:66vh;min-height:560px}.story-panel{border-left:0;border-top:1px solid var(--line)}.archive-note{width:48%}}
    @media(max-width:620px){.topbar{height:64px;padding:0 15px}.top-actions .ghost{display:none}.hero{min-height:calc(100vh - 64px)}h1{font-size:49px}.address-row{grid-template-columns:1fr}.intake-footer{align-items:stretch;flex-direction:column}.primary{width:100%}.hero-visual{min-height:340px}.archive-note{width:66%;padding:15px}.archive-note p{font-size:15px}.result-head{align-items:flex-start;flex-direction:column}.workspace{min-height:0}.map-shell{height:72vh;min-height:570px}.map-overlay{left:11px;right:11px;top:11px}.map-card{max-width:64%;padding:11px}.map-card strong{font-size:16px}.map-card p{display:none}.lens{max-width:44%;flex-wrap:wrap;border-radius:14px}.lens button{padding:7px 8px;font-size:9px}.time-control{left:11px;right:11px;bottom:11px;grid-template-columns:1fr;padding:10px;gap:7px}.time-title{display:flex;justify-content:space-between}.era-shortcuts{display:none}.year-tools{position:absolute;right:9px;top:8px}.time-slider{padding-right:0}.compare-range{right:11px;bottom:151px}.map-status{left:11px;right:175px;bottom:151px}.model-grid{grid-template-columns:1fr 1fr}.steps{grid-template-columns:1fr}.step{display:none}.step.done{display:block}}
    @media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;animation:none!important;transition:none!important}}
    .model-card{text-decoration:none;color:inherit}
  </style>
</head>
<body>
  <div class="noise"></div>
  <header class="topbar">
    <div class="brand"><div class="brand-mark"></div><div>文脉镜 ContextLens<small>SHANGHAI MEMORY ATLAS</small></div></div>
    <div class="top-actions"><span class="status-dot" id="statusDot"></span><button class="ghost" id="researchBtn">研究方法</button><button class="ghost" id="langBtn">EN</button></div>
  </header>

  <main id="homePage">
    <section class="hero">
      <div class="hero-copy">
        <div class="kicker">My Shanghai Address</div>
        <h1>你记得上海的<br>哪一个地址？</h1>
        <p class="lead">从一条旧路名、一个门牌或一段私人记忆出发。<strong>文脉镜会沿时间轴重建这里的建筑、人物与事件</strong>，并让每个结论回到真实来源。</p>
        <div class="intake">
          <div class="address-row">
            <div class="field"><label for="addressInput">上海旧址 / 道路 / 门牌</label><input id="addressInput" value="霞飞路436号" maxlength="180" autocomplete="off"></div>
            <div class="field"><label for="eraInput">约略年代</label><input id="eraInput" value="1930年代" maxlength="20"></div>
          </div>
          <div class="field memory-field"><label for="memoryInput">我的一句记忆 · 可选</label><textarea id="memoryInput" maxlength="180" placeholder="例如：外婆说，这里以前有一家总是亮着灯的书店。"></textarea></div>
          <div class="privacy">这段记忆只留在当前浏览器，不上传、不记录、不发送给模型。</div>
          <div class="intake-footer">
            <div class="examples">
              <button class="chip" data-address="霞飞路436号" data-era="1930年代">霞飞路 · 1930</button>
              <button class="chip" data-address="南京路百货公司" data-era="1940年代">南京路百货</button>
              <button class="chip" data-address="外滩20号" data-era="1920年代">外滩20号</button>
              <button class="chip" data-address="武康路129号" data-era="1930年代">武康路129号</button>
            </div>
            <button class="primary" id="resolveBtn">打开城市记忆虫洞</button>
          </div>
        </div>
        <div class="candidate-panel" id="candidatePanel">
          <div class="candidate-head"><div><strong>确认你记忆中的地点</strong><div id="candidateGuidance" style="font-size:12px;color:#69737a;margin-top:3px"></div></div><button class="primary" id="investigateBtn">开始调查</button></div>
          <div class="candidate-list" id="candidateList"></div>
        </div>
      </div>
      <div class="hero-visual" aria-hidden="true">
        <div class="contour c1"></div><div class="contour c2"></div><div class="contour c3"></div><div class="river"></div><div class="hero-pin"></div>
        <div class="archive-note"><small>ARCHIVE NOTE · 04</small><p>“城市不会泄露自己的过去，只会把它像手纹一样藏起来。”</p></div>
      </div>
    </section>
  </main>

  <main class="result-page" id="resultPage">
    <header class="result-head">
      <div class="result-title"><button class="secondary" id="backBtn">← 返回</button><div><h2 id="resultPlace">城市记忆虫洞</h2><p id="resultSummary"></p></div></div>
      <div class="result-actions"><button class="secondary" id="mapsBtn">历史地图档案</button><button class="secondary" id="memoryCardBtn">生成我的记忆卡</button><button class="secondary" id="methodBtn">证据与方法</button></div>
    </header>
    <section class="workspace">
      <div class="map-shell">
        <div class="map history-map" id="historyMap" role="application" aria-label="按所选年份过滤的上海历史地图"></div>
        <div class="map modern-map" id="modernMap" aria-label="上海现代三维建筑地图"></div>
        <div class="compare-divider" id="compareDivider" aria-hidden="true"></div>
        <div class="map-fallback" id="mapFallback"><div class="fallback-grid"></div><div class="fallback-river"></div><div class="fallback-pins" id="fallbackPins"></div><div style="position:absolute;right:10px;bottom:6px;color:#dce6e3;font-size:10px">离线上海轮廓 · 在线底图 © OpenFreeMap © OpenStreetMap</div></div>
        <div class="map-overlay">
          <div class="map-card"><small>ONE PLACE · MANY TIMES</small><strong id="mapFinding"></strong><p id="mapDescription"></p></div>
          <div class="lens" aria-label="古今地图显示方式"><button class="active" data-view="compare">古今对照</button><button data-view="history">历史地图</button><button data-view="modern">现代3D</button></div>
        </div>
        <div class="map-status" id="mapStatus"><strong>历史矢量层</strong> · 正在准备年代数据</div>
        <label class="compare-range" id="compareControl">古今分界 <input id="compareRange" type="range" min="18" max="82" value="52" aria-label="古今地图分界位置"></label>
        <div class="time-control">
          <div class="time-title"><strong id="eraLabel">选择任意年份</strong><small id="eraName">逐年探索 · 非预设节点</small></div>
          <div class="time-slider"><input id="yearRange" type="range" min="1600" max="2026" step="1" value="1934" aria-label="历史年份"><div class="era-shortcuts" id="eraShortcuts"></div></div>
          <div class="year-tools"><button class="play-time" id="playTime" aria-label="播放年代变化">▶</button><input class="year-input" id="yearInput" type="number" min="1600" max="2026" value="1934" aria-label="直接输入历史年份"></div>
        </div>
      </div>
      <aside class="story-panel"><div class="story-kicker">EVIDENCE-BOUND STORY</div><div class="finding" id="finding"></div><div class="metrics" id="metrics"></div><div class="era-card" id="eraCard"></div><div class="model-section"><div class="story-kicker">CITY LANDMARK CABINET · 3D</div><h3>时代地标体量</h3><p>按所选年份展示当时已经出现的地标。所有模型均为概念体量，并非测绘级复原。</p><div class="model-grid" id="modelGrid"></div></div><div class="story-kicker" style="margin-bottom:17px">PLACE TIMELINE</div><div class="timeline" id="timeline"></div><div class="timeline-empty" id="timelineEmpty" hidden></div></aside>
    </section>
  </main>

  <div class="drawer-backdrop" id="drawerBackdrop"></div>
  <aside class="drawer" id="drawer" aria-hidden="true"><div class="drawer-top"><span class="story-kicker" id="drawerKicker">SOURCE PASSPORT</span><button class="drawer-close" id="drawerClose" aria-label="关闭">×</button></div><div id="drawerBody"></div></aside>
  <div class="progress-layer" id="progressLayer" role="status" aria-live="polite"><div class="progress-box"><div class="kicker">Historical Evidence Agent</div><h2 id="progressTitle">正在打开城市记忆</h2><p id="progressMessage">调查已进入队列</p><div class="bar"><span id="progressBar"></span></div><div class="steps" id="progressSteps"></div></div></div>
  <div class="toast" id="toast"></div>
  <canvas id="memoryCanvas" width="1200" height="1500" hidden></canvas>
  <script src="/vendor/maplibre-gl.js"></script>
  <script src="/vendor/maplibre-gl-dates.js"></script>
  <script>
    const state={resolution:null,candidate:null,job:null,result:null,historyMap:null,modernMap:null,historyReady:false,modernReady:false,view:"compare",year:1934,memory:"",lang:"zh",playTimer:null,syncing:false};
    const $=id=>document.getElementById(id); const escapeHtml=v=>String(v??"").replace(/[&<>'"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));
    const stages=["resolving","fetching","linking","auditing","complete"];
    function toast(message){$("toast").textContent=message;$("toast").classList.add("open");setTimeout(()=>$("toast").classList.remove("open"),2200)}
    async function api(url,options={}){const response=await fetch(url,{...options,headers:{"Content-Type":"application/json",...(options.headers||{})}});const data=await response.json();if(!response.ok)throw new Error(data.error||"请求失败");return data}
    document.querySelectorAll(".chip").forEach(button=>button.addEventListener("click",()=>{$("addressInput").value=button.dataset.address;$("eraInput").value=button.dataset.era;$("candidatePanel").classList.remove("open")}));
    $("resolveBtn").addEventListener("click",resolveAddress); $("investigateBtn").addEventListener("click",startInvestigation); $("backBtn").addEventListener("click",()=>{closeMap();$("resultPage").classList.remove("open");$("homePage").style.display="block";scrollTo(0,0)});
    $("drawerClose").addEventListener("click",closeDrawer);$("drawerBackdrop").addEventListener("click",closeDrawer);$("methodBtn").addEventListener("click",openMethodDrawer);$("mapsBtn").addEventListener("click",openMapArchive);$("researchBtn").addEventListener("click",openResearchOverview);$("memoryCardBtn").addEventListener("click",downloadMemoryCard);
    $("yearRange").addEventListener("input",event=>setYear(event.target.value));$("yearInput").addEventListener("input",event=>setYear(event.target.value));$("playTime").addEventListener("click",toggleTimePlayback);$("compareRange").addEventListener("input",event=>document.querySelector(".map-shell").style.setProperty("--compare",`${event.target.value}%`));
    document.querySelectorAll("[data-view]").forEach(button=>button.addEventListener("click",()=>setMapView(button.dataset.view)));
    $("langBtn").addEventListener("click",()=>toast("English research labels remain available in exported JSON; the flagship narrative currently prioritizes Chinese."));
    async function resolveAddress(){const address=$("addressInput").value.trim();if(!address){toast("请先输入一条上海地址");return}state.memory=$("memoryInput").value.trim();$("resolveBtn").disabled=true;$("resolveBtn").textContent="正在解析地点…";try{state.resolution=await api("/api/place/resolve",{method:"POST",body:JSON.stringify({address,era_hint:$("eraInput").value})});renderCandidates()}catch(error){toast(error.message)}finally{$("resolveBtn").disabled=false;$("resolveBtn").textContent="打开城市记忆虫洞"}}
    function renderCandidates(){const r=state.resolution;$("candidateGuidance").textContent=r.guidance||"";const list=$("candidateList");if(!r.candidates?.length){list.innerHTML=`<div style="padding:13px;color:#7d4137">${escapeHtml(r.guidance)}</div>`;$("investigateBtn").disabled=true}else{$("investigateBtn").disabled=false;state.candidate=r.candidates.find(c=>c.candidate_id===r.recommended_candidate_id)||r.candidates[0];list.innerHTML=r.candidates.map(c=>`<label class="candidate ${c.candidate_id===state.candidate.candidate_id?"selected":""}"><input type="radio" name="candidate" value="${escapeHtml(c.candidate_id)}" ${c.candidate_id===state.candidate.candidate_id?"checked":""}><span><strong>${escapeHtml(c.display_name)}</strong><span>${escapeHtml(c.match_reason)}</span></span><span class="confidence">${Math.round((c.confidence||0)*100)}%</span></label>`).join("");list.querySelectorAll("input").forEach(input=>input.addEventListener("change",()=>{state.candidate=r.candidates.find(c=>c.candidate_id===input.value);renderCandidates()}))}$("candidatePanel").classList.add("open")}
    async function startInvestigation(){if(!state.candidate)return;openProgress();try{state.job=await api("/api/investigations",{method:"POST",body:JSON.stringify({address:$("addressInput").value.trim(),era_hint:$("eraInput").value,candidate:state.candidate,allow_live:true})});pollJob()}catch(error){closeProgress();toast(error.message)}}
    function openProgress(){renderProgress({stage:"queued",progress:4,message:"调查已进入队列"});$("progressLayer").classList.add("open")}
    function closeProgress(){$("progressLayer").classList.remove("open")}
    function renderProgress(job){$("progressBar").style.width=`${job.progress||0}%`;$("progressMessage").textContent=job.message||"";const activeIndex=stages.indexOf(job.stage);$("progressSteps").innerHTML=stages.map((stage,index)=>`<div class="step ${index<=activeIndex?"done":""}">${["地址解析","官方数据搜索","时空关联","证据审计","档案完成"][index]}</div>`).join("")}
    async function pollJob(){try{const job=await api(`/api/investigations/${state.job.id}`);renderProgress(job);if(job.status==="complete"){state.result=job.result;setTimeout(()=>{closeProgress();openResult()},320);return}if(job.status==="failed"){throw new Error(job.error||"调查未完成")}setTimeout(pollJob,500)}catch(error){closeProgress();toast(error.message)}}
    function openResult(){$("homePage").style.display="none";$("resultPage").classList.add("open");const r=state.result,time=r.map.time||{};$("resultPlace").textContent=r.candidate.display_name;$("resultSummary").textContent=r.summary;$("finding").textContent=r.finding;$("mapFinding").textContent=r.candidate.display_name;$("mapDescription").textContent="左侧为按年份过滤的历史矢量层，右侧为现代三维城市；拖动分界线可比较。";const q=r.quality||{};$("metrics").innerHTML=`<span class="metric"><strong>${q.direct_claim_count||0}</strong> 条直接主张</span><span class="metric"><strong>${q.source_count||0}</strong> 个来源</span><span class="metric"><strong>${(time.catalog||[]).length}</strong> 幅跨年代地图</span><span class="metric">空间状态 · <strong>${q.uncertainty||"review"}</strong></span>`;$("yearRange").min=time.min_year||1600;$("yearRange").max=time.max_year||new Date().getFullYear();$("yearInput").min=$("yearRange").min;$("yearInput").max=$("yearRange").max;state.year=Number(r.query?.focus_year||r.query?.era_hint||1934);renderEraShortcuts();renderTimeline();setYear(state.year);setMapView("compare");requestAnimationFrame(initMap);scrollTo(0,0)}
    function renderTimeline(){const items=state.result.timeline||[];$("timeline").innerHTML=items.map(item=>`<button class="event-card" data-feature="${escapeHtml(item.feature_id)}" data-start="${item.start_year||""}" data-end="${item.end_year||""}"><time>${escapeHtml(item.time_label)}</time><h3>${escapeHtml(item.title)}</h3><p>${escapeHtml(item.address||"地点待进一步确认")}</p><div class="event-meta"><span>${item.type==="event"?"历史事件":"历史建筑"}</span><span class="precision">${item.spatial_precision==="source_coordinate"?"来源坐标":"范围定位"}</span></div></button>`).join("");$("timeline").querySelectorAll(".event-card").forEach(node=>node.addEventListener("click",()=>openEvidence(node.dataset.feature)))}
    function visibleAt(feature,year){const p=feature.properties||{};if(!p.start_year&&!p.end_year)return true;const start=p.start_year||1600,end=p.end_year||p.start_year||new Date().getFullYear();return year>=start&&year<=end}
    function setYear(value){if(!state.result)return;const min=Number($("yearRange").min)||1600,max=Number($("yearRange").max)||new Date().getFullYear();state.year=Math.max(min,Math.min(max,Number(value)||state.year));$("yearRange").value=state.year;$("yearInput").value=state.year;applyEraFilter()}
    function activeEra(year){return (state.result.map.time?.era_guide||[]).find(item=>year>=item.from_year&&year<=item.to_year)||state.result.map.time?.active_era}
    function placeNameAtYear(year){const periods=state.result.candidate.name_periods||[];const hit=periods.find(item=>(item.from_year==null||year>=item.from_year)&&(item.to_year==null||year<item.to_year));return hit?.name||(periods.length?"道路尚未形成／名称待考":state.result.candidate.canonical_name)}
    function nearestMap(year){return [...(state.result.map.time?.catalog||[])].sort((a,b)=>Math.abs(a.year-year)-Math.abs(b.year-year))[0]}
    function renderEraShortcuts(){const years=[1810,1855,1910,1934,1949,1972,1994,2026].filter(year=>year<=Number($("yearRange").max));$("eraShortcuts").innerHTML=years.map(year=>`<button data-year="${year}">${year}</button>`).join("");$("eraShortcuts").querySelectorAll("button").forEach(button=>button.addEventListener("click",()=>setYear(button.dataset.year)))}
    function renderTemporalContext(visibleCount){const era=activeEra(state.year)||{},map=nearestMap(state.year),name=placeNameAtYear(state.year),gap=map?Math.abs(map.year-state.year):null;$("eraName").textContent=`${era.label||"历史切片"} · ${name}`;$("eraCard").innerHTML=`<small>${state.year} · ${escapeHtml(name)}</small><strong>${escapeHtml(era.label||"年代待考")}</strong><p>${escapeHtml(era.note||"")} ${visibleCount?`本地点有 ${visibleCount} 个可显示节点。`:"本地点暂无可核查的逐年事件，历史地图仍可继续探索。"}</p>`;$("mapStatus").innerHTML=`<strong>${state.year} 历史矢量</strong> · ${map?`最近原图 ${map.year}《${escapeHtml(map.title)}》${gap?`，相差 ${gap} 年`:"，同年"}`:"暂无地图原件"}`;renderModels()}
    function renderModels(){const models=(state.result.map.time?.landmark_models||[]).filter(item=>item.year<=state.year).slice(-4).reverse();$("modelGrid").innerHTML=models.length?models.map(item=>`<a class="model-card" href="${escapeHtml(item.source_url)}" target="_blank" rel="noopener noreferrer"><small class="concept-tag">概念体量</small><div class="model-stage"><div class="model-obj ${escapeHtml(item.model_type)}"></div></div><strong>${escapeHtml(item.title)}</strong><small>${item.year}${item.height_m?` · ${item.height_m}m`:""}</small></a>`).join(""):`<div class="timeline-empty" style="grid-column:1/-1">${state.year} 年前暂无已核对的地标体量；这不代表当时没有重要建筑。</div>`}
    function applyEraFilter(){if(!state.result)return;const visibleFeatures=(state.result.feature_collection.features||[]).filter(f=>visibleAt(f,state.year));let visibleCount=0;document.querySelectorAll(".event-card").forEach(node=>{const start=Number(node.dataset.start)||null,end=Number(node.dataset.end)||start,visible=!start||state.year>=start&&state.year<=(end||start);node.classList.toggle("hidden-era",!visible);if(visible)visibleCount++});$("timelineEmpty").hidden=visibleCount>0;$("timelineEmpty").textContent=`${state.year} 年暂未找到与该地点直接关联、且时间明确的事件。可继续查看年代待考建筑，或打开历史地图档案。`;const data={type:"FeatureCollection",features:visibleFeatures};for(const map of [state.historyMap,state.modernMap])map?.getSource("memory-features")?.setData(data);if(state.historyReady&&typeof state.historyMap?.filterByDate==="function"){try{state.historyMap.filterByDate(String(state.year))}catch{}}renderTemporalContext(visibleCount);renderFallbackPins()}
    function setMapView(view){state.view=view;const shell=document.querySelector(".map-shell");shell.classList.toggle("history-only",view==="history");shell.classList.toggle("modern-only",view==="modern");$("compareControl").style.display=view==="compare"?"flex":"none";document.querySelectorAll("[data-view]").forEach(node=>node.classList.toggle("active",node.dataset.view===view))}
    function toggleTimePlayback(){if(state.playTimer){clearInterval(state.playTimer);state.playTimer=null;$("playTime").textContent="▶";return}$("playTime").textContent="Ⅱ";state.playTimer=setInterval(()=>{const max=Number($("yearRange").max);if(state.year>=max){clearInterval(state.playTimer);state.playTimer=null;$("playTime").textContent="▶"}else setYear(state.year+1)},180)}
    function closeMap(){if(state.playTimer){clearInterval(state.playTimer);state.playTimer=null;$("playTime").textContent="▶"}for(const key of ["historyMap","modernMap"]){if(state[key]){try{state[key].remove()}catch{}state[key]=null}}state.historyReady=false;state.modernReady=false;$("historyMap").innerHTML="";$("modernMap").innerHTML=""}
    function addMemoryLayers(map){const features=(state.result.feature_collection.features||[]).filter(f=>visibleAt(f,state.year));map.addSource("memory-features",{type:"geojson",data:{type:"FeatureCollection",features}});map.addLayer({id:"uncertainty-halo",type:"circle",source:"memory-features",filter:["!=",["get","spatial_precision"],"source_coordinate"],paint:{"circle-radius":24,"circle-color":"rgba(163,58,43,.08)","circle-stroke-color":"rgba(163,58,43,.42)","circle-stroke-width":1}});map.addLayer({id:"memory-points",type:"circle",source:"memory-features",paint:{"circle-radius":["case",["==",["get","feature_type"],"event"],8,7],"circle-color":["case",["==",["get","feature_type"],"event"],"#a33a2b","#b18a45"],"circle-stroke-color":"#faf8f1","circle-stroke-width":2}});map.on("click","memory-points",event=>{const feature=event.features?.[0];if(feature)openEvidence(feature.id||feature.properties.feature_id)});map.on("mouseenter","memory-points",()=>map.getCanvas().style.cursor="pointer");map.on("mouseleave","memory-points",()=>map.getCanvas().style.cursor="")}
    function syncCamera(source,target){source.on("move",()=>{if(state.syncing||!target)return;state.syncing=true;const center=source.getCenter();target.jumpTo({center:[center.lng,center.lat],zoom:source.getZoom(),bearing:source.getBearing()});state.syncing=false})}
    function supplyMissingMapImages(map){map.on("styleimagemissing",event=>{if(!map.hasImage(event.id))map.addImage(event.id,{width:1,height:1,data:new Uint8Array([0,0,0,0])})})}
    function initMap(){closeMap();$("mapFallback").classList.remove("open");if(!window.maplibregl){showFallback();return}const r=state.result,common={center:r.map.center,zoom:13.4,localIdeographFontFamily:'"PingFang SC","Microsoft YaHei",sans-serif'};try{state.historyMap=new maplibregl.Map({container:"historyMap",style:r.map.historical_style,...common,attributionControl:{customAttribution:'<a href="https://www.openhistoricalmap.org/">OpenHistoricalMap</a>'},maxPitch:0});state.modernMap=new maplibregl.Map({container:"modernMap",style:r.map.remote_style,...common,pitch:52,bearing:-14,attributionControl:{compact:true}});supplyMissingMapImages(state.historyMap);supplyMissingMapImages(state.modernMap);syncCamera(state.historyMap,state.modernMap);syncCamera(state.modernMap,state.historyMap);state.historyMap.on("load",()=>{state.historyReady=true;try{if(typeof state.historyMap.filterByDate==="function")state.historyMap.filterByDate(String(state.year));addMemoryLayers(state.historyMap);state.historyMap.addControl(new maplibregl.NavigationControl({visualizePitch:true}),"bottom-left")}catch{}if(r.map.bounds&&r.map.bounds[0]!==r.map.bounds[2])state.historyMap.fitBounds([[r.map.bounds[0],r.map.bounds[1]],[r.map.bounds[2],r.map.bounds[3]]],{padding:90,maxZoom:15});applyEraFilter()});state.modernMap.on("load",()=>{state.modernReady=true;try{addMemoryLayers(state.modernMap)}catch{}applyEraFilter()});state.historyMap.on("error",()=>{if(!state.historyReady)$("mapStatus").innerHTML=`<strong>${state.year}</strong> · 历史矢量层暂不可用，现代3D与档案原图仍可使用`});setTimeout(()=>{if(!state.historyReady&&!state.modernReady)showFallback()},9000)}catch(error){showFallback()}}
    function showFallback(){closeMap();$("mapFallback").classList.add("open");$("mapStatus").innerHTML=`<strong>离线地图</strong> · 历史事件与建筑坐标仍按 ${state.year} 年过滤`;renderFallbackPins()}
    function renderFallbackPins(){if(!state.result)return;const all=state.result.feature_collection.features||[],visible=all.filter(f=>visibleAt(f,state.year)&&f.geometry);const bounds=state.result.map.bounds||[121.43,31.20,121.51,31.26];const dx=Math.max(.001,bounds[2]-bounds[0]),dy=Math.max(.001,bounds[3]-bounds[1]);$("fallbackPins").innerHTML=visible.map(f=>{const [lon,lat]=f.geometry.coordinates,x=14+72*(lon-bounds[0])/dx,y=84-68*(lat-bounds[1])/dy;return `<button class="fallback-pin" style="left:${x}%;top:${y}%" data-feature="${escapeHtml(f.id)}" aria-label="${escapeHtml(f.properties.title)}"></button>`}).join("");$("fallbackPins").querySelectorAll("button").forEach(node=>node.addEventListener("click",()=>openEvidence(node.dataset.feature)))}
    function openEvidence(featureId){const evidence=(state.result.evidence||[]).find(item=>item.evidence_id===featureId);if(!evidence)return;$("drawerKicker").textContent="SOURCE PASSPORT";$("drawerBody").innerHTML=`<h2>${escapeHtml(evidence.title)}</h2><p style="line-height:1.75;color:#56636b">${escapeHtml(evidence.description)}</p>${evidence.source_uri?`<a class="evidence-source" href="${escapeHtml(evidence.source_uri)}" target="_blank" rel="noopener noreferrer">打开上海图书馆来源 ↗</a>`:""}<div class="detail-table">${detail("来源",evidence.source_title)}${detail("时间",evidence.time_label)}${detail("地点",evidence.address||"待确认")}${detail("证据类型",evidence.feature_type)}${detail("空间精度",evidence.spatial_precision==="source_coordinate"?"来源提供坐标":"道路范围定位，不表示精确门牌")}${detail("支持主张",`${(evidence.claim_ids||[]).length} 条`)}</div>`;openDrawer()}
    function detail(label,value){return `<div class="detail-row"><small>${escapeHtml(label)}</small><div>${escapeHtml(value||"—")}</div></div>`}
    function openMapArchive(){if(!state.result)return;const time=state.result.map.time||{},maps=[...(time.catalog||[])].sort((a,b)=>a.year-b.year);$("drawerKicker").textContent="HISTORICAL MAP ARCHIVE";$("drawerBody").innerHTML=`<h2>跨时代地图档案</h2><p style="line-height:1.75;color:#56636b">动态历史层可选择任意年份；下列地图是原始文献目录。只有明确完成地理配准的地图才能覆盖到现代坐标，其他原图在来源站点查看。</p><div class="research-section"><strong>任意年份动态层</strong><p>${escapeHtml(time.dynamic_layer?.coverage_note||"")}</p><a class="evidence-source" href="${escapeHtml(time.dynamic_layer?.source_url||"https://www.openhistoricalmap.org/")}" target="_blank" rel="noopener noreferrer">OpenHistoricalMap ↗</a></div>${maps.map(item=>`<div class="research-section"><strong>${item.year} · ${escapeHtml(item.title)}</strong><p>${escapeHtml(item.provider)} · ${escapeHtml(item.scope)} · ${item.access==="public_iiif"?"公共 IIIF":"馆藏原图目录"}</p><a href="${escapeHtml(item.source_url)}" target="_blank" rel="noopener noreferrer">打开原图记录 ↗</a></div>`).join("")}<div class="research-section"><strong>使用边界</strong><p>Virtual Shanghai 材料限教育和非商业使用并须署名；本项目只保存目录元数据与链接，不重新打包高分辨率原图。</p></div>`;openDrawer()}
    function openMethodDrawer(){if(!state.result)return;const r=state.result;$("drawerKicker").textContent="RESEARCH MODE";$("drawerBody").innerHTML=`<h2>证据与方法</h2><p style="line-height:1.75;color:#56636b">本页只把同时满足地点实体、历史关系和可打开来源的材料标记为直接支撑。宽泛词不会单独提升证据等级。</p>${(r.replay||[]).map(item=>`<div class="research-section"><strong>${escapeHtml(item.label)}</strong><p>${escapeHtml(item.detail)}</p></div>`).join("")}<div class="research-section"><strong>质量边界</strong><p>${escapeHtml((r.quality.warnings||[]).join("；")||"没有新的接口警告。范围定位仍需在公开使用前人工复核。")}</p></div>`;openDrawer()}
    function openResearchOverview(){$("drawerKicker").textContent="CONTEXTLENS METHOD";$("drawerBody").innerHTML=`<h2>历史证据编译器</h2><p style="line-height:1.75;color:#56636b">文脉镜不是让AI自由讲故事，而是让智能体操作道路实体、历史事件和建筑坐标，并公开展示证据边界。</p>${["地址解析：分离旧路名、门牌与年代","地名消歧：保留历史名称、现代名称和官方URI","时空关联：只连接直接命中地点的事件与建筑","主张审计：综合结论至少绑定两个独立来源","公众叙事：个人记忆与历史事实永远分区呈现"].map((text,index)=>`<div class="research-section"><strong>0${index+1}</strong><p>${escapeHtml(text)}</p></div>`).join("")}<a class="evidence-source" href="/research-tools">进入更多研究工具 ↗</a>`;openDrawer()}
    function openDrawer(){$("drawer").classList.add("open");$("drawerBackdrop").classList.add("open");$("drawer").setAttribute("aria-hidden","false")}
    function closeDrawer(){$("drawer").classList.remove("open");$("drawerBackdrop").classList.remove("open");$("drawer").setAttribute("aria-hidden","true")}
    function downloadMemoryCard(){if(!state.result)return;const canvas=$("memoryCanvas"),ctx=canvas.getContext("2d"),r=state.result;ctx.fillStyle="#f3efe5";ctx.fillRect(0,0,1200,1500);ctx.fillStyle="#11263b";ctx.fillRect(0,0,1200,190);ctx.fillStyle="#d9bb80";ctx.font="700 28px sans-serif";ctx.fillText("文脉镜 · MY SHANGHAI ADDRESS",70,78);ctx.fillStyle="#fff8e9";ctx.font="700 52px serif";ctx.fillText(r.candidate.display_name,70,145);ctx.fillStyle="#a33a2b";ctx.fillRect(70,250,74,8);ctx.fillStyle="#11263b";ctx.font="700 34px serif";ctx.fillText("我的记忆",70,330);ctx.font="34px serif";wrapText(ctx,state.memory||"我从这个地址出发，重新看见城市的时间。",70,395,1040,55);ctx.strokeStyle="rgba(17,38,59,.2)";ctx.beginPath();ctx.moveTo(70,650);ctx.lineTo(1130,650);ctx.stroke();ctx.fillStyle="#11263b";ctx.font="700 34px serif";ctx.fillText("可核查的历史",70,725);ctx.font="30px serif";wrapText(ctx,r.finding,70,790,1040,48);const ev=r.evidence?.[0];ctx.fillStyle="#5d696f";ctx.font="24px sans-serif";wrapText(ctx,`来源：${ev?.source_title||"上海图书馆开放数据"} · ${ev?.time_label||"年代待考"}`,70,1120,1040,36);ctx.fillStyle="#11263b";ctx.fillRect(70,1260,1060,2);ctx.font="22px sans-serif";ctx.fillText("个人记忆不是历史事实；历史结论均可回到来源复核。",70,1325);ctx.fillStyle="#a33a2b";ctx.font="700 24px sans-serif";ctx.fillText("CONTEXTLENS / 城市记忆虫洞",70,1405);const link=document.createElement("a");link.download=`文脉镜-${r.candidate.canonical_name}-记忆卡.png`;link.href=canvas.toDataURL("image/png");link.click();toast("记忆卡已生成，仅保存到你的设备")}
    function wrapText(ctx,text,x,y,maxWidth,lineHeight){const chars=Array.from(String(text||""));let line="";for(const char of chars){const test=line+char;if(ctx.measureText(test).width>maxWidth&&line){ctx.fillText(line,x,y);line=char;y+=lineHeight}else line=test}if(line)ctx.fillText(line,x,y)}
    fetch("/api/health").then(r=>r.json()).then(data=>{$("statusDot").style.background=data.api_key_configured?"#3c7168":"#b18a45"}).catch(()=>{$("statusDot").style.background="#a33a2b"});
  </script>
</body>
</html>'''


def health_payload() -> dict:
    settings = get_settings()
    source_counts = count_records_by_source()
    return {
        "ok": True,
        "version": VERSION,
        **source_counts,
        "official_records": source_counts["live_records"] + source_counts["official_snapshot_records"],
        "official_source_mode": "verified_official_snapshot",
        "demo_seed_active": source_counts["seed_records"] > 0,
        "api_key_configured": bool(settings.api_key),
        "deepseek_available": bool(settings.deepseek_api_key) and settings.use_deepseek,
        "deepseek_mode": "user_opt_in_public_evidence_only",
        "maplibre_bundled": (VENDOR_DIR / "maplibre-gl.js").exists(),
        "historical_date_filter_bundled": OHM_DATES_PATH.exists(),
        "curated_frontend_built": (STATIC_DIR / "index.html").exists(),
        "privacy_mode": "hashed_query_logs",
    }


def write_private_audit(payload: dict, result: dict | None = None, error: str = "") -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    address = str(payload.get("address") or payload.get("question") or "")
    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "query_hash": hash_private_query(address),
        "mode": payload.get("mode") or "place_memory",
        "result_count": len((result or {}).get("candidates") or (result or {}).get("evidence") or []),
        "error_type": error.split(":", 1)[0] if error else "",
    }
    with (LOG_DIR / "query_audit.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def sanitize_legacy_audit_log() -> None:
    """Remove raw questions left by pre-privacy versions of the prototype."""
    path = LOG_DIR / "query_audit.jsonl"
    if not path.exists():
        return
    sanitized: list[str] = []
    changed = False
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        raw_query = str(record.pop("question", record.pop("address", "")) or "")
        for sensitive_key in ("memory", "api_key", "deepseek_api_key"):
            changed = bool(record.pop(sensitive_key, None)) or changed
        if raw_query:
            record["query_hash"] = hash_private_query(raw_query)
            changed = True
        sanitized.append(json.dumps(record, ensure_ascii=False))
    if changed:
        temporary = path.with_suffix(".jsonl.tmp")
        temporary.write_text("\n".join(sanitized) + ("\n" if sanitized else ""), encoding="utf-8")
        temporary.replace(path)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            index = STATIC_DIR / "index.html"
            self.respond(200, index.read_bytes() if index.exists() else HTML.encode("utf-8"), "text/html; charset=utf-8")
        elif path == "/research-tools":
            from app.web_demo import HTML as RESEARCH_HTML, app_data

            html = RESEARCH_HTML.replace("REPLACE_APP_DATA", json.dumps(app_data(), ensure_ascii=False))
            self.respond(200, html.encode("utf-8"), "text/html; charset=utf-8")
        elif path == "/api/health":
            self.respond_json(health_payload())
        elif path.startswith("/api/investigations/"):
            job_id = unquote(path.removeprefix("/api/investigations/")).strip()
            job = INVESTIGATION_STORE.get(job_id)
            self.respond_json(job or {"error": "investigation not found"}, status=200 if job else 404)
        elif path.startswith("/vendor/"):
            self.serve_vendor(unquote(path.removeprefix("/vendor/")))
        elif path.startswith("/assets/"):
            self.serve_static(unquote(path.removeprefix("/assets/")))
        elif path == "/sw.js":
            self.serve_static("sw.js", service_worker=True)
        elif path.startswith("/source/") or path.startswith("/api/evidence/"):
            from app.web_demo import Handler as ResearchHandler

            ResearchHandler.do_GET(self)
        elif path == "/favicon.ico":
            self.respond(204, b"", "image/x-icon")
        else:
            self.respond_json({"error": "not found"}, status=404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        payload = self.read_json()
        if payload is None:
            return
        if path.startswith("/api/investigations/") and path.endswith("/interpret"):
            job_id = unquote(path.removeprefix("/api/investigations/").removesuffix("/interpret")).strip("/")
            result = INVESTIGATION_STORE.completed_result(job_id)
            if not result:
                self.respond_json({"error": "completed investigation not found"}, status=409)
                return
            question = str(payload.get("question") or "").strip()[:320]
            if not question:
                self.respond_json({"error": "question is required"}, status=400)
                return
            try:
                year = int(payload.get("year")) if payload.get("year") is not None else None
            except (TypeError, ValueError):
                year = None
            settings = get_settings()
            interpretation = interpret_place_archive(
                api_key=settings.deepseek_api_key if settings.use_deepseek else None,
                model=settings.deepseek_model,
                question=question,
                language="en" if payload.get("language") == "en" else "zh",
                place_name=str((result.get("candidate") or {}).get("display_name") or "上海历史地点"),
                year=year,
                evidence_cards=result.get("evidence") or [],
                archive_network=result.get("archive_network") or {},
            )
            write_private_audit({"question": question, "mode": "optional_archive_interpretation"}, interpretation)
            self.respond_json(interpretation)
        elif path == "/api/place/resolve":
            address = str(payload.get("address") or "").strip()
            if not address:
                self.respond_json({"error": "address is required"}, status=400)
                return
            try:
                result = resolve_place(address, payload.get("era_hint"), allow_live=bool(payload.get("allow_live", True)))
                write_private_audit(payload, result)
                self.respond_json(result)
            except Exception as exc:
                write_private_audit(payload, error=type(exc).__name__)
                self.respond_json({"error": f"place resolution failed: {type(exc).__name__}"}, status=502)
        elif path == "/api/investigations":
            if not isinstance(payload.get("candidate"), dict):
                self.respond_json({"error": "candidate is required"}, status=400)
                return
            self.respond_json(INVESTIGATION_STORE.create(payload), status=202)
        elif path == "/api/ask":
            question = str(payload.get("question") or "").strip()
            if not question:
                self.respond_json({"error": "question is required"}, status=400)
                return
            result = answer_question(
                question[:800],
                top_k=max(1, min(int(payload.get("top_k", 8)), 12)),
                language=str(payload.get("language", "zh")),
                mode=str(payload.get("mode", "general")),
                output_style=str(payload.get("output_style", "evidence_brief")),
                use_deepseek=bool(payload.get("use_deepseek", False)),
            )
            write_private_audit(payload, result)
            self.respond_json(result)
        else:
            self.respond_json({"error": "not found"}, status=404)

    def read_json(self) -> dict | None:
        try:
            length = int(self.headers.get("content-length", "0"))
        except ValueError:
            length = 0
        if length > MAX_BODY:
            self.respond_json({"error": "request body too large"}, status=413)
            return None
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self.respond_json({"error": "invalid JSON"}, status=400)
            return None
        return payload if isinstance(payload, dict) else {}

    def serve_vendor(self, filename: str) -> None:
        allowed = {"maplibre-gl.js", "maplibre-gl.css", "maplibre-gl.js.map", "maplibre-gl-dates.js"}
        if filename not in allowed:
            self.respond_json({"error": "asset not found"}, status=404)
            return
        path = OHM_DATES_PATH if filename == "maplibre-gl-dates.js" else VENDOR_DIR / filename
        if not path.exists():
            self.respond_json({"error": "MapLibre assets are not installed; run npm install"}, status=404)
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.respond(200, path.read_bytes(), content_type)

    def serve_static(self, filename: str, service_worker: bool = False) -> None:
        relative = Path(filename)
        if not filename or relative.is_absolute() or ".." in relative.parts:
            self.respond_json({"error": "asset not found"}, status=404)
            return
        path = STATIC_DIR / relative
        if not path.is_file():
            self.respond_json({"error": "asset not found"}, status=404)
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        extra = {"Service-Worker-Allowed": "/"} if service_worker else None
        self.respond(200, path.read_bytes(), content_type, extra_headers=extra)

    def respond_json(self, payload: dict, status: int = 200) -> None:
        self.respond(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def respond(self, status: int, body: bytes, content_type: str, extra_headers: dict[str, str] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Cache-Control", "no-store" if content_type.startswith("application/json") else "no-cache")
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        return


def main() -> None:
    sanitize_legacy_audit_log()
    port = 8765
    for key in ("CONTEXTLENS_PORT", "STABLETRADE_PORT"):
        try:
            port = int(os.environ.get(key, port))
        except ValueError:
            port = 8765
        if key in os.environ:
            break
    server = ThreadingHTTPServer((HOST, port), Handler)
    print(f"ContextLens Memory Wormhole running at http://{HOST}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nContextLens stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
