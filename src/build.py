# Builds the multi-page Alhabib site from shared parts.
import os, re, shutil, struct
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)

EXTRA_CSS = r'''
/* ---- multi-page additions ---- */
.pin{overflow-x:auto;scroll-snap-type:x mandatory;scrollbar-width:none;padding-block:10px 30px}
.pin::-webkit-scrollbar{display:none}
.card{scroll-snap-align:start}
.scroll-ctl{display:flex;gap:10px}
.scroll-ctl button{width:52px;height:52px;border-radius:0 18px 0 18px;border:1.5px solid var(--line-2);display:grid;place-items:center;font-size:1.3rem;transition:all .3s}
.scroll-ctl button:hover{background:var(--red);border-color:var(--red);color:#fff}
.links a.on{color:inherit}
.links a.on::after{transform:scaleX(1)}
.nav.solid .links a.on{color:var(--red)}
/* page hero */
.phero{position:relative;min-height:min(62svh,620px);display:flex;align-items:flex-end;color:#fff;overflow:hidden;isolation:isolate;background:#2a2320}
.phero img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:-2;animation:kb 22s ease-in-out infinite alternate}
.phero::before{content:"";position:absolute;inset:0;z-index:-1;background:linear-gradient(270deg,rgba(20,14,12,.85),rgba(20,14,12,.35) 60%,rgba(20,14,12,.15)),linear-gradient(0deg,rgba(20,14,12,.6),transparent 50%)}
.phero .wrap{width:100%;padding-block:150px 64px}
.crumbs{display:flex;gap:10px;font-size:.95rem;color:rgba(255,255,255,.8)}
.crumbs a:hover{color:#fff;text-decoration:underline;text-underline-offset:6px}
.phero h1{font-size:clamp(2.6rem,6vw,5rem);font-weight:900;margin-top:14px}
.phero h1::after{content:"";display:block;width:80px;height:6px;background:var(--red);margin-top:20px;border-radius:0 6px 0 6px}
.phero p{margin-top:18px;max-width:52ch;font-size:1.15rem;color:rgba(255,255,255,.88)}
/* product rows */
.prod{display:grid;grid-template-columns:1.15fr 1fr;gap:clamp(30px,5vw,90px);align-items:center;padding-block:clamp(50px,7vw,100px);border-bottom:1px solid var(--line)}
.prod:nth-child(even) .frame{order:2}
.prod h2{font-size:clamp(2rem,3.6vw,3.2rem)}
.prod h2::after{content:"";display:block;width:64px;height:5px;background:var(--red);margin-top:16px;border-radius:0 5px 0 5px}
.prod p{margin-top:20px;color:var(--ink-2);max-width:50ch;font-size:1.08rem}
.uses{list-style:none;margin:22px 0 0;padding:0;display:flex;flex-wrap:wrap;gap:8px}
.uses li{padding:8px 16px;background:var(--cream);border-radius:0 14px 0 14px;font-weight:500;font-size:.95rem}
.prod .row{display:flex;flex-wrap:wrap;gap:12px;margin-top:30px}
/* works */
.filters{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:36px}
.filters button{height:44px;padding-inline:20px;border-radius:0 16px 0 16px;border:1.5px solid var(--line-2);font-weight:700;transition:all .3s}
.filters button:hover{border-color:var(--red);color:var(--red)}
.filters button[aria-pressed="true"]{background:var(--red);border-color:var(--red);color:#fff}
.works{columns:3 320px;column-gap:18px}
.work{break-inside:avoid;margin:0 0 18px;position:relative;overflow:hidden;border-radius:0 var(--leaf) 0 var(--leaf);background:var(--cream-2)}
.work img{width:100%;height:auto;transition:transform 1.2s var(--ease)}
.work:hover img{transform:scale(1.06)}
.work figcaption{position:absolute;inset-inline:14px;bottom:14px;background:rgba(255,255,255,.95);padding:10px 16px;border-radius:0 14px 0 14px;display:flex;justify-content:space-between;gap:10px;font-weight:700}
.work figcaption span{color:var(--red-deep);font-weight:500;font-size:.88rem}
/* ISO */
.iso{display:grid;grid-template-columns:1fr 2fr;gap:clamp(30px,5vw,80px);align-items:center}
.iso-list{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}
.iso-item{display:flex;flex-direction:column;align-items:center;text-align:center;gap:14px;padding:26px 16px;background:var(--white);border-radius:var(--leaf) 0 var(--leaf) 0;box-shadow:0 24px 44px -34px rgba(31,26,23,.35)}
.iso-item img{width:min(150px,80%);height:auto;transition:transform .8s var(--ease)}
.iso-item:hover img{transform:rotate(-8deg) scale(1.05)}
.iso-item b{font-size:1.05rem}
.iso-item span{color:var(--ink-2);font-size:.92rem}
.foot-iso{display:flex;gap:10px;margin-top:22px}
.foot-iso img{width:58px;height:58px;background:#fff;border-radius:50%}
/* process */
.proc{display:grid;grid-template-columns:repeat(4,1fr);gap:0;border-top:1px solid var(--line-2)}
.proc div{padding:30px 24px 10px;border-inline-start:1px solid var(--line-2)}
.proc div:first-child{border-inline-start:0;padding-inline-start:0}
.proc i{font-style:normal;font-family:var(--mono);color:var(--red-deep);font-size:1rem}
.proc b{display:block;font-size:1.25rem;margin-top:8px}
.proc p{color:var(--ink-2);margin-top:8px;font-size:.95rem}
/* forms */
.form{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.form .full{grid-column:1/-1}
.form label{display:flex;flex-direction:column;gap:6px;font-weight:700;font-size:.95rem}
.form input,.form select,.form textarea{font:inherit;font-weight:400;padding:14px 16px;border:1.5px solid var(--line-2);border-radius:0 14px 0 14px;background:#fff;color:var(--ink);transition:border-color .3s}
.form input:focus,.form select:focus,.form textarea:focus{outline:none;border-color:var(--red)}
.form textarea{min-height:130px;resize:vertical}
.form .err{color:var(--red-deep);font-size:.85rem;font-weight:500;min-height:1.2em}
.form-done{grid-column:1/-1;background:var(--cream);padding:20px 22px;border-radius:0 20px 0 20px;display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:14px}
.panel{background:var(--white);border-radius:0 var(--leaf) 0 var(--leaf);padding:clamp(24px,4vw,48px);box-shadow:0 30px 60px -40px rgba(31,26,23,.35)}
.contact-grid{display:grid;grid-template-columns:1fr 1.3fr;gap:clamp(30px,5vw,70px);align-items:start}
.cinfo{display:grid;gap:14px}
.cinfo div{padding:22px 24px;background:var(--cream);border-radius:0 24px 0 24px}
.cinfo dt{font-size:.85rem;color:var(--ink-2)}
.cinfo dd{margin:4px 0 0;font-size:1.3rem;font-weight:800}
.band{background:var(--ink);color:#fff;border-radius:0 var(--leaf) 0 var(--leaf);padding:clamp(30px,5vw,70px);display:grid;grid-template-columns:1.3fr 1fr;gap:30px;align-items:center;overflow:hidden;position:relative;isolation:isolate}
.band::after{content:"";position:absolute;inset:0;left:auto;width:50%;z-index:-1;background:url("img/cladding.jpg") center/cover;opacity:.35;mask-image:linear-gradient(90deg,#000,transparent)}
.band h2{font-size:clamp(1.9rem,4vw,3.2rem);font-weight:900}
.band p{color:#d9d2cc;margin-top:12px;max-width:46ch}
@media (max-width:900px){
  .prod,.iso,.contact-grid,.band{grid-template-columns:1fr}
  .prod:nth-child(even) .frame{order:0}
  .iso-list{grid-template-columns:repeat(3,1fr)}
  .proc{grid-template-columns:1fr 1fr}
  .proc div:nth-child(3){border-inline-start:0;padding-inline-start:0}
}
@media (max-width:600px){
  .iso-list{grid-template-columns:1fr}
  .form{grid-template-columns:1fr}
  .proc{grid-template-columns:1fr}
  .proc div{border-inline-start:0;padding-inline-start:0}
}
'''
EXTRA_CSS += r'''
/* ---- product card clip that plays on hover ---- */
.card .ph video{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;transform:scale(1.06);opacity:0;transition:transform 1.2s var(--ease),opacity .35s ease-out}
.card:hover .ph video{transform:scale(1.14)}
.card .ph video.on{opacity:1}
/* ISO seals resting on the top edge of the hero info strip, half over the photo */
.hero-base{position:relative}
.hero-iso{position:absolute;top:0;inset-inline-end:clamp(18px,2.2vw,28px);z-index:2;display:flex;flex-direction:row-reverse;gap:clamp(6px,.9vw,12px);transform:translateY(-60%)}
.hero-iso img{width:clamp(64px,6.4vw,92px);height:auto;aspect-ratio:1;border-radius:50%;filter:drop-shadow(0 14px 16px rgba(10,6,5,.38));transition:rotate .6s var(--ease),scale .6s var(--ease)}
.hero-iso img:hover{rotate:-8deg;scale:1.06}
.hero-iso:focus-visible{outline:3px solid #fff;outline-offset:6px;border-radius:999px}
.hero-strip div{padding-top:clamp(40px,4vw,50px)}
#iso{scroll-margin-top:72px}
/* hero clip: the house moves through the day as the page scrolls (site.js adds .scrub) */
.hero-img img{object-position:50% 50%;transform:none;animation:none;transform-origin:50% 55%}
.hero-vid{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:50% 50%;opacity:0;transition:opacity .6s var(--ease)}
.hero-vid.on{opacity:1}
.hero-track{position:relative}
.hero-track.scrub{background:var(--red)}
.hero-track.scrub .hero{position:sticky;min-height:100vh;min-height:100svh}
.hero-held .wa{transform:translateY(calc(-1 * var(--hold-lift, 0px)))}
@media print{.hero-track{height:auto!important;background:none}.hero-track .hero{position:relative!important;top:auto!important}.hero-vid{display:none}}
/* from imagination to reality: the plan and the finished work stacked; dragging the line changes only which part shows (site.js "compare") */
.sig{display:block;min-height:0;background:var(--cream);color:var(--ink);padding-block:clamp(20px,3vw,44px) clamp(64px,8vw,110px)}
.sig::before{content:none}
.sig-head{display:grid;grid-template-columns:1.2fr 1fr;gap:clamp(18px,4vw,56px);align-items:end;margin-bottom:clamp(26px,3.5vw,48px)}
.sig-head h2{margin-top:0;line-height:1.15;text-wrap:balance;color:var(--ink)}
.sig-head>p{color:var(--ink-2);max-width:44ch;font-size:1.1rem}
.sig-sub{margin-top:12px;color:var(--red-deep);font-weight:700}
.sig .promise span{border-color:rgba(31,26,23,.16);background:#fff;color:var(--ink);backdrop-filter:none}
.cmp{position:relative;direction:ltr;user-select:none;-webkit-user-select:none;-webkit-touch-callout:none;touch-action:pan-y;cursor:ew-resize;--k:56px}
.cmp-media{position:relative;aspect-ratio:1672/941;max-height:84vh;max-height:84svh;overflow:hidden;background:#EDEBE7;border-radius:0 clamp(28px,4vw,64px) 0 clamp(28px,4vw,64px);box-shadow:0 30px 60px -34px rgba(90,40,20,.45)}
.cmp-img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:50% 50%;pointer-events:none;-webkit-user-drag:none}
.cmp-before{position:absolute;inset:0;-webkit-clip-path:inset(0 50% 0 0);clip-path:inset(0 50% 0 0)}
.cmp-tag{position:absolute;top:clamp(12px,2vw,24px);padding:7px 16px;border-radius:0 14px 0 14px;font-weight:700;font-size:.92rem;line-height:1.6;pointer-events:none;transition:opacity .3s var(--ease)}
.cmp-tag-b{left:clamp(12px,2vw,24px);background:#fff;color:var(--ink);box-shadow:0 8px 20px -10px rgba(31,26,23,.35)}
.cmp-tag-a{right:clamp(12px,2vw,24px);background:var(--red);color:#fff;box-shadow:0 8px 20px -10px rgba(0,0,0,.5)}
.cmp-line{position:absolute;top:0;bottom:0;left:0;width:3px;margin-left:-1.5px;background:var(--red);box-shadow:0 0 0 1px rgba(255,255,255,.35);pointer-events:none;will-change:transform;transform:translate3d(0,0,0)}
.cmp-knob{position:absolute;top:50%;left:0;touch-action:none;width:var(--k);height:var(--k);margin:calc(var(--k) / -2) 0 0 calc(var(--k) / -2);cursor:grab;will-change:transform;outline:none;border-radius:0 20px 0 20px}
.cmp-k{display:grid;place-items:center;width:100%;height:100%;border-radius:inherit;background:var(--red);color:#fff;border:3px solid #fff;box-shadow:0 10px 24px -8px rgba(0,0,0,.55);transition:transform .25s var(--ease),background-color .25s var(--ease)}
.cmp-knob:hover .cmp-k{background:var(--red-deep)}
.cmp.dragging,.cmp.dragging .cmp-knob{cursor:grabbing}
.cmp.dragging .cmp-k{transform:scale(1.08);background:var(--red-deep)}
.cmp-knob:focus-visible .cmp-k{box-shadow:0 0 0 3px #fff,0 0 0 6px var(--ink)}
.cmp-hint{margin-top:16px;text-align:center;color:var(--ink-2);font-size:.95rem}
.sig-foot{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:18px 24px;margin-top:clamp(26px,3vw,40px)}
.sig-foot .promise{margin-top:0}
@media (max-width:900px){.sig-head{grid-template-columns:1fr;align-items:start}}
@media (max-width:700px){.cmp{--k:50px}.cmp-media{aspect-ratio:4/3}.cmp-tag{font-size:.85rem;padding:6px 12px}}
@media print{.cmp-line,.cmp-knob,.cmp-hint{display:none}}

/* branches: the name is a link to the branch on Google Maps */
.maplink{display:inline-flex;align-items:center;gap:8px;color:inherit;text-decoration:underline;text-decoration-color:rgba(218,31,38,.35);text-decoration-thickness:2px;text-underline-offset:6px;transition:color .2s var(--ease),text-decoration-color .2s var(--ease)}
.maplink svg{color:var(--red);flex:none;transition:transform .3s var(--ease)}
.maplink:hover,.maplink:focus-visible{color:var(--red);text-decoration-color:var(--red)}
.maplink:hover svg{transform:translateY(-3px)}

/* the designer's signature: the last thing on every page, shown only */
.sig-mark{display:flex;justify-content:center;margin-top:34px}
.sig-mark img{width:auto;height:44px;opacity:.5;pointer-events:none;user-select:none;-webkit-user-drag:none}

/* top clients: white logo tiles drifting along the red band under the hero */
.clients{background:var(--red);color:#fff;display:grid;grid-template-columns:auto 1fr;align-items:center;gap:clamp(14px,2vw,28px);padding-block:clamp(16px,1.8vw,24px) clamp(4px,.6vw,10px);padding-inline-start:var(--gut);overflow:hidden}
.clients-head{display:flex;align-items:center;gap:12px;padding-bottom:14px}
.clients h2{margin:0;font-size:clamp(1.15rem,1.7vw,1.5rem);font-weight:800;white-space:nowrap;line-height:1.3}
.clients-pause{flex:none;width:40px;height:40px;border-radius:50%;border:1.5px solid rgba(255,255,255,.7);background:transparent;color:#fff;display:grid;place-items:center;cursor:pointer;transition:background .3s,border-color .3s}
.clients-pause:hover{background:rgba(255,255,255,.14);border-color:#fff}
.clients-pause:focus-visible{outline:3px solid #fff;outline-offset:3px}
.clients-pause i{width:12px;height:14px;border-inline:4px solid currentColor;box-sizing:border-box}
.clients-pause[aria-pressed="true"] i{width:0;height:0;border-inline:0;border-block:8px solid transparent;border-left:13px solid currentColor;margin-left:3px}
.clients-view{overflow:hidden;cursor:grab;touch-action:pan-y pinch-zoom;user-select:none;-webkit-user-select:none;padding-block:10px 24px;-webkit-mask-image:linear-gradient(to left,transparent 0,#000 4%,#000 90%,transparent);mask-image:linear-gradient(to left,transparent 0,#000 4%,#000 90%,transparent)}
.clients-view.drag{cursor:grabbing}
.clients-view:focus-visible{outline:3px solid #fff;outline-offset:-3px;border-radius:0 18px 0 18px}
.clients-track{list-style:none;margin:0;padding:0;display:flex;gap:clamp(10px,1.2vw,16px);width:max-content;will-change:transform}
.client{flex:none;width:clamp(138px,13vw,188px);height:clamp(74px,6.6vw,96px);display:grid;place-items:center;background:#fff;border-radius:0 18px 0 18px;box-shadow:0 12px 24px -16px rgba(60,6,8,.55)}
.client img{max-width:80%;max-height:64%;width:auto;height:auto;object-fit:contain;pointer-events:none}
.client.txt span{color:var(--ink);font-weight:800;font-size:clamp(.82rem,1vw,.98rem);line-height:1.35;text-align:center;padding-inline:10px}
@media (max-width:700px){.clients{grid-template-columns:1fr;padding-inline-start:0;row-gap:4px}.clients-head{padding-inline:var(--gut);padding-bottom:0;justify-content:space-between}
  .clients-view{-webkit-mask-image:linear-gradient(to left,transparent 0,#000 6%,#000 94%,transparent);mask-image:linear-gradient(to left,transparent 0,#000 6%,#000 94%,transparent)}}
@media (max-width:900px){.hero-strip div{padding-top:24px}.hero-strip div:nth-child(-n+2){padding-top:clamp(36px,5vw,46px)}}
@media (max-width:600px){.hero-copy{padding-block:156px 62px}.hero-iso{inset-inline-end:auto;inset-inline-start:18px}.hero-strip div{padding-top:18px}.hero-strip div:nth-child(-n+2){padding-top:36px}}
.prod .frame video{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:0;transition:opacity .35s ease-out}
.prod .frame video.on{opacity:1}

/* ---- project reels (works page) ---- */
.reels-head{display:flex;align-items:end;justify-content:space-between;gap:20px;flex-wrap:wrap;margin-bottom:28px}
.reels-head p{color:var(--mute);max-width:48ch;margin-top:10px}
.reels{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,210px),280px));gap:18px;margin-bottom:clamp(56px,8vw,96px)}
.reel{position:relative;display:block;width:100%;aspect-ratio:9/16;overflow:hidden;isolation:isolate;border-radius:0 var(--leaf) 0 var(--leaf);background:var(--ink);color:#fff;text-align:start;cursor:pointer;box-shadow:0 30px 50px -36px rgba(31,26,23,.6);transition:transform .6s var(--ease),box-shadow .6s var(--ease)}
.reel video,.reel img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:-2;transition:transform 1.2s var(--ease),filter .6s var(--ease)}
.reel::after{content:"";position:absolute;inset:0;z-index:-1;background:linear-gradient(0deg,rgba(20,14,12,.82),rgba(20,14,12,.1) 45%,transparent 70%)}
.reel .cap{position:absolute;inset-inline:18px;bottom:18px;display:grid;gap:4px}
.reel .cap b{font-size:1.12rem;line-height:1.4}
.reel .cap span{font-size:.88rem;color:#f3e3d3;display:flex;gap:10px;align-items:center}
.reel .cap .mono{font-size:.82rem;letter-spacing:.02em;font-style:normal}
.reel .play{position:absolute;top:16px;inset-inline-start:16px;width:48px;height:48px;border-radius:0 16px 0 16px;background:var(--red);display:grid;place-items:center;box-shadow:0 12px 24px -12px rgba(120,20,20,.8);transition:transform .5s var(--ease),background .3s}
.reel .play svg{width:18px;height:18px;fill:#fff}
.reel:hover{transform:translateY(-6px);box-shadow:0 44px 60px -40px rgba(31,26,23,.7)}
.reel:hover video,.reel:hover img{transform:scale(1.05)}
.reel:hover .play{transform:scale(1.08);background:var(--red-deep)}
.reel:focus-visible{outline:3px solid var(--red);outline-offset:4px}
.player{position:fixed;inset:0;width:100%;height:100%;max-width:none;max-height:none;margin:0;padding:0;border:0;background:transparent;overflow:hidden;color:#fff}
.player::backdrop{background:rgba(20,14,12,.94)}
.player[open]::backdrop{animation:bdin .35s ease-out}
@keyframes bdin{from{opacity:0}}
.player .stage{position:absolute;inset:0;display:grid;grid-template-columns:auto minmax(0,auto) auto;align-items:center;justify-content:center;gap:clamp(10px,3vw,40px);padding:clamp(56px,6vh,80px) 16px clamp(20px,4vh,40px)}
.player figure{margin:0;display:grid;gap:14px;justify-items:start}
.player .frame-v{position:relative;height:min(calc(100svh - clamp(56px,6vh,80px) - clamp(20px,4vh,40px) - 90px),calc((100vw - 32px) * 16 / 9));aspect-ratio:9/16;max-width:calc(100vw - 32px);border-radius:0 calc(var(--leaf) * .6) 0 calc(var(--leaf) * .6);overflow:hidden;background:#000;box-shadow:0 60px 90px -50px rgba(0,0,0,.9)}
.player .frame-v.wide{aspect-ratio:16/9;height:auto;width:min(84vw,calc((100svh - 200px) * 16 / 9))}
.player video{width:100%;height:100%;object-fit:contain;display:block;background:#000}
.player figcaption{display:grid;gap:2px}
.player figcaption b{font-size:1.2rem}
.player figcaption span{color:#e9d9c9;font-size:.92rem}
.player .x,.player .nav-b{width:52px;height:52px;border-radius:0 18px 0 18px;display:grid;place-items:center;border:1.5px solid rgba(255,255,255,.35);color:#fff;transition:background .3s,border-color .3s,transform .4s var(--ease)}
.player .x{position:absolute;top:16px;inset-inline-end:16px;z-index:2}
.player .x:hover,.player .nav-b:hover{background:var(--red);border-color:var(--red)}
.player .nav-b:disabled{opacity:.3;pointer-events:none}
.player svg.i{width:22px;height:22px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.player .x:focus-visible,.player .nav-b:focus-visible{outline:3px solid #fff;outline-offset:3px}
@media (max-width:700px){
  .reels{grid-template-columns:1fr 1fr;gap:12px}
  .reel .cap{inset-inline:12px;bottom:12px}
  .reel .cap b{font-size:.98rem}
  .reel .play{width:40px;height:40px;top:12px;inset-inline-start:12px}
  .player .stage{grid-template-columns:1fr;justify-items:center;padding-top:76px}
  .player .nav-b{display:none}
  .player .frame-v{height:min(calc(100svh - 76px - clamp(20px,4vh,40px) - 90px),calc((100vw - 32px) * 16 / 9))}
}
@media (max-height:520px) and (orientation:landscape){
  .player .stage{padding:16px 84px 16px 16px}
  .player figure{grid-template-columns:auto auto;align-items:end;gap:18px}
  .player .frame-v{height:calc(100svh - 32px)}
  .player .frame-v.wide{height:auto;width:min(70vw,calc((100svh - 32px) * 16 / 9))}
}
.motion-t{display:inline-flex;align-items:center;gap:10px;height:44px;padding-inline:18px;border-radius:0 16px 0 16px;border:1.5px solid var(--line-2);font-weight:700;color:var(--ink-2);transition:border-color .3s,color .3s}
.motion-t svg{width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:2.2;stroke-linecap:round}
.motion-t .ir{fill:currentColor;stroke:none;display:none}
.motion-t[aria-pressed="true"] .ir{display:inline}
.motion-t[aria-pressed="true"] .ip{display:none}
.motion-t:hover{border-color:var(--red);color:var(--red-deep)}
.motion-t:focus-visible{outline:3px solid var(--red);outline-offset:3px}
@media (prefers-reduced-motion:reduce){
  .reel,.reel video,.reel img,.reel .play{transition:none}
  .reel:hover{transform:none}
  .reel:hover video,.reel:hover img{transform:none}
}
'''

base = open(os.path.join(HERE, 'base.css')).read()
# drop desktop-only pin rules from the single-page build
base = re.sub(r'\n  \.pin\{overflow-x:auto;[^\n]*\n  \.pin::-webkit-scrollbar\{display:none\}\n  \.card\{scroll-snap-align:center;width:min\(84vw,420px\)\}', '\n  .card{width:min(84vw,420px)}', base)
open(os.path.join(OUT, 'site.css'), 'w').write(base + EXTRA_CSS)

WA = '966530868800'
# every "book a consultation" button opens WhatsApp with the message ready to send (user decision 2026-09-28;
# it used to open the Odoo calendar at https://masatech-habib-factory.odoo.com/calendar/mw-d-stshr-m-1)
from urllib.parse import quote as _q
BOOK = f'https://wa.me/{WA}?text=' + _q('حجز استشارة')
FIX = 'https://masatech-habib-factory.odoo.com/fix'
COMPLAIN = 'https://masatech-habib-factory.odoo.com/complaints'
PORTAL = 'https://masatech-habib-factory.odoo.com/portal-employees'
COPY_SVG = '<svg viewBox="0 0 24 24"><rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V4H4v12h4"/></svg>'
FAV = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Cpath d='M0 0h24a8 8 0 0 1 8 8v24H8a8 8 0 0 1-8-8z' fill='%23DA1F26'/%3E%3Cpath d='M11 25V9h9v5' stroke='%23fff' stroke-width='3' fill='none'/%3E%3C/svg%3E"

NAV = [('index.html', 'الرئيسية'), ('products.html', 'منتجاتنا'), ('works.html', 'أعمالنا'), ('services.html', 'خدماتنا'),
       ('branches.html', 'مواقع الفروع'), ('franchise.html', 'الامتياز التجاري'), ('contact.html', 'اتصل بنا')]

PRODUCTS = [
  ('doors', 'الأبواب', 'door.jpg', 'باب محوري من الزجاج بإطار ألمنيوم أسود',
   'أبواب ألمنيوم وزجاج للمداخل والغرف والمحلات، من الأبواب المفصلية والسحاب إلى الأبواب المحورية الكبيرة. خطوط نظيفة، حلوق متينة، وتشطيبات تعيش سنين.',
   ['مداخل الفلل', 'المحلات والمعارض', 'الغرف والمكاتب', 'الأبواب المحورية']),
  ('windows', 'النوافذ', 'window.jpg', 'نوافذ سحاب بطول الجدار تطل على الخارج',
   'نوافذ سحاب ومفصلية بعزل يحفظ الهدوء والبرودة، بمقاسات تناسب كل فتحة حتى الجدار الكامل من الأرض للسقف.',
   ['نوافذ سحاب', 'نوافذ مفصلية', 'جدران زجاجية كاملة', 'عزل حراري وصوتي']),
  ('facades', 'الواجهات', 'facade.jpg', 'برج بواجهة زجاجية وستائر ألمنيوم',
   'واجهات زجاجية وستائر حائطية للأبراج والمباني التجارية والفلل، تعطي المبنى حضوره من أول نظرة وتحميه من الحرارة.',
   ['الأبراج التجارية', 'المباني الإدارية', 'واجهات الفلل', 'الستائر الحائطية']),
  ('cladding', 'الكلادينج', 'cladding.jpg', 'مبنى مكسو بألواح كلادينج بيضاء مع واجهة زجاجية',
   'كسوة واجهات بألواح الكلادينج بتشكيلات هندسية، تحمي المبنى وتعطيه هوية معمارية واضحة تدوم.',
   ['واجهات المعارض', 'المباني التجارية', 'تشكيلات هندسية', 'اللوحات والهويات']),
  ('skylights', 'الأسقف الزجاجية', 'skylight.jpg', 'سقف زجاجي مائل فوق صالة داخلية',
   'أسقف زجاجية ومناور تدخل الضوء الطبيعي للمجالس والأحواش والممرات، بهياكل ألمنيوم متينة وتصريف محكم.',
   ['المناور', 'الأحواش', 'الممرات والصالات', 'أسقف المجالس']),
  ('domes', 'القبب الزجاجية', 'dome.jpg', 'قبة زجاجية بأضلاع ألمنيوم فوق مبنى دائري',
   'قبب زجاجية بتصاميم هندسية تصير قطعة فنية بحد ذاتها فوق المداخل والصالات، وتغمر المكان بالضوء.',
   ['مداخل القصور', 'الصالات الكبيرة', 'المساجد', 'المباني العامة']),
  ('glass', 'الزجاج المتخصص', 'glass.jpg', 'ألواح زجاج على حوامل داخل المصنع',
   'ألواح زجاج بالجملة والتجزئة، تُقص وتُجهّز حسب مشروعك في مصنعنا بالمدينة الصناعية الأولى في القصيم.',
   ['بيع بالجملة', 'بيع بالتجزئة', 'قص حسب المقاس', 'تجهيز للمشاريع']),
]

