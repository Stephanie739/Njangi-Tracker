const params=new URLSearchParams(location.search);
let token=sessionStorage.getItem('reset_token')||params.get('token')||'';
// Which login page linked here (?role=member or ?role=admin) decides which
// account a shared email resolves to, when the same email is both an
// admin (in one group) and a member (in another).
let roleHint=sessionStorage.getItem('reset_role_hint')||params.get('role')||'';
if(roleHint)sessionStorage.setItem('reset_role_hint',roleHint);

const f=document.getElementById('forgotForm');
if(f)f.onsubmit=async e=>{
  e.preventDefault();
  try{
    const d=await api('/auth/forgot',{
      method:'POST',
      body:JSON.stringify({email:resetEmail.value,role:roleHint||undefined})
    });
    sessionStorage.setItem('reset_token',d.reset_token||'');
    if(d.dev_pin)resetMessage.textContent='Development PIN: '+d.dev_pin;
    setTimeout(()=>location.href='verify-pin.html',800);
  }catch(x){
    resetMessage.textContent=x.message;
  }
};

const vf=document.getElementById('verifyForm');
if(vf)vf.onsubmit=async e=>{
  e.preventDefault();
  try{
    const d=await api('/auth/verify-pin',{
      method:'POST',
      body:JSON.stringify({reset_token:token,pin:pin.value})
    });
    sessionStorage.setItem('reset_token',d.reset_token||token);
    sessionStorage.setItem('reset_role',d.role||'');
    location.href='reset-password.html?token='+encodeURIComponent(d.reset_token||token);
  }catch(x){
    resetMessage.textContent=x.message;
  }
};

const rr=document.getElementById('resetForm');
if(rr)rr.onsubmit=async e=>{
  e.preventDefault();

  if(newPassword.value!==confirmPassword.value){
    resetMessage.textContent='Passwords do not match';
    return;
  }

  try{
    const d=await api('/auth/reset',{
      method:'POST',
      body:JSON.stringify({reset_token:token,password:newPassword.value})
    });

    const role=d.role||sessionStorage.getItem('reset_role')||'';
    // A password reset invalidates all existing server sessions.
    // Clear any stale browser-side authentication before logging in again.
    localStorage.removeItem('njangi_token');
    localStorage.removeItem('njangi_user');
    sessionStorage.removeItem('reset_token');
    sessionStorage.removeItem('reset_role');
    sessionStorage.removeItem('reset_role_hint');

    resetMessage.textContent='Password changed. Redirecting to login…';

    setTimeout(()=>{
      location.href=role==='member'?'member-login.html':'login.html';
    },900);
  }catch(x){
    resetMessage.textContent=x.message;
  }
};