/* 玄照 v2.0 - 八术排盘渲染引擎 */
(function(){
'use strict';

/* ===== 工具函数 ===== */
const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);
const WUXING_MAP = {
    '甲':'木','乙':'木','丙':'火','丁':'火','戊':'土','己':'土','庚':'金','辛':'金','壬':'水','癸':'水',
    '子':'水','丑':'土','寅':'木','卯':'木','辰':'土','巳':'火','午':'火','未':'土','申':'金','酉':'金','戌':'土','亥':'水'
};
const WX_CLASS = {'金':'wx-jin','木':'wx-mu','水':'wx-shui','火':'wx-huo','土':'wx-tu'};
const WX_COLOR = {'金':'#c0a040','木':'#40a060','水':'#4080d0','火':'#e84040','土':'#a08050'};

function wxClass(c){ return WX_CLASS[WUXING_MAP[c]] || ''; }
function wxColor(c){ return WX_COLOR[WUXING_MAP[c]] || '#888'; }
function esc(s){ if(!s)return''; const d=document.createElement('div'); d.textContent=s; return d.innerHTML; }

/* ===== Tab切换 ===== */
function initTabs(){
    $$('.tab').forEach(btn=>{
        btn.addEventListener('click', ()=>{
            $$('.tab').forEach(t=>t.classList.remove('active'));
            $$('.method-panel').forEach(p=>p.classList.remove('active'));
            btn.classList.add('active');
            const panel = $('#panel-'+btn.dataset.method);
            if(panel) panel.classList.add('active');
        });
    });
}

/* ===== 参数解析 ===== */
function getParams(){
    const u = new URL(location.href);
    return {
        birth: u.searchParams.get('birth')||'',
        location: u.searchParams.get('location')||'北京',
        gender: u.searchParams.get('gender')||'男',
        name: u.searchParams.get('name')||''
    };
}

/* ===== 主流程 ===== */
async function init(){
    initTabs();
    const params = getParams();
    if(!params.birth){ alert('缺少出生时间参数'); return; }

    // 显示头部信息
    $('#headerBirth').textContent = params.birth;
    $('#headerLocation').textContent = params.location;

    // 调用API
    let url = `/api/chart?birth=${encodeURIComponent(params.birth)}&location=${encodeURIComponent(params.location)}&gender=${encodeURIComponent(params.gender)}`;
    if(params.name) url += `&name=${encodeURIComponent(params.name)}`;

    try {
        const resp = await fetch(url);
        const data = await resp.json();
        if(data.error){ throw new Error(data.error); }

        // 隐藏加载，显示面板
        $('#loadingOverlay').style.display = 'none';
        $('#panelsContainer').style.display = 'block';

        // 渲染各面板
        renderHeaderPills(data);
        if(data.bazi) renderBazi(data.bazi, data.corrected_time);
        if(data.ziwei) renderZiwei(data.ziwei);
        if(data.liuyao) renderLiuyao(data.liuyao);
        if(data.qimen) renderQimen(data.qimen);
        if(data.liuren) renderLiuren(data.liuren);
        if(data.taiyi) renderTaiyi(data.taiyi);
        if(data.astro) renderAstro(data.astro);
        if(data.xingming) renderXingming(data.xingming);
    } catch(e) {
        $('#loadingOverlay').innerHTML = `<div style="color:var(--crimson);text-align:center;"><div style="font-size:1.2rem;margin-bottom:8px;">排盘失败</div><div style="font-size:0.85rem;color:var(--text-muted);">${esc(e.message)}</div></div>`;
    }
}

/* ===== 头部标签 ===== */
function renderHeaderPills(data){
    const pills = [];
    if(data.corrected_time){
        const ct = data.corrected_time;
        if(ct.diff_minutes !== undefined) pills.push(`真太阳时校正 ${ct.diff_minutes>0?'+':''}${ct.diff_minutes}分`);
    }
    if(data.methods) data.methods.forEach(m=>pills.push(m));
    $('#headerPills').innerHTML = pills.map(p=>`<span class="header-pill">${esc(p)}</span>`).join('');
}

/* ===== 八字渲染 ===== */
function renderBazi(bazi, ct){
    // 四柱
    const pillars = $('#baziPillars');
    const cols = [
        {label:'年柱', gan:bazi.year?.[0], zhi:bazi.year?.[1], shishen_g:bazi.shishen_gan?.year, shishen_z:bazi.shishen_zhi?.year, nayin:bazi.nayin?.year},
        {label:'月柱', gan:bazi.month?.[0], zhi:bazi.month?.[1], shishen_g:bazi.shishen_gan?.month, shishen_z:bazi.shishen_zhi?.month, nayin:bazi.nayin?.month},
        {label:'日柱', gan:bazi.day?.[0], zhi:bazi.day?.[1], shishen_g:'', shishen_z:bazi.shishen_zhi?.day, nayin:bazi.nayin?.day, isDay:true},
        {label:'时柱', gan:bazi.time?.[0], zhi:bazi.time?.[1], shishen_g:bazi.shishen_gan?.time, shishen_z:bazi.shishen_zhi?.time, nayin:bazi.nayin?.time},
    ];
    // 表头
    let html = cols.map(c=>`<div class="pillar-col"><div class="pillar-label">${c.label}</div></div>`).join('');
    // 重新组织为行
    const rows = [
        {name:'十神', vals: cols.map(c=>c.isDay?'日主':(c.shishen_g||''))},
        {name:'天干', vals: cols.map(c=>c.gan||''), isGan:true},
        {name:'地支', vals: cols.map(c=>c.zhi||''), isZhi:true},
        {name:'藏干', vals: cols.map(c=>{ const hg=bazi.hidden_gans; if(!hg)return''; const key=['year','month','day','time'][cols.indexOf(c)]; const h=hg[key]; return h?(Array.isArray(h)?h.join(' '):h):'';})},
        {name:'纳音', vals: cols.map(c=>c.nayin||'')},
        {name:'星运', vals: cols.map(c=>{ const ch=bazi.changsheng; if(!ch)return''; const key=['year','month','day','time'][cols.indexOf(c)]; return ch[key]||'';})},
    ];
    // 添加神煞行（如果有）
    if(bazi.shensha_per_pillar){
        rows.push({name:'神煞', vals: cols.map((c,i)=>{
            const key=['year','month','day','time'][i];
            const ss=bazi.shensha_per_pillar[key];
            return ss?(Array.isArray(ss)?ss.join(' '):ss):'';
        })});
    }

    let tableHtml = '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:0.8rem;">';
    tableHtml += '<tr><th style="padding:6px;background:var(--bg-cell-alt);color:var(--text-muted);border:1px solid var(--border);width:50px;"></th>';
    cols.forEach(c=>{ tableHtml += `<th style="padding:6px;text-align:center;background:var(--bg-cell-alt);color:var(--text-muted);border:1px solid var(--border);">${c.label}</th>`; });
    tableHtml += '</tr>';
    rows.forEach(r=>{
        tableHtml += '<tr>';
        tableHtml += `<td style="padding:5px 8px;background:var(--bg-cell-alt);color:var(--text-muted);border:1px solid var(--border);font-size:0.7rem;white-space:nowrap;">${r.name}</td>`;
        r.vals.forEach((v,i)=>{
            let cls = '';
            if(r.isGan) cls = `font-size:1.4rem;font-weight:700;color:${wxColor(v)};`;
            else if(r.isZhi) cls = `font-size:1.4rem;font-weight:700;color:${wxColor(v)};`;
            else cls = 'color:var(--text-primary);';
            tableHtml += `<td style="padding:5px 8px;text-align:center;border:1px solid var(--border);background:var(--bg-cell);${cls}">${esc(v)}</td>`;
        });
        tableHtml += '</tr>';
    });
    tableHtml += '</table></div>';
    pillars.innerHTML = tableHtml;

    // 五行旺衰
    const wx = bazi.wuxing_score;
    if(wx){
        const maxVal = Math.max(...Object.values(wx), 1);
        const wxBars = $('#baziWuxing');
        let barHtml = '';
        ['金','木','水','火','土'].forEach(w=>{
            const val = wx[w] || 0;
            const pct = Math.round(val / maxVal * 100);
            barHtml += `<div class="wx-bar-row">
                <span class="wx-bar-label ${WX_CLASS[w]}" style="color:${WX_COLOR[w]}">${w}</span>
                <div class="wx-bar-track"><div class="wx-bar-fill" style="width:${pct}%;background:${WX_COLOR[w]};"></div></div>
                <span class="wx-bar-val">${val}</span>
            </div>`;
        });
        wxBars.innerHTML = barHtml;
    }

    // 十神
    const ss = bazi.shishen_gan;
    if(ss){
        const ssGrid = $('#baziShishen');
        let ssHtml = '';
        ['year','month','day','time'].forEach((k,i)=>{
            const labels = ['年干','月干','日干','时干'];
            const val = k==='day'?'日主':(ss[k]||'');
            ssHtml += `<div class="shishen-cell"><span class="label">${labels[i]}</span><span class="value">${esc(val)}</span></div>`;
        });
        ssGrid.innerHTML = ssHtml;
    }

    // 神煞
    const shensha = bazi.shensha;
    if(shensha && shensha.length){
        $('#baziShensha').innerHTML = shensha.map(s=>{
            const name = typeof s==='string'?s:(s.name||s[0]||'');
            return `<span class="shensha-tag">${esc(name)}</span>`;
        }).join('');
    }

    // 大运
    const dayun = bazi.dayun;
    if(dayun && dayun.length){
        const duTable = $('#baziDayun');
        let duHtml = '<div class="dayun-table">';
        dayun.forEach((dy,i)=>{
            const isCurrent = dy.is_current || i===0;
            const gan = dy.gan||dy.ganzhi?.[0]||'';
            const zhi = dy.zhi||dy.ganzhi?.[1]||'';
            const age = dy.age||dy.start_age||'';
            const year = dy.start_year||dy.year||'';
            duHtml += `<div class="dayun-col${isCurrent?' current':''}">
                <div class="dy-age">${age}岁</div>
                <div class="dy-gan ${wxClass(gan)}">${esc(gan)}</div>
                <div class="dy-zhi ${wxClass(zhi)}">${esc(zhi)}</div>
                <div class="dy-year">${year}</div>
            </div>`;
        });
        duHtml += '</div>';
        duTable.innerHTML = duHtml;
    }

    // 喜用神
    const xy = bazi.xi_yong;
    if(xy){
        const xyCard = $('#baziXiyong');
        let xyHtml = '<div class="xiyong-row">';
        const xi = xy.xi || xy.favorable || [];
        const ji = xy.ji || xy.unfavorable || [];
        (Array.isArray(xi)?xi:[xi]).filter(Boolean).forEach(x=>{ xyHtml += `<span class="xiyong-item xi">喜: ${esc(x)}</span>`; });
        (Array.isArray(ji)?ji:[ji]).filter(Boolean).forEach(j=>{ xyHtml += `<span class="xiyong-item ji">忌: ${esc(j)}</span>`; });
        xyHtml += '</div>';
        if(xy.reason || xy.strength) xyHtml += `<div class="xiyong-reason">${esc(xy.reason||xy.strength||'')}</div>`;
        xyCard.innerHTML = xyHtml;
    }
}

/* ===== 紫微渲染 ===== */
function renderZiwei(zw){
    const grid = $('#ziweiGrid');
    const palaces = zw.palaces;
    if(!palaces) { grid.innerHTML='<div style="padding:20px;color:var(--text-muted);text-align:center;">紫微数据不可用</div>'; return; }

    // 紫微十二宫布局：逆时针排列
    // 标准布局：[巳] [午] [未] [申]
    //          [辰] [  中  ] [酉]
    //          [卯] [  央  ] [戌]
    //          [寅] [丑] [子] [亥]
    const gridOrder = [
        '巳','午','未','申',
        '辰','__center__','__center2__','酉',
        '卯','__center3__','__center4__','戌',
        '寅','丑','子','亥'
    ];

    // 找到每个宫位对应的地支
    let cellsHtml = '';
    const zhiList = ['子','丑','寅','卯','辰','巳','午','未','申','酉','戌','亥'];

    // 构建宫位映射
    const palaceMap = {};
    if(Array.isArray(palaces)){
        palaces.forEach(p=>{
            const zhi = p.branch || p.zhi || p.name?.slice(-1) || '';
            palaceMap[zhi] = p;
        });
    } else if(typeof palaces === 'object'){
        Object.entries(palaces).forEach(([k,v])=>{
            palaceMap[k] = v;
        });
    }

    // 标准4x3网格布局
    const layout = [
        ['巳','午','未','申'],
        ['辰',null,null,'酉'],
        ['卯',null,null,'戌'],
        ['寅','丑','子','亥']
    ];

    let gridHtml = '';
    layout.forEach(row=>{
        row.forEach(zhi=>{
            if(zhi === null){
                // 中央区域
                gridHtml += renderZiweiCenter(zw, row.indexOf(zhi));
                return;
            }
            const p = palaceMap[zhi] || {};
            const name = p.name || p.palace_name || '';
            const stars = p.stars || p.star_list || [];
            const gan = p.gan || p.heavenly_stem || '';
            const selfHua = (zw.self_hua_map||{})[zhi] || '';

            let starHtml = '';
            if(Array.isArray(stars)){
                stars.forEach(s=>{
                    const sname = typeof s==='string'?s:(s.name||'');
                    let cls = 'zw-star';
                    if(s.is_main || s.type==='main') cls += ' main';
                    if(sname.includes('禄')) cls += ' hua-lu';
                    if(sname.includes('权')) cls += ' hua-quan';
                    if(sname.includes('科')) cls += ' hua-ke';
                    if(sname.includes('忌')) cls += ' hua-ji';
                    starHtml += `<span class="${cls}">${esc(sname)}</span>`;
                });
            }

            gridHtml += `<div class="ziwei-cell">
                <div class="zw-palace-name">${esc(name)||esc(zhi+'宫')}</div>
                <div class="zw-palace-gan">${esc(gan)}${zhi}</div>
                <div class="zw-stars">${starHtml}</div>
                ${selfHua?`<div class="zw-self-hua">自${esc(selfHua)}</div>`:''}
            </div>`;
        });
    });
    grid.innerHTML = gridHtml;

    // 四化
    const sihua = zw.sihua;
    if(sihua){
        const shGrid = $('#ziweiSihua');
        const types = ['化禄','化权','化科','化忌'];
        const classes = ['hua-lu','hua-quan','hua-ke','hua-ji'];
        let shHtml = '<div class="sihua-grid">';
        types.forEach((t,i)=>{
            const star = sihua[t] || sihua[i] || sihua[['lu','quan','ke','ji'][i]] || '';
            shHtml += `<div class="sihua-item"><div class="sihua-type">${t}</div><div class="sihua-star ${classes[i]}">${esc(typeof star==='object'?star.name||'':star)}</div></div>`;
        });
        shHtml += '</div>';
        shGrid.innerHTML = shHtml;
    }
}

function renderZiweiCenter(zw, idx){
    if(idx !== 0) return '<div class="ziwei-cell center-cell" style="border:none;background:transparent;"></div>';
    // 中央显示命主信息
    const mingGong = zw.ming_gong || '';
    const shenGong = zw.shen_gong || '';
    const wuxingJu = zw.wuxing_ju || '';
    const soulStar = zw.soul_star || '';
    const bodyStar = zw.body_star || '';
    const zodiac = zw.zodiac || '';
    return `<div class="ziwei-cell center-cell">
        <div style="font-size:0.8rem;color:var(--gold);font-weight:700;">命盘信息</div>
        <div style="font-size:0.7rem;color:var(--text-secondary);">命宫: ${esc(mingGong)} · 身宫: ${esc(shenGong)}</div>
        <div style="font-size:0.7rem;color:var(--text-secondary);">${esc(wuxingJu)} · ${esc(zodiac)}</div>
        <div style="font-size:0.7rem;color:var(--text-secondary);">命主: ${esc(soulStar)} · 身主: ${esc(bodyStar)}</div>
    </div>`;
}

/* ===== 六爻渲染 ===== */
function renderLiuyao(ly){
    const guaDiv = $('#liuyaoGua');
    const ben = ly.ben_gua || {};
    const bian = ly.bian_gua || {};
    const lines = ly.lines || [];
    const bianLines = ly.bian_lines || [];
    const dongYao = ly.dong_yao || [];
    const liuShen = ly.liu_shen || [];

    function renderGuaPanel(gua, glines, title, isBian){
        let html = `<div class="gua-panel"><div class="gua-title">${esc(title)}</div>`;
        html += `<div class="gua-subtitle">${esc(gua.name||'')} · ${esc(gua.gong||'')}</div>`;
        html += '<div class="yao-row header"><span>爻</span><span>爻象</span><span>六亲</span><span>六神</span><span>干支</span></div>';
        // 从上到下（6爻到1爻）
        for(let i=5; i>=0; i--){
            const yao = glines[i] || {};
            const isDong = !isBian && dongYao.includes(i+1);
            const yaoName = ['初爻','二爻','三爻','四爻','五爻','六爻'][i];
            const isYang = yao.yang || yao.value === 1 || yao.value === '阳';
            const liuqin = yao.liu_qin || yao.liuqin || '';
            const ganzhi = yao.gan_zhi || yao.ganzhi || yao.ganzhi || '';
            const shen = liuShen[i] || '';

            html += `<div class="yao-row${isDong?' yao-dong':''}">
                <span>${yaoName}${isDong?' ○':''}</span>
                <span class="yao-line">${isYang?'<span class="yang"></span>':'<span class="yin"><span></span><span></span></span>'}</span>
                <span>${esc(liuqin)}</span>
                <span style="color:var(--purple)">${esc(shen)}</span>
                <span>${esc(ganzhi)}</span>
            </div>`;
        }
        html += '</div>';
        return html;
    }

    guaDiv.innerHTML = renderGuaPanel(ben, lines, '本卦', false) + renderGuaPanel(bian, bianLines, '变卦', true);

    // 六神
    if(liuShen.length){
        const lsDiv = $('#liuyaoLiushen');
        lsDiv.innerHTML = '<div style="padding:10px 14px;display:flex;gap:8px;flex-wrap:wrap;">' +
            liuShen.map(s=>`<span class="shensha-tag" style="color:var(--purple);">${esc(s)}</span>`).join('') +
            '</div>';
    }

    // 五行分析
    const wxa = ly.wuxing_analysis;
    if(wxa){
        $('#liuyaoWuxing').innerHTML = `<div style="padding:10px 14px;font-size:0.85rem;color:var(--text-secondary);">${esc(typeof wxa==='string'?wxa:JSON.stringify(wxa))}</div>`;
    }
}

/* ===== 奇门遁甲渲染 ===== */
function renderQimen(qm){
    // 信息标签
    const info = $('#qimenInfo');
    const tags = [];
    if(qm.ju_name) tags.push(qm.ju_name);
    if(qm.yin_yang) tags.push(qm.yin_yang);
    if(qm.jieqi) tags.push(qm.jieqi);
    if(qm.zhi_fu) tags.push(`值符: ${qm.zhi_fu}`);
    if(qm.zhi_shi) tags.push(`值使: ${qm.zhi_shi}`);
    info.innerHTML = tags.map(t=>`<span class="qimen-info-tag">${esc(t)}</span>`).join('');

    // 九宫格
    const grid = $('#qimenGrid');
    const palaces = qm.palaces || {};
    const gongs = ['坎','坤','震','巽','中','乾','兑','艮','离']; // 洛书九宫

    // 地支对应宫位
    const gongZhi = {'坎':'子','坤':'未申','震':'卯','巽':'辰巳','中':'中','乾':'戌亥','兑':'酉','艮':'丑寅','离':'午'};

    let gridHtml = '';
    // 按洛书排列：离(上中)、坤(上右)、兑(中右)...
    // 标准九宫格布局：
    // 巽(4) | 离(9) | 坤(2)
    // 震(3) | 中(5) | 兑(7)
    // 艮(8) | 坎(1) | 乾(6)
    const gridLayout = [
        ['巽','离','坤'],
        ['震','中','兑'],
        ['艮','坎','乾']
    ];

    gridLayout.forEach(row=>{
        row.forEach(gong=>{
            const p = palaces[gong] || {};
            const diPan = (qm.di_pan||{})[gong] || '';
            const tianPan = (qm.tian_pan||{})[gong] || '';
            const baMen = (qm.ba_men||{})[gong] || '';
            const jiuXing = (qm.jiu_xing||{})[gong] || '';
            const baShen = (qm.ba_shen||{})[gong] || '';

            gridHtml += `<div class="qm-cell">
                <div class="qm-gong-name">${esc(gong)}宫</div>
                <div class="qm-row"><span class="qm-label">天盘</span><span class="qm-tian">${esc(tianPan)}</span></div>
                <div class="qm-row"><span class="qm-label">地盘</span><span class="qm-di">${esc(diPan)}</span></div>
                <div class="qm-row"><span class="qm-label">八门</span><span class="qm-men">${esc(baMen)}</span></div>
                <div class="qm-row"><span class="qm-label">九星</span><span class="qm-xing">${esc(jiuXing)}</span></div>
                <div class="qm-row"><span class="qm-label">八神</span><span class="qm-shen">${esc(baShen)}</span></div>
            </div>`;
        });
    });
    grid.innerHTML = gridHtml;

    // 格局分析
    const geju = qm.ge_ju_analysis;
    if(geju){
        const gjDiv = $('#qimenGeju');
        if(typeof geju === 'string'){
            gjDiv.innerHTML = `<div style="padding:10px 14px;font-size:0.85rem;color:var(--text-secondary);">${esc(geju)}</div>`;
        } else {
            gjDiv.innerHTML = `<div style="padding:10px 14px;font-size:0.85rem;color:var(--text-secondary);">${esc(JSON.stringify(geju))}</div>`;
        }
    }
}

/* ===== 大六壬渲染 ===== */
function renderLiuren(lr){
    // 信息标签
    const info = $('#liurenInfo');
    const tags = [];
    if(lr.zhan_shi) tags.push(`占时: ${lr.zhan_shi}`);
    if(lr.yue_jiang) tags.push(`月将: ${lr.yue_jiang}`);
    if(lr.jieqi) tags.push(lr.jieqi);
    if(lr.ge_ju) tags.push(lr.ge_ju);
    info.innerHTML = tags.map(t=>`<span class="liuren-info-tag">${esc(t)}</span>`).join('');

    // 天盘表格
    const panDiv = $('#liurenPan');
    const tianPan = lr.tian_pan || {};
    const positions = lr.positions || {};
    const tianJiang = lr.tian_jiang || {};

    if(Object.keys(tianPan).length){
        const zhiList = ['子','丑','寅','卯','辰','巳','午','未','申','酉','戌','亥'];
        let tableHtml = '<table class="lr-table"><tr><th>地盘</th>';
        zhiList.forEach(z=>{ tableHtml += `<th>${z}</th>`; });
        tableHtml += '</tr><tr><td style="background:var(--bg-cell-alt);color:var(--gold);font-weight:600;">天盘</td>';
        zhiList.forEach(z=>{
            const val = tianPan[z] || positions[z] || '';
            tableHtml += `<td>${esc(val)}</td>`;
        });
        tableHtml += '</tr>';
        if(Object.keys(tianJiang).length){
            tableHtml += '<tr><td style="background:var(--bg-cell-alt);color:var(--gold);font-weight:600;">天将</td>';
            zhiList.forEach(z=>{
                const val = tianJiang[z] || '';
                tableHtml += `<td style="color:var(--purple);">${esc(val)}</td>`;
            });
            tableHtml += '</tr>';
        }
        tableHtml += '</table>';
        panDiv.innerHTML = tableHtml;
    }

    // 四课三传
    const siKe = lr.si_ke || {};
    const sanChuan = lr.san_chuan || {};
    const sikeDiv = $('#liurenSike');

    let sikeHtml = '<div style="margin-bottom:12px;"><div style="font-size:0.75rem;color:var(--gold);margin-bottom:6px;font-weight:600;">四课</div><div class="sike-grid">';
    const sikeNames = ['一课','二课','三课','四课'];
    sikeNames.forEach((name,i)=>{
        const val = siKe[name] || siKe[i+1] || siKe[`ke${i+1}`] || '';
        sikeHtml += `<div class="sike-item"><div class="sike-label">${name}</div><div class="sike-value">${esc(typeof val==='object'?val.display||val.text||'':val)}</div></div>`;
    });
    sikeHtml += '</div></div>';

    sikeHtml += '<div><div style="font-size:0.75rem;color:var(--gold);margin-bottom:6px;font-weight:600;">三传</div><div class="sanchuan-grid">';
    const scNames = ['初传','中传','末传'];
    scNames.forEach((name,i)=>{
        const val = sanChuan[name] || sanChuan[i] || sanChuan[`chuan${i+1}`] || '';
        sikeHtml += `<div class="sc-item"><div class="sc-label">${name}</div><div class="sc-value">${esc(typeof val==='object'?val.display||val.text||'':val)}</div></div>`;
    });
    sikeHtml += '</div></div>';
    sikeDiv.innerHTML = sikeHtml;

    // 天将分析
    const tjDiv = $('#liurenTianjiang');
    const yongShen = lr.yong_shen;
    if(yongShen){
        tjDiv.innerHTML = `<div style="padding:10px 14px;font-size:0.85rem;">
            <div style="color:var(--gold);font-weight:600;margin-bottom:4px;">用神</div>
            <div style="color:var(--text-secondary);">${esc(typeof yongShen==='string'?yongShen:JSON.stringify(yongShen))}</div>
        </div>`;
    }
}

/* ===== 太乙渲染 ===== */
function renderTaiyi(ty){
    // 信息表格
    const infoDiv = $('#taiyiInfo');
    const rows = [
        ['局数', ty.ju_name||''],
        ['局数', ty.ju_num||''],
        ['阴阳', ty.yin_yang||''],
        ['太乙宫', ty.taiyi_gong||''],
        ['太乙卦', ty.taiyi_gua||''],
        ['积年', ty.ji_nian||''],
        ['纪元', ty.ji_yuan||''],
        ['年干支', ty.year_ganzhi||''],
        ['月干支', ty.month_ganzhi||''],
        ['日干支', ty.day_ganzhi||''],
        ['时干支', ty.hour_ganzhi||''],
    ].filter(r=>r[1]);
    infoDiv.innerHTML = '<table class="taiyi-table">' + rows.map(r=>`<tr><th>${r[0]}</th><td>${esc(r[1])}</td></tr>`).join('') + '</table>';

    // 三基五福
    const sjDiv = $('#taiyiSanji');
    const sjRows = [
        ['三基', ty.san_ji||''],
        ['五福', ty.wu_fu||''],
        ['大游', ty.da_you||''],
        ['小游', ty.xiao_you||''],
        ['天乙', ty.tian_yi||''],
        ['地乙', ty.di_yi||''],
        ['四神', ty.si_shen||''],
    ].filter(r=>r[1]);
    sjDiv.innerHTML = '<table class="taiyi-table">' + sjRows.map(r=>`<tr><th>${r[0]}</th><td>${esc(r[1])}</td></tr>`).join('') + '</table>';

    // 八门
    const bmDiv = $('#taiyiBamen');
    const bmRows = [
        ['值符', ty.zhi_fu||''],
        ['文昌', ty.wen_chang||''],
        ['始击', ty.shi_ji||''],
        ['主算', ty.zhu_suan||''],
        ['客算', ty.ke_suan||''],
        ['定算', ty.ding_suan||''],
    ].filter(r=>r[1]);
    bmDiv.innerHTML = '<table class="taiyi-table">' + bmRows.map(r=>`<tr><th>${r[0]}</th><td>${esc(r[1])}</td></tr>`).join('') + '</table>';

    // 算术分析
    const suanDiv = $('#taiyiSuan');
    const suan = ty.suan_analysis;
    if(suan){
        suanDiv.innerHTML = `<div style="padding:10px 14px;font-size:0.85rem;color:var(--text-secondary);">${esc(typeof suan==='string'?suan:JSON.stringify(suan))}</div>`;
    }
}

/* ===== 占星渲染 ===== */
function renderAstro(astro){
    // 圆形星盘
    drawAstroChart(astro);

    // 行星落座
    const pDiv = $('#astroPlanets');
    const planets = astro.planetary_details || astro.planets || {};
    if(Object.keys(planets).length){
        let tHtml = '<table class="astro-table"><tr><th>行星</th><th>星座</th><th>度数</th><th>宫位</th><th>状态</th></tr>';
        Object.entries(planets).forEach(([name, info])=>{
            if(typeof info === 'string'){
                tHtml += `<tr><td>${esc(name)}</td><td colspan="4">${esc(info)}</td></tr>`;
            } else {
                tHtml += `<tr>
                    <td style="color:var(--gold);font-weight:600;">${esc(name)}</td>
                    <td>${esc(info.sign||info.zodiac||'')}</td>
                    <td>${esc(info.degree||info.deg||'')}</td>
                    <td>${esc(info.house||'')}</td>
                    <td style="font-size:0.7rem;">${esc(info.retrograde?'逆行':'')}</td>
                </tr>`;
            }
        });
        tHtml += '</table>';
        pDiv.innerHTML = tHtml;
    }

    // 相位表
    const aDiv = $('#astroAspects');
    const aspects = astro.aspects || astro.aspects_summary || [];
    if(aspects.length){
        let aHtml = '<table class="astro-table"><tr><th>行星A</th><th>相位</th><th>行星B</th><th>容许度</th></tr>';
        aspects.forEach(a=>{
            if(typeof a === 'string'){
                aHtml += `<tr><td colspan="4">${esc(a)}</td></tr>`;
            } else {
                aHtml += `<tr>
                    <td style="color:var(--gold);">${esc(a.planet1||a[0]||'')}</td>
                    <td>${esc(a.aspect||a.type||a[1]||'')}</td>
                    <td style="color:var(--gold);">${esc(a.planet2||a[2]||'')}</td>
                    <td>${esc(a.orb||a[3]||'')}</td>
                </tr>`;
            }
        });
        aHtml += '</table>';
        aDiv.innerHTML = aHtml;
    }
}

function drawAstroChart(astro){
    const canvas = document.getElementById('astroCanvas');
    if(!canvas || !canvas.getContext) return;
    const ctx = canvas.getContext('2d');
    const W = canvas.width, H = canvas.height;
    const cx = W/2, cy = H/2, R = Math.min(W,H)/2 - 20;

    ctx.clearRect(0,0,W,H);

    // 背景
    ctx.fillStyle = '#0e0e22';
    ctx.beginPath(); ctx.arc(cx,cy,R,0,Math.PI*2); ctx.fill();

    // 外圈
    ctx.strokeStyle = 'rgba(201,169,110,0.3)';
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.arc(cx,cy,R,0,Math.PI*2); ctx.stroke();
    ctx.beginPath(); ctx.arc(cx,cy,R*0.85,0,Math.PI*2); ctx.stroke();
    ctx.beginPath(); ctx.arc(cx,cy,R*0.4,0,Math.PI*2); ctx.stroke();

    // 十二宫分线
    const signs = ['♈','♉','♊','♋','♌','♍','♎','♏','♐','♑','♒','♓'];
    const signNames = ['白羊','金牛','双子','巨蟹','狮子','处女','天秤','天蝎','射手','摩羯','水瓶','双鱼'];
    for(let i=0; i<12; i++){
        const angle = (i * 30 - 90) * Math.PI / 180;
        ctx.strokeStyle = 'rgba(201,169,110,0.15)';
        ctx.beginPath();
        ctx.moveTo(cx + R*0.4*Math.cos(angle), cy + R*0.4*Math.sin(angle));
        ctx.lineTo(cx + R*Math.cos(angle), cy + R*Math.sin(angle));
        ctx.stroke();

        // 星座名
        const labelR = R * 0.92;
        const lx = cx + labelR * Math.cos(angle + 15*Math.PI/180);
        const ly = cy + labelR * Math.sin(angle + 15*Math.PI/180);
        ctx.fillStyle = 'rgba(201,169,110,0.6)';
        ctx.font = '10px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(signNames[i], lx, ly);
    }

    // 行星标注
    const details = astro.planetary_details || {};
    const planetSymbols = {'太阳':'☉','月亮':'☽','水星':'☿','金星':'♀','火星':'♂','木星':'♃','土星':'♄','天王':'♅','海王':'♆','冥王':'♇'};
    const planetColors = {'太阳':'#ffcc00','月亮':'#cccccc','水星':'#88ccff','金星':'#ff88aa','火星':'#ff4444','木星':'#44aaff','土星':'#ccaa44','天王':'#44dddd','海王':'#4466ff','冥王':'#884488'};

    let placedPlanets = [];
    Object.entries(details).forEach(([name, info])=>{
        if(typeof info === 'string') return;
        const sign = info.sign || info.zodiac || '';
        const deg = parseFloat(info.degree || info.deg || 0);
        const signIdx = signNames.indexOf(sign);
        if(signIdx < 0) return;
        const angle = ((signIdx * 30 + deg) - 90) * Math.PI / 180;
        const pr = R * 0.65;

        // 避免重叠
        let offset = 0;
        placedPlanets.forEach(pp=>{
            if(Math.abs(pp.angle - angle) < 0.15) offset += 12;
        });

        const px = cx + pr * Math.cos(angle);
        const py = cy + pr * Math.sin(angle) + offset;

        ctx.fillStyle = planetColors[name] || '#fff';
        ctx.font = 'bold 12px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(planetSymbols[name] || name[0], px, py + 4);

        placedPlanets.push({angle});
    });

    // 图例
    const legend = $('#astroLegend');
    let legendHtml = '';
    legendHtml += `<div class="astro-legend-item"><span class="astro-legend-dot" style="background:var(--gold);"></span><span>太阳: ${esc(astro.sun_sign||'')}</span></div>`;
    legendHtml += `<div class="astro-legend-item"><span class="astro-legend-dot" style="background:#ccc;"></span><span>月亮: ${esc(astro.moon_sign||'')}</span></div>`;
    legendHtml += `<div class="astro-legend-item"><span class="astro-legend-dot" style="background:var(--blue);"></span><span>上升: ${esc(astro.ascendant_sign||astro.ascendant||'')}</span></div>`;
    if(astro.mc_sign) legendHtml += `<div class="astro-legend-item"><span class="astro-legend-dot" style="background:var(--purple);"></span><span>天顶: ${esc(astro.mc_sign)}</span></div>`;
    legend.innerHTML = legendHtml;
}

/* ===== 姓名学渲染 ===== */
function renderXingming(xm){
    // 评分
    const scoreDiv = $('#xmScore');
    const score = xm.total_score || xm.score || 0;
    scoreDiv.innerHTML = `<div class="xm-score-num">${score}</div><div class="xm-score-label">姓名评分</div>`;

    // 五格
    const wugeDiv = $('#xmWuge');
    const wuge = xm.wu_ge || xm.wuge || {};
    const geNames = ['天格','人格','地格','外格','总格'];
    const geKeys = ['tiange','renge','dige','waige','zongge'];
    let wugeHtml = '<div class="xm-wuge-grid">';
    geNames.forEach((name,i)=>{
        const ge = wuge[geKeys[i]] || wuge[name] || {};
        const num = ge.score || ge.num || ge.number || '';
        const wx = ge.wuxing || ge.element || '';
        const ji = ge.ji_xiong || ge.fortune || '';
        const jiCls = ji.includes('吉')?'ji-ok':'xiong';
        wugeHtml += `<div class="xm-wuge-item">
            <div class="xm-wuge-label">${name}</div>
            <div class="xm-wuge-num ${WX_CLASS[wx]}" style="color:${WX_COLOR[wx]||'var(--text-bright)'}">${num}</div>
            <div class="xm-wuge-wx">${esc(wx)}</div>
            <div class="xm-wuge-ji ${jiCls}">${esc(ji)}</div>
        </div>`;
    });
    wugeHtml += '</div>';
    wugeDiv.innerHTML = wugeHtml;

    // 三才
    const sancaiDiv = $('#xmSancai');
    const sancai = xm.san_cai || xm.sancai || {};
    const sancaiWx = sancai.wuxing || sancai.element || '';
    const sancaiResult = sancai.result || sancai.ji_xiong || '';
    const sancaiDesc = sancai.description || sancai.analysis || '';
    sancaiDiv.innerHTML = `<div class="sancai-card">
        <div class="sancai-wuxing">${esc(sancaiWx)}</div>
        <div class="sancai-result">${esc(sancaiResult)}</div>
        <div class="sancai-desc">${esc(sancaiDesc)}</div>
    </div>`;

    // 数理剖析
    const shuliDiv = $('#xmShuli');
    const shuli = xm.shu_li || xm.shuli || xm.ge_analysis || {};
    let shuliHtml = '';
    geNames.forEach((name,i)=>{
        const ge = shuli[geKeys[i]] || shuli[name] || wuge[geKeys[i]] || wuge[name] || {};
        const num = ge.score || ge.num || ge.number || '';
        const ji = ge.ji_xiong || ge.fortune || '';
        const desc = ge.analysis || ge.description || ge.detail || '';
        if(!num && !desc) return;
        const jiCls = ji.includes('吉')?'ji':'xiong';
        shuliHtml += `<div class="shuli-card">
            <div class="shuli-card-title">${name} <span class="shuli-card-num">(${num})</span>${ji?`<span class="shuli-card-ji ${jiCls}">${esc(ji)}</span>`:''}</div>
            <div class="shuli-card-body">${esc(desc)}</div>
        </div>`;
    });
    shuliDiv.innerHTML = shuliHtml || '<div style="padding:10px 14px;color:var(--text-muted);">数理数据不可用</div>';
}

/* ===== 启动 ===== */
document.addEventListener('DOMContentLoaded', init);
})();
