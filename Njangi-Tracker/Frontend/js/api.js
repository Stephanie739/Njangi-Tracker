const API=(window.NJANGI_CONFIG&&window.NJANGI_CONFIG.API_BASE)||'http://127.0.0.1:8000/api';

function loginPageFor(role){return role==='member'?'member-login.html':'login.html'}

async function api(path,opts={}){
  const token=localStorage.getItem('njangi_token');
  const headers={'Content-Type':'application/json',...(opts.headers||{})};
  if(token)headers.Authorization='Bearer '+token;
  let r;
  try{r=await fetch(API+path,{...opts,headers})}
  catch{throw new Error('Cannot reach the Njangi server. Check your connection and try again.')}
  let d={};try{d=await r.json()}catch{}
  // An expired or revoked session on a signed-in page: go back to the right login page.
  if(r.status===401&&token&&!path.startsWith('/auth/login')&&!path.startsWith('/member/login')){
    let role='admin';try{role=(JSON.parse(localStorage.getItem('njangi_user')||'null')||{}).role||'admin'}catch{}
    localStorage.removeItem('njangi_token');localStorage.removeItem('njangi_user');
    location.replace(loginPageFor(role));
    return new Promise(()=>{});
  }
  if(!r.ok||d.ok===false)throw new Error(d.error||'Request failed ('+r.status+')');
  return d;
}
function saveSession(d){localStorage.setItem('njangi_token',d.token);localStorage.setItem('njangi_user',JSON.stringify(d.user));}
async function logout(){
  // Revoke the session on the server (best effort), then clear the browser.
  try{await fetch(API+'/auth/logout',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+(localStorage.getItem('njangi_token')||'')},body:'{}'})}catch{}
  localStorage.removeItem('njangi_token');
  localStorage.removeItem('njangi_user');
  sessionStorage.removeItem('reset_token');
  sessionStorage.removeItem('reset_role');
  location.replace('index.html');
}

function bindLogout(){
  document.querySelectorAll('#logoutButton,#logoutBtn,.logout-button[data-logout]').forEach(btn=>{
    btn.onclick=(event)=>{
      event.preventDefault();
      logout();
    };
  });
}

if(document.readyState==='loading'){
  document.addEventListener('DOMContentLoaded',bindLogout,{once:true});
}else{
  bindLogout();
}
function user(){try{return JSON.parse(localStorage.getItem('njangi_user')||'null')}catch{return null}}
function money(n){return new Intl.NumberFormat('fr-FR').format(Number(n||0))+' FCFA'}
function esc(s){return String(s??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
function fmtDate(s){if(!s)return'-';const d=new Date(/\d{2}:\d{2}:\d{2}/.test(s)?s.replace(' ','T'):s+'T00:00:00');return isNaN(d)?'-':d.toLocaleDateString()}

// Fills the parts of the page shared by every signed-in screen: real group name,
// current cycle and the alerts bell (pending loan requests for the administrator).
async function initShell(){
  try{
    const d=await api('/settings');
    document.querySelectorAll('.group-switcher strong').forEach(e=>{e.textContent=d.group.name||'Njangi Group'});
    const cycleLabel=document.querySelector('.group-switcher span');
    if(cycleLabel&&!document.getElementById('sideCycle'))cycleLabel.textContent=d.active_cycle?('Cycle #'+d.active_cycle):'No active cycle';
    const bell=document.querySelector('.notification');
    if(bell){
      const n=Number(d.pending_loans||0);
      const dot=bell.querySelector('span');
      if(bell.firstChild&&bell.firstChild.nodeType===3&&bell.firstChild.nodeValue.trim()!=='\uD83D\uDD14')bell.firstChild.nodeValue='Alerts';
      bell.title=n?`${n} pending loan request${n>1?'s':''}`:'No new alerts';
      if(dot)dot.style.display=n?'':'none';
      if(n){bell.style.cursor='pointer';bell.onclick=()=>{if(d.role==='admin')location.href='loans.html'}}
    }
    return d;
  }catch{return null}
}

// Shared top bar / sidebar behaviour: signed-in name, avatar and the mobile menu button.
function bindShell(u){
  const $=id=>document.getElementById(id);
  if($('userName'))$('userName').textContent=u.name;
  if($('userAvatar'))$('userAvatar').textContent=(u.name||'NG').split(/\s+/).map(x=>x[0]).slice(0,2).join('').toUpperCase();
  const menu=$('mobileMenu')||$('menuBtn'),side=$('sidebar'),over=$('sidebarOverlay')||$('overlay');
  if(menu&&side&&over){
    menu.onclick=()=>{side.classList.toggle('open');over.classList.toggle('show')};
    over.onclick=()=>{side.classList.remove('open');over.classList.remove('show')};
  }
}

// Redirects to the right login page unless a signed-in user with the given role is present.
async function requireRole(role){
  try{
    const d=await api('/auth/me');
    if(!d.ok||d.user.role!==role)throw 0;
    bindShell(d.user);
    initShell();
    return d.user;
  }catch{
    location.replace(loginPageFor(role));
    return new Promise(()=>{});   // stop the calling page script: we are leaving
  }
}


// Returns '' when the e-mail looks right, otherwise a readable hint. Browsers accept "name@gmailcom"
// as valid, so the missing dot (and a few very common typos) are caught here.
function emailProblem(value){
  const v=String(value||'').trim().toLowerCase();
  if(!v)return 'Enter your email address.';
  if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)){
    if(/@(gmail|yahoo|hotmail|outlook|icloud)com$/.test(v))return 'A "." seems to be missing before "com" (for example name@gmail.com).';
    return 'Enter a valid email address, for example name@gmail.com.';
  }
  const [name,domain]=v.split('@');
  const typos={'gmial.com':'gmail.com','gmai.com':'gmail.com','gamil.com':'gmail.com','gmail.co':'gmail.com','gmail.con':'gmail.com','gmail.cm':'gmail.com','yaho.com':'yahoo.com','hotmial.com':'hotmail.com'};
  if(typos[domain])return `Did you mean ${name}@${typos[domain]}?`;
  return '';
}
