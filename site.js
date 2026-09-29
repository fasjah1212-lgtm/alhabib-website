(function(){
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var G = typeof gsap !== 'undefined' && typeof ScrollTrigger !== 'undefined';
  if (G) gsap.registerPlugin(ScrollTrigger);
  // html has scroll-behavior:smooth; flush it to auto before ScrollTrigger measures, or Chromium's scrollTo(0)
  // during a refresh never lands and every trigger below ends up offset by the current scroll
  if (G){
    var sbWas = null;
    ScrollTrigger.addEventListener('refreshInit', function(){ var d = document.documentElement; if (sbWas === null) sbWas = d.style.scrollBehavior; d.style.scrollBehavior = 'auto'; d.offsetHeight; });
    ScrollTrigger.addEventListener('refresh', function(){ if (sbWas !== null){ document.documentElement.style.scrollBehavior = sbWas; sbWas = null; } });
  }
  var heroEnd = 0; // where the home hero lets go of the page (set by the hero clip block)

  var loader = document.getElementById('loader'), started = false;
  function go(){ if (started) return; started = true; if (loader) loader.classList.add('done'); intro(); }
  if (loader){ addEventListener('load', function(){ setTimeout(go, 300); }); setTimeout(go, 3000); } else go();
  function intro(){
    if (!G || reduce) return;
    if (document.querySelector('#heroTitle .ln>span')) gsap.from('#heroTitle .ln>span', {yPercent:110, duration:1.4, ease:'expo.out', stagger:.12});
    if (document.querySelector('.hero-sub')) gsap.from('.hero-sub, .hero-ctas', {y:30, opacity:0, duration:1.2, ease:'expo.out', stagger:.1, delay:.3});
    if (document.querySelector('.hero-base')) gsap.from('.hero-base', {yPercent:100, duration:1.4, ease:'expo.out', delay:.5});
    else if (document.querySelector('.hero-strip')) gsap.from('.hero-strip', {yPercent:100, duration:1.4, ease:'expo.out', delay:.5});
    if (document.querySelector('.hero-iso img')) gsap.from('.hero-iso img', {scale:.6, opacity:0, duration:.9, ease:'back.out(1.7)', stagger:.12, delay:1.1, clearProps:'transform,opacity'});
    if (document.querySelector('.saudi')) gsap.from('.saudi', {scale:.8, opacity:0, duration:1, ease:'back.out(1.6)', delay:.8});
    if (document.querySelector('.phero h1')) gsap.from('.phero h1, .phero .lead, .phero .crumbs', {y:30, opacity:0, duration:1.1, ease:'expo.out', stagger:.08});
  }

  var nav = document.getElementById('nav');
  // the top bar always floats (same shape at the top of the page and while scrolling)
  function ns(){}
  var drawer = document.getElementById('drawer'), mb = document.getElementById('menuBtn');
  if (drawer && mb){
    mb.addEventListener('click', function(){ drawer.hidden = false; mb.setAttribute('aria-expanded','true'); });
    document.getElementById('menuClose').addEventListener('click', function(){ drawer.hidden = true; mb.setAttribute('aria-expanded','false'); });
    addEventListener('keydown', function(e){ if (e.key === 'Escape' && !drawer.hidden){ drawer.hidden = true; mb.setAttribute('aria-expanded','false'); mb.focus(); } });
  }

  document.querySelectorAll('.copy').forEach(function(b){
    b.addEventListener('click', function(){
      var v = b.getAttribute('data-copy'), old = b.innerHTML;
      function ok(){ b.classList.add('ok'); b.textContent = 'تم النسخ ✓'; setTimeout(function(){ b.classList.remove('ok'); b.innerHTML = old; }, 1600); }
      function fb(){ var t=document.createElement('textarea'); t.value=v; document.body.appendChild(t); t.select(); try{ document.execCommand('copy'); ok(); }catch(e){} t.remove(); }
      try { navigator.clipboard.writeText(v).then(ok, fb); } catch(e){ fb(); }
    });
  });

  // home hero: the house moves through the day only as the page scrolls. The hero sticks while the
  // page scrolls through an extra stretch, and that stretch drives the clip's time (eased, so wheel
  // steps glide). Until the clip arrives the still photo eases in with the same scroll, so the stretch is
  // never frozen. Reduced motion, Save-Data, no JS, or a clip that cannot play here keep the still photo
  // and a normal-length page.
  var heroScrub = false;
  (function(){
    var track = document.getElementById('heroTrack'), hero = track && track.querySelector('.hero'), v = hero && hero.querySelector('.hero-vid');
    if (!v || reduce) return;
    var cn = navigator.connection;
    if (cn && (cn.saveData || /(^|-)2g$/.test(cn.effectiveType || ''))) return;
    heroScrub = true;
    track.classList.add('scrub');
    var root = document.documentElement, base = hero.querySelector('.hero-base'), still = hero.querySelector('.hero-img img');
    // a 100svh probe: the small viewport does not change when mobile toolbars slide, so nothing jumps
    var probe = document.createElement('div');
    probe.style.cssText = 'position:absolute;top:0;left:0;width:0;height:100vh;height:100svh;visibility:hidden;pointer-events:none';
    track.appendChild(probe);
    var dur = 10, vh = 0, h = 0, T = 0, top = 0, extra = 1, start = 0, p = 0, target = 0, cur = 0, raf = 0, last = 0,
        ready = false, shown = false, dead = false, quit = false, asked = false, seen = '', url = '', blobs = {};
    function measure(){
      if (dead) return;
      vh = probe.offsetHeight || innerHeight; h = hero.offsetHeight; top = Math.min(0, vh - h);
      // a hero taller than the screen sticks with its info strip on screen, unless the strip would leave
      // too little of the house (landscape phones, deep zoom): then it sticks at the top and the strip follows
      if (top < 0 && vh - (nav ? nav.offsetHeight : 0) - (base ? base.offsetHeight : 0) < vh * 0.45) top = 0;
      extra = Math.round(vh * (innerWidth < innerHeight ? 1.3 : 1.6));
      hero.style.top = top + 'px';
      track.style.height = (h + extra) + 'px';
      T = track.getBoundingClientRect().top + scrollY;
      start = T - top; // scroll position where the hero starts to stick
      heroEnd = start + extra;
      var key = [innerWidth, vh, h, top, extra].join('x');
      if (key !== seen){ seen = key; if (G) ScrollTrigger.refresh(); }
      if (asked) pick();
      onScroll(); ns();
    }
    function onScroll(){
      if (dead) return;
      var y = scrollY;
      if (quit && y <= start) return off();
      p = (y - start) / extra; p = p < 0 ? 0 : p > 1 ? 1 : p;
      target = p * (dur - 0.05);
      if (!shown && still) still.style.transform = 'scale(' + (1 + p * 0.07).toFixed(4) + ')';
      if (ready && !raf){ last = 0; raf = requestAnimationFrame(tick); }
    }
    function tick(now){
      raf = 0;
      var dt = last ? Math.min(64, now - last) : 16.7; last = now;
      var d = target - cur;
      cur = Math.abs(d) < 0.004 ? target : cur + d * (1 - Math.pow(0.82, dt / 16.7));
      if (!v.seeking && Math.abs(v.currentTime - cur) > 0.004) v.currentTime = cur;
      if (cur !== target || v.seeking) raf = requestAnimationFrame(tick);
    }
    // the clip cannot play here: back to the still photo and a normal-length page. Done while the visitor is
    // above the hero's hold (or before the page is scrolled) so the page does not jump under them.
    function off(){
      if (dead) return;
      var y = scrollY;
      if (y > start){ quit = true; return; }
      dead = true; heroScrub = false; heroEnd = 0;
      track.style.height = ''; hero.style.top = ''; v.classList.remove('on');
      if (still) still.style.transform = '';
      removeEventListener('scroll', onScroll); removeEventListener('resize', measure);
      if (G) ScrollTrigger.refresh();
      ns();
    }
    function prime(){ var pr; try { pr = v.play(); } catch(e){} if (pr && pr.then) pr.then(function(){ v.pause(); }, function(){}); }
    // iOS Low Power Mode refuses muted play() without a gesture and then loads nothing: retry on each tap until the clip is in
    function retry(){
      if (ready || dead){ removeEventListener('touchend', retry); removeEventListener('click', retry); return; }
      if (v.getAttribute('src')) prime();
    }
    addEventListener('touchend', retry, {passive:true}); addEventListener('click', retry);
    v.addEventListener('loadeddata', function(){
      if (ready || dead) return;
      dur = v.duration && isFinite(v.duration) ? v.duration : 10;
      ready = true; v.pause(); cur = target; v.currentTime = cur; onScroll();
    });
    v.addEventListener('seeked', function(){
      if (!ready || shown) return;
      shown = true; v.classList.add('on');
      if (still) setTimeout(function(){ still.style.transform = ''; }, 700); // under the clip by then
    });
    v.addEventListener('error', function(){
      if ((v.getAttribute('src') || '').indexOf('blob:') === 0) return use(url); // a page that refuses blob: media streams the file instead
      if (v.getAttribute('src')) off();
    });
    function use(src){ ready = false; shown = false; v.classList.remove('on'); v.preload = 'auto'; v.src = src; v.load(); prime(); }
    // portrait phones get a centre crop; the choice follows rotation
    function pick(){
      var want = v.getAttribute(innerWidth / innerHeight < 0.76 ? 'data-src-m' : 'data-src');
      if (want === url) return;
      url = want;
      if (blobs[url]) return use(blobs[url]);
      // the clip is small, so fetch it once and seek from memory: no range requests while scrubbing
      if (window.fetch && location.protocol !== 'file:'){
        var u = url;
        fetch(u).then(function(r){ if (!r.ok) throw r.status; return r.blob(); })
          .then(function(b){ blobs[u] = URL.createObjectURL(b); if (u === url) use(blobs[u]); }, function(){ if (u === url) use(u); });
      } else use(url);
    }
    // start loading once the still photo is in (it is the first paint), not after every image on the page;
    // a clip that has not arrived 25 s later is given up
    function begin(){
      if (asked || dead) return; asked = true; pick();
      setTimeout(function(){ if (!ready) off(); }, 25000);
    }
    measure();
    addEventListener('scroll', onScroll, {passive:true});
    addEventListener('resize', measure);
    if (window.ResizeObserver) new ResizeObserver(function(){ measure(); }).observe(hero);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(measure);
    if (still && !still.complete) still.addEventListener('load', begin, {once:true}); else begin();
    addEventListener('load', function(){ measure(); begin(); });
  })();

  // compare: the plan (left) over the finished work (right). Dragging the line only moves the clip edge;
  // the two images never move or scale, so their structure stays matched while comparing.
  (function(){
    var box = document.getElementById('cmp'); if (!box) return;
    var before = box.querySelector('.cmp-before'), line = box.querySelector('.cmp-line'), knob = box.querySelector('.cmp-knob');
    var tagB = box.querySelector('.cmp-tag-b'), tagA = box.querySelector('.cmp-tag-a');
    var cur = 50, target = 50, tau = 0, raf = 0, last = 0, said = -1, touched = false, drag = null, W = 0, L = 0;
    var AR = ['٠','١','٢','٣','٤','٥','٦','٧','٨','٩'];
    function ar(n){ return String(n).replace(/\d/g, function(d){ return AR[d]; }); }
    function measure(){ var r = box.getBoundingClientRect(); W = r.width; L = r.left; }
    function paint(){
      var px = cur / 100 * W, k = knob.offsetWidth / 2 + 4;
      var cp = 'inset(0 ' + (100 - cur).toFixed(3) + '% 0 0)';
      before.style.webkitClipPath = cp; before.style.clipPath = cp;
      line.style.transform = 'translate3d(' + px.toFixed(2) + 'px,0,0)';
      knob.style.transform = 'translate3d(' + Math.min(W - k, Math.max(k, px)).toFixed(2) + 'px,0,0)';
      tagB.style.opacity = Math.min(1, Math.max(0, (cur - 6) / 14));
      tagA.style.opacity = Math.min(1, Math.max(0, (94 - cur) / 14));
      var v = Math.round(cur);
      if (v !== said){ said = v; knob.setAttribute('aria-valuenow', v); knob.setAttribute('aria-valuetext', 'المخطط ' + ar(v) + '٪، التنفيذ ' + ar(100 - v) + '٪'); }
    }
    function frame(t){
      var dt = last ? Math.min(64, t - last) : 16.7; last = t;
      cur = tau > 0 ? cur + (target - cur) * (1 - Math.exp(-dt / tau)) : target;
      if (Math.abs(target - cur) < 0.02) cur = target;
      paint();
      raf = cur === target ? 0 : requestAnimationFrame(frame);
      if (!raf) last = 0;
    }
    // follow: tight while a finger or mouse drags (feels attached), softer for taps, keys and the hint
    function go(x, soft){ target = Math.min(100, Math.max(0, x)); tau = reduce ? 0 : soft || 20; if (!raf) raf = requestAnimationFrame(frame); }
    function pct(clientX){ return (clientX - L) / W * 100; }
    function lineX(){ return L + cur / 100 * W; }
    function grab(e, off){ drag.on = true; drag.off = off; touched = true; try { box.setPointerCapture(e.pointerId); } catch(_){} box.classList.add('dragging'); }
    box.addEventListener('pointerdown', function(e){
      if (e.button > 0 || drag) return;
      measure();
      var near = knob.contains(e.target) || Math.abs(e.clientX - lineX()) < 28;
      drag = {id: e.pointerId, sx: e.clientX, sy: e.clientY, t: e.timeStamp, on: false, off: 0};
      // mouse: press anywhere to take the line there; touch: only the handle grabs at once, so a vertical swipe still scrolls the page
      if (near) grab(e, e.clientX - lineX());
      else if (e.pointerType === 'mouse'){ grab(e, 0); go(pct(e.clientX), 70); }
      if (e.pointerType === 'mouse') e.preventDefault();
    });
    box.addEventListener('pointermove', function(e){
      if (!drag || e.pointerId !== drag.id) return;
      if (!drag.on){
        var dx = e.clientX - drag.sx, dy = e.clientY - drag.sy;
        if (Math.abs(dx) < 7 || Math.abs(dx) < Math.abs(dy)) return;
        grab(e, 0);
      }
      go(pct(e.clientX - drag.off));
    });
    function end(e){
      if (!drag || e.pointerId !== drag.id) return;
      var d = drag; drag = null; box.classList.remove('dragging');
      // a quick tap away from the handle glides the line to the tap
      if (!d.on && e.type === 'pointerup' && e.timeStamp - d.t < 600 && Math.abs(e.clientX - d.sx) < 7 && Math.abs(e.clientY - d.sy) < 7){ touched = true; go(pct(e.clientX), 90); }
    }
    box.addEventListener('pointerup', end);
    box.addEventListener('pointercancel', end);
    box.addEventListener('dragstart', function(e){ e.preventDefault(); });
    knob.addEventListener('keydown', function(e){
      var k = e.key, x = null;
      if (k === 'ArrowRight' || k === 'ArrowUp') x = target + 5;
      else if (k === 'ArrowLeft' || k === 'ArrowDown') x = target - 5;
      else if (k === 'PageUp') x = target + 20;
      else if (k === 'PageDown') x = target - 20;
      else if (k === 'Home') x = 0;
      else if (k === 'End') x = 100;
      if (x === null) return;
      e.preventDefault(); touched = true; measure(); go(Math.round(x), 90);
    });
    function resize(){ measure(); paint(); }
    if ('ResizeObserver' in window) new ResizeObserver(resize).observe(box); else addEventListener('resize', resize);
    resize();
    // one gentle sway the first time it comes into view, ending back in the middle, to show it can be dragged
    if (!reduce && 'IntersectionObserver' in window){
      var io = new IntersectionObserver(function(es){
        if (!es[0].isIntersecting) return; io.disconnect();
        var steps = [[62, 0], [40, 650], [50, 1300]];
        steps.forEach(function(s){ setTimeout(function(){ if (!touched && !drag){ measure(); go(s[0], 200); } }, 700 + s[1]); });
      }, {threshold: .6});
      io.observe(box);
    }
  })();

  // products strip: native scroll; a mouse can grab it and throw it sideways (touch already swipes)
  var pin = document.getElementById('pin'), prog = document.getElementById('prog');
  if (pin){
    var dx0 = 0, sl0 = 0, down = false, moved = false, vx = 0, lx = 0, lt = 0, glide = 0;
    pin.addEventListener('pointerdown', function(e){
      if (e.pointerType !== 'mouse' || e.button !== 0) return;
      cancelAnimationFrame(glide); down = true; moved = false; dx0 = lx = e.clientX; sl0 = pin.scrollLeft; vx = 0; lt = performance.now();
    });
    addEventListener('pointermove', function(e){
      if (!down) return;
      var d = e.clientX - dx0;
      if (!moved && Math.abs(d) > 5){ moved = true; pin.classList.add('drag'); }
      if (!moved) return;
      e.preventDefault();
      var now = performance.now(); vx = (e.clientX - lx) / Math.max(1, now - lt); lx = e.clientX; lt = now;
      pin.scrollLeft = sl0 - d;
    });
    addEventListener('pointerup', function(){
      if (!down) return; down = false;
      if (!moved) return;
      var v = vx * 16;
      function step(){
        v *= .94; pin.scrollLeft -= v;
        if (Math.abs(v) > .4 && !reduce) glide = requestAnimationFrame(step);
        else pin.classList.remove('drag');
      }
      if (reduce) pin.classList.remove('drag'); else glide = requestAnimationFrame(step);
    });
    // a drag must not also open the card it started on
    pin.addEventListener('click', function(e){ if (moved){ e.preventDefault(); e.stopPropagation(); moved = false; } }, true);
    pin.addEventListener('dragstart', function(e){ e.preventDefault(); });
    if (prog) pin.addEventListener('scroll', function(){ var m = pin.scrollWidth - pin.clientWidth; prog.style.transform = 'scaleX(' + (.08 + (m > 0 ? Math.abs(pin.scrollLeft)/m : 0)*.92) + ')'; }, {passive:true});
  }

  // works filter
  var fbtns = document.querySelectorAll('.filters [data-f]');
  fbtns.forEach(function(b){
    b.addEventListener('click', function(){
      var f = b.getAttribute('data-f');
      fbtns.forEach(function(x){ x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
      document.querySelectorAll('.work, .reel').forEach(function(w){ w.hidden = !(f === 'all' || w.getAttribute('data-cat') === f); });
      var rl = document.getElementById('reels'), rh = document.querySelector('.reels-head');
      if (rl){ var any = [].some.call(rl.querySelectorAll('.reel'), function(r){ return !r.hidden; }); rl.hidden = !any; if (rh) rh.hidden = !any; }
      if (G) ScrollTrigger.refresh();
    });
  });

  // forms: validate, then prepare a WhatsApp message to the factory
  var WA = '966530868800';
  document.querySelectorAll('.wa-form').forEach(function(form){
    form.addEventListener('submit', function(e){
      e.preventDefault();
      var bad = null, lines = [form.getAttribute('data-subject') || 'رسالة من الموقع'];
      form.querySelectorAll('input, textarea, select').forEach(function(el){
        var err = el.parentNode.querySelector('.err'), msg = '';
        var v = (el.value || '').trim().replace(/\s+/g, '');
        if (el.required && !el.value.trim()) msg = 'هذا الحقل مطلوب';
        else if (el.type === 'tel' && el.value.trim() && !/^(05|\+9665|9665)[0-9]{8}$/.test(v)) msg = 'اكتب رقم جوال سعودي صحيح مثل 05xxxxxxxx';
        else if (el.type === 'email' && el.value.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(el.value.trim())) msg = 'اكتب بريدًا إلكترونيًا صحيحًا';
        if (err) err.textContent = msg;
        el.setAttribute('aria-invalid', msg ? 'true' : 'false');
        if (msg && !bad) bad = el;
        if (!msg && el.value.trim()) lines.push((el.name || '') + ': ' + el.value.trim());
      });
      if (bad){ bad.focus(); return; }
      var href = 'https://wa.me/' + WA + '?text=' + encodeURIComponent(lines.join('\n'));
      var done = form.querySelector('.form-done');
      if (!done){ done = document.createElement('div'); done.className = 'form-done'; done.setAttribute('role', 'status'); form.appendChild(done); }
      done.innerHTML = '<p><b>رسالتك جاهزة.</b> اضغط الزر لإرسالها لنا على واتساب.</p><a class="btn btn-red" target="_blank" rel="noopener">أرسل عبر واتساب</a>';
      done.querySelector('a').href = href;
      done.querySelector('a').focus();
    });
  });

  // product clips (home cards and the products page): play while the pointer (or keyboard focus) is on the
  // product, pause when it leaves. Touch screens have no hover, so there the clip plays while it is on screen.
  var hoverable = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  document.querySelectorAll('.card .ph video[data-src], .prod .frame video[data-src]').forEach(function(v){
    if (reduce) return;
    var box = v.closest('.card, .prod');
    // a home card reacts anywhere on the card; a products page row reacts on its photo only
    var zone = box.classList.contains('card') ? box : v.parentNode;
    function play(){ if (!v.getAttribute('src')) v.src = v.getAttribute('data-src'); var p = v.play(); if (p && p.catch) p.catch(function(){}); }
    v.addEventListener('playing', function(){ v.classList.add('on'); });
    if (hoverable){
      zone.addEventListener('pointerenter', play);
      zone.addEventListener('pointerleave', function(){ v.pause(); });
      // a products page row only plays from keyboard focus: a mouse click on its buttons focuses them too,
      // and the pointer is not on the photo then, so nothing would pause it
      box.addEventListener('focusin', function(e){ var kb = true; try { kb = e.target.matches(':focus-visible'); } catch(err){} if (box === zone || kb) play(); });
      box.addEventListener('focusout', function(e){ if (!box.contains(e.relatedTarget)) v.pause(); });
    } else if ('IntersectionObserver' in window){
      new IntersectionObserver(function(es){ es.forEach(function(e){ if (e.isIntersecting && e.intersectionRatio > .6) play(); else v.pause(); }); }, {threshold:[0, .6, 1]}).observe(v.parentNode);
    }
  });

  // top clients strip: drifts on its own; holding it with a finger or the mouse, hovering or keyboard focus stop it,
  // and it can be dragged or moved with the arrow keys. With reduced motion it starts still.
  (function(){
    var view = document.querySelector('.clients-view'); if (!view) return;
    var track = view.querySelector('.clients-track');
    var items = track.children, half = track.querySelectorAll('.client:not([aria-hidden])').length;
    var W = 0, x = 0, speed = 34, last = 0, hover = false, focus = false, seen = true, drag = null, resumeAt = 0, nudge = 0;
    var paused = reduce;
    function measure(){ W = Math.abs(items[0].offsetLeft - items[half].offsetLeft); }
    function paint(){ if (W) x = ((x % W) + W) % W; track.style.transform = 'translate3d(' + x.toFixed(2) + 'px,0,0)'; }
    function tick(t){
      var dt = last ? Math.min(t - last, 64) / 1000 : 0; last = t;
      if (nudge){ var step = nudge * Math.min(1, dt * 9); if (Math.abs(nudge - step) < .5) step = nudge; nudge -= step; x += step; paint(); }
      else if (!paused && !hover && !focus && !drag && seen && t > resumeAt){ x += speed * dt; paint(); }
      requestAnimationFrame(tick);
    }
    measure(); paint();
    window.addEventListener('resize', function(){ var r = W ? x / W : 0; measure(); x = r * W; paint(); });
    if ('IntersectionObserver' in window) new IntersectionObserver(function(es){ seen = es[0].isIntersecting; }).observe(view);
    view.addEventListener('pointerenter', function(e){ if (e.pointerType === 'mouse') hover = true; });
    view.addEventListener('pointerleave', function(e){ if (e.pointerType === 'mouse') hover = false; });
    // only keyboard focus holds it still: a mouse press on the strip focuses it too, and it should keep drifting after a drag
    view.addEventListener('focus', function(){ var kb = true; try { kb = view.matches(':focus-visible'); } catch(err){} focus = kb; });
    view.addEventListener('blur', function(){ focus = false; });
    view.addEventListener('pointerdown', function(e){
      if (e.button !== 0) return;
      drag = {x0: e.clientX, start: x, id: e.pointerId}; nudge = 0;
      try { view.setPointerCapture(e.pointerId); } catch(err){}
    });
    view.addEventListener('pointermove', function(e){
      if (!drag || e.pointerId !== drag.id) return;
      var dx = e.clientX - drag.x0;
      if (!drag.on && Math.abs(dx) > 4){ drag.on = true; view.classList.add('drag'); }
      if (drag.on){ x = drag.start + dx; paint(); }
    });
    function end(e){ if (!drag || (e && e.pointerId !== drag.id)) return; drag = null; view.classList.remove('drag'); resumeAt = performance.now() + 1500; }
    view.addEventListener('pointerup', end); view.addEventListener('pointercancel', end);
    view.addEventListener('keydown', function(e){
      var tile = items[0].offsetWidth + (parseFloat(getComputedStyle(track).columnGap) || 0);
      // RTL: the left arrow brings in the next logos (they come from the left), the right arrow goes back
      if (e.key === 'ArrowLeft'){ e.preventDefault(); nudge += tile; }
      else if (e.key === 'ArrowRight'){ e.preventDefault(); nudge -= tile; }
    });
    requestAnimationFrame(tick);
  })();

  // project reels: muted loops play only while on screen; a tap opens the full clip with sound
  var reels = [].slice.call(document.querySelectorAll('.reel'));
  var player = document.getElementById('player');
  if (reels.length && player){
    var pv = player.querySelector('video'), frame = player.querySelector('.frame-v'),
        pt = player.querySelector('figcaption b'), ps = player.querySelector('figcaption span'),
        pb = player.querySelector('[data-step="-1"]'), nb = player.querySelector('[data-step="1"]'),
        xb = player.querySelector('[data-close]'), mt = document.getElementById('reelsMotion'),
        cur = -1, from = null, busy = false, closing = false, pending = false, anim = null, refocusScroll = false, io = null;
    var still = reduce;
    try { var saved = localStorage.getItem('alhabib-reels-motion'); if (saved) still = saved === 'off'; } catch(e){}
    function loopOf(r){ return r.querySelector('video'); }
    function startLoop(v){ if (!v.getAttribute('src')) v.src = v.getAttribute('data-loop'); var p = v.play(); if (p && p.catch) p.catch(function(){}); }
    function stopAll(){ reels.forEach(function(r){ loopOf(r).pause(); }); }
    // re-observing makes the observer report each reel's current visibility again
    function resync(){ if (!io || still || player.open || document.hidden) return; reels.forEach(function(r){ io.unobserve(r); io.observe(r); }); }
    if ('IntersectionObserver' in window){
      io = new IntersectionObserver(function(es){
        es.forEach(function(e){ var v = loopOf(e.target);
          if (!still && !player.open && e.isIntersecting && e.intersectionRatio > .55) startLoop(v); else v.pause(); });
      }, {threshold:[0, .55, 1]});
      reels.forEach(function(r){ io.observe(r); });
    }
    document.addEventListener('visibilitychange', function(){ if (document.hidden) stopAll(); else resync(); });
    addEventListener('pageshow', function(e){ if (e.persisted) resync(); });
    function paintMotion(){ if (!mt) return; mt.setAttribute('aria-pressed', still ? 'true' : 'false'); mt.querySelector('span').textContent = still ? 'تشغيل الحركة' : 'إيقاف الحركة'; }
    paintMotion();
    if (mt) mt.addEventListener('click', function(){
      still = !still; paintMotion();
      try { localStorage.setItem('alhabib-reels-motion', still ? 'off' : 'on'); } catch(e){}
      if (still) stopAll(); else resync();
    });

    function shown(){ return reels.filter(function(r){ return !r.hidden; }); }
    function setNav(){
      var list = shown(), k = list.indexOf(reels[cur]), dp = k <= 0, dn = k >= list.length - 1, ae = document.activeElement;
      // never disable the button that has focus: hand focus to the other arrow, or to close
      if ((ae === pb && dp) || (ae === nb && dn)){ var t = ae === pb ? (!dn && nb) : (!dp && pb); (t || xb).focus(); }
      pb.disabled = dp; nb.disabled = dn;
    }
    function load(r){
      cur = reels.indexOf(r);
      pv.src = r.getAttribute('data-src'); pv.poster = loopOf(r).getAttribute('poster');
      pv.setAttribute('aria-label', r.getAttribute('data-title'));
      pt.textContent = r.getAttribute('data-title'); ps.textContent = r.getAttribute('data-sub');
      frame.classList.toggle('wide', r.hasAttribute('data-wide'));
      setNav();
      var p = pv.play(); if (p && p.catch) p.catch(function(){});
    }
    // the card grows into the player: FLIP from the card's box to the frame's box
    function flip(el, box, reverse){
      if (!el.animate) return null;
      var end = el.getBoundingClientRect();
      if (!box || reduce) return el.animate([{opacity:reverse ? 1 : 0}, {opacity:reverse ? 0 : 1}], {duration:reverse ? 160 : 220, easing:'ease-out', fill:'both'});
      var t = 'translate(' + (box.left - end.left) + 'px,' + (box.top - end.top) + 'px) scale(' + (box.width / end.width) + ',' + (box.height / end.height) + ')';
      var k = [{transform:t, opacity:.6}, {transform:'none', opacity:1}];
      return el.animate(reverse ? k.reverse() : k, {duration:reverse ? 320 : 560, easing:'cubic-bezier(.16,1,.3,1)', fill:'both'});
    }
    function stopAnim(){ if (anim){ anim.onfinish = null; anim.cancel(); anim = null; } }
    // one teardown for every way the dialog can close (our close, a native Esc/Back, script)
    player.addEventListener('close', function(){
      stopAnim(); busy = false; closing = false; pending = false;
      pv.pause(); pv.removeAttribute('src'); pv.load();
      document.documentElement.style.overflow = '';
      if (from){
        if (refocusScroll) from.scrollIntoView({block:'center', behavior:'auto'});
        from.focus({preventScroll:true});
      }
      resync();
    });
    function open(r){
      if (busy || player.open) return;
      busy = true; stopAll(); from = r;
      player.showModal(); document.documentElement.style.overflow = 'hidden';
      load(r);
      anim = flip(frame, r.getBoundingClientRect(), false);
      if (anim) anim.onfinish = function(){ stopAnim(); busy = false; }; else busy = false;
    }
    function close(){
      if (!player.open || closing) return;
      stopAnim(); // a close while opening cuts the entrance short
      closing = busy = true; pv.pause();
      var back = from && !from.hidden ? from.getBoundingClientRect() : null;
      if (back && (back.bottom < 0 || back.top > innerHeight)) back = null;
      refocusScroll = !back;
      anim = flip(frame, back, true);
      if (anim) anim.onfinish = function(){ player.close(); }; else player.close();
    }
    function step(d){
      if (busy || pending || !player.open) return;
      var list = shown(), k = list.indexOf(reels[cur]) + d;
      if (k < 0 || k >= list.length) return;
      var next = list[k]; pending = true;
      var a = frame.animate ? frame.animate([{opacity:1}, {opacity:0}], {duration:140, easing:'ease-in', fill:'forwards'}) : null;
      function swap(){
        pending = false;
        var ok = player.open && !busy; // the player may have closed during the fade
        if (ok){ from = next; load(next); }
        if (a) a.cancel();
        if (ok && frame.animate) frame.animate([{opacity:0}, {opacity:1}], {duration:220, easing:'ease-out'});
      }
      if (a) a.onfinish = swap; else swap();
    }
    reels.forEach(function(r){ r.addEventListener('click', function(){ open(r); }); });
    player.addEventListener('cancel', function(e){ if (e.cancelable){ e.preventDefault(); close(); } });
    xb.addEventListener('click', close);
    pb.addEventListener('click', function(){ step(-1); });
    nb.addEventListener('click', function(){ step(1); });
    player.addEventListener('click', function(e){ if (e.target === player || e.target.classList.contains('stage')) close(); });
    document.addEventListener('keydown', function(e){
      if (!player.open || e.target === pv) return;
      // RTL: the left arrow moves forward through the list
      if (e.key === 'ArrowLeft'){ e.preventDefault(); step(1); }
      if (e.key === 'ArrowRight'){ e.preventDefault(); step(-1); }
    });
  }

  if (!G || reduce) return;
  gsap.utils.toArray('.clip').forEach(function(el){
    gsap.fromTo(el, {clipPath:'inset(0 0 18% 0)'}, {clipPath:'inset(0 0 0% 0)', duration:1.4, ease:'expo.out', scrollTrigger:{trigger:el, start:'top 88%', once:true}});
  });
  gsap.utils.toArray('.par').forEach(function(img){
    gsap.fromTo(img, {scale:1.15, yPercent:-4}, {scale:1.15, yPercent:4, ease:'none', scrollTrigger:{trigger:img.parentNode, start:'top bottom', end:'bottom top', scrub:true}});
  });
  gsap.utils.toArray('.par-sig').forEach(function(el){
    gsap.fromTo(el, {yPercent:-6}, {yPercent:6, ease:'none', scrollTrigger:{trigger:el.parentNode, start:'top bottom', end:'bottom top', scrub:true}});
  });
  if (!heroScrub && document.querySelector('.hero-img img')) gsap.to('.hero-img img', {yPercent:12, ease:'none', scrollTrigger:{trigger:'.hero', start:'top top', end:'bottom top', scrub:true}});
  addEventListener('load', function(){ ScrollTrigger.refresh(); });
})();
