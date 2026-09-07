// ============================================================
// MEMBER LOGIN
// Members are created by an admin. New members receive the
// default demo password: member123.
// ============================================================

function memberInitials(name){return String(name||'M').trim().split(/\s+/).slice(0,2).map(w=>w[0]).join('').toUpperCase()||'M';}

document.querySelectorAll('.password-toggle').forEach(button=>button.addEventListener('click',()=>{const input=document.getElementById(button.dataset.target);if(!input)return;const show=input.type==='password';input.type=show?'text':'password';button.textContent=show?'Hide':'Show';}));

const memberSelect=document.getElementById('memberSelect');
async function loadMemberOptions(){
  try{
    const data=await api('/members/public',{},'member');
    memberSelect.innerHTML='<option value="">Select your name…</option>';
    data.members.forEach(m=>{const option=document.createElement('option');option.value=m.id;option.textContent=m.name;memberSelect.appendChild(option);});
  }catch(err){memberSelect.innerHTML='<option value="">Unable to load members</option>';}
}

const form=document.getElementById('memberLoginForm');
form.addEventListener('submit',async e=>{
  e.preventDefault();
  const message=document.getElementById('memberLoginMessage'),selectError=document.getElementById('memberSelectError'),passwordError=document.getElementById('memberPasswordError'),password=document.getElementById('memberPassword');
  selectError.textContent='';passwordError.textContent='';showMessage(message,'');
  if(!memberSelect.value){selectError.textContent='Please select your name.';return;}
  if(!password.value){passwordError.textContent='Please enter your password.';return;}
  try{
    const result=await post('/auth/member-login',{memberId:memberSelect.value,password:password.value},'member');
    setToken(result.token,'member');
    showMessage(message,'Login successful! Opening your dashboard…','success');
    setTimeout(()=>location.href='member-dashboard.html',300);
  }catch(err){showMessage(message,err.message,'error');}
});

loadMemberOptions();
