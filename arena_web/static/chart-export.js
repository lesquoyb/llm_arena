/* Render the selected chart as a self-contained PNG in the browser. */
const CHART_EXPORT_WRAPPERS = '.evolution-scroll,.repetition-scroll,.overview-matrix-wrap,.table-wrap,.table-scroll,.resource-bar-list,.length-rows';
const CHART_EXPORT_STYLES = (
  'display visibility box-sizing position top right bottom left ' +
  'width height min-width max-width min-height max-height overflow-x overflow-y ' +
  'padding-top padding-right padding-bottom padding-left margin-top margin-right margin-bottom margin-left ' +
  'border-top border-right border-bottom border-left border-radius border-collapse border-spacing ' +
  'background-color background-image color opacity box-shadow ' +
  'font-family font-size font-weight font-style font-variant-numeric line-height letter-spacing ' +
  'text-align text-decoration-line text-decoration-color text-transform white-space overflow-wrap vertical-align ' +
  'align-items align-content align-self justify-items justify-content justify-self gap ' +
  'flex-direction flex-wrap flex-grow flex-shrink flex-basis order ' +
  'grid-template-columns grid-template-rows grid-auto-columns grid-auto-rows grid-auto-flow grid-column grid-row ' +
  'list-style-type list-style-position transform transform-origin ' +
  'fill fill-opacity stroke stroke-width stroke-opacity stroke-dasharray stroke-linecap stroke-linejoin text-anchor'
).split(' ');

function exportChartOptions(chart) {
  return [...new Set([...chart.querySelectorAll('select')]
    .filter(select=>select.getClientRects().length&&select.matches(
      '[data-repetition-metric],[data-repetition-rounds],[data-length-setting]'
    ))
    .map(select=>select.selectedOptions[0]?.textContent.trim()).filter(Boolean))];
}

