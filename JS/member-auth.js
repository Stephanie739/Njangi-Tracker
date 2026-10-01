document.querySelectorAll('.password-toggle').forEach(b=>b.onclick=()=>{const i=document.getElementById(b.dataset.target);i.type=i.type==='password'?'text':'password';b.textContent=i.type==='password'?'Show':'Hide'});

const form=document.getElementById('memberLoginForm');
const groupPicker=document.getElementById('memberGroupPicker');
const groupList=document.getElementById('memberGroupList');
const groupPickerBack=document.getElementById('memberGroupPickerBack');
let pendingCredentials=null;

async function completeMemberLogin(email,password,groupId){
  const msg=document.getElementById('memberLoginMessage');
  try{
    const body={email,password};
    if(groupId!==undefined) body.group_id=groupId;
    const d=await api('/member/login',{method:'POST',body:JSON.stringify(body)});
    if(d.choose_group){
      showGroupPicker(d.groups,email,password);
      return;
    }
    saveSession(d);
    location.href='member-dashboard.html';
  }catch(x){
    msg.textContent=x.message;
    msg.className='form-message error';
  }
}

function showGroupPicker(groups,email,password){
  pendingCredentials={email,password};
  groupList.innerHTML='';
  groups.forEach(g=>{
    const btn=document.createElement('button');
    btn.type='button';
    btn.className='btn btn-primary group-picker-option';
    btn.textContent=g.group_name;
    btn.onclick=()=>completeMemberLogin(pendingCredentials.email,pendingCredentials.password,g.group_id);
    groupList.appendChild(btn);
  });
  form.hidden=true;
  groupPicker.hidden=false;
}

if(groupPickerBack)groupPickerBack.onclick=()=>{
  groupPicker.hidden=true;
  form.hidden=false;
  pendingCredentials=null;
};

if(form)form.onsubmit=async e=>{
  e.preventDefault();
  await completeMemberLogin(memberEmail.value,memberPassword.value);
};