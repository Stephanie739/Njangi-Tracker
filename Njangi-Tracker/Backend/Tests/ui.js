const { chromium } = require('playwright')  // npm i playwright require('playwright')require('playwright') npx playwright install chromium;
const FRONT = 'http://127.0.0.1:5500', API = 'http://127.0.0.1:8000/api';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const results = []; let shot = 0;
const ok = (name, cond, extra='') => { results.push(!!cond); console.log((cond?'PASS ':'FAIL ')+name+(cond||!extra?'':'  -> '+extra)); };
const stamp = Date.now();
const adminEmail = `admin${stamp}@test.cm`, memA = `alice${stamp}@test.cm`, memB = `bob${stamp}@test.cm`;

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();
  const dialogs = []; const jsErrors = [];
  page.on('dialog', async d => { dialogs.push(d.message()); await d.accept(); });
  page.on('pageerror', e => jsErrors.push(e.message));
  const lastDialog = () => dialogs[dialogs.length-1] || '';
  const go = async (p) => { await page.goto(`${FRONT}/${p}`); await page.waitForLoadState('networkidle'); };
  const snap = async (name) => { await page.screenshot({ path: `/home/claude/test/shot-${String(++shot).padStart(2,'0')}-${name}.png` }); };
  const api = async (path, method='GET', body, token) => { const r = await fetch(API+path,{method,headers:{'Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{})},body:body?JSON.stringify(body):undefined}); return {status:r.status, json: await r.json().catch(()=>({}))}; };

  // ---------- 1. registration: typo caught client-side, then real signup with group fields ----------
  await go('register.html');
  await page.fill('#registerName','Test Admin'); await page.fill('#registerEmail','nadaljunior999@gmailcom');
  await page.fill('#registerPhone','+237653039108'); await page.fill('#registerPassword','Secret123!'); await page.fill('#registerConfirm','Secret123!');
  await page.check('#agreeTerms'); await page.click('#registerForm button[type=submit]'); await sleep(400);
  const typoMsg = await page.textContent('#registerMessage');
  ok('register: missing dot in e-mail (gmailcom) shows a clear hint, not a generic error', /"\." seems to be missing/.test(typoMsg), typoMsg);
  await snap('register-typo');
  await page.fill('#registerEmail', adminEmail);
  await page.fill('#registerGroupName','Family Njangi'); await page.fill('#registerAmount','10000'); await page.selectOption('#registerFrequency','Weekly');
  await page.click('#registerForm button[type=submit]'); await page.waitForURL('**/dashboard.html', {timeout: 8000}).catch(()=>{});
  ok('register: valid signup lands on the dashboard', page.url().endsWith('dashboard.html'), page.url());
  await sleep(800);
  ok('shell: sidebar shows the real group name', /Family Njangi/.test(await page.textContent('.group-switcher')), await page.textContent('.group-switcher'));
  await snap('dashboard-empty');

  // ---------- 2. settings ----------
  await go('settings.html');
  ok('settings: page loads with admin data', (await page.inputValue('#setEmail')) === adminEmail && (await page.inputValue('#setGroupName')) === 'Family Njangi');
  ok('settings: group panel + email status visible for admin', await page.isVisible('#groupPanel') && await page.isVisible('#emailPanel'));
  ok('settings: e-mail shows "Not configured" when SMTP is missing', /Not configured/.test(await page.textContent('#emailStatus')));
  await page.fill('#setAmount','12000'); await page.click('#groupForm button[type=submit]'); await sleep(700);
  ok('settings: group saved', /Settings saved/.test(await page.textContent('#groupMsg')), await page.textContent('#groupMsg'));
  await page.fill('#curPassword','wrongpass'); await page.fill('#newPass','NewSecret456!'); await page.fill('#newPass2','NewSecret456!');
  await page.click('#passwordForm button[type=submit]'); await sleep(600);
  ok('settings: wrong current password is refused', /incorrect/.test(await page.textContent('#passwordMsg')), await page.textContent('#passwordMsg'));
  await page.fill('#curPassword','Secret123!');
  await page.click('#passwordForm button[type=submit]'); await sleep(700);
  ok('settings: password changed', /Password changed/.test(await page.textContent('#passwordMsg')), await page.textContent('#passwordMsg'));
  await snap('settings');
  const bad = await api('/auth/login','POST',{email:adminEmail,password:'Secret123!'}); const good = await api('/auth/login','POST',{email:adminEmail,password:'NewSecret456!'});
  ok('settings: old password no longer works, new one does', bad.status===401 && good.status===200);
  const adminToken = good.json.token;

  // ---------- 3. members through the UI ----------
  await go('members.html');
  await page.click('#openMemberModal'); await sleep(200);
  ok('members: add form is pre-filled (expected = group default, position = next)', (await page.inputValue('#memberExpected'))==='12000' && (await page.inputValue('#memberPosition'))==='1', `${await page.inputValue('#memberExpected')} / ${await page.inputValue('#memberPosition')}`);
  await page.fill('#memberName','Alice Member'); await page.fill('#memberPhone','671111111'); await page.fill('#memberEmail',memA); await page.fill('#memberPassword','AlicePass1!');
  await page.click('#memberForm button[type=submit]'); await sleep(900);
  ok('members: add with temporary password -> no "undefined" in message', /Alice Member was added/.test(lastDialog()) && !/undefined/.test(lastDialog()), lastDialog());
  await page.click('#openMemberModal'); await sleep(150);
  await page.fill('#memberName','Bob Member'); await page.fill('#memberPhone','672222222'); await page.fill('#memberEmail',memB);
  await page.click('#memberForm button[type=submit]'); await sleep(900);
  ok('members: add without password explains Forgot password flow', /Forgot password/.test(lastDialog()) && !/undefined/.test(lastDialog()), lastDialog());
  ok('members: both members listed', /Alice Member/.test(await page.textContent('#memberTable')) && /Bob Member/.test(await page.textContent('#memberTable')));
  await page.click('#openMemberModal'); await page.fill('#memberName','Dup'); await page.fill('#memberPhone','6'); await page.fill('#memberEmail',memA); await page.fill('#memberPosition','1');
  await page.click('#memberForm button[type=submit]'); await sleep(700);
  ok('members: duplicate e-mail / taken position gives a readable error', /already/.test(lastDialog()), lastDialog());
  await page.click('#closeMemberModal');
  await snap('members');
  const tok = adminToken; const list = (await api('/members','GET',null,tok)).json.members;
  const A = list.find(m=>m.email===memA), B = list.find(m=>m.email===memB);

  // expected amounts must be visible even when there is no active cycle (regression: they showed 0)
  ok('members: expected contribution is shown (not 0) while no cycle is open', /12[\s\u202f\u00a0]?000/.test(await page.textContent('#memberTable')), (await page.textContent('#memberTable')).slice(0,160));
  await page.locator('#memberTable tr', { hasText: 'Alice Member' }).locator('button', { hasText: 'Edit' }).click(); await sleep(200);
  await page.fill('#memberPhone','670000001'); await page.click('#memberForm button[type=submit]'); await sleep(800);
  const afterEdit = (await api('/members','GET',null,tok)).json.members.find(m=>m.email===memA);
  ok('members: editing a member keeps the expected contribution (was reset to 0 before)', Number(afterEdit.expected)===12000 && afterEdit.phone==='670000001', JSON.stringify({e:afterEdit.expected,p:afterEdit.phone}));

  // ---------- 4. cycles ----------
  await go('cycles.html');
  await page.click('#openCycle'); await sleep(250);
  const recipientVal = await page.inputValue('#cycleRecipient');
  ok('cycles: first recipient is suggested by rotation (position 1)', String(A.id) === recipientVal, `${recipientVal} vs ${A.id}`);
  const s = await page.inputValue('#cycleStart'), e2 = await page.inputValue('#cycleEnd');
  ok('cycles: end date defaults to start + 7 days (Weekly)', Math.round((new Date(e2)-new Date(s))/864e5) === 7, `${s} -> ${e2}`);
  ok('cycles: target pool in the form = sum of expected amounts (24 000)', /24[\s\u202f\u00a0]?000/.test(await page.inputValue('#cycleTargetInput')), await page.inputValue('#cycleTargetInput'));
  await snap('cycle-modal');
  await page.click('#cycleForm button[type=submit]'); await sleep(900);
  ok('cycles: cycle created', /Cycle created/.test(lastDialog()), lastDialog());

  // ---------- 5. contributions + delete recomputes status ----------
  await go('contributions.html');
  await page.click('#openContribution'); await page.selectOption('#memberSelect', String(A.id)); await page.fill('#amountInput','12000');
  await page.click('#contributionForm button[type=submit]'); await sleep(900);
  ok('contributions: payment recorded through the form', /recorded/.test(lastDialog()), lastDialog());
  await page.click('#openContribution'); await page.selectOption('#memberSelect', String(B.id)); await page.fill('#amountInput','5000');
  await page.click('#contributionForm button[type=submit]'); await sleep(700);
  await page.click('#openContribution'); await page.selectOption('#memberSelect', String(B.id)); await page.fill('#amountInput','7000');
  await page.click('#contributionForm button[type=submit]'); await sleep(700);
  let contribs = (await api('/contributions','GET',null,tok)).json.contributions.filter(c=>c.member_id===B.id);
  ok('contributions: two partial payments add up to Paid', contribs.length===2 && contribs.every(c=>c.status==='Paid'), JSON.stringify(contribs.map(c=>c.status)));
  const delBtn = page.locator('#contributionTable tr', { hasText: 'Bob Member' }).first().locator('button');
  await delBtn.click(); await sleep(800);
  contribs = (await api('/contributions','GET',null,tok)).json.contributions.filter(c=>c.member_id===B.id);
  ok('contributions: deleting a payment re-evaluates the remaining one (no stale "Paid")', contribs.length===1 && contribs[0].status==='Partial', JSON.stringify(contribs.map(c=>c.status)));
  // pay the rest again
  await page.click('#openContribution'); await page.selectOption('#memberSelect', String(B.id)); await page.fill('#amountInput','12000');
  await page.click('#contributionForm button[type=submit]'); await sleep(700);
  await snap('contributions');
  const bad2 = await api('/contributions','POST',{member_id:A.id,cycle_id:1,amount:'abc'},tok);
  ok('contributions: non-numeric amount gives a readable error (not a Python message)', bad2.status===400 && /Amount must be a number/.test(bad2.json.error), bad2.json.error);

  // ---------- 6. history filters ----------
  await go('history.html');
  ok('history: no dead "Clear Records" button any more', (await page.locator('#clearHistory').count())===0);
  const before = await page.locator('#historyBody tr').count();
  await page.selectOption('#memberFilter', String(A.id)); await sleep(200);
  const afterMember = await page.locator('#historyBody tr').count();
  ok('history: member filter works', before>afterMember && afterMember===1, `${before} -> ${afterMember}`);
  await page.click('#resetFilter'); await sleep(200);
  ok('history: reset restores all rows', (await page.locator('#historyBody tr').count())===before);
  await page.fill('#dateFilter','2001-01-01'); await sleep(200);
  ok('history: date filter works (no rows shows empty message)', (await page.locator('#historyBody tr').count())===0 && await page.isVisible('#emptyHistory'));
  await snap('history');

  // ---------- 7. close cycle, member login with temp password, loan lifecycle, alerts ----------
  await go('cycles.html'); await sleep(700);
  ok('cycles: active-cycle panel shows real data (pool, 100% progress, dates, paid members)', !/^0 FCFA/.test((await page.textContent('#cyclePool')).trim()) && (await page.textContent('#progressPercent')).trim()==='100%' && /2 \/ 2/.test(await page.textContent('#paidMembers')) && (await page.textContent('#startDate')).trim()!=='-', `${await page.textContent('#cyclePool')} | ${await page.textContent('#progressPercent')} | ${await page.textContent('#paidMembers')}`);
  await page.fill('#topSearch','zzz'); await sleep(200);
  const hidden = await page.locator('#cycleTable tr').count();
  await page.fill('#topSearch','alice'); await sleep(200);
  ok('cycles: top search filters the table', (await page.locator('#cycleTable tr').count())===1 && /Alice/.test(await page.textContent('#cycleTable')), 'rows for zzz='+hidden);
  await page.fill('#topSearch','');
  await snap('cycles-active');
  await page.click('#closeCycleButton'); await sleep(900);
  ok('cycles: closing a fully paid cycle works (with confirmation)', /closed successfully/.test(lastDialog()), lastDialog());
  const closedDel = await api('/contributions/'+contribs[0].id,'DELETE',null,tok);
  ok('contributions: payments of a closed cycle cannot be deleted', closedDel.status===409, closedDel.json.error);

  const mctx = await browser.newContext({ viewport: { width: 1280, height: 900 } }); const mp = await mctx.newPage();
  const mdialogs=[]; mp.on('dialog', async d=>{mdialogs.push(d.message()); await d.accept();});
  await mp.goto(`${FRONT}/member-login.html`); await mp.fill('#memberCode', memA); await mp.fill('#memberPassword','AlicePass1!');
  await mp.click('#memberLoginButton'); await mp.waitForURL('**/member-dashboard.html',{timeout:8000}).catch(()=>{});
  ok('member login with the temporary password set by the admin', mp.url().endsWith('member-dashboard.html'), mp.url());
  await sleep(900);
  await mp.fill('#loanAmount','5000'); await mp.fill('#loanReason','School fees'); await mp.click('#memberLoanForm button[type=submit]'); await sleep(1000);
  ok('member: loan request submitted', /submitted/i.test(await mp.textContent('#loanMessage')), await mp.textContent('#loanMessage'));
  await mp.screenshot({path:'/home/claude/test/shot-member-dashboard.png'});

  await go('dashboard.html'); await sleep(800);
  ok('alerts: admin bell shows the pending loan request', /pending loan/.test(await page.getAttribute('.notification','title')||''), await page.getAttribute('.notification','title'));
  await go('loans.html'); await sleep(800);
  await page.locator('#loanTableBody button', { hasText: 'Approve' }).first().click().catch(async()=>{ await page.locator('button', { hasText: 'Approve' }).first().click(); });
  await sleep(900);
  ok('loans: admin approves the request', /approved/i.test(lastDialog()), lastDialog());
  await page.locator('button', { hasText: 'Repay' }).first().click(); await sleep(300);
  ok('loans: Repay opens a modal (no browser prompt)', await page.isVisible('#paymentModal.show') || await page.isVisible('#paymentAmount'));
  await snap('loans-repay-modal');
  await page.fill('#paymentAmount','1000'); await page.click('#paymentForm button[type=submit]'); await sleep(900);
  ok('loans: repayment recorded through the modal', /Repayment recorded/.test(lastDialog()), lastDialog());
  await page.fill('#memberSearch','nobody-here'); await sleep(250);
  ok('loans: top search filters the loan table', (await page.locator('#loanTableBody tr').count())===0 || /No loan/i.test(await page.textContent('#emptyState')));
  await page.fill('#memberSearch','');
  await snap('loans');

  // ---------- 8. member settings: change own password ----------
  await mp.goto(`${FRONT}/settings.html`); await mp.waitForLoadState('networkidle'); await sleep(600);
  ok('member settings: group panel hidden, name read-only', !(await mp.isVisible('#groupPanel')) && (await mp.getAttribute('#setName','readonly'))!==null);
  await mp.fill('#curPassword','AlicePass1!'); await mp.fill('#newPass','AliceNew123!'); await mp.fill('#newPass2','AliceNew123!');
  await mp.click('#passwordForm button[type=submit]'); await sleep(800);
  ok('member settings: password changed', /Password changed/.test(await mp.textContent('#passwordMsg')), await mp.textContent('#passwordMsg'));
  const relog = await api('/member/login','POST',{email:memA,password:'AliceNew123!'});
  ok('member can sign in with the new password', relog.json.ok === true);

  // ---------- 9. session expiry sends you back to login ----------
  await go('members.html');
  const pageToken = await page.evaluate(() => localStorage.getItem('njangi_token'));
  await api('/auth/logout','POST',{},pageToken);          // the server revokes the browser's own session
  await go('members.html'); await sleep(1200);
  ok('expired/revoked session: page redirects to the login page', /login\.html/.test(page.url()), page.url());

  // ---------- 10. security: public member list gone, brute-force throttle ----------
  const pub = await api('/members/public');
  ok('security: /members/public no longer leaks members (404/401)', pub.status===404 || pub.status===401, 'status '+pub.status);
  let last = 0; for (let i=0;i<12;i++){ last = (await api('/auth/login','POST',{email:'nobody@test.cm',password:'x'})).status; }
  ok('security: repeated wrong logins are throttled (429)', last===429, 'last status '+last);
  const health = await api('/health');
  ok('health reports email_configured (false in this test)', health.json.email_configured===false);

  // ---------- 11. password reset through the UI (dev PIN mode) ----------
  await go('forgot-password.html?role=member'); await page.fill('#resetEmail', memB); await page.click('#forgotForm button[type=submit]'); await sleep(800);
  const pinMsg = await page.textContent('#resetMessage'); const pin=(pinMsg.match(/(\d{6})/)||[])[1];
  ok('reset: PIN issued (dev mode shows it)', !!pin, pinMsg);
  await page.waitForURL('**/verify-pin.html',{timeout:8000}).catch(()=>{});
  ok('reset: verify page offers "request a new PIN" link', await page.isVisible('a[href="forgot-password.html"]'));
  await page.fill('#pin', pin); await page.click('#verifyForm button[type=submit]'); await page.waitForURL('**/reset-password.html*',{timeout:8000}).catch(()=>{});
  await page.fill('#newPassword','BobNewPass9!'); await page.fill('#confirmPassword','BobNewPass9!'); await page.click('#resetForm button[type=submit]'); await sleep(1500);
  const bobLogin = await api('/member/login','POST',{email:memB,password:'BobNewPass9!'});
  ok('reset: member Bob set his own password via PIN and can log in', bobLogin.json.ok===true);

  ok('no uncaught JavaScript errors on any page', jsErrors.length===0, jsErrors.join(' | '));
  await browser.close();
  const failed = results.filter(r=>!r).length;
  console.log(`\n${results.length-failed}/${results.length} checks passed`);
  process.exit(failed?1:0);
})().catch(e => { console.error('TEST CRASH', e); process.exit(2); });