WORKS = [
  ('tent.jpg', 'جلسة زجاجية مثمنة على تراس', 'خيام زجاجية', 'tent'),
  ('hero.jpg', 'فيلا بواجهات زجاجية', 'واجهات', 'facade'),
  ('facade.jpg', 'برج بستائر زجاجية', 'واجهات', 'facade'),
  ('cladding.jpg', 'مبنى بكسوة كلادينج', 'كلادينج', 'cladding'),
  ('door.jpg', 'باب محوري للمدخل', 'أبواب ونوافذ', 'doors'),
  ('window.jpg', 'نوافذ سحاب بطول الجدار', 'أبواب ونوافذ', 'doors'),
  ('skylight.jpg', 'سقف زجاجي لصالة', 'أسقف وقبب', 'roof'),
  ('dome.jpg', 'قبة زجاجية', 'أسقف وقبب', 'roof'),
  ('domeb.jpg', 'القبة من الداخل', 'أسقف وقبب', 'roof'),
]
import json
_vj = os.path.join(HERE, 'videos.json')
if os.environ.get('DEMO'): _vj = os.path.join(HERE, 'videos.demo.json')
VIDEOS = json.load(open(_vj)) if os.path.exists(_vj) else []
PLAY_SVG = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 4.5v15a1 1 0 0 0 1.5.86l12.5-7.5a1 1 0 0 0 0-1.72L8.5 3.64A1 1 0 0 0 7 4.5z"/></svg>'

def fmt_dur(sec):
    sec = int(round(sec)); return f'{sec // 60}:{sec % 60:02d}'

def reels_block():
    if not VIDEOS: return ''
    cards = ''
    for i, v in enumerate(VIDEOS):
        cards += (f'<button type="button" class="reel" data-cat="{v["cat"]}" data-i="{i}" data-src="vid/{v["slug"]}.mp4" data-title="{v["title"]}" data-sub="{v["catLabel"]}"'
                  f'{" data-wide" if not v.get("portrait", True) else ""} aria-label="شغّل مقطع {v["title"]}">'
                  f'<video muted loop playsinline preload="none" poster="vid/{v["slug"]}.jpg" data-loop="vid/{v["slug"]}-loop.mp4" aria-hidden="true"></video>'
                  f'<span class="play">{PLAY_SVG}</span>'
                  f'<span class="cap"><b>{v["title"]}</b><span>{v["catLabel"]}<i class="mono">{fmt_dur(v["dur"])}</i></span></span></button>')
    return f'''<div class="reels-head"><div><h2 class="title">مشاريعنا <u>بالفيديو</u></h2><p>لقطات من مشاريع نفذها فريق مصنع الحبيب في الموقع. اضغط أي مقطع لمشاهدته كامل مع الصوت.</p></div>
    <button type="button" class="motion-t" id="reelsMotion" aria-pressed="false"><svg viewBox="0 0 24 24" aria-hidden="true"><path class="ip" d="M9 6v12M15 6v12"/><path class="ir" d="M8 5.5v13l11-6.5z"/></svg><span>إيقاف الحركة</span></button></div>
  <div class="reels" id="reels">{cards}</div>
  <h2 class="title" style="margin-bottom:28px">معرض <u>الأعمال</u></h2>'''

PLAYER = '''<dialog class="player" id="player" aria-label="مشغل الفيديو">
  <button type="button" class="x" data-close aria-label="إغلاق"><svg class="i" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg></button>
  <div class="stage">
    <button type="button" class="nav-b" data-step="-1" aria-label="المقطع السابق"><svg class="i" viewBox="0 0 24 24"><path d="M9 6l6 6-6 6"/></svg></button>
    <figure><div class="frame-v"><video controls playsinline preload="metadata"></video></div><figcaption aria-live="polite" aria-atomic="true"><b></b><span></span></figcaption></figure>
    <button type="button" class="nav-b" data-step="1" aria-label="المقطع التالي"><svg class="i" viewBox="0 0 24 24"><path d="M15 6l-6 6 6 6"/></svg></button>
  </div>
</dialog>'''

FILTERS = [('all', 'الكل'), ('facade', 'واجهات'), ('doors', 'أبواب ونوافذ'), ('roof', 'أسقف وقبب'), ('tent', 'خيام زجاجية'), ('cladding', 'كلادينج')]

ISO = [('iso9001.png', 'ISO 9001:2015', 'نظام إدارة الجودة'),
       ('iso14001.png', 'ISO 14001:2015', 'نظام الإدارة البيئية'),
       ('iso45001.png', 'ISO 45001:2018', 'نظام إدارة السلامة والصحة المهنية')]

BRANCHES = [
  ('القصيم', 'المقر الرئيسي والمصنع', 'المدينة الصناعية الأولى، القصيم', ['0530868800'], True),
  ('الرياض', 'فرع الياسمين', '', ['0501438000', '0532787000', '0530591000'], False),
  ('الرياض', 'فرع مخرج 17', '', ['0537463000'], False),
  ('بريدة', 'فرع الدائري الشمالي', '', ['0534264000', '0504629000'], False),
  ('حائل', 'فرع حائل', 'للتواصل عبر خط المبيعات الموحد', ['0530868800'], False),
]

# each branch name opens Google Maps. Until the factory sends each branch's exact pin link, the link searches
# the factory's name with the branch and city; paste a maps.app.goo.gl link into MAPS to pin one exactly.
from urllib.parse import quote
MAPS = {'فرع الدائري الشمالي': 'https://maps.app.goo.gl/LqDKbkHfdy7opApQ8'}
def map_url(city, name):
    if name in MAPS: return MAPS[name]
    area = 'المدينة الصناعية الأولى بريدة' if name == 'المقر الرئيسي والمصنع' else f"{name.replace('فرع ', '')} {city}".replace(f'{city} {city}', city)
    return 'https://www.google.com/maps/search/?api=1&query=' + quote(f'مصنع الحبيب للزجاج والألمنيوم {area}')
PIN_SVG = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M12 21s-7-6.1-7-11.5a7 7 0 0 1 14 0C19 14.9 12 21 12 21z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><circle cx="12" cy="9.5" r="2.5" fill="currentColor"/></svg>'

def fmt(n): return f'{n[:3]} {n[3:6]} {n[6:]}'
def chip(n, label=None):
    return f'<button class="chip copy" data-copy="{n}">{COPY_SVG}{label or fmt(n)}</button>'

# link previews (WhatsApp, X, etc.) need an absolute image URL; change this when the site moves to its own domain
SITE_URL = 'https://fasjah1212-lgtm.github.io/alhabib-website/'

def head(title, desc, full):
    t = f'<title>{title}</title>'
    common = f'''<meta name="description" content="{desc}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="مصنع الحبيب للزجاج والألمنيوم">
<meta property="og:locale" content="ar_SA">
<meta property="og:image" content="{SITE_URL}img/og.jpg">
<meta property="og:image:type" content="image/jpeg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="شعار مصنع الحبيب للزجاج والألمنيوم">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{SITE_URL}img/og.jpg">
<meta name="theme-color" content="#DA1F26">
<link rel="icon" href="{FAV}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;500;700;800;900&family=IBM+Plex+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="site.css">'''
    if full:
        return f'<!doctype html>\n<html lang="ar" dir="rtl">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n{t}\n{common}\n</head>\n<body>\n'
    return f'{t}\n<script>document.documentElement.setAttribute("dir","rtl");document.documentElement.setAttribute("lang","ar");</script>\n{common}\n'

def header(active):
    ON = ' class="on" aria-current="page"'
    links = ''.join(f'<a href="{h}"{ON if h == active else ""}>{l}</a>' for h, l in NAV)
    return f'''<a class="skip" href="#main">تخطَّ إلى المحتوى</a>
<header class="nav" id="nav">
  <div class="wrap nav-in">
    <a href="index.html" class="logo" aria-label="مصنع الحبيب للزجاج والألمنيوم، الرئيسية"><img src="img/logo.png" alt="مصنع الحبيب alhabib factory" width="155" height="52"></a>
    <nav class="links" aria-label="القائمة الرئيسية">{links}</nav>
    <div class="nav-cta">
      <a class="btn btn-red" href="{BOOK}" target="_blank" rel="noopener">احجز استشارة</a>
      <button class="menu-btn" id="menuBtn" aria-label="فتح القائمة" aria-expanded="false"><span></span></button>
    </div>
  </div>
</header>
<div class="drawer" id="drawer" hidden>
  <button class="x" id="menuClose" aria-label="إغلاق القائمة">×</button>
  {links}
</div>
'''

SOCIAL = '''<div class="socials">
          <a href="https://x.com/alhabib_fac" target="_blank" rel="noopener" aria-label="إكس"><svg viewBox="0 0 24 24"><path d="M17.8 3h3.1l-6.8 7.8L22 21h-6.2l-4.9-6.4L5.3 21H2.2l7.3-8.3L2 3h6.4l4.4 5.8zm-1.1 16.2h1.7L7.4 4.7H5.5z"/></svg></a>
          <a href="https://www.instagram.com/alhabib_fac/" target="_blank" rel="noopener" aria-label="إنستقرام"><svg viewBox="0 0 24 24"><path d="M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10zm0 8.2a3.2 3.2 0 1 1 0-6.4 3.2 3.2 0 0 1 0 6.4zM17.3 5.5a1.2 1.2 0 1 0 0 2.4 1.2 1.2 0 0 0 0-2.4zM12 2c-2.7 0-3 0-4.1.1C4.3 2.3 2.3 4.3 2.1 7.9 2 9 2 9.3 2 12s0 3 .1 4.1c.2 3.6 2.2 5.6 5.8 5.8 1.1.1 1.4.1 4.1.1s3 0 4.1-.1c3.6-.2 5.6-2.2 5.8-5.8.1-1.1.1-1.4.1-4.1s0-3-.1-4.1c-.2-3.6-2.2-5.6-5.8-5.8C15 2 14.7 2 12 2zm0 1.8c2.7 0 3 0 4 .1 2.7.1 4 1.4 4.1 4.1.1 1 .1 1.3.1 4s0 3-.1 4c-.1 2.7-1.4 4-4.1 4.1-1 .1-1.3.1-4 .1s-3 0-4-.1c-2.7-.1-4-1.4-4.1-4.1-.1-1-.1-1.3-.1-4s0-3 .1-4C4 5.3 5.3 4 8 3.9c1-.1 1.3-.1 4-.1z"/></svg></a>
          <a href="https://www.tiktok.com/@alhabibfac" target="_blank" rel="noopener" aria-label="تيك توك"><svg viewBox="0 0 24 24"><path d="M16.6 2h-3.3v13.2a2.9 2.9 0 1 1-2-2.8V9a6.3 6.3 0 1 0 5.3 6.2V8.6a7.9 7.9 0 0 0 4.4 1.4V6.7A4.6 4.6 0 0 1 16.6 2z"/></svg></a>
          <a href="https://www.youtube.com/@alhabib_fac/videos" target="_blank" rel="noopener" aria-label="يوتيوب"><svg viewBox="0 0 24 24"><path d="M23 7.2a3 3 0 0 0-2.1-2.1C19 4.6 12 4.6 12 4.6s-7 0-8.9.5A3 3 0 0 0 1 7.2 31 31 0 0 0 .5 12a31 31 0 0 0 .5 4.8 3 3 0 0 0 2.1 2.1c1.9.5 8.9.5 8.9.5s7 0 8.9-.5a3 3 0 0 0 2.1-2.1 31 31 0 0 0 .5-4.8 31 31 0 0 0-.5-4.8zM9.8 15.1V8.9L15.5 12z"/></svg></a>
          <a href="https://www.linkedin.com/company/alhabib-factory" target="_blank" rel="noopener" aria-label="لينكدإن"><svg viewBox="0 0 24 24"><path d="M4.98 3.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5zM3 9.8h4V21H3zM9.5 9.8h3.8v1.6h.1c.5-1 1.8-2 3.8-2 4 0 4.8 2.6 4.8 6V21h-4v-5c0-1.2 0-2.8-1.7-2.8s-2 1.3-2 2.7V21h-4z"/></svg></a>
        </div>'''

