function renderRadarChart(data) {
    var bazi = data.bazi || {};
    var shishen = bazi.shishen_gan || {};
    var shensha = bazi.shensha || [];
    var xiYong = bazi.xi_yong || {};
    var wuxingScore = bazi.wuxing_score || {};
    var features = bazi.features || [];
    var allShishen = Object.values(shishen);
    var scores = {};
    var career = 50;
    allShishen.forEach(function(s) { if (s === '正官') career += 12; if (s === '七杀') career += 8; });
    if (bazi.ming_gong) career += 5;
    features.forEach(function(f) { if (f.indexOf('官') >= 0 || f.indexOf('杀') >= 0) career += 5; });
    scores['事业'] = Math.min(career, 95);
    var wealth = 45;
    allShishen.forEach(function(s) { if (s === '正财') wealth += 12; if (s === '偏财') wealth += 10; });
    allShishen.forEach(function(s) { if (s === '食神' || s === '伤官') wealth += 4; });
    scores['财运'] = Math.min(wealth, 95);
    var love = 55;
    if (bazi.day) { var dayZhi = bazi.day[1]; if ('子午卯酉'.indexOf(dayZhi) >= 0) love += 10; }
    shensha.forEach(function(s) { if (s.indexOf('桃花') >= 0) love += 10; if (s.indexOf('红鸾') >= 0) love += 8; });
    features.forEach(function(f) { if (f.indexOf('冲') >= 0) love -= 8; if (f.indexOf('合') >= 0) love += 5; });
    scores['感情'] = Math.max(20, Math.min(love, 95));
    var health = 60;
    if (xiYong.ratio) health = Math.round(xiYong.ratio * 0.8 + 20);
    if (xiYong.strength === '身弱') health -= 8;
    features.forEach(function(f) { if (f.indexOf('刑') >= 0 || f.indexOf('冲') >= 0) health -= 5; });
    scores['健康'] = Math.max(25, Math.min(health, 95));
    var study = 50;
    allShishen.forEach(function(s) { if (s === '正印') study += 15; if (s === '偏印') study += 10; });
    shensha.forEach(function(s) { if (s.indexOf('文昌') >= 0) study += 10; });
    scores['学业'] = Math.min(study, 95);
    var noble = 35;
    shensha.forEach(function(s) { if (s.indexOf('贵人') >= 0) noble += 12; if (s.indexOf('天德') >= 0 || s.indexOf('月德') >= 0) noble += 8; });
    scores['贵人'] = Math.min(noble, 95);
    var creative = 45;
    allShishen.forEach(function(s) { if (s === '食神') creative += 15; if (s === '伤官') creative += 12; });
    features.forEach(function(f) { if (f.indexOf('食伤') >= 0) creative += 8; });
    scores['创造力'] = Math.min(creative, 95);
    var balance = 50;
    if (xiYong.ratio) balance = xiYong.ratio > 30 ? 75 : xiYong.ratio > 20 ? 60 : 40;
    if (wuxingScore && Object.keys(wuxingScore).length > 0) {
        var vals = Object.values(wuxingScore).filter(function(v) { return typeof v === 'number'; });
        if (vals.length > 0) {
            var max = Math.max.apply(null, vals), min = Math.min.apply(null, vals);
            balance += (max - min < 5) ? 15 : (max - min < 10) ? 5 : -10;
        }
    }
    scores['平衡'] = Math.max(25, Math.min(balance, 95));
    var keys = Object.keys(scores);
    var total = Math.round(keys.reduce(function(a, k) { return a + scores[k]; }, 0) / keys.length);
    var section = document.getElementById('radarSection');
    section.style.display = 'block';
    var totalColor = total >= 70 ? '#4ecdc4' : total >= 50 ? 'var(--accent-gold)' : '#ff6b6b';
    document.getElementById('radarTotal').innerHTML = '<span style="color:' + totalColor + '">' + total + '</span><span style="font-size:0.7rem;color:var(--text-muted);margin-left:0.3rem">/100</span>';
    var canvas = document.getElementById('radarCanvas');
    var ctx = canvas.getContext('2d');
    var dpr = window.devicePixelRatio || 1;
    var size = 320;
    canvas.width = size * dpr; canvas.height = size * dpr;
    canvas.style.width = size + 'px'; canvas.style.height = size + 'px';
    ctx.scale(dpr, dpr);
    var cx = size / 2, cy = size / 2, maxR = 120;
    var n = keys.length, angleStep = (Math.PI * 2) / n, startAngle = -Math.PI / 2;
    ctx.clearRect(0, 0, size, size);
    for (var layer = 1; layer <= 5; layer++) {
        var r = maxR * layer / 5;
        ctx.beginPath();
        for (var i = 0; i <= n; i++) {
            var a = startAngle + i * angleStep;
            var x = cx + r * Math.cos(a), y = cy + r * Math.sin(a);
            i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        }
        ctx.closePath(); ctx.strokeStyle = 'rgba(201, 169, 110, 0.08)'; ctx.lineWidth = 1; ctx.stroke();
    }
    for (var i = 0; i < n; i++) {
        var a = startAngle + i * angleStep;
        ctx.beginPath(); ctx.moveTo(cx, cy);
        ctx.lineTo(cx + maxR * Math.cos(a), cy + maxR * Math.sin(a));
        ctx.strokeStyle = 'rgba(201, 169, 110, 0.12)'; ctx.stroke();
    }
    ctx.beginPath();
    for (var i = 0; i <= n; i++) {
        var idx = i % n;
        var a = startAngle + idx * angleStep;
        var r = maxR * scores[keys[idx]] / 100;
        var x = cx + r * Math.cos(a), y = cy + r * Math.sin(a);
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.closePath(); ctx.fillStyle = 'rgba(201, 169, 110, 0.15)'; ctx.fill();
    ctx.strokeStyle = 'rgba(201, 169, 110, 0.6)'; ctx.lineWidth = 2; ctx.stroke();
    for (var i = 0; i < n; i++) {
        var a = startAngle + i * angleStep;
        var r = maxR * scores[keys[i]] / 100;
        var x = cx + r * Math.cos(a), y = cy + r * Math.sin(a);
        ctx.beginPath(); ctx.arc(x, y, 4, 0, Math.PI * 2);
        ctx.fillStyle = '#c9a96e'; ctx.fill();
        ctx.strokeStyle = '#0a0a1a'; ctx.lineWidth = 2; ctx.stroke();
        var lx = cx + (maxR + 22) * Math.cos(a), ly = cy + (maxR + 22) * Math.sin(a);
        ctx.font = '12px Noto Sans SC, sans-serif'; ctx.fillStyle = '#f0e6d3';
        ctx.textAlign = Math.abs(Math.cos(a)) < 0.1 ? 'center' : Math.cos(a) > 0 ? 'left' : 'right';
        ctx.textBaseline = Math.abs(Math.sin(a)) < 0.1 ? 'middle' : Math.sin(a) > 0 ? 'top' : 'bottom';
        ctx.fillText(keys[i] + ' ' + scores[keys[i]], lx, ly);
    }
    var details = document.getElementById('radarDetails');
    var html = '';
    var colors = ['#c9a96e','#4ecdc4','#ff6b6b','#ffd93d','#3a7bd5','#a78bfa','#ff9ff3','#2d8b56'];
    keys.forEach(function(k, i) {
        var v = scores[k];
        var color = v >= 70 ? '#4ecdc4' : v >= 50 ? colors[i % colors.length] : '#ff6b6b';
        html += '<div class="radar-score-item"><span class="radar-score-label">' + k + '</span><div class="radar-score-bar"><div class="radar-score-fill" style="width:' + v + '%;background:' + color + '"></div></div><span class="radar-score-value" style="color:' + color + '">' + v + '</span></div>';
    });
    details.innerHTML = html;
}
