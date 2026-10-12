(() => {
  const $ = s => document.querySelector(s), stage = $('#stage'), err = $('#error');
  const demos = [2,3,4,5,6];
  let demo=2, step=0, budget=15, manual=false, revealed=false, report=null, epoch=null, timer=null, renderSeq=0;
  const cache={};
  let budgetSnapshot=null;
  const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const json=x=>JSON.stringify(x,null,2);
  const text=x=>typeof x==='string'?x:json(x);
  const tag=s=>`<span class="tag ${esc(s)}">${({fact:'事实',inference:'推断',missing:'缺失',conflict:'冲突'})[s]||esc(s)}</span>`;
  const card=(title,body,cls='')=>`<article class="card ${cls}"><strong>${title}</strong><div>${body}</div></article>`;
  const details=(title,body)=>`<details><summary>${title}</summary>${body}</details>`;
  const pre=x=>`<pre>${esc(json(x))}</pre>`;
  async function api(url,opts){const r=await fetch(url,opts);if(!r.ok)throw Error(`${r.status} ${await r.text()}`);return r.json()}
  async function data(key,url){if(!cache[key]){const pending=api(url);cache[key]=pending;try{return await pending}catch(e){if(cache[key]===pending)delete cache[key];throw e}}return cache[key]}
  function showError(e){err.hidden=false;err.innerHTML=`<strong>载入失败，可重试。</strong> ${esc(e.message)} <button id="retry">重试</button> <button id="err-reset">重置</button>`;$('#retry').onclick=render;$('#err-reset').onclick=reset;}
  function clearError(){err.hidden=true;err.textContent=''}
  function nav(){ $('#demo-nav').innerHTML=demos.map(n=>`<button type="button" data-demo="${n}" class="${demo===n?'active':''}">Demo ${n}</button>`).join('');$('#demo-nav').querySelectorAll('button').forEach(b=>b.onclick=()=>{demo=+b.dataset.demo;step=0;render()}); }
  function shell(title,total){window.scrollTo(0,0);$('#lesson-title').textContent=title;$('#step-label').textContent=`阶段 ${step+1} / ${total}`;$('#prev').disabled=step===0;$('#next').disabled=step===total-1;$('#next').textContent='下一步 →';$('#prev').onclick=()=>{step--;render()};$('#next').onclick=()=>{step++;render()};nav()}
  const rowsTable=(heads,rows)=>`<div class="table-wrap"><table><thead><tr>${heads.map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${r.map(v=>`<td>${v??''}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  function stageHtml(content){stage.innerHTML=`<div class="step-content">${content}</div>`}
  async function render(){const seq=++renderSeq, target=demo;clearError();try{if(target===2)await d2(seq);if(target===3)await d3(seq);if(target===4)await d4(seq);if(target===5)await d5(seq);if(target===6)await d6(seq)}catch(e){if(seq===renderSeq)showError(e)}}
  function buildDemo2Prompt(prd, withRisks=false) {
    const paragraphs=(prd.paragraphs||[]).map(p=>p.source_id+'：'+p.text).join('\n');
    const openQuestions=(prd.open_questions||[]).map(q=>q.question_id+'：'+q.text).join('\n');
    const base=[
      '请根据下面的商城售后需求设计10条有代表性的业务测试用例，覆盖正常流程、异常流程和边界条件。',
      '每条包含：编号、测试场景、前置条件、操作步骤、预期结果。请用表格输出。',
      '文档：《'+prd.title+'》（V'+prd.version+'）',
      '业务需求：\n'+paragraphs
    ];
    if(!withRisks)return base.join('\n\n');
    return [
      ...base.slice(0,2),
      '对每条测试预期标注具体依据（P10～P60）；将明确事实、合理推断和规则待确认分开。遇到不能由需求与待确认事项确定的结果，写明“待确认”，不要补造业务规定。Q10～Q50是尚未确定的问题，不能当作正式规则。请在表格最后增加“需求依据／证据状态”列，并在表格后列出需要业务确认的规则。',
      ...base.slice(2),
      '待确认事项：\n'+openQuestions
    ].join('\n\n');
  }
  async function d2(seq){const d=await data('d2','/api/lesson/2');if(seq!==renderSeq||demo!==2)return;const title=d.prd.title; shell(`Demo 2｜${title}`,3);const cases=d.direct_generation.result.sample_cases||[];
    if(step===0){
      const directPrompt=buildDemo2Prompt(d.prd,false);
      const riskPrompt=buildDemo2Prompt(d.prd,true);
      stageHtml(`<section class="panel"><h2>需求输入 · 两轮 AI 对照实验</h2><p class="lead">同一份 V1.0 需求，比较直接生成与增加风险约束后的结果。原来的 ${cases.length} 条示例用例仍是冻结的预置演示结果，不是实时 AI 生成。</p><div class="toolbar"><button id="demo2-copy-direct" class="primary" type="button">① 直接生成测试用例</button><button id="demo2-copy-risk" type="button">② 带风险约束生成</button></div><p class="muted small">① 仅包含 P10～P60 需求正文；② 在相同任务上增加 Q10～Q50、预期依据和待确认标记。建议同一模型、新建两轮独立对话进行比较。</p><p id="demo2-copy-status" class="muted small" role="status">先点击①，复制后粘贴到 AI 对话框。</p><details id="demo2-prompt-details"><summary>预览当前提示词 / 手动复制</summary><p class="muted small" id="demo2-prompt-label">当前：① 直接生成（仅 P10～P60）</p><textarea id="demo2-prompt-preview" readonly rows="14" style="width:100%;min-height:260px;resize:vertical;background:#111c2b;color:#f5f7fb;border:1px solid #52627a;border-radius:7px;padding:12px;font:16px/1.5 monospace;">${esc(directPrompt)}</textarea></details><div class="grid">${cases.slice(0,6).map(c=>card(`${c.case_id} · ${c.title}`,`<span class="tag badge">${c.priority}</span>${c.expected}`)).join('')}</div>${details('查看全部用例与需求原文',rowsTable(['ID','优先级','前置条件','步骤','预期','来源'],cases.map(c=>[c.case_id,c.priority,esc((c.preconditions||[]).join('；')),esc((c.steps||[]).join(' → ')),esc(c.expected),esc((c.source_ids||[]).join(', '))]))+details('PRD V1.0',pre(d.prd)))}</section>`);
      const directButton=stage.querySelector('#demo2-copy-direct');
      const riskButton=stage.querySelector('#demo2-copy-risk');
      const preview=stage.querySelector('#demo2-prompt-preview');
      const label=stage.querySelector('#demo2-prompt-label');
      const status=stage.querySelector('#demo2-copy-status');
      const detail=stage.querySelector('#demo2-prompt-details');
      const copyPrompt=async(withRisks)=>{
        const prompt=withRisks?riskPrompt:directPrompt;
        preview.value=prompt;
        label.textContent=withRisks?'当前：② 带风险约束（P10～P60 + Q10～Q50）':'当前：① 直接生成（仅 P10～P60）';
        directButton.classList.toggle('primary',!withRisks);
        riskButton.classList.toggle('primary',withRisks);
        try{
          if(navigator.clipboard&&window.isSecureContext)await navigator.clipboard.writeText(prompt);
          else{
            detail.open=true;preview.focus();preview.select();
            if(!document.execCommand('copy'))throw new Error('Clipboard unavailable');
          }
          status.textContent=withRisks?'② 已复制：包含待确认事项与预期溯源要求。':'① 已复制：仅包含原始需求正文。';
        }catch(error){
          detail.open=true;preview.focus();preview.select();
          status.textContent='自动复制受阻；已选中全文，请按 ⌘C / Ctrl+C。';
        }
      };
      directButton.onclick=()=>copyPrompt(false);
      riskButton.onclick=()=>copyPrompt(true);
    }
    if(step===1){const axes=d.structured_analysis, names={roles:'角色',inputs:'输入',flow:'业务流程',states:'状态',rules:'业务规则',external_dependencies:'外部依赖',risks:'风险',questions:'待确认问题'};const cards=Object.entries(axes).map(([k,v])=>{let arr=Array.isArray(v)?v:[];const body=arr.slice(0,4).map(x=>{if(typeof x==='string')return esc(x);const ev=x.evidence_status?tag(x.evidence_status):'';return `${ev} ${esc(x.name||x.statement||x.question||x.rule_id||text(x))}`}).join('<br>')||esc(text(v));return card(names[k]||k,body)});stageHtml(`<section class="panel"><h2>八维结构化分析 · 证据分级</h2><p>绿色事实 · 黄色推断 · 红色缺失或冲突。流程与状态是需求整理项，不单独标成证据结论。</p><div class="grid">${cards.join('')}</div>${details('查看完整分析资产',pre(axes))}</section>`)}
    if(step===2){let m=d.scenario_map, ruleById=Object.fromEntries(d.rules.map(r=>[r.rule_id,r]));let sceneEvidence=s=>{const rr=(s.rule_ids||[]).map(id=>ruleById[id]).filter(Boolean), statuses=rr.map(r=>r.evidence_status);if(statuses.includes('conflict'))return 'conflict';if(statuses.includes('missing'))return 'missing';if(statuses.includes('inference')||s.validity==='needs_confirmation')return 'inference';return 'fact'};let h=`<div class="scene-map"><div class="map-head">场景类型</div>${m.columns.map(c=>`<div class="map-head">${esc(c)}</div>`).join('')}`;m.rows.forEach(r=>{h+=`<div class="map-row">${esc(r)}</div>`+m.columns.map(c=>{let ids=m.cells[c][r]||[];return `<div>${ids.length?ids.map(id=>{let s=d.scenarios.find(x=>x.scenario_id===id);return `<details><summary>${esc(id)} · ${esc(s?.title||'场景')}</summary>${esc(s?.description||'场景定义见候选资产')}<br>${tag(sceneEvidence(s))}<br>规则：${esc((s?.rule_ids||[]).join(', '))}<br>条件：${esc(text(s?.conditions||{}))}<br>来源：${esc((s?.rule_ids||[]).flatMap(id=>ruleById[id]?.source_ids||[]).join(', ')||'未标注')}</details>`}).join(''):'<span class="empty">—</span>'}</div>`}).join('')});h+='</div>';stageHtml(`<section class="panel"><h2>V1.0 场景地图</h2><p>5 行 × 6 列。点击场景 ID 查看场景细节。</p><div class="table-wrap">${h}</div>${details('图例与全部场景',`正常 · 分支 · 异常 · 边界 · 外部依赖${pre(d.scenarios)}`)}<p class="teaching">教学观点：需求理解不足时，过早生成用例容易把假设写成预期。</p></section>`)}
  }
  // ───────── AI 实验面板（Demo 3～6 共用）：复制完整提示词 · 预览输入 · 粘贴 AI 输出 · 服务端解析比较 ─────────
  const lab={inputs:{},prompts:{}};
  const labReset=()=>{lab.inputs={};lab.prompts={}};
  const labGet=k=>lab.inputs[k]||'';
  const post=(url,body)=>api(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const vtag=(cls,t)=>`<span class="tag ${cls}">${esc(t)}</span>`;
  const idList=(ids,info,empty='无')=>ids&&ids.length?`<ul class="idlist">${ids.map(id=>{const s=info&&info[id];return `<li><b>${esc(id)}</b>${s?` ${esc(s.title)} <span class="muted">风险${s.risk_score}·成本${s.cost}</span>`:''}</li>`}).join('')}</ul>`:`<p class="muted small">${empty}</p>`;
  const noteList=n=>n&&n.length?`<ul class="notes">${n.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:'';
  const labPanel=(id,title,lead,button)=>`<section class="lab" data-lab="${id}"><h3>AI 实验 · ${title}</h3><p class="muted small">${lead}</p><div class="toolbar"><button class="primary" type="button" data-lab-copy disabled>${button}</button><span class="small muted" data-lab-status role="status">正在生成提示词…</span></div><details data-lab-details><summary>预览输入内容 / 手动复制</summary><div class="lab-meta small" data-lab-meta></div><textarea class="lab-text" data-lab-preview readonly rows="12" aria-label="完整提示词" spellcheck="false"></textarea></details></section>`;
  function labWire(id,request){
    const root=stage.querySelector(`[data-lab="${id}"]`);if(!root)return {refresh(){}};
    const btn=root.querySelector('[data-lab-copy]'),status=root.querySelector('[data-lab-status]'),ta=root.querySelector('[data-lab-preview]'),det=root.querySelector('[data-lab-details]'),meta=root.querySelector('[data-lab-meta]');
    let current='',seq=0;
    async function refresh(){
      const my=++seq,req=request(),key=JSON.stringify(req);
      btn.disabled=true;status.textContent='正在生成提示词…';
      try{
        const p=lab.prompts[key]||(lab.prompts[key]=await post('/api/ai-lab/prompt',req));
        if(my!==seq||!root.isConnected)return;
        current=p.prompt;ta.value=p.prompt;
        meta.innerHTML=`<p>${esc(p.title)} · 共 ${p.chars} 字</p><p><b>包含：</b>${p.includes.map(esc).join('；')}</p><p><b>刻意不含：</b>${p.withholds.map(esc).join('；')}</p>`;
        btn.disabled=false;status.textContent='提示词已就绪：点击按钮复制，粘贴到全新的 AI 对话框（换模型时复制同一份）。';
      }catch(e){delete lab.prompts[key];if(my===seq&&root.isConnected)status.textContent='提示词生成失败：'+e.message+'。请切换阶段后重试。'}
    }
    btn.onclick=async()=>{
      let ok=false;
      if(navigator.clipboard&&window.isSecureContext){try{await navigator.clipboard.writeText(current);ok=true}catch(e){}}
      if(!ok){det.open=true;ta.focus();ta.select();try{ok=document.execCommand('copy')}catch(e){}}
      status.textContent=ok?`已复制 ${current.length} 字。请在全新的 AI 对话框中粘贴。`:'自动复制受阻：已展开并选中全文，请按 ⌘C / Ctrl+C 手动复制。';
    };
    refresh();return {refresh};
  }
  const labPaste=(id,label,placeholder,rows=7)=>`<div class="lab-paste"><label for="paste-${id}"><strong>${label}</strong></label><textarea id="paste-${id}" class="lab-text" data-lab-paste="${id}" rows="${rows}" placeholder="${esc(placeholder)}" spellcheck="false">${esc(labGet(id))}</textarea><div class="toolbar"><button type="button" data-lab-clear="${id}">清空</button><span class="small muted">仅保存在本页内存；刷新或全局重置后清空。解析不出来也不影响继续课堂。</span></div></div>`;
  const labInput=(id,label,placeholder)=>`<label class="lab-label small muted">${label}<input class="lab-input" data-lab-paste="${id}" value="${esc(labGet(id))}" placeholder="${esc(placeholder)}" maxlength="80"></label>`;
  function labBind(id,onChange){
    const el=stage.querySelector(`[data-lab-paste="${id}"]`);if(!el)return;
    let t=null;
    el.addEventListener('input',()=>{lab.inputs[id]=el.value;clearTimeout(t);t=setTimeout(()=>onChange(el.value),250)});
    const clear=stage.querySelector(`[data-lab-clear="${id}"]`);
    if(clear)clear.onclick=()=>{el.value='';lab.inputs[id]='';onChange('')};
    onChange(el.value);
  }
  function labOut(box){let seq=0;return async fn=>{const my=++seq;try{const html=await fn();if(my===seq&&box&&box.isConnected)box.innerHTML=html}catch(e){if(my===seq&&box&&box.isConnected)box.innerHTML=`<p class="fail">对照暂不可用（${esc(e.message)}），不影响继续课堂。</p>`}}}
  const analyze=body=>post('/api/ai-lab/analyze',body);
  const verdictTag=v=>v?({SUPPORTED:vtag('fact','材料足以证明预期'),UNSUPPORTED:vtag('inference','材料不足以证明'),CONTRADICTED:vtag('missing','材料证明预期有误')})[v]||vtag('badge',v):vtag('badge','未给出');
  const markerBlock=m=>`<div class="grid"><div class="card"><strong>预期是否有依据</strong>${verdictTag(m.expectations)}</div><div class="card"><strong>经典订单退 B（AI 给出）</strong>${esc(m.classic_b_refund||'未给出')}</div><div class="card"><strong>AI 声称依据的材料</strong>${esc(m.evidence_used||'未给出')}</div></div>`;
  const PASTE3='粘贴 AI 的完整回答（需包含最后一行 FINAL_SELECTION: SC01, SC02, …）';
  function d3ParseHtml(r,info){
    if(!r.parsed)return `<div class="lab-result"><p class="fail">未解析到合法场景ID。</p>${noteList(r.notes)}</div>`;
    return `<div class="lab-result"><div class="grid">${card('AI 选择',`${r.ai.count} / ${r.budget} 条${r.ai.over_budget?' '+vtag('missing','超预算'):''}`)}${card('风险分合计 / 执行成本合计',`${r.ai.risk_total} / ${r.ai.cost_total}`)}${card('解析来源',r.source==='FINAL_SELECTION'?'FINAL_SELECTION 行':'全文提取（请核对）')}</div>${noteList(r.notes)}${details(`AI 选择的 ${r.ai.count} 条场景`,idList(r.ai.ids,info))}</div>`;
  }
  function d3CompareHtml(r,info){
    if(!r.parsed)return '<p class="muted">尚未粘贴 AI 结果（或未解析到合法场景）。在上方粘贴后，这里显示共同入选、仅 AI 入选、仅算法入选。</p>';
    const c=r.compare_baseline,total=(k)=>`<td>${r.ai[k]}</td><td>${r.algorithm[k]}</td>`;
    return `<div class="grid"><div class="card cmp-common"><strong>共同入选 ${c.common.length} 条</strong>${idList(c.common,info)}</div><div class="card cmp-ai"><strong>仅 AI 入选 ${c.ai_only.length} 条</strong>${idList(c.ai_only,info,'无：AI 的名单是算法名单的子集')}</div><div class="card cmp-algo"><strong>仅算法入选 ${c.algorithm_only.length} 条</strong>${idList(c.algorithm_only,info,'无：算法名单已全部被 AI 选中')}</div></div><div class="table-wrap"><table><thead><tr><th>指标</th><th>AI</th><th>算法基线</th></tr></thead><tbody><tr><td>入选条数</td>${total('count')}</tr><tr><td>风险分合计</td>${total('risk_total')}</tr><tr><td>执行成本合计</td>${total('cost_total')}</tr><tr><td>未被任何入选场景引用的规则</td><td>${r.uncovered.ai.length} 项</td><td>${r.uncovered.baseline.length} 项</td></tr></tbody></table></div>${noteList(r.notes)}<p class="teaching">算法排序是可复算的基准，不是唯一正确答案；分歧处要回到风险与业务依据上判断。</p>`;
  }
  function d3ThreeHtml(r,info,manualOn){
    const add=r.final.manual_addition;
    const ai=r.parsed?r.ai:null;
    const aiHas36=r.parsed&&r.ai.ids.includes('SC36');
    const rows=[['入选条数',ai?ai.count:'—',r.algorithm.count,r.final.count],['风险分合计',ai?ai.risk_total:'—',r.algorithm.risk_total,r.final.risk_total],['执行成本合计',ai?ai.cost_total:'—',r.algorithm.cost_total,r.final.cost_total],['含 SC36',ai?(aiHas36?'是':'否'):'—','否',r.final.ids.includes('SC36')?'是':'否'],['与 AI 重合',ai?'—':'—',ai?r.compare_baseline.common.length:'—',ai?r.compare_final.common.length:'—'],['未覆盖规则',ai?r.uncovered.ai.length+' 项':'—',r.uncovered.baseline.length+' 项',r.uncovered.final.length+' 项']];
    return `<div class="table-wrap"><table><thead><tr><th>指标</th><th>AI 建议</th><th>算法基线</th><th>算法 + 人工补漏${manualOn?'':'（尚未补漏）'}</th></tr></thead><tbody>${rows.map(x=>`<tr><td>${x[0]}</td><td>${x[1]}</td><td>${x[2]}</td><td>${x[3]}</td></tr>`).join('')}</tbody></table></div>${add?`<p class="muted">人工补漏：SC36 替换 ${esc(add.replaced_id||'末位场景')}；预算保持 ${r.budget} 条，最终 ${r.final.count} 条，不超限。</p>`:''}${r.parsed&&aiHas36?'<p class="muted">AI 已自行选入 SC36：说明这个多维高风险组合并非只有人才看得到——但依据仍要由人确认。</p>':''}`;
  }
  function d3CoverageHtml(r,manualOn){
    const showAi=r.parsed;
    const cell=ids=>ids.length?`<span class="pass">✓ ${ids.length}</span><br><span class="small muted">${esc(ids.join('、'))}</span>`:'<span class="fail">未引用</span>';
    const weak=r.coverage.filter(c=>(c.final.length||c.ai.length)&&['missing','inference'].includes(c.evidence_status));
    return `<div class="table-wrap"><table><thead><tr><th>规则 / 证据状态</th><th>算法基线</th><th>算法 + 人工${manualOn?'':'（未补漏）'}</th>${showAi?'<th>AI 建议</th>':''}</tr></thead><tbody>${r.coverage.map(c=>`<tr><td>${esc(c.rule_id)}<br>${tag(c.evidence_status)}<br><span class="small">${esc(c.statement)}</span></td><td>${cell(c.baseline)}</td><td>${cell(c.final)}</td>${showAi?`<td>${cell(c.ai)}</td>`:''}</tr>`).join('')}</tbody></table></div><div class="grid">${card('算法基线未引用的规则',esc(r.uncovered.baseline.join('、')||'无'))}${card('补漏后未引用的规则',esc(r.uncovered.final.join('、')||'无'))}${showAi?card('AI 方案未引用的规则',esc(r.uncovered.ai.join('、')||'无')):''}</div><div class="formula">“被场景引用”≠“业务规则已确认”：当前被引用的规则中，仍有 ${weak.length} 条证据状态是缺失或推断（${esc(weak.map(c=>c.rule_id).join('、')||'无')}）。</div>`;
  }
  async function d3(seq){
    const load=(b,m)=>data(`d3-${b}-${m}`,`/api/lesson/3?budget=${b}&manual=${m}`);
    const auto=await load(budget,false),fin=manual?await load(budget,true):auto;
    if(seq!==renderSeq||demo!==3)return;
    shell('Demo 3｜AI、算法与人工：有限预算下选场景',4);
    const aiKey=`d3-ai-${budget}`,info={};
    [...auto.scenarios,...auto.excluded_scenarios,...fin.scenarios,...fin.excluded_scenarios].forEach(s=>info[s.scenario_id]=s);
    const bar=`<div class="toolbar">预算：${[10,15,20].map(n=>`<button data-budget="${n}" class="${budget===n?'selected':''}" aria-pressed="${budget===n}">${n} 条</button>`).join('')}<span class="muted small">AI 提示词与算法结果都随预算变化</span></div>`;
    const bindBudget=()=>stage.querySelectorAll('[data-budget]').forEach(b=>b.onclick=()=>{const next=+b.dataset.budget;if(next===budget)return;budgetSnapshot={budget,ids:[...auto.selected_ids]};budget=next;render()});
    const analyzeBody=text=>({kind:'d3_select',budget,manual,text});
    if(step===0){
      stageHtml(`<section class="panel"><h2>阶段 1 · 让 AI 在预算内选场景</h2><p class="lead">同一批 ${auto.candidate_count} 条候选场景、同一预算：先听 AI 的建议，下一步再看可复算的算法基准。</p>${bar}<div class="grid">${card('候选场景',`${auto.candidate_count} 条`)}${card('等价合并后',`${auto.merged_candidate_count} 条`)}${card('理论组合',`${auto.theoretical_product?.count||432} 种`)}</div>${labPanel('d3','场景选择','提示词已带上全部候选场景的风险分、执行成本、关联规则和证据状态，以及当前预算；AI 无需读取任何文件。',`复制 AI 场景选择提示词（预算 ${budget} 条）`)}${labPaste(aiKey,PASTE3,'FINAL_SELECTION: SC01, SC19, …')}<div id="d3-parse"></div>${details('查看候选池、等价合并与完整场景数据',pre({merge_groups:auto.merge_groups,all_scenarios:auto.all_scenarios,dimensions:auto.dimensions}))}<p><a href="/api/practice/3" download>下载 Demo 3 学员练习材料</a></p></section>`);
      bindBudget();labWire('d3',()=>({kind:'d3_select',budget}));
      const out=labOut($('#d3-parse'));
      labBind(aiKey,text=>out(async()=>text.trim()?d3ParseHtml(await analyze(analyzeBody(text)),info):'<p class="muted small">粘贴后在此显示解析出的合法场景ID与预算检查。</p>'));
    }
    if(step===1){
      const ids=auto.selected_ids,previous=budgetSnapshot&&budgetSnapshot.budget!==budget?budgetSnapshot:null;
      const added=previous?ids.filter(id=>!previous.ids.includes(id)):[],removed=previous?previous.ids.filter(id=>!ids.includes(id)):[];
      const delta=previous?`<div class="formula">预算 ${previous.budget} → ${budget}：新增 ${added.length} 条 · 移除 ${removed.length} 条</div><p class="muted">新入选：${esc(added.join('、')||'无')}；移出：${esc(removed.join('、')||'无')}</p>`:'<p class="muted">切换预算 10、15、20，观察算法名单随预算的变化。</p>';
      const rows=auto.scenarios.map((s,i)=>[String(i+1),esc(s.scenario_id),esc(s.title),esc(s.risk_score),esc(s.cost),esc(s.selection_reason)]);
      stageHtml(`<section class="panel"><h2>阶段 2 · 算法基准与 AI 对照</h2><p class="lead">算法按“影响 × 概率 × 难发现度”排序并保护 SC01/SC19，结果可复算——它是基准，不是标准答案。</p>${bar}<div class="grid">${card('算法入选',`${auto.selected_count} / ${budget} 条`)}${card('算法未入选',`${auto.excluded_scenarios.length} 条`)}${card('未引用规则',`${auto.post_uncovered.length} 项`)}</div>${delta}<h3>算法基线入选场景（不含 SC36）</h3>${rowsTable(['序号','场景 ID','测试场景','风险分','执行成本','入选依据'],rows)}<p class="muted small">风险分 = 影响度 × 发生概率 × 难发现度；执行成本独立展示。SC36 保留给“人工补漏”阶段。</p><h3>AI × 算法</h3>${labPaste(aiKey,PASTE3,'FINAL_SELECTION: SC01, SC19, …',5)}<div id="d3-compare"></div></section>`);
      bindBudget();
      const out=labOut($('#d3-compare'));
      labBind(aiKey,text=>out(async()=>d3CompareHtml(await analyze(analyzeBody(text)),info)));
    }
    if(step===2){
      stageHtml(`<section class="panel"><h2>阶段 3 · 人工补漏：判断由人负责</h2><p>候选 SC36 同时涉及金卡、混合支付、优惠失效和渠道超时，各维度规则仍待确认；它风险高但依据弱，需要人来决定是否占用名额。</p><button id="manual" class="${manual?'selected':''}">${manual?'已纳入 SC36（点击撤销）':'人工补回 SC36'}</button>${fin.manual_addition?`<div class="formula">SC36 替换 ${esc(fin.manual_addition.replaced_id||'末位场景')}</div><p>${esc(fin.manual_addition.replaced_reason||'保持预算上限')}</p>`:'<p class="muted">尚未补漏：算法基线仍是纯风险分排序的结果。</p>'}<h3>三方对照：AI / 算法 / 算法 + 人工</h3><div id="d3-three"></div>${labPaste(aiKey,PASTE3,'FINAL_SELECTION: SC01, SC19, …',4)}${details('预算内完整选择结果',pre(fin.scenarios))}<p class="teaching">AI 给出建议，算法提供可复算的基准，人负责最终判断：为什么取舍、替换谁、理由是什么。</p></section>`);
      $('#manual').onclick=()=>{manual=!manual;render()};
      const out=labOut($('#d3-three'));
      labBind(aiKey,text=>out(async()=>d3ThreeHtml(await analyze(analyzeBody(text)),info,manual)));
    }
    if(step===3){
      stageHtml(`<section class="panel"><h2>阶段 4 · 覆盖验证：规则被引用 ≠ 规则已确认</h2><p>“未引用”表示没有入选场景关联该规则；规则本身的证据等级（事实 / 推断 / 缺失）独立保留。</p><div id="d3-cover"></div>${labPaste(aiKey,PASTE3,'FINAL_SELECTION: SC01, SC19, …',4)}${details('算法最终选择的逐场景规则覆盖矩阵',`<div class="table-wrap"><table class="matrix"><thead><tr><th>规则 / 证据</th>${fin.selected_ids.map(id=>`<th>${esc(id)}</th>`).join('')}</tr></thead><tbody>${fin.coverage.map(r=>`<tr><td>${esc(r.rule_id)}<br>${tag(r.evidence_status)}<br>${esc(r.statement)}</td>${fin.selected_ids.map(id=>`<td class="matrix-cell">${r.covered_by.includes(id)?'<span class="pass">✓</span>':'—'}</td>`).join('')}</tr>`).join('')}</tbody></table></div>${card('人工补漏前未覆盖',esc(fin.pre_manual_uncovered.join(', ')||'无'))}${card('当前未覆盖',esc(fin.post_uncovered.join(', ')||'无'))}`)}${details('候选 / 排除 / 覆盖依据',pre({excluded:fin.excluded_scenarios,coverage_note:fin.coverage_note,coverage_matrix:fin.coverage_matrix}))}<p class="teaching">教学观点：预算裁剪可展开、人工补漏可追溯；AI 的建议、算法的基准和人的判断要放在同一张覆盖表里对照。</p></section>`);
      const out=labOut($('#d3-cover'));
      labBind(aiKey,text=>out(async()=>d3CoverageHtml(await analyze(analyzeBody(text)),manual)));
    }
  }
  function d4Round1Html(r){
    if(!r.parsed)return `<div class="lab-result"><p class="muted">没有识别到 EXPECTATIONS / CLASSIC_B_REFUND 标记行，请直接阅读 AI 原文。</p>${noteList(r.notes)}</div>`;
    const cmp=r.vs_test_expected==='same'?'与测试预期 85.13 相同':r.vs_test_expected==='different'?'与测试预期 85.13 不同':'';
    return `<div class="lab-result"><h4>AI 的评价标记（AI 的看法，不改变本地事实）</h4>${markerBlock(r.markers)}${cmp?`<p class="muted">经典订单退 B：${cmp}。</p>`:''}<p class="muted small">无论 AI 怎么说，20/20 PASS 只证明“实现符合测试预期”。财务规范揭示后再用它复算一次，看结论是否需要修正。</p></div>`;
  }
  function d4Round2Html(r){
    const base=r.parsed?`<h4>第二次评价标记</h4>${markerBlock(r.markers)}<div class="grid">${card('AI 退 B 金额是否正确',r.classic_b_correct===null?'未给出':r.classic_b_correct?'正确（'+esc(r.correct_classic_b)+'）':'与财务规范不符（本地计算 '+esc(r.correct_classic_b)+'）')}${card('结论是否修正',esc(r.markers.conclusion_revised||'未给出'))}${card('AI 复算与本地计算一致',r.recompute_found?`${r.recompute_match} / ${r.recompute_found} 条`:'未解析到复算区块')}</div>`:'<p class="muted">没有识别到标记行，请直接阅读 AI 原文，并对照下面的本地参考值。</p>';
    const rows=r.reference.map(x=>[x.case_id,esc(x.title),esc(x.test_expected),`<b>${esc(x.finance_refund)}</b>`,x.ai===null?'—':esc(x.ai),x.ai===null?'':x.match?'<span class="pass">一致</span>':'<span class="fail">不一致</span>',x.expectation_wrong?'<span class="fail">测试预期与规范不符</span>':'<span class="pass">相符</span>']);
    return `<div class="lab-result">${base}${noteList(r.notes)}<p class="muted">按财务规范本地重算：20 条测试预期中有 <b>${r.wrong_expectations}</b> 条与规范不符——但它们全部“PASS”。AI 复算也要和本地计算核对，不能整体照单全收。</p>${details('逐条对照：测试预期 · 财务规范（本地计算）· AI 复算',rowsTable(['用例','标题','测试预期','财务规范（本地）','AI 复算','AI 是否一致','预期是否正确'],rows))}</div>`;
  }
  async function d4(seq){
    const d=await data('d4','/api/lesson/4');if(seq!==renderSeq||demo!==4)return;
    shell('Demo 4｜真实执行 · AI 评价 · 财务规范揭示',3);
    const run=async()=>{const requestSeq=renderSeq;try{const result=await api('/api/run-tests',{method:'POST'});if(demo!==4||requestSeq!==renderSeq)return;report=result;step=1;render()}catch(e){if(demo===4&&requestSeq===renderSeq)showError(e)}};
    if(step===0){$('#next').disabled=!report;stageHtml(`<section class="panel"><h2>经典金额样例 · 待执行测试</h2><div class="formula">A 199 元 + B 99 元 + C 59 元<br>满 300 减 50 · 实付 307 元</div><p>待执行 ${d.cases.count} 条金额用例。请先运行本地测试，再请 AI 评价，最后揭示财务规范。</p><button id="run" class="primary">执行 20 条测试</button>${details('用例 ID、标题与预期',rowsTable(['用例','标题','预期'],d.cases.cases.map(c=>[c.case_id,esc(c.title),esc(text(c.expected))])))}</section>`);$('#run').onclick=run;}
    if(step===1){$('#next').textContent='揭示财务规范 →';$('#next').disabled=!report;
      const allPass=report&&report.failed===0&&report.total>0;
      stageHtml(`<section class="panel"><h2>本地测试执行报告</h2>${report?`<div class="kpi big-kpi">${report.passed}/${report.total} PASS</div><div class="grid two">${card('失败用例',`${report.failed}`)}${card('金额样例执行率',`${report.total?((report.passed/report.total)*100).toFixed(0):0}%`)}</div><p class="muted">通过 ${report.passed} / 总数 ${report.total}；此执行率仅指这批金额样例，不代表完整业务覆盖率。</p>${details('展开本地实际执行明细',rowsTable(['用例','结果','实际','预期','标题'],report.cases.map(c=>[c.case_id,c.passed?'<span class="pass">PASS</span>':'<span class="fail">FAIL</span>',esc(text(c.actual)),esc(text(c.expected)),esc(c.title)])))}${allPass?`${labPanel('d4a','让 AI 评价这次测试','全绿之后，把 PRD、测试假设、20 条用例预期和上面的实际执行证据交给 AI：它能看出这批测试证明了什么、没证明什么？此时提示词里<b>没有</b>财务规范，也没有正确金额。','复制 AI 测试结果评价提示词')}${labPaste('d4-r1','粘贴 AI 的评价（可选）','AI 的完整回答，末尾含 EXPECTATIONS= / CLASSIC_B_REFUND= / EVIDENCE_USED= 三行',7)}<div id="d4-r1-out"></div>`:''}`:`<p>尚未执行。执行成功后会进入本阶段。</p><button id="run2" class="primary">执行 20 条测试</button>`}</section>`);
      if(!report)$('#run2').onclick=run;
      else if(allPass){labWire('d4a',()=>({kind:'d4_eval1'}));const out=labOut($('#d4-r1-out'));labBind('d4-r1',t=>out(async()=>t.trim()?d4Round1Html(await analyze({kind:'d4_eval1',text:t})):'<p class="muted small">粘贴后在此显示 AI 的评价标记。</p>'));}}
    if(step===2){if(!report){step=1;$('#next').disabled=true;return}
      const dr=await data('d4r','/api/lesson/4?reveal=true');if(seq!==renderSeq||demo!==4)return;
      const c=dr.comparison,o=dr.order,returnGross=o.items.filter(i=>o.return_skus.includes(i.sku)).reduce((n,i)=>n+Number(i.gross),0).toFixed(2);
      stageHtml(`<section class="panel"><h2>财务规范揭示 · 逐步复算</h2><p class="lead">比例分摊假设与正式财务规则并列，金额来自本地计算接口。</p><div class="grid two">${card('比例分摊假设',`${c.assumed_refund} 元`,'inference')}${card('财务规范退款',`${c.correct_refund} 元`,'fact')}</div><h3>比例分摊假设</h3><div class="formula">优惠分摊 = ${c.original_discount} × ${returnGross} / ${c.gross_total} = ${c.discount_share}<br>假设退款 = ${returnGross} − ${c.discount_share} = ${c.assumed_refund}</div><h3>财务规范：先重算剩余订单优惠</h3><div class="formula">${c.gross_total} − ${returnGross} = ${c.remaining_gross} &lt; 300 → 优惠 ${c.original_discount} 重算为 ${c.remaining_discount}<br>退款 = ${returnGross} − (${c.original_discount} − ${c.remaining_discount}) = ${c.correct_refund}</div>${card('金额差异',`${c.difference} 元`)}<p>规则来源：独立财务规范。存在出处不代表来源已经充分支持用例预期，仍需核对业务规则和计算。</p>${details('规范原文及接口计算明细',pre({finance:dr.finance,comparison:c}))}${labPanel('d4b','带上财务规范，让 AI 复算并修正结论','这一版提示词补充独立财务规范 F10～F40（不含算例和答案），并增加逐条复算及结论修正要求；如已粘贴上一轮评价，也会带入供 AI 对照。','复制 AI 复评提示词（含财务规范）')}${labPaste('d4-r1','上一轮 AI 评价（可选，自动带入复评提示词）','把第一次 AI 评价的回答粘贴到这里；留空则当作全新评价',4)}${labPaste('d4-r2','粘贴 AI 的复评（可选）','AI 的完整回答，含 RECOMPUTE: 复算区块和末尾标记行',7)}<div id="d4-r2-out"></div><p class="teaching">教学观点：执行正确、断言正确和业务正确，是不同层次。测试预期需要验证；有出处不等于有依据。</p></section>`);
      revealed=true;$('#next').disabled=true;
      const wired=labWire('d4b',()=>({kind:'d4_eval2',previous:labGet('d4-r1')}));let tmr=null;
      let first=true;labBind('d4-r1',()=>{if(first){first=false;return}clearTimeout(tmr);tmr=setTimeout(()=>wired.refresh(),150)});
      const out=labOut($('#d4-r2-out'));
      labBind('d4-r2',t=>out(async()=>t.trim()?d4Round2Html(await analyze({kind:'d4_eval2',text:t})):`<p class="muted small">粘贴后在此显示 AI 的复算与本地财务计算的逐条对照。</p>${details('先看本地参考值：按财务规范重算的 20 条',rowsTable(['用例','标题','测试预期','财务规范（本地）'],Object.entries(dr.finance_reference).map(([k,v])=>[k,esc(v.title),esc(v.test_expected),`<b>${esc(v.status==='financial_review_required'?'REVIEW（暂停转人工）':v.refund)}</b>`])))}`));}
  }
  const kwTag=(on,t)=>on?vtag('fact',t):vtag('badge','未提及 '+t);
  function d5RoundHtml(r,n){
    const has=r.expectations||r.classic_b_refund||r.evidence_used;
    if(!has)return '<p class="muted small">粘贴后在此显示该轮的评价标记；没有识别到标记行时请直接阅读 AI 原文。</p>';
    return `<div class="lab-result"><h4>Review ${n} 解析${r.label?'（'+esc(r.label)+'）':''}</h4>${markerBlock(r)}<p class="small">关键词检测（非判断）：${kwTag(r.mentions_85_13,'85.13')} ${kwTag(r.mentions_49,'49')} ${kwTag(r.mentions_36_13,'36.13')}</p></div>`;
  }
  function d5CompareHtml(r,frozen){
    const a=r.round1,b=r.round2,both=(a.expectations||a.classic_b_refund)&&(b.expectations||b.classic_b_refund);
    const live=both?`<div class="table-wrap"><table><thead><tr><th>对照项</th><th>Review 1（无财务规范）${a.label?'<br>'+esc(a.label):''}</th><th>Review 2（+独立财务规范）${b.label?'<br>'+esc(b.label):''}</th></tr></thead><tbody><tr><td>预期是否有依据</td><td>${verdictTag(a.expectations)}</td><td>${verdictTag(b.expectations)}</td></tr><tr><td>经典订单退 B</td><td>${esc(a.classic_b_refund||'未给出')}</td><td>${esc(b.classic_b_refund||'未给出')}</td></tr><tr><td>AI 声称依据的材料</td><td>${esc(a.evidence_used||'未给出')}</td><td>${esc(b.evidence_used||'未给出')}</td></tr><tr><td>提及 85.13 / 49 / 36.13</td><td>${kwTag(a.mentions_85_13,'85.13')} ${kwTag(a.mentions_49,'49')} ${kwTag(a.mentions_36_13,'36.13')}</td><td>${kwTag(b.mentions_85_13,'85.13')} ${kwTag(b.mentions_49,'49')} ${kwTag(b.mentions_36_13,'36.13')}</td></tr></tbody></table></div>${noteList(r.notes)}`:`<p class="muted">还没有两轮都粘贴。回到前两个阶段粘贴各自的 AI 回答后，这里并排显示。</p>${noteList(r.notes)}`;
    return `${live}${details('冻结备用对照（FROZEN，预置结果，非实时 AI）',`<div class="grid two">${card('Review 1（冻结）',esc(frozen.round1.review.decision))}${card('Review 2（冻结）',esc(frozen.round2.review.decision))}</div>${pre({round1:frozen.round1.review,round2:frozen.round2.review})}`)}`;
  }
  async function d5(seq){
    const d=await data('d5','/api/lesson/5');if(seq!==renderSeq||demo!==5)return;
    shell('Demo 5｜AI 独立审查与信息源对照',3);
    const rep=d.execution_report;
    const cmp=()=>analyze({kind:'d5_compare',text:labGet('d5-o1'),text2:labGet('d5-o2'),label1:labGet('d5-l1'),label2:labGet('d5-l2')});
    if(step===0){
      stageHtml(`<section class="panel"><h2>Review 1 · 独立审查，不含财务规范</h2><div class="timeline">${card('输入','PRD V1.0 + 20 条用例与预期')}${card('执行证据',`${rep.passed}/${rep.total} 本地通过`)}${card('刻意不含','独立财务规范')}</div><p>让一个“没参与过这批用例”的 AI 做独立审查：只指出有充分证据的问题，说不清的明确写“无法确认”。不预设它会发现或漏掉什么。</p>${labPanel('d5a','Review 1 独立审查','建议新开一个对话。提示词自带 PRD、全部用例和执行报告。','复制 Review 1 审查提示词')}${labInput('d5-l1','本轮使用的模型 / Agent（选填，仅用于对照显示）','例如：模型甲')}${labPaste('d5-o1','粘贴 Review 1 的回答（可选）','AI 的完整回答，末尾含 EXPECTATIONS= / CLASSIC_B_REFUND= / EVIDENCE_USED= 三行',7)}<div id="d5-r1"></div>${details('冻结备用：预置 Review 1（FROZEN，非实时 AI）',`<p><span class="tag badge">FROZEN</span> 课堂预置结果，仅在现场 AI 不可用时作备用。</p>${pre({review:d.round1,execution_report:rep,inputs:['PRD V1.0','用例资产','本地执行报告']})}`)}</section>`);
      labWire('d5a',()=>({kind:'d5_review1'}));labBind('d5-l1',()=>{});
      const out=labOut($('#d5-r1'));labBind('d5-o1',()=>out(async()=>d5RoundHtml((await cmp()).round1,1)));
    }
    if(step===1){
      stageHtml(`<section class="panel"><h2>Review 2 · 唯一新增：独立财务规范</h2><div class="timeline">${card('同样的任务','同样的 PRD、用例和执行报告')}${card('新增输入','独立财务规范 F10～F40')}${card('要求','重新检查退款计算依据和测试预期')}</div><div id="d5-diff" class="lab-result"></div>${labPanel('d5b','Review 2 独立审查（加入财务规范）','建议使用与 Review 1 相同的模型，新开全新对话；只增加独立财务规范，便于比较证据的作用。更换模型可另做扩展实验。','复制 Review 2 审查提示词')}${labInput('d5-l2','本轮使用的模型 / Agent（选填，仅用于对照显示）','例如：与 Review 1 相同的模型')}${labPaste('d5-o2','粘贴 Review 2 的回答（可选）','AI 的完整回答，末尾含 EXPECTATIONS= / CLASSIC_B_REFUND= / EVIDENCE_USED= 三行',7)}<div id="d5-r2"></div>${details('冻结备用：预置 Review 2 与独立财务规范（FROZEN，非实时 AI）',`<p><span class="tag badge">FROZEN</span> 课堂预置结果，仅在现场 AI 不可用时作备用。</p>${pre({review:d.round2,finance:d.finance,execution_report:rep,inputs:['PRD V1.0','用例资产','本地执行报告','独立财务规范']})}`)}</section>`);
      labWire('d5b',()=>({kind:'d5_review2'}));labBind('d5-l2',()=>{});
      cmp().then(r=>{const box=$('#d5-diff');if(!box)return;const x=r.input_difference;box.innerHTML=x.identical_after_removing_block&&!x.round1_contains_finance&&x.round2_contains_finance?`<p>${vtag('fact','输入核对')} 本地逐字比对：Review 2 提示词去掉“独立财务规范”一段后，与 Review 1 提示词<b>完全相同</b>；Review 1 不含任何财务规范内容。</p>`:`<p class="fail">输入核对异常：两轮提示词的差别不只是财务规范，请勿用于课堂。</p>`}).catch(()=>{});
      const out=labOut($('#d5-r2'));labBind('d5-o2',()=>out(async()=>d5RoundHtml((await cmp()).round2,2)));
    }
    if(step===2){
      stageHtml(`<section class="panel"><h2>两轮对照 · 新增独立财务证据后的审查变化</h2><div id="d5-cmp"></div><div class="grid two">${card('Review 1 输入','PRD + 用例 + 执行报告')}${card('Review 2 输入','PRD + 用例 + 执行报告 + 独立财务规范')}</div><p class="teaching">更换模型或 Agent ≠ 获得独立的业务证据；审查质量取决于输入里有没有独立来源。独立 Verifier 的价值，也受它能看到的信息源限制。</p></section>`);
      const out=labOut($('#d5-cmp'));out(async()=>d5CompareHtml(await cmp(),d));
    }
  }
  const ACT={retain:'保留',modify:'修改',obsolete:'作废'},KIND={agree:'一致',missed:'AI 遗漏（确定性分析需改，AI 说保留）',over_reaction:'AI 误判（确定性分析保留，AI 要改/废）',different_change:'都要动，但处置不同',unparsed:'未解析到'};
  function d6CompareHtml(r,sum){
    if(!r.parsed)return `<p class="muted">粘贴 AI 的回答后，这里与确定性影响分析逐项对照。</p>${noteList(r.notes)}`;
    const g=r.groups,cn=r.counts,short=a=>a.length>10?a.slice(0,10).join('、')+` 等共 ${a.length} 个`:a.join('、')||'无',set=(x,label)=>`<div class="card"><strong>${label}</strong><p class="small">共同 ${x.common.length}：${esc(short(x.common))}</p><p class="small">仅 AI ${x.ai_only.length}：${esc(short(x.ai_only))}</p><p class="small">仅确定性分析 ${x.algorithm_only.length}：${esc(short(x.algorithm_only))}</p></div>`;
    const diff=r.cases.filter(x=>x.result!=='agree').map(x=>[x.case_id,esc(x.title),ACT[x.algorithm]||x.algorithm,x.ai?ACT[x.ai]:'—',esc(KIND[x.result])]);
    return `<div class="lab-result"><div class="grid"><div class="card"><strong>处置一致</strong><div class="kpi">${g.agree.length} / ${cn.history_total}</div></div><div class="card"><strong>遗漏</strong><div class="kpi ${g.missed.length?'warn-text':''}">${g.missed.length}</div><span class="small muted">${esc(g.missed.join('、')||'无')}</span></div><div class="card"><strong>误判 / 不必要的改动</strong><div class="kpi ${g.over_reaction.length?'warn-text':''}">${g.over_reaction.length}</div><span class="small muted">${g.over_reaction.length>6?'金额用例等 '+g.over_reaction.length+' 条':esc(g.over_reaction.join('、')||'无')}</span></div></div><div class="grid two">${set(r.rules,'受影响规则')}${set(r.scenarios,'受影响场景')}</div><div class="table-wrap"><table><thead><tr><th>对照项</th><th>AI</th><th>确定性影响分析</th></tr></thead><tbody><tr><td>保留 / 修改 / 作废</td><td>${cn.ai.retain} / ${cn.ai.modify} / ${cn.ai.obsolete}（已解析 ${cn.ai_parsed} 条）</td><td>${cn.algorithm.retain} / ${cn.algorithm.modify} / ${cn.algorithm.obsolete}</td></tr><tr><td>新增用例</td><td>${cn.ai_new??'未给出'}</td><td>${cn.algorithm_new}</td></tr><tr><td>需要动手的资产（修改 + 作废 + 新增）</td><td>${cn.ai_rebuild_total??'—'}</td><td>${cn.algorithm_rebuild_total}</td></tr><tr><td>整套重生成</td><td colspan="2">${cn.full_regeneration} 条（对照上限）</td></tr></tbody></table></div>${noteList(r.notes)}${diff.length?details(`逐条分歧（${diff.length} 条）`,rowsTable(['用例','标题','确定性分析','AI','结论'],diff)):'<p class="pass">所有已解析的历史用例处置与确定性分析一致。</p>'}<p class="muted small">确定性影响分析的 ${sum.retain} 保留 / ${sum.modify} 修改 / ${sum.obsolete} 作废 / ${sum.add} 新增与 25/25 回归是本地实际执行的已验收结果，不会被 AI 的输出改写。AI 与它不同时，要回到依赖链上核对谁对——合理的分歧同样值得采纳。</p></div>`;
  }
  async function d6(seq){
    const d=await data('d6','/api/lesson/6');if(seq!==renderSeq||demo!==6)return;shell('Demo 6｜版本变更、影响分析与增量回归',7);
    const m=d.migration||d,sum=m.summary||{},rows=m.case_actions||[],label={retain:'保留',modify:'修改',obsolete:'作废',add:'新增'};
    if(step===0)stageHtml(`<section class="panel"><h2>已验证基线 V1.0</h2><p class="lead">历史用例 ${sum.history_total??'—'} 条。V1.1 变化从该基线追踪。</p>${details('基线与 V1.0 PRD',pre(d.prd_v1_0))}</section>`);
    if(step===1){const p=d.prd_v1_1;stageHtml(`<section class="panel"><h2>V1.1 三项需求变化</h2><div class="grid">${(p.changes||[]).map(c=>card(`${c.change_id} · ${c.rule_id}`,esc(c.text))).join('')}</div><div class="grid two">${card('流程顺序 · V1.0','寄回 → 质检 → 退款')}${card('流程顺序 · 极速退款资格','寄回 → 退款 → 质检')}${card('期限规则','普通 / 银卡 7 日；金卡 15 日')}${card('会员等级判定','使用下单时记录的等级')}</div><p>来源：${(p.paragraphs_added||[]).map(x=>x.source_id).join('、')}</p>${labPanel('d6a','让 AI 同时做影响分析','讲后面几步的同时，可以先把提示词复制给 AI 让它在另一个窗口里分析；最后一步再把它的回答和确定性分析对照。提示词已带上 V1.0 基线、这三项变更和 32 条历史用例的依赖信息。','复制 AI 变更影响分析提示词')}</section>`);labWire('d6a',()=>({kind:'d6_impact'}))}
    if(step===2)stageHtml(`<section class="panel"><h2>三条 RuleDiff</h2>${rowsTable(['变更','类型','影响规则','摘要'],(m.rule_diff||[]).map(x=>[x.change_id,x.change_type,esc(x.affected_rule_ids.join(', ')),esc(x.summary)]))}</section>`);
    if(step===3){const located=rows.filter(x=>x.before&&(x.change_ids||[]).length);stageHtml(`<section class="panel"><h2>受影响规则、场景与历史用例定位</h2><div class="grid two">${card('受影响规则',esc((m.affected_rules||[]).join(', ')))}${card('受影响场景',`${(m.affected_scenarios||[]).length} 条`)}${card('依赖受影响的历史用例',`${sum.affected_dependency_count??located.length} 条`)}${card('行为断言需调整',`${sum.behavior_affected??'—'} 条`)}</div>${rowsTable(['场景','标题','关联变更'],(m.affected_scenarios||[]).map(x=>[x.scenario_id,esc(x.title),esc(x.change_ids.join(', '))]))}${details('定位依赖发生变化的历史用例',rowsTable(['用例','标题','关联规则 / 场景','变更'],located.map(x=>[x.case_id,esc(x.title),esc((x.dependencies||[]).join(', ')),esc(x.change_ids.join(', '))])))}</section>`)}
    if(step===4){const actionRows=rows.map(x=>[x.case_id,label[x.action]||x.action,esc((x.change_ids||[]).join(', ')),['modify','obsolete','add'].includes(x.action)?'是':'否',x.provenance_update?'是':'否',`${esc(x.title)} ${details('查看理由与 before / after',`${esc(x.reason)}${pre({before:x.before,after:x.after})}`)}`]);stageHtml(`<section class="panel"><h2>历史用例处置与增量资产</h2><div class="grid">${card('保留',`${sum.retain??0} 条`)}${card('修改',`${sum.modify??0} 条`)}${card('作废',`${sum.obsolete??0} 条`)}${card('新增',`${sum.add??0} 条`)}</div><p>行为受影响 ${sum.behavior_affected??0} 条；来源依据更新 ${sum.provenance_only_count??0} 条，二者含义不同。</p>${details('查看完整处置清单与前后输入',rowsTable(['ID','处置','变更','行为影响','来源更新','理由 / 前后'],actionRows))}${details('未新增的重复候选',pre(m.not_added))}</section>`)}
    if(step===5){const reg=m.regression||{},titles=Object.fromEntries((reg.selected_cases||[]).map(c=>[c.case_id,c.title]));const merge=(m.not_added||[])[0];stageHtml(`<section class="panel"><h2>回归报告 · 预算、排除与合并</h2><div class="grid">${card('回归执行',`${reg.report?.passed??0}/${reg.report?.total??0} PASS`)}${card('完整重生成',`${m.comparison?.full_regeneration??0} 条`)}${card('行为新增 / 修改',`${m.comparison?.behavior_edit_or_add??0} 条`)}</div><p>来源依据正式化单列 ${m.comparison?.provenance_only_updates??0} 条；已验证的历史财务金额保持不变。</p>${rowsTable(['ID','结果','标题'],(reg.report?.cases||[]).map(c=>[c.case_id,c.passed?'<span class="pass">PASS</span>':'<span class="fail">FAIL</span>',esc(titles[c.case_id]||c.title||'')]))}<p>合并示例：${merge?`${esc(merge.case_id)} 已由 ${esc(merge.covered_by)} 覆盖，${esc(merge.reason)}`:'无重复候选'}</p>${details('查看回归入选项、排除项与其他合并候选',pre({selected:reg.selected_ids,excluded:reg.excluded,not_added:m.not_added,selection_reasons:reg.selection_reasons}))}<p><a href="/api/practice/6" download>下载 Demo 6 学员练习材料</a></p><p class="teaching">教学观点：需求变化时沿规则和资产依赖增量更新，不必从头开始。</p></section>`)}
    if(step===6){
      stageHtml(`<section class="panel"><h2>AI 影响分析 × 确定性分析：遗漏、误判与不必要的重建</h2><p class="lead">同一份 V1.0 基线与三项变更：AI 怎么判断？和沿规则依赖链推导出的 ${sum.retain} 保留 / ${sum.modify} 修改 / ${sum.obsolete} 作废 / ${sum.add} 新增相比，差在哪里？</p>${labPanel('d6','变更影响分析','提示词自带 V1.0 基线、三项变更和 32 条历史用例（依赖规则、场景、输入、预期），不含任何确定性分析的结果。','复制 AI 变更影响分析提示词')}${labPaste('d6-ai','粘贴 AI 的回答','含 AFFECTED_RULES: / AFFECTED_SCENARIOS: 行、逐条处置表（| 用例ID | 保留/修改/作废 | 理由 |）、新增用例清单和 NEW_CASE_COUNT=',8)}<div id="d6-cmp"></div></section>`);
      labWire('d6',()=>({kind:'d6_impact'}));
      const out=labOut($('#d6-cmp'));labBind('d6-ai',t=>out(async()=>t.trim()?d6CompareHtml(await analyze({kind:'d6_impact',text:t}),sum):'<p class="muted">粘贴 AI 的回答后，这里与确定性影响分析逐项对照。</p>'));
    }
  }
  async function reset(){renderSeq++;try{const s=await api('/api/reset',{method:'POST'});epoch=s.epoch;demo=2;step=0;budget=15;manual=false;revealed=false;report=null;budgetSnapshot=null;labReset();Object.keys(cache).forEach(k=>delete cache[k]);render()}catch(e){showError(e)}}
  async function watch(){try{const s=await api('/api/state');if(epoch===null)epoch=s.epoch;else if(epoch!==s.epoch){epoch=s.epoch;demo=2;step=0;budget=15;manual=false;revealed=false;report=null;budgetSnapshot=null;labReset();Object.keys(cache).forEach(k=>delete cache[k]);render()}}catch{}timer=setTimeout(watch,3000)}
  document.addEventListener('keydown',e=>{if(e.target.matches('button,input,textarea,select,summary'))return;if(e.key==='ArrowRight'&&!(demo===4&&step===0&&!report)&&step<({2:3,3:4,4:3,5:3,6:7}[demo])-1){step++;render()}else if(e.key==='ArrowLeft'&&step>0){step--;render()}else if(e.key.toLowerCase()==='r')reset();else if('23456'.includes(e.key)){demo=+e.key;step=0;render()}});
  $('#reset').onclick=reset;render();watch();
})();