def footer(full):
    prods = ''.join(f'<li><a href="products.html#{i}">{n}</a></li>' for i, n, *_ in PRODUCTS)
    iso = ''.join(f'<img src="img/{f}" alt="{c}" width="58" height="58">' for f, c, _ in ISO)
    return f'''
<footer>
  <div class="wrap">
    <div class="foot">
      <div><a href="index.html" class="flogo"><img src="img/logo.png" alt="مصنع الحبيب"></a>
        <p>مصنع الحبيب للزجاج والألمنيوم. صُنع لك ومن أجلك.. وكما تتخيل.</p>
        {SOCIAL}
        <div class="foot-iso">{iso}</div></div>
      <div><h2>المنتجات</h2><ul>{prods}</ul></div>
      <div><h2>الخدمات</h2><ul><li><a href="{FIX}" target="_blank" rel="noopener">طلبات الصيانة</a></li><li><a href="{BOOK}" target="_blank" rel="noopener">احجز موعد استشارة</a></li><li><a href="{COMPLAIN}" target="_blank" rel="noopener">صوتك مسموع</a></li><li><a href="{PORTAL}" target="_blank" rel="noopener">البوابة الإلكترونية للموظفين</a></li></ul></div>
      <div><h2>الشركة</h2><ul>{''.join(f'<li><a href="{h}">{l}</a></li>' for h, l in NAV[2:])}</ul></div>
    </div>
    <div class="foot-bottom"><span>© 2026 مصنع الحبيب للزجاج والألمنيوم. جميع الحقوق محفوظة.</span><span>صناعة سعودية · القصيم</span></div>
    <div class="sig-mark"><img src="img/signature.png" alt="" width="65" height="72" loading="lazy" draggable="false"></div>
  </div>
</footer>
<a class="wa" href="https://wa.me/{WA}" target="_blank" rel="noopener" aria-label="تواصل عبر واتساب"><svg viewBox="0 0 24 24"><path d="M17.5 14.4c-.3-.1-1.8-.9-2-1-.3-.1-.5-.1-.7.1-.2.3-.8 1-.9 1.2-.2.2-.3.2-.6.1-.3-.1-1.3-.5-2.4-1.5-.9-.8-1.5-1.8-1.7-2.1-.2-.3 0-.5.1-.6l.4-.5c.2-.2.2-.3.3-.5.1-.2 0-.4 0-.5l-.9-2.2c-.2-.6-.5-.5-.7-.5h-.6c-.2 0-.5.1-.8.4-.3.3-1 1-1 2.5s1.1 2.9 1.2 3.1c.1.2 2.1 3.2 5.1 4.5.7.3 1.3.5 1.7.6.7.2 1.4.2 1.9.1.6-.1 1.8-.7 2-1.4.2-.7.2-1.3.2-1.4-.1-.2-.3-.3-.6-.4zM12 21.8c-1.8 0-3.5-.5-5-1.4l-.4-.2-3.7 1 1-3.6-.2-.4A9.8 9.8 0 0 1 12 2.2a9.8 9.8 0 0 1 0 19.6zM12 0a12 12 0 0 0-10.3 18L0 24l6.2-1.6A12 12 0 1 0 12 0z"/></svg></a>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/ScrollTrigger.min.js"></script>
<script src="site.js"></script>
''' + ('</body>\n</html>\n' if full else '')

def phero(title, sub, img, alt, crumb):
    return f'''<section class="phero"><img src="img/{img}" alt="{alt}" fetchpriority="high">
  <div class="wrap"><nav class="crumbs" aria-label="مسار الصفحة"><a href="index.html">الرئيسية</a><span aria-hidden="true">/</span><span>{crumb}</span></nav>
  <h1>{title}</h1><p>{sub}</p></div></section>'''

def cta():
    return f'''<section class="sec" style="padding-top:0"><div class="wrap"><div class="cta">
      <div><h2>كما تتخيل.. نصنعه لك</h2><p>خبّرنا وش في بالك، والباقي علينا.</p>
        <div class="row"><a class="btn btn-white" href="https://wa.me/{WA}" target="_blank" rel="noopener">راسلنا واتساب</a><a class="btn btn-ghostw" href="contact.html">صفحة التواصل <span class="arrow">←</span></a></div></div>
      <div><span style="opacity:.8">المبيعات</span><span class="phone">053 086 8800</span>
        <div class="row">{chip('0530868800','انسخ الرقم').replace('class="chip copy"','class="chip copy" style="color:var(--red)"')}{chip('info@alhabibsa.com','info@alhabibsa.com').replace('class="chip copy"','class="chip copy" style="color:var(--red)"')}</div></div>
    </div></div></section>'''

def iso_block():
    items = ''.join(f'<div class="iso-item"><img src="img/{f}" alt="شهادة {c}" width="150" height="150" loading="lazy"><b class="mono">{c}</b><span>{d}</span></div>' for f, c, d in ISO)
    return f'''<section class="sec cream" id="iso"><div class="wrap iso">
      <div><h2 class="title">شهادات <u>الجودة</u> العالمية</h2><p class="lead" style="margin-top:22px">مصنع حاصل على شهادات الأيزو في الجودة والبيئة والسلامة المهنية، عشان كل منتج يطلع من مصنعنا بمعايير عالمية.</p></div>
      <div class="iso-list">{items}</div></div></section>'''

# product cards that swap their photo for a clip that plays on hover (key -> first-frame still, clip)
HERO_VID = ('house-scrub.mp4', 'house-scrub-m.mp4')  # home hero, scrubbed by scroll (site.js)
HOVER_VID = {'doors': ('door-first.jpg', 'door-open.mp4'), 'windows': ('window-first.jpg', 'window-open.mp4'), 'facades': ('facade-first.jpg', 'facade-build.mp4'), 'cladding': ('cladding-first.jpg', 'cladding-build.mp4'), 'skylights': ('skylight-first.jpg', 'skylight-cycle.mp4'), 'domes': ('dome-first.jpg', 'dome-cycle.mp4'), 'glass': ('glass-first.jpg', 'glass-showcase.mp4')}

def prod_cards():
    out = ''
    for i, n, img, alt, desc, _ in PRODUCTS:
        hv = HOVER_VID.get(i)
        media = (f'<img src="img/{hv[0]}" alt="{alt}" loading="lazy" width="1400" height="1050">'
                 f'<video muted loop playsinline preload="none" aria-hidden="true" tabindex="-1" data-src="vid/{hv[1]}"></video>') if hv else \
                f'<img src="img/{img}" alt="{alt}" loading="lazy" width="1400" height="1050">'
        out += f'''<article class="card"><a href="products.html#{i}" class="ph">{media}</a>
        <div class="card-body"><h3>{n}</h3><p>{desc.split('،')[0]}.</p><a class="more" href="products.html#{i}">التفاصيل <span class="arrow">←</span></a></div></article>'''
    return out

def branches_block():
    rows = ''
    for city, name, note, phones, hq in BRANCHES:
        rows += f'''<div class="branch"><div><span class="city">{city}</span><h3><a class="maplink" href="{map_url(city, name)}" target="_blank" rel="noopener" aria-label="{name}، افتح الموقع في خرائط قوقل">{name}{PIN_SVG}</a></h3>{f'<p class="note">{note}</p>' if note else ''}</div>{'<span class="tag">المقر</span>' if hq else '<span></span>'}
          <div class="phones">{''.join(chip(p) for p in phones)}</div></div>'''
    mp = '''<div class="map" aria-label="خريطة مواقع الفروع">
        <svg viewBox="0 0 600 400">
          <g stroke="rgba(31,26,23,.07)"><path d="M40 0V400M105 0V400M170 0V400M235 0V400M300 0V400M365 0V400M430 0V400M495 0V400M560 0V400M0 40H600M0 104H600M0 168H600M0 232H600M0 296H600M0 360H600"/></g>
          <g font-family="IBM Plex Mono,monospace" font-size="9" fill="#665C56"><text x="44" y="392">40°E</text><text x="304" y="392">44°E</text><text x="564" y="392">48°E</text><text x="4" y="36">28.5°N</text><text x="4" y="356">23.5°N</text></g>
          <path class="route" d="M150 103 Q220 120 298 177"/><path class="route" d="M298 177 Q400 200 475 283"/>
          <g font-family="Tajawal,sans-serif" fill="#1F1A17" text-anchor="middle">
            <circle cx="150" cy="103" r="7" class="ring"/><circle cx="150" cy="103" r="6" fill="#DA1F26"/>
            <text x="150" y="80" font-size="17" font-weight="700">حائل</text>
            <circle cx="298" cy="177" r="8" class="ring" style="animation-delay:-.9s"/><circle cx="298" cy="177" r="9" fill="#DA1F26"/><circle cx="298" cy="177" r="3.5" fill="#fff"/>
            <text x="298" y="150" font-size="18" font-weight="800">القصيم · بريدة</text><text x="298" y="206" font-size="11" fill="#665C56">المقر الرئيسي والمصنع</text>
            <circle cx="475" cy="283" r="7" class="ring" style="animation-delay:-1.8s"/><circle cx="475" cy="283" r="6" fill="#DA1F26"/>
            <text x="475" y="260" font-size="17" font-weight="700">الرياض</text><text x="475" y="308" font-size="11" fill="#665C56">فرعين</text>
          </g>
        </svg>
      </div>'''
    return f'<div class="br">{mp}<div>{rows}</div></div>'

