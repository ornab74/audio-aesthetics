'use strict';
(function(){
  const wave=document.getElementById('wave');
  if(wave){const rng=(i)=>Math.abs(Math.sin(i*1.917)*Math.cos(i*.41));
    for(let i=0;i<64;i++){
      const bar=document.createElement('i');bar.style.height=(8+rng(i)*108)+'px';bar.style.setProperty('--n',String(i));wave.appendChild(bar);
    }
  }
  const status=document.getElementById('billing-message');
  const say=(s)=>{if(status)status.textContent=s;};
  const params=new URLSearchParams(location.search);
  const form=document.getElementById('checkout-form');
  async function post(path,payload){
    const res=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const data=await res.json().catch(()=>({}));
    if(!res.ok)throw Error(typeof data.detail==='string'?data.detail:`Request failed (${res.status})`);
    return data;
  }
  if(form)form.addEventListener('submit',async(e)=>{
    e.preventDefault();const b=form.querySelector('button'),mail=document.getElementById('customer-email').value;
    b.disabled=true;say('Opening secure Stripe checkout...');
    try{const r=await post('/api/billing/checkout',{email:mail});
      if(!r.url||!r.url.startsWith('https://checkout.stripe.com/'))throw Error('Invalid checkout response');
      location.href=r.url;
    }catch(err){say('Checkout unavailable: '+err.message);}finally{b.disabled=false;}
  });
  const manage=document.getElementById('manage-subscription');
  if(manage)manage.addEventListener('click',async()=>{
    const key=document.getElementById('manage-key').value.trim();
    if(!key){say('Enter your Pro access key to manage billing.');return;}
    manage.disabled=true;say('Opening the secure Stripe billing portal...');
    try{
      const r=await fetch('/api/billing/portal',{method:'POST',headers:{Authorization:'Bearer '+key}});
      const data=await r.json();
      if(!r.ok)throw Error(typeof data.detail==='string'?data.detail:'Unable to open billing portal');
      if(!data.url||!data.url.startsWith('https://billing.stripe.com/'))throw Error('Invalid billing portal URL');
      location.href=data.url;
    }catch(err){say(err.message);}finally{manage.disabled=false;}
  });
  const modal=document.getElementById('license-modal');
  function showKey(k){document.getElementById('license-key').value=k;modal.hidden=false;}
  document.getElementById('copy-license').addEventListener('click',async()=>{
    try{await navigator.clipboard.writeText(document.getElementById('license-key').value);
      document.getElementById('copy-license').textContent='COPIED ✓';}
    catch{document.getElementById('license-key').select();}
  });
  document.getElementById('close-license').addEventListener('click',()=>{modal.hidden=true;});
  if(params.has('canceled'))say('Checkout canceled. You were not charged.');
  if(params.has('session_id')){
    const sessionId=params.get('session_id');
    history.replaceState({},'',location.pathname+'#pricing');
    say('Verifying your Stripe subscription...');
    post('/api/billing/activate',{session_id:sessionId}).then(r=>{say('Pro is activated. Save your one-time access key.');showKey(r.access_token);})
      .catch(err=>say('Unable to activate: '+err.message+' (Contact support if checkout was paid).'));
  }
})();
