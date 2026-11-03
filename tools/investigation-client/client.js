'use strict';
const field = id => document.getElementById(id);
const message = field('message');
const output = field('output');
let auth;
let account;
let submissionKey = crypto.randomUUID();

function ids() {
  const tenant = field('tenant').value.trim();
  const client = field('client').value.trim();
  const api = field('api').value.trim();
  const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  if (![tenant, client, api].every(value => uuid.test(value))) throw new Error('Enter valid tenant, client, and API application IDs.');
  return {tenant, client, api};
}

async function signIn() {
  const {tenant, client, api} = ids();
  auth = new msal.PublicClientApplication({
    auth: {clientId: client, authority: `https://login.microsoftonline.com/${tenant}`, redirectUri: `${location.origin}/redirect.html`},
    cache: {cacheLocation: 'memoryStorage'},
  });
  await auth.initialize();
  const result = await auth.loginPopup({scopes: [`api://${api}/access_as_user`]});
  account = result.account;
  message.textContent = `Signed in as ${account.username}.`;
}

async function request(path, method = 'GET', body) {
  if (!auth || !account) throw new Error('Sign in first.');
  const {api} = ids();
  const request = {account, scopes: [`api://${api}/access_as_user`]};
  let token;
  try { token = await auth.acquireTokenSilent(request); }
  catch (error) {
    if (!(error instanceof msal.InteractionRequiredAuthError)) throw error;
    token = await auth.acquireTokenPopup(request);
  }
  const response = await fetch(`/api${path}`, {
    method, headers: {'Authorization': `Bearer ${token.accessToken}`, 'Content-Type': 'application/json'},
    ...(body ? {body: JSON.stringify(body)} : {}),
  });
  const content = await response.text();
  try { output.textContent = JSON.stringify(JSON.parse(content), null, 2); }
  catch { output.textContent = content; }
  if (!response.ok) throw new Error(`API returned HTTP ${response.status}. See response below.`);
  return content ? JSON.parse(content) : null;
}

function run(action) {
  return async () => {
    message.textContent = 'Working…';
    try { await action(); }
    catch (error) { message.textContent = error.message || 'Request failed.'; }
  };
}
field('signin').onclick = run(signIn);
field('submit').onclick = run(async () => {
  const result = await request('/investigations', 'POST', {
    submission_key: submissionKey, service: field('service').value, environment: field('environment').value,
    window_start: field('start').value, window_end: field('end').value,
  });
  if (result?.investigation_id) field('investigation').value = result.investigation_id;
  submissionKey = crypto.randomUUID();
  message.textContent = 'Investigation submitted.';
});
function investigationPath() {
  const id = field('investigation').value.trim();
  if (!/^[A-Za-z0-9-]+$/.test(id)) throw new Error('Enter an investigation ID.');
  return `/investigations/${id}`;
}
field('status').onclick = run(async () => { await request(investigationPath()); message.textContent = 'Status retrieved.'; });
field('report').onclick = run(async () => { await request(`${investigationPath()}/report`); message.textContent = 'Report retrieved.'; });