SVC = [
  ('<svg viewBox="0 0 48 48"><rect x="6" y="6" width="36" height="36" rx="2"/><path d="M6 20h36M20 20v22M12 13h6"/></svg>', 'خدمات ما قبل البيع', 'نزور موقعك، نقيس ونقترح الحلول المناسبة للمساحة والميزانية قبل ما تبدأ.', 'contact.html', 'تواصل مع المبيعات', False),
  ('<svg viewBox="0 0 48 48"><path d="M29 12a8 8 0 0 0-10.8 10.8L6 35l7 7 12.2-12.2A8 8 0 0 0 36 19l-5 5-5-1-1-5z"/></svg>', 'طلبات الصيانة وخدمة العملاء', 'ارفع طلب صيانة لمنتجاتك وفريقنا يتابعه معك حتى يُقفل.', FIX, 'قدّم طلب صيانة', True),
  ('<svg viewBox="0 0 48 48"><rect x="6" y="10" width="36" height="32" rx="3"/><path d="M6 20h36M16 6v8M32 6v8M15 28h6M27 28h6M15 35h6"/></svg>', 'حجز استشارة عامة', 'احجز موعد مع مختصينا ونراجع معك فكرتك ونحولها لتصميم قابل للتنفيذ.', BOOK, 'احجز موعدك', True),
  ('<svg viewBox="0 0 48 48"><path d="M8 10h32v22H18l-10 8z"/><path d="M16 18h16M16 24h10"/></svg>', 'صوتك مسموع', 'ملاحظاتك وشكاويك تصل للإدارة مباشرة، ونرد عليك.', COMPLAIN, 'أرسل ملاحظتك', True),
]
EXT = ' target="_blank" rel="noopener"'
def svc_list():
    return '<div class="svc-list">' + ''.join(
        f'<div class="svc-row">{s}<h3>{h}</h3><p>{t}</p><a href="{u}"{EXT if ext else ""}>{l} <span class="arrow">←</span></a></div>'
        for s, h, t, u, l, ext in SVC) + '</div>'

FR_FEAT = [
  ('<svg viewBox="0 0 48 48"><circle cx="24" cy="19" r="11"/><path d="M24 13l2 4 4 .5-3 3 .8 4-3.8-2-3.8 2 .8-4-3-3 4-.5z"/><path d="M17 28l-5 13 7-3 4 6 1-10M31 28l5 13-7-3-4 6"/></svg>', 'علامة تجارية موثوقة ومعروفة'),
  ('<svg viewBox="0 0 48 48"><path d="M10 26v-4a14 14 0 0 1 28 0v4"/><rect x="7" y="25" width="7" height="11" rx="3"/><rect x="34" y="25" width="7" height="11" rx="3"/><path d="M38 36c0 5-6 6-11 6"/></svg>', 'دعم فني وتسويقي مستمر'),
  ('<svg viewBox="0 0 48 48"><rect x="18" y="6" width="24" height="18"/><circle cx="11" cy="12" r="4"/><path d="M11 16v14M6 22h10l8-6M8 44V30M14 44V30M24 38v6M34 38v6"/><circle cx="24" cy="34" r="3"/><circle cx="34" cy="34" r="3"/></svg>', 'تدريب كامل للمالك والفريق'),
  ('<svg viewBox="0 0 48 48"><path d="M24 12c-5-4-12-4-17-2v28c5-2 12-2 17 2 5-4 12-4 17-2V10c-5-2-12-2-17 2zM24 12v28"/><path d="M11 17h8M11 22h8M11 27h8M29 17h8M29 22h8M29 27h8"/></svg>', 'دليل تشغيلي معتمد'),
]

# top clients, in the order the client gave them. The logo file is clients/<slug>.(svg|png|jpg|webp);
# a client with no file yet shows its name in the tile instead
CLIENTS = [('nawat', 'نواة للاستثمار العقاري'), ('sasco', 'ساسكو'), ('sar', 'الخطوط الحديدية السعودية (سار)'), ('almarai', 'المراعي'),
           ('watania', 'الدواجن الوطنية'), ('sabic', 'سابك'), ('mewa', 'وزارة البيئة والمياه والزراعة'), ('aramco', 'أرامكو السعودية'),
           ('moh', 'وزارة الصحة'), ('western', 'Western Hotel'), ('goldentulip', 'Golden Tulip'), ('aldrees', 'الدريس')]
CLIENT_DIR = os.path.join(HERE, 'clients')

def client_logo(slug):
    for ext in ('svg', 'png', 'webp', 'jpg'):
        if os.path.exists(os.path.join(CLIENT_DIR, f'{slug}.{ext}')): return f'{slug}.{ext}'

# optical sizing: every logo gets about the same visual area on its tile, so a square mark and a long
# wordmark read as equals. width is a % of the tile, from the logo's aspect ratio (PNG header), capped by the CSS box.
LOGO_WEIGHT = {'watania': .92, 'goldentulip': 1.1}
def logo_width(f, slug):
    if not f.endswith('.png'): return ''
    with open(os.path.join(CLIENT_DIR, f), 'rb') as fh: w, h = struct.unpack('>II', fh.read(24)[16:24])
    px = (4400 * LOGO_WEIGHT.get(slug, 1) * w / h) ** .5  # on a 188px-wide tile
    return f' style="width:{min(80, px / 188 * 100):.1f}%"'

def clients_strip():
    def tiles(dup):
        out = ''
        for slug, name in CLIENTS:
            f = client_logo(slug)
            hid = ' aria-hidden="true"' if dup else ''
            inner = f'<img src="img/clients/{f}" alt="{"" if dup else name}"{logo_width(f, slug)} draggable="false" decoding="async">' if f else f'<span>{name}</span>'
            out += f'<li class="client{"" if f else " txt"}"{hid}>{inner}</li>'
        return out
    return f'''<section class="clients" aria-labelledby="clientsTitle">
  <div class="clients-head"><h2 id="clientsTitle">أبرز عملائنا</h2>
    <button type="button" class="clients-pause" aria-pressed="false" aria-label="إيقاف حركة الشريط"><i aria-hidden="true"></i></button></div>
  <div class="clients-view" tabindex="0" role="group" aria-roledescription="شريط متحرك" aria-label="شعارات أبرز عملائنا. اسحب الشريط أو استخدم الأسهم للتنقل">
    <ul class="clients-track">{tiles(False)}{tiles(True)}{tiles(True)}</ul>
  </div>
</section>'''

