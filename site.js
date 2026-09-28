(function(){
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var G = typeof gsap !== 'undefined' && typeof ScrollTrigger !== 'undefined';
  if (G) gsap.registerPlugin(ScrollTrigger);

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
  function ns(){ if (nav) nav.classList.toggle('solid', scrollY > 60); }
  addEventListener('scroll', ns, {passive:true}); ns();
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

  // products strip: native scroll with buttons (no pinning, so no jump at the page end)
  var pin = document.getElementById('pin'), prog = document.getElementById('prog');
  if (pin){
    document.querySelectorAll('.scroll-ctl button').forEach(function(b){
      b.addEventListener('click', function(){
        var card = pin.querySelector('.pcard, .track > *'), w = card ? card.getBoundingClientRect().width + 24 : pin.clientWidth * .8;
        // RTL: moving "next" means scrolling toward negative scrollLeft
        pin.scrollBy({left: parseInt(b.getAttribute('data-dir'), 10) * w, behavior: reduce ? 'auto' : 'smooth'});
      });
    });
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

  // top clients strip: drifts on its own; hovering, keyboard focus or the pause button stop it, and it can be
  // dragged (mouse or finger) or moved with the arrow keys. With reduced motion it starts paused.
  (function(){
    var view = document.querySelector('.clients-view'); if (!view) return;
    var track = view.querySelector('.clients-track'), btn = document.querySelector('.clients-pause');
    var items = track.children, half = track.querySelectorAll('.client:not([aria-hidden])').length;
    var W = 0, x = 0, speed = 34, last = 0, hover = false, focus = false, seen = true, drag = null, resumeAt = 0, nudge = 0;
    var paused = reduce;
    function measure(){ W = Math.abs(items[0].offsetLeft - items[half].offsetLeft); }
    function paint(){ if (W) x = ((x % W) + W) % W; track.style.transform = 'translate3d(' + x.toFixed(2) + 'px,0,0)'; }
    function setBtn(){
      btn.setAttribute('aria-pressed', paused ? 'true' : 'false');
    }
    function tick(t){
      var dt = last ? Math.min(t - last, 64) / 1000 : 0; last = t;
      if (nudge){ var step = nudge * Math.min(1, dt * 9); if (Math.abs(nudge - step) < .5) step = nudge; nudge -= step; x += step; paint(); }
      else if (!paused && !hover && !focus && !drag && seen && t > resumeAt){ x += speed * dt; paint(); }
      requestAnimationFrame(tick);
    }
    measure(); paint(); setBtn();
    window.addEventListener('resize', function(){ var r = W ? x / W : 0; measure(); x = r * W; paint(); });
    if ('IntersectionObserver' in window) new IntersectionObserver(function(es){ seen = es[0].isIntersecting; }).observe(view);
    btn.addEventListener('click', function(){ paused = !paused; setBtn(); });
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
  if (document.querySelector('.hero-img img')) gsap.to('.hero-img img', {yPercent:12, ease:'none', scrollTrigger:{trigger:'.hero', start:'top top', end:'bottom top', scrub:true}});
  addEventListener('load', function(){ ScrollTrigger.refresh(); });
})();