function compactExportBars(chart) {
  const canvas = document.createElement('canvas');
  const context = canvas.getContext('2d');
  const columns = (selector, label, minimum, maximum) => {
    const rows = [...chart.querySelectorAll(selector)];
    if (!rows.length) return {rows, labels:minimum};
    const textWidths = rows.flatMap(row=>[...row.querySelectorAll(label)].map(node=>{
      const style = getComputedStyle(node);
      context.font = `${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
      return context.measureText(node.textContent.trim()).width;
    }));
    return {rows, labels:Math.min(maximum,Math.max(minimum,Math.ceil(Math.max(0,...textWidths))))};
  };
  const rank = columns('.overview-rank-body','strong',52,196);
  for (const row of rank.rows) {
    row.style.gridTemplateColumns = `${rank.labels}px minmax(0,1fr) 6ch`;
  }
  const workspace = columns('.workspace-bar',':scope > div:first-child > strong, :scope > div:first-child > small',52,196);
  const valueColumn = chart.classList.contains('usage-chart') ? '12ch' : '6ch';
  for (const row of workspace.rows) {
    Object.assign(row.style,{gridTemplateColumns:`${workspace.labels}px minmax(0,1fr) ${valueColumn}`,gap:'8px'});
  }
  const resources = columns('.resource-score-row',':scope > strong',52,196);
  let resourceValues = 80;
  if (resources.rows.length) {
    const amountWidth = columns('.resource-score-row', '.resource-amount', 104, 174).labels;
    const layout = {gridTemplateColumns:`${resources.labels}px minmax(0,1fr) ${amountWidth}px`,gap:'8px'};
    const head = chart.querySelector('.resource-bar-head');
    if (head) Object.assign(head.style,{...layout,padding:'4px 0',lineHeight:'1.2'});
    for (const row of resources.rows) {
      Object.assign(row.style,{...layout,padding:'4px 0',lineHeight:'1.25'});
    }
    resourceValues=amountWidth+36;
  }
  const labelWidth = Math.max(rank.labels,workspace.labels,resources.labels);
  return Math.max(320,labelWidth+220+resourceValues);
}

function prepareChartImage(chart, title, context, caption='') {
  const rowChart = chart.querySelector('.overview-ranking,.workspace-bars,.resource-bar-list');
  const clone = chart.cloneNode(true);
  clone.classList.remove('chart-expanded');
  if (clone.classList.contains('comparison-chart')) {
    const series = clone.querySelector(':scope > .chart-filterable');
    if (series) clone.replaceChildren(series);
  }
  clone.querySelectorAll([
    '.overview-section-head', '.panel-title', '.chart-controls', '.chart-view-choice',
    '.chart-hidden', '.chart-legend-hidden', '.progression-availability', 'details',
    'p', '.overview-caption', ':scope > small', '.overview-rank-body > small',
    'button', 'select', 'input', 'textarea', 'svg title',
  ].join(',')).forEach(node=>node.remove());
  if (clone.classList.contains('resource-chart')) {
    clone.querySelectorAll(':scope > div > small').forEach(node=>node.remove());
  }
  clone.querySelectorAll('.chart-dimmed,.chart-selected').forEach(node=>node.classList.remove('chart-dimmed','chart-selected'));
  clone.querySelectorAll('[id],[data-chart-key],[tabindex],[href]').forEach(node=>{
    for (const attr of ['id','data-chart-key','tabindex','href']) node.removeAttribute(attr);
  });
  clone.removeAttribute('id');
  clone.removeAttribute('data-chart-key');
  Object.assign(clone.style, {
    width:'100%', maxWidth:'none', height:'auto', padding:'0', border:'0',
    boxShadow:'none', background:'#fff', overflow:'visible',
  });
  clone.querySelectorAll(CHART_EXPORT_WRAPPERS).forEach(node=>{
    Object.assign(node.style,{overflow:'visible',maxHeight:'none',maxWidth:'none'});
  });
  clone.querySelectorAll('.overview-matrix th').forEach(node=>{node.style.position='static';});
  for (const legend of clone.querySelectorAll('.chart-legend,.overview-legend')) {
    if (!legend.textContent.trim()) legend.remove();
  }
  if (clone.querySelector('.overview-ranking')) {
    clone.querySelector('.overview-ranking').classList.add('compact');
  }
  if (clone.querySelector('.resource-bar-list')) {
    for (const row of clone.querySelectorAll('.resource-bar-head,.resource-score-row')) {
      row.append(row.querySelector('.resource-amount'));
    }
    for (const total of clone.querySelectorAll('.resource-score-row .resource-amount small')) {
      total.prepend(' / ');
      Object.assign(total.style,{display:'inline',whiteSpace:'nowrap'});
    }
    clone.querySelector('.chart-legend')?.remove();
  }
  const workspaceBars = clone.querySelector('.workspace-bars');
  if (workspaceBars) Object.assign(workspaceBars.style,{gap:'8px',margin:'0'});
  if (!clone.querySelector('svg,table,.overview-ranking,.resource-bar-list,.workspace-bars,.length-rows,.error-rate-row')) {
    throw new Error('No chart data to export.');
  }
  const groupedWidth = compactGroupedBars(clone,{forExport:true});
  const width = (groupedWidth || rowChart) ? Math.max(320,groupedWidth) :
    Math.max(640,Math.min(900,chart.clientWidth),...[...chart.querySelectorAll(CHART_EXPORT_WRAPPERS)]
      .map(wrapper=>wrapper.scrollWidth));

  const stage = document.createElement('div');
  stage.setAttribute('aria-hidden','true');
  stage.inert = true;
  Object.assign(stage.style,{position:'fixed',left:'-100000px',top:'0',pointerEvents:'none'});
  const page = document.createElement('article');
  Object.assign(page.style,{
    width:`${Math.ceil(width+36)}px`, padding:'18px', background:'#fff', color:'var(--ink)',
  });
  const heading = document.createElement('h1');
  heading.textContent = title;
  Object.assign(heading.style,{fontSize:'26px',lineHeight:'1.2',margin:'0 0 8px'});
  page.append(heading);
  if (context.length) {
    const subtitle = document.createElement('p');
    subtitle.textContent = context.join(' · ');
    Object.assign(subtitle.style,{color:'var(--muted)',fontSize:'13px',margin:'0 0 12px'});
    page.append(subtitle);
  }
  page.append(clone);
  if (caption) {
    const description = document.createElement('p');
    description.textContent = caption;
    Object.assign(description.style,{color:'var(--muted)',fontSize:'12px',margin:'12px 0 0'});
    page.append(description);
  }
  stage.append(page);
  (document.fullscreenElement || document.body).append(stage);
  try {
    if (rowChart) page.style.width = `${compactExportBars(clone)+36}px`;
    const bounds = page.getBoundingClientRect();
    const imageWidth = Math.ceil(Math.max(bounds.width,page.scrollWidth));
    const imageHeight = Math.ceil(Math.max(bounds.height,page.scrollHeight));
    // Read all the styles before writing so the browser lays out the staging chart only once.
    const styled = [page,...page.querySelectorAll('*')].map(node=>{
      const style = getComputedStyle(node);
      return [node,CHART_EXPORT_STYLES.map(name=>[name,style.getPropertyValue(name)])
        .filter(([,value])=>value&&!value.includes('url('))];
    });
    for (const [node,styles] of styled) {
      for (const [name,value] of styles) node.style.setProperty(name,value);
    }
    const contents = new XMLSerializer().serializeToString(page);
    return {
      width:imageWidth,height:imageHeight,
      svg:`<svg xmlns="http://www.w3.org/2000/svg" width="${imageWidth}" height="${imageHeight}"><foreignObject width="100%" height="100%">${contents}</foreignObject></svg>`,
    };
  } finally {
    stage.remove();
  }
}

async function exportChartPng(chart, {title, context, name, caption}) {
  const options = exportChartOptions(chart);
  const {width,height,svg} = prepareChartImage(chart,title,[...new Set([...context,...options])],caption);
  const image = new Image();
  image.src = 'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(svg);
  await image.decode();
  const scale = Math.min(2,8192/Math.max(width,height),Math.sqrt(24_000_000/(width*height)));
  const canvas = document.createElement('canvas');
  canvas.width = Math.max(1,Math.floor(width*scale));
  canvas.height = Math.max(1,Math.floor(height*scale));
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#fff';
  ctx.fillRect(0,0,canvas.width,canvas.height);
  ctx.drawImage(image,0,0,canvas.width,canvas.height);
  const png = await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));
  if (!png) throw new Error('The chart could not be saved as PNG.');
  const url = URL.createObjectURL(png);
  const link = document.createElement('a');
  link.href = url;
  link.download = (name.normalize('NFKD').replace(/[^\p{L}\p{N}]+/gu,'-').replace(/^-|-$/g,'').slice(0,120)||'arena-chart')+'.png';
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(()=>URL.revokeObjectURL(url),10000);
}