# ---------------- pages ----------------
def page_index(full):
    b = head('مصنع الحبيب', 'مصنع الحبيب للزجاج والألمنيوم منذ 2001: أبواب، نوافذ، واجهات، كلادينج، أسقف وقبب زجاجية. صُنع لك ومن أجلك.. وكما تتخيل', full)
    b += '<div class="loader" id="loader" aria-hidden="true"><div style="display:grid;justify-items:center"><img src="img/logo.png" alt=""><i></i></div></div>\n'
    b += header('index.html')
    hero_iso = ''.join(f'<img src="img/{f}" alt="شهادة {c}" width="92" height="92">' for f, c, _ in ISO)
    b += f'''<main id="main">
<div class="hero-track" id="heroTrack">
<section class="hero">
  <div class="hero-img"><img src="img/house-first.jpg" srcset="img/house-first-960.jpg 960w, img/house-first.jpg 1672w" sizes="(max-aspect-ratio: 16/9) 178vh, 100vw" width="1672" height="942" alt="فيلا حديثة بواجهات زجاجية وإطارات ألمنيوم" fetchpriority="high"><video class="hero-vid" muted playsinline preload="none" disablepictureinpicture disableremoteplayback aria-hidden="true" tabindex="-1" data-src="vid/house-scrub.mp4" data-src-m="vid/house-scrub-m.mp4"></video></div>
  <img class="saudi" src="img/saudi.png" alt="صناعة سعودية" width="130" height="56">
  <div class="wrap" style="width:100%">
    <div class="hero-copy">
      <h1 id="heroTitle"><span class="ln"><span>صناعة التغيير والابتكار</span></span><span class="ln"><span>في عالم <em>الزجاج والألمنيوم</em></span></span></h1>
      <p class="hero-sub">مصنع الحبيب للزجاج والألمنيوم منذ 2001. صُنع لك ومن أجلك.. وكما تتخيل، رواد في واجهات المباني والكلادينج والزجاج المتخصص.</p>
      <div class="hero-ctas">
        <a class="btn btn-red" href="products.html">استكشف منتجاتنا <span class="arrow">←</span></a>
        <a class="btn btn-line" href="works.html">شاهد أعمالنا</a>
      </div>
    </div>
    <div class="hero-base">
    <a class="hero-iso" href="#iso">{hero_iso}</a>
    <dl class="hero-strip">
      <div><dt>المقر الرئيسي</dt><dd>المدينة الصناعية الأولى، القصيم</dd></div>
      <div><dt>التخصص</dt><dd>واجهات، كلادينج، زجاج متخصص</dd></div>
      <div><dt>الفروع</dt><dd>الرياض · بريدة · حائل</dd></div>
      <div><dt>المبيعات</dt><dd class="mono">053 086 8800</dd></div>
    </dl>
    </div>
  </div>
</section>
</div>
{clients_strip()}

<section class="sec" id="about">
  <div class="wrap about">
    <div class="about-text">
      <h2 class="title">نصنع <u>الزجاج والألمنيوم</u> اللي يرسم ملامح مبانيك</h2>
      <p class="lead">مصنع الحبيب للزجاج والألمنيوم مصنع سعودي بدأ رحلته عام 2001 من المدينة الصناعية الأولى في القصيم. نصمم ونصنع ونركّب الأبواب والنوافذ والواجهات والكلادينج والأسقف والقبب الزجاجية، ونوفر ألواح الزجاج بالجملة والتجزئة.</p>
      <p class="quote">جودة في التنفيذ، ودقة في التفاصيل، وسرعة في التسليم.</p>
      <div style="margin-top:30px;display:flex;gap:12px;flex-wrap:wrap"><a class="btn btn-dark" href="works.html">شاهد أعمالنا <span class="arrow">←</span></a><a class="btn btn-dark" href="branches.html">مواقع الفروع</a></div>
    </div>
    <div class="about-media">
      <div class="frame clip"><img class="par" src="img/glass.jpg" alt="ألواح زجاج على حوامل داخل المصنع" loading="lazy"></div>
      <div class="badge"><b>2001</b><span>سنة التأسيس</span></div>
    </div>
  </div>
</section>

<section class="sec cream" id="products" style="padding-bottom:clamp(60px,8vw,110px)">
  <div class="wrap head">
    <div><h2 class="title">منتجات تُصنع <u>لتعيش</u></h2></div>
    <div class="scroll-ctl"><button type="button" data-dir="1" aria-label="المنتجات السابقة">→</button><button type="button" data-dir="-1" aria-label="المنتجات التالية">←</button></div>
  </div>
  <div class="pin" id="pin"><div class="track" id="track">{prod_cards()}</div></div>
  <div class="wrap"><a class="btn btn-red" href="products.html">كل المنتجات بالتفاصيل <span class="arrow">←</span></a></div>
</section>

<section class="sig" id="works">
  <div class="wrap sig-head">
    <div><h2>من الخيال إلى الواقع</h2><p class="sig-sub">من أعمالنا المنجزة</p></div>
    <p>خيمة زجاجية بالكامل بتصميم استثنائي. فكرة غير مألوفة، هندسة دقيقة، وتنفيذ يطابق الخيال.</p>
  </div>
  <div class="wrap">
    <div class="cmp" id="cmp">
      <div class="cmp-media clip">
        <img class="cmp-img" src="img/tent-real.jpg" srcset="img/tent-real-960.jpg 960w, img/tent-real.jpg 1672w" sizes="(max-width:700px) 134vw, (max-width:1440px) 100vw, 1440px" width="1672" height="941" alt="بعد التنفيذ: جلسة زجاجية مثمنة بإطارات ألمنيوم داكنة على تراس عند الغروب" loading="lazy" decoding="async" draggable="false">
        <div class="cmp-before"><img class="cmp-img" src="img/tent-plan.jpg" srcset="img/tent-plan-960.jpg 960w, img/tent-plan.jpg 1672w" sizes="(max-width:700px) 134vw, (max-width:1440px) 100vw, 1440px" width="1672" height="941" alt="قبل التنفيذ: المخطط الهندسي للجلسة الزجاجية نفسها" loading="lazy" decoding="async" draggable="false"></div>
        <span class="cmp-tag cmp-tag-b" dir="rtl">قبل التنفيذ</span>
        <span class="cmp-tag cmp-tag-a" dir="rtl">بعد التنفيذ</span>
      </div>
      <div class="cmp-line" aria-hidden="true"></div>
      <div class="cmp-knob" role="slider" tabindex="0" dir="rtl" aria-label="قارن بين المخطط والتنفيذ النهائي" aria-orientation="horizontal" aria-valuemin="0" aria-valuemax="100" aria-valuenow="50" aria-valuetext="المخطط ٥٠٪، التنفيذ ٥٠٪"><span class="cmp-k"><svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true"><path d="M9 6l-6 6 6 6M15 6l6 6-6 6" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg></span></div>
    </div>
    <p class="cmp-hint">اسحب المقبض يمينًا للمخطط، ويسارًا للتنفيذ النهائي</p>
    <div class="sig-foot">
      <div class="promise"><span>جودة في التنفيذ</span><span>دقة في التفاصيل</span><span>سرعة في التسليم</span></div>
      <a class="btn btn-red" href="works.html">كل أعمالنا <span class="arrow">←</span></a>
    </div>
  </div>
</section>

{iso_block().replace('class="sec cream" id="iso"','class="sec" id="iso"')}

<section class="sec">
  <div class="wrap">
    <div class="head"><h2 class="title">معك <u>قبل البيع وبعده</u></h2><a class="btn btn-dark" href="services.html">تفاصيل خدماتنا <span class="arrow">←</span></a></div>
    {svc_list()}
  </div>
</section>

<section class="sec" style="padding-top:0"><div class="wrap"><div class="band">
  <div><h2>امتلك امتياز مصنع الحبيب</h2><p>فرصة تكون جزء من نجاحنا عبر نظام الامتياز التجاري المعتمد، باستثمار من 300 ألف إلى 750 ألف ريال.</p></div>
  <div><a class="btn btn-red" href="franchise.html">تفاصيل الامتياز <span class="arrow">←</span></a></div>
</div></div></section>
</main>
'''
    return b + cta() + footer(full)

def page_products(full):
    b = head('منتجاتنا · مصنع الحبيب', 'منتجات مصنع الحبيب: الأبواب، النوافذ، الواجهات، الكلادينج، الأسقف والقبب الزجاجية، والزجاج المتخصص.', full) + header('products.html')
    rows = ''
    for i, n, img, alt, desc, uses in PRODUCTS:
        msg = f'السلام عليكم، أبي عرض سعر لـ {n}'
        hv = HOVER_VID.get(i)
        media = (f'<img class="par" src="img/{hv[0]}" alt="{alt}" loading="lazy" width="1400" height="1050">'
                 f'<video class="par" muted loop playsinline preload="none" aria-hidden="true" tabindex="-1" data-src="vid/{hv[1]}"></video>') if hv else \
                f'<img class="par" src="img/{img}" alt="{alt}" loading="lazy">'
        rows += f'''<article class="prod" id="{i}"><div class="frame clip">{media}</div>
      <div><h2>{n}</h2><p>{desc}</p><ul class="uses">{''.join(f'<li>{u}</li>' for u in uses)}</ul>
        <div class="row"><a class="btn btn-red" href="https://wa.me/{WA}?text={msg.replace(' ', '%20')}" target="_blank" rel="noopener">اطلب عرض سعر</a><a class="btn btn-dark" href="{BOOK}" target="_blank" rel="noopener">احجز استشارة</a></div></div></article>'''
    b += f'<main id="main">{phero("منتجاتنا", "كل ما يحتاجه مشروعك من الزجاج والألمنيوم، سكني أو تجاري، من مصنع واحد.", "facade.jpg", "برج بواجهة زجاجية", "منتجاتنا")}<section class="sec" style="padding-top:clamp(20px,4vw,50px)"><div class="wrap">{rows}</div></section></main>'
    return b + cta() + footer(full)

def page_works(full):
    b = head('أعمالنا · مصنع الحبيب', 'مشاريع مصنع الحبيب للزجاج والألمنيوم: واجهات، أبواب ونوافذ، أسقف وقبب، خيام زجاجية، وكلادينج.', full) + header('works.html')
    fl = ''.join(f'<button type="button" data-f="{k}" aria-pressed="{"true" if k == "all" else "false"}">{l}</button>' for k, l in FILTERS)
    it = ''.join(f'<figure class="work" data-cat="{c}"><img src="img/{f}" alt="{t}" loading="lazy"><figcaption>{t}<span>{cl}</span></figcaption></figure>' for f, t, cl, c in WORKS)
    b += f'''<main id="main">{phero("أعمالنا", "من الخيال إلى الواقع. مشاريع نفذناها بجودة في التنفيذ ودقة في التفاصيل وسرعة في التسليم.", "tent.jpg", "خيمة زجاجية مضاءة", "أعمالنا")}
<section class="sec"><div class="wrap">
  <div class="filters" role="group" aria-label="تصفية الأعمال">{fl}</div>
  {reels_block()}<div class="works" id="works">{it}</div>
  <div style="margin-top:40px;display:flex;gap:12px;flex-wrap:wrap"><a class="btn btn-red" href="https://x.com/alhabib_fac" target="_blank" rel="noopener">المزيد على إكس</a><a class="btn btn-dark" href="https://www.instagram.com/alhabib_fac/" target="_blank" rel="noopener">إنستقرام</a><a class="btn btn-dark" href="https://www.tiktok.com/@alhabibfac" target="_blank" rel="noopener">تيك توك</a></div>
</div></section></main>{PLAYER if VIDEOS else ""}'''
    return b + cta() + footer(full)

