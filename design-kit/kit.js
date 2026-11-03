/* design-kit/kit.js — 템플릿 공통 함수 (외부 요청 0, 라이브러리 0, 전역은 K 하나). 템플릿에서 <script src="../kit.js"></script>
   K.esc(s) · K.fmt(n, 소수자리) · K.hhmm(ISO) · K.kv([[라벨, 값, raw]]) · K.badge(글자, ok|warn|bad|info|off|brand)
   K.chips(요소, [[키, 글자]], 해제(키)) · K.toast(글자) · K.setStatus(배너, ok|fallback|failed, 상세)
   K.load(url, 내장샘플) => Promise {data, state, error}. 주소에 ?state=fallback 또는 ?state=failed 를 붙이면 그 상태를 강제한다(빈·오류 화면 확인용)
   K.spark(값[], {limits:[lcl, ucl], target, lg, label}) => SVG 문자열 · K.hbar([[라벨, 값, warn|bad|off]], {max, unit, target}) => HTML 문자열(축 눈금·값 포함) */
(function (w, d) {
  'use strict';
  var ESC = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  var K = {};
  K.esc = function (s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return ESC[c]; }); };
  K.fmt = function (n, dg) {
    if (n === null || n === undefined || n === '' || isNaN(n)) return '-';
    return Number(n).toLocaleString('ko-KR', { minimumFractionDigits: dg || 0, maximumFractionDigits: dg || 0 });
  };
  K.hhmm = function (iso) {   // 문자열에 적힌 현지 시각을 그대로 쓴다(브라우저 시간대로 바꾸지 않는다)
    var m = /(\d{2}):(\d{2})/.exec(iso || '');
    return m ? m[1] + ':' + m[2] : '-';
  };
  K.kv = function (rows) {
    return '<dl class="kv">' + rows.map(function (r) {
      var v = (r[1] === null || r[1] === undefined || r[1] === '') ? '-' : r[1];
      return '<dt>' + K.esc(r[0]) + '</dt><dd>' + (r[2] ? v : K.esc(v)) + '</dd>';
    }).join('') + '</dl>';
  };
  K.badge = function (text, level) { return '<span class="badge ' + K.esc(level || 'off') + '">' + K.esc(text) + '</span>'; };
  K.chips = function (el, items, onRemove) {
    el.innerHTML = items.map(function (it) {
      return '<span class="chip">' + K.esc(it[1]) + '<button class="x" type="button" data-key="' + K.esc(it[0]) +
        '" aria-label="' + K.esc(it[1]) + ' 해제">&times;</button></span>';
    }).join('');
    el.hidden = !items.length;
    el.onclick = function (e) {
      var b = e.target.closest('button[data-key]');
      if (b && onRemove) onRemove(b.getAttribute('data-key'));
    };
  };
  var tEl, tTimer;
  K.toast = function (msg) {
    if (!tEl) { tEl = d.createElement('div'); tEl.className = 'toast'; tEl.setAttribute('role', 'status'); d.body.appendChild(tEl); }
    tEl.textContent = msg;
    tEl.classList.add('show');
    clearTimeout(tTimer);
    tTimer = setTimeout(function () { tEl.classList.remove('show'); }, 2400);
  };
  var ST = { ok: ['ok', '실데이터'], fallback: ['warn', '내장 샘플 표시 중'], failed: ['bad', '데이터를 불러오지 못함'] };
  K.setStatus = function (el, state, detail) {
    var s = ST[state] || ST.failed;
    el.className = 'banner ' + s[0];
    el.setAttribute('role', state === 'ok' ? 'status' : 'alert');
    el.innerHTML = '<b>' + s[1] + '</b><span>' + K.esc(detail || '') + '</span>';
    el.hidden = false;
    d.documentElement.setAttribute('data-state', state);
  };
  K.load = function (url, sample) {
    var force = (/[?&]state=(fallback|failed)/.exec(w.location.search) || [])[1];
    var fail = function (msg) {
      return (sample && force !== 'failed') ? { data: sample, state: 'fallback', error: msg } : { data: null, state: 'failed', error: msg };
    };
    if (force) return Promise.resolve(fail('?state=' + force));
    return fetch(url, { cache: 'no-store' }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    }).then(function (data) { return { data: data, state: 'ok', error: '' }; },
      function (e) { return fail(String((e && e.message) || e)); });
  };
  K.spark = function (vals, o) {
    o = o || {};
    var W = 120, H = o.lg ? 60 : 32, P = 3, lim = o.limits || [];
    var all = vals.concat(lim, o.target == null ? [] : [o.target]);
    var lo = Math.min.apply(null, all), hi = Math.max.apply(null, all), sp = (hi - lo) || 1;
    var x = function (i) { return (P + i * (W - 2 * P) / Math.max(vals.length - 1, 1)).toFixed(1); };
    var y = function (v) { return (H - P - (v - lo) * (H - 2 * P) / sp).toFixed(1); };
    var hl = function (c, v) { return '<line class="' + c + '" x1="0" x2="' + W + '" y1="' + y(v) + '" y2="' + y(v) + '"/>'; };
    var s = '<svg class="spark' + (o.lg ? ' lg' : '') + '" viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="none" role="img" aria-label="' + K.esc(o.label || '추세') + '">';
    lim.forEach(function (v) { s += hl('limit', v); });
    if (o.target != null) s += hl('target', o.target);
    s += '<polyline class="line" points="' + vals.map(function (v, i) { return x(i) + ',' + y(v); }).join(' ') + '"/>';
    if (lim.length === 2) {
      var a = Math.min(lim[0], lim[1]), b = Math.max(lim[0], lim[1]);
      vals.forEach(function (v, i) { if (v < a || v > b) s += '<line class="ooc" x1="' + x(i) + '" x2="' + x(i) + '" y1="' + y(v) + '" y2="' + y(v) + '"/>'; });
    }
    return s + '</svg>';
  };
  K.hbar = function (rows, o) {
    o = o || {};
    var max = o.max || Math.max.apply(null, rows.map(function (r) { return r[1]; })) || 1, u = o.unit || '';
    var pct = function (v) { return Math.max(0, Math.min(100, v / max * 100)).toFixed(1) + '%'; };
    var tgt = o.target == null ? '' : '<b style="left:' + pct(o.target) + '"></b>';
    var s = '<div class="hbar">';
    rows.forEach(function (r) {
      s += '<div class="hb"><span class="k">' + K.esc(r[0]) + '</span><span class="track"><i class="' + K.esc(r[2] || '') +
        '" style="width:' + pct(r[1]) + '"></i>' + tgt + '</span><span class="v">' + K.fmt(r[1]) + u + '</span></div>';
    });
    return s + '<div class="hb axis"><span></span><span class="ticks"><span>0</span><span>' + K.fmt(max / 2) + '</span><span>' +
      K.fmt(max) + u + '</span></span><span></span></div></div>';
  };
  w.K = K;
})(window, document);
