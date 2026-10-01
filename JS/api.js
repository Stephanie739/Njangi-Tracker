const API='/api';
async function api(path,opts={}){const token=localStorage.getItem('njangi_token');const headers={'Content-Type':'application/json',...(opts.headers||{})};if(token)headers.Authorization='Bearer '+token;const r=await fetch(API+path,{...opts,headers});let d={};try{d=await r.json()}catch{}if(!r.ok||d.ok===false)throw new Error(d.error||'Request failed');return d}
function saveSession(d){localStorage.setItem('njangi_token',d.token);localStorage.setItem('njangi_user',JSON.stringify(d.user));}
function logout(){
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
async function requireRole(role){try{const d=await api('/auth/me');if(!d.ok||d.user.role!==role)throw 0;return d.user}catch{location.href=role==='member'?'member-login.html':'login.html'}}