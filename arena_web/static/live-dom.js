/* Reconcile live data without replacing interactive DOM nodes. Navigation may
   still mount a fresh page. Declare data-live-preserve on independently loaded
   readers; their owner updates their content through this same reconciler. */
(() => {
  function key(node) {
    if(node.nodeType!==1)return '';
    if(node.id)return 'id:'+node.id;
    if(node.dataset.liveKey)return 'live:'+node.dataset.liveKey;
    if(node.matches('input[name],select[name],textarea[name]'))
      return node.tagName+':'+node.name+(/^(checkbox|radio)$/.test(node.type)?':'+node.value:'');
    if(node.dataset.action)return 'action:'+node.dataset.action+':'+['session','id','path','tab','index','offset','version','model','file','kind'].map(name=>node.dataset[name]||'').join(':');
    return '';
  }
  const compatible=(a,b)=>a.nodeType===b.nodeType && a.nodeName===b.nodeName && a.namespaceURI===b.namespaceURI && key(a)===key(b) && (key(a)||a.nodeType!==1||(a.classList[0]||'')===(b.classList[0]||''));
  function sync(node,next) {
    if(node.isEqualNode(next))return;
    if(node.nodeType!==1) {if(node.nodeValue!==next.nodeValue)node.nodeValue=next.nodeValue;return;}
    if(node.hasAttribute('data-live-preserve')&&next.hasAttribute('data-live-preserve'))return;
    const focused=node===document.activeElement;
    // Mutating options while a native picker is open closes it on some hosts.
    // Deferred options are picked up by the next refresh after focus leaves.
    if(node.tagName==='SELECT'&&focused)return;
    const control=node.matches('input,select,textarea');
    const value=control?node.value:null,checked=node.checked;
    const top=node.scrollTop,left=node.scrollLeft;
    for(const attribute of [...node.attributes]) {
      if(attribute.name==='open'&&node.tagName==='DETAILS')continue;
      if(control&&['value','checked','selected'].includes(attribute.name))continue;
      if(!next.hasAttribute(attribute.name))node.removeAttribute(attribute.name);
    }
    for(const attribute of [...next.attributes]) {
      if(attribute.name==='open'&&node.tagName==='DETAILS')continue;
      if(control&&['value','checked','selected'].includes(attribute.name))continue;
      if(node.getAttribute(attribute.name)!==attribute.value)node.setAttribute(attribute.name,attribute.value);
    }
    if(!node.hasAttribute('data-live-preserve')&&node.tagName!=='TEXTAREA'&&node.tagName!=='INPUT')children(node,next);
    if(control) {
      if(node.tagName!=='SELECT'||[...node.options].some(option=>option.value===value))node.value=value;
      if(node.type==='checkbox'||node.type==='radio')node.checked=checked;
    }
    if(top)node.scrollTop=top;
    if(left)node.scrollLeft=left;
  }
  function children(parent,next) {
    const previous=[...parent.childNodes],used=new Set();
    const keyed=new Map(previous.filter(node=>key(node)).map(node=>[key(node),node]));
    let cursor=parent.firstChild;
    for(const desired of [...next.childNodes]) {
      let node=key(desired)?keyed.get(key(desired)):cursor;
      if(!node||used.has(node)||!compatible(node,desired))node=null;
      if(!node)node=desired.cloneNode(true);
      else sync(node,desired);
      if(node!==cursor)parent.insertBefore(node,cursor);
      used.add(node);cursor=node.nextSibling;
    }
    for(const node of previous)if(!used.has(node)&&node.parentNode===parent)node.remove();
  }
  function preserveViewport(change) {
    // Snapshot at mutation time, never before awaiting a network response.
    const main=document.querySelector('#main'),scroll=window.scrollY;
    const rect=main?.getBoundingClientRect();
    const hit=rect?document.elementFromPoint(Math.max(1,Math.min(innerWidth-1,rect.left+Math.min(rect.width/2,80))),Math.min(innerHeight-1,120)):null;
    const anchor=hit&&main.contains(hit)?hit:null;
    const before=anchor?.getBoundingClientRect().top;
    const result=change();
    const delta=anchor?.isConnected?anchor.getBoundingClientRect().top-before:scroll-window.scrollY;
    if(Math.abs(delta)>1)window.scrollTo({top:window.scrollY+delta,behavior:'instant'});
    return result;
  }
  function update(parent,html) {
    if(parent.tagName==='SELECT'&&parent===document.activeElement)return false;
    const template=document.createElement('template');template.innerHTML=html;
    preserveViewport(()=>children(parent,template.content));
    return true;
  }
  function replace(node,html) {
    const template=document.createElement('template');template.innerHTML=html;
    const next=template.content.firstElementChild;
    preserveViewport(()=>{
      if(next&&compatible(node,next))sync(node,next);
      else if(next)node.replaceWith(next);
    });
  }
  window.LiveDOM={update,replace};
})();