def page_services(full):
    b = head('خدماتنا · مصنع الحبيب', 'خدمات مصنع الحبيب: ما قبل البيع، الصيانة وخدمة العملاء، حجز استشارة، وصوتك مسموع.', full) + header('services.html')
    b += f'''<main id="main">{phero("خدماتنا", "من أول استشارة إلى آخر صيانة، قنواتنا مفتوحة لك طول رحلتك مع المشروع.", "skylight.jpg", "سقف زجاجي فوق صالة", "خدماتنا")}
<section class="sec"><div class="wrap"><h2 class="sr">قائمة الخدمات</h2>{svc_list()}</div></section>
<section class="sec cream"><div class="wrap">
  <h2 class="title">كيف نشتغل <u>على مشروعك</u></h2>
  <div class="proc" style="margin-top:40px">
    <div><i>1</i><b>استشارة</b><p>نسمع فكرتك ونحدد احتياجك والميزانية.</p></div>
    <div><i>2</i><b>قياس وتصميم</b><p>نزور الموقع، نقيس، ونجهز التصميم وعرض السعر.</p></div>
    <div><i>3</i><b>تصنيع</b><p>نصنع في مصنعنا بالمدينة الصناعية الأولى في القصيم.</p></div>
    <div><i>4</i><b>تركيب وصيانة</b><p>نركّب ونسلّم، ونبقى معك بخدمة الصيانة بعدها.</p></div>
  </div>
</div></section>{iso_block()}</main>'''
    return b + cta() + footer(full)

def page_branches(full):
    b = head('مواقع الفروع · مصنع الحبيب', 'فروع مصنع الحبيب في القصيم والرياض وبريدة وحائل مع أرقام التواصل.', full) + header('branches.html')
    b += f'''<main id="main">{phero("مواقع الفروع", "من مصنعنا في القصيم إلى معارضنا في الرياض وبريدة وحائل. اضغط اسم الفرع لتفتح موقعه في خرائط قوقل، أو الرقم لنسخه.", "hero.jpg", "فيلا بواجهات زجاجية", "مواقع الفروع")}
<section class="sec"><div class="wrap"><h2 class="sr">الفروع وأرقامها</h2>{branches_block()}</div></section></main>'''
    return b + cta() + footer(full)

def page_franchise(full):
    b = head('الامتياز التجاري · مصنع الحبيب', 'امتلك امتياز مصنع الحبيب للزجاج والألمنيوم: الاستثمار، المميزات، خطوات التقديم ونموذج الطلب.', full) + header('franchise.html')
    feat = ''.join(f'<div>{s}<b>{t}</b></div>' for s, t in FR_FEAT)
    b += f'''<main id="main">{phero("امتلك امتياز مصنع الحبيب للزجاج والألمنيوم", "هل ترغب في دخول عالم الأعمال بثقة؟ نقدّم لك فرصة مميزة لتكون جزءًا من نجاحنا عبر نظام الامتياز التجاري المعتمد لمصنع الحبيب للزجاج والألمنيوم، الرائد في تقديم واجهات المباني، الكلادينج، والزجاج المتخصص.", "cladding.jpg", "مبنى بواجهة كلادينج وزجاج", "الامتياز التجاري")}
<section class="sec"><div class="wrap">
  <div class="fr-hero">
    <div><h2 class="title">تفاصيل <u>الاستثمار</u></h2>
      <dl class="figs">
        <div class="wide"><dt>حجم الاستثمار</dt><dd><span class="mono">300,000 – 750,000</span> ر.س</dd></div>
        <div><dt>نوع الامتياز</dt><dd>متعدد الوحدات</dd></div>
        <div><dt>مدة العقد</dt><dd><span class="mono">5</span> سنوات</dd></div>
        <div><dt>الرسوم الإدارية المستمرة</dt><dd class="mono">7%</dd></div>
        <div><dt>المتطلبات</dt><dd style="font-size:1rem">سجل تجاري ساري وملاءة مالية</dd></div>
      </dl></div>
    <div class="frame clip" style="aspect-ratio:4/3"><img class="par" src="img/facade.jpg" alt="برج بواجهة زجاجية" loading="lazy"></div>
  </div>
</div></section>
<section class="sec cream"><div class="wrap">
  <h2 class="title">مميزات <u>الامتياز التجاري</u></h2>
  <div class="feat">{feat}</div>
  <h2 class="title" style="margin-top:clamp(60px,7vw,100px)">خطوات <u>التقديم</u></h2>
  <div class="steps" style="margin-top:30px">
    <div class="step"><i>1</i><b>تعبئة نموذج الطلب</b></div>
    <div class="step"><i>2</i><b>التواصل مع إدارة الامتياز</b></div>
    <div class="step"><i>3</i><b>مراجعة المتطلبات والموافقة</b></div>
    <div class="step"><i>4</i><b>توقيع العقد والانطلاق</b></div>
  </div>
</div></section>
<section class="sec" id="apply"><div class="wrap" style="max-width:980px">
  <h2 class="title">نموذج <u>الطلب</u></h2>
  <form class="form panel wa-form" style="margin-top:36px" data-subject="طلب امتياز تجاري" novalidate>
    <label>الاسم الكامل<input id="fr-name" name="الاسم" required autocomplete="name"><span class="err"></span></label>
    <label>المدينة<input id="fr-city" name="المدينة" required><span class="err"></span></label>
    <label>رقم الجوال<input id="fr-phone" name="الجوال" type="tel" inputmode="tel" required pattern="^(05|\\+9665|9665)[0-9]{{8}}$" placeholder="05xxxxxxxx" autocomplete="tel"><span class="err"></span></label>
    <label>البريد الإلكتروني<input id="fr-email" name="البريد" type="email" autocomplete="email"><span class="err"></span></label>
    <label class="full">رأس المال المتوقع<select id="fr-cap" name="رأس المال"><option>300,000 – 500,000 ر.س</option><option>500,000 – 750,000 ر.س</option><option>أكثر من 750,000 ر.س</option></select></label>
    <label class="full">ملاحظات<textarea id="fr-msg" name="ملاحظات"></textarea></label>
    <div class="full"><button class="btn btn-red" type="submit">جهّز الطلب</button></div>
  </form>
</div></section></main>'''
    return b + footer(full)

def page_contact(full):
    b = head('اتصل بنا · مصنع الحبيب', 'تواصل مع مصنع الحبيب للزجاج والألمنيوم: المبيعات 053 086 8800، واتساب، والبريد info@alhabibsa.com.', full) + header('contact.html')
    b += f'''<main id="main">{phero("اتصل بنا", "خبّرنا وش في بالك، والباقي علينا.", "door.jpg", "باب محوري بمدخل مضاء", "اتصل بنا")}
<section class="sec"><div class="wrap contact-grid">
  <dl class="cinfo">
    <div><dt>المبيعات</dt><dd class="mono">053 086 8800</dd><div style="margin-top:10px">{chip('0530868800','انسخ الرقم')}</div></div>
    <div><dt>البريد الإلكتروني</dt><dd class="mono" style="font-size:1.1rem">info@alhabibsa.com</dd><div style="margin-top:10px">{chip('info@alhabibsa.com','انسخ البريد')}</div></div>
    <div><dt>المقر الرئيسي والمصنع</dt><dd>المدينة الصناعية الأولى، القصيم</dd><div style="margin-top:10px"><a class="chip" href="branches.html">كل الفروع ←</a></div></div>
    <div><dt>الحجز والخدمات</dt><dd>استشارة، صيانة، ملاحظات</dd><div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap"><a class="chip" href="{BOOK}" target="_blank" rel="noopener">احجز استشارة</a><a class="chip" href="{FIX}" target="_blank" rel="noopener">طلب صيانة</a></div></div>
  </dl>
  <form class="form panel wa-form" data-subject="استفسار من الموقع" novalidate>
    <h2 class="full" style="font-size:1.8rem">أرسل لنا رسالتك</h2>
    <label>الاسم<input id="c-name" name="الاسم" required autocomplete="name"><span class="err"></span></label>
    <label>رقم الجوال<input id="c-phone" name="الجوال" type="tel" inputmode="tel" required pattern="^(05|\\+9665|9665)[0-9]{{8}}$" placeholder="05xxxxxxxx" autocomplete="tel"><span class="err"></span></label>
    <label class="full">المنتج<select id="c-prod" name="المنتج">{''.join(f'<option>{n}</option>' for _, n, *_ in PRODUCTS)}<option>أخرى</option></select></label>
    <label class="full">رسالتك<textarea id="c-msg" name="الرسالة" required></textarea><span class="err"></span></label>
    <div class="full"><button class="btn btn-red" type="submit">جهّز الرسالة</button></div>
  </form>
</div></section></main>'''
    return b + footer(full)

PAGES = {'index.html': page_index, 'products.html': page_products, 'works.html': page_works, 'services.html': page_services,
         'branches.html': page_branches, 'franchise.html': page_franchise, 'contact.html': page_contact}

# artifact build: index is body-only (the host wraps it); every other page is a full document
ART = os.path.join(OUT, 'artifact'); STAND = os.path.join(OUT, 'standalone')
for d in (ART, STAND):
    os.makedirs(d, exist_ok=True)
    for f in ('site.css',): shutil.copy(os.path.join(OUT, f), d)
    shutil.copy(os.path.join(HERE, 'site.js'), d)
    vd = os.path.join(d, 'vid'); shutil.rmtree(vd, ignore_errors=True); os.makedirs(vd)
    cd = os.path.join(d, 'img', 'clients'); shutil.rmtree(cd, ignore_errors=True); os.makedirs(cd)
    for slug, _ in CLIENTS:
        if client_logo(slug): shutil.copy(os.path.join(CLIENT_DIR, client_logo(slug)), cd)
    for _, clip in HOVER_VID.values():
        shutil.copy(os.path.join(HERE, 'vid', clip), vd)
    for clip in HERO_VID:
        shutil.copy(os.path.join(HERE, 'vid', clip), vd)
    if VIDEOS:
        for v in VIDEOS:
            for suf in ('.mp4', '-loop.mp4', '.jpg'):
                src = os.path.join(v.get('dir', os.path.join(HERE, 'vid')), v['slug'] + suf)
                assert os.path.getsize(src) <= 15e6, src + ' is over the 15 MB per-file limit'
                shutil.copy(src, vd)
for name, fn in PAGES.items():
    open(os.path.join(ART, name), 'w').write(fn(name != 'index.html'))
    open(os.path.join(STAND, name), 'w').write(fn(True))
print('built', list(PAGES))
