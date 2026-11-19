/* One account control follows the active workspace and its existing state poll. */
(() => {
 const button = $('account-shortcut');
 const dialog = $('account-dialog');
 const action = $('account-action');
 let submitting = false;
 let feedback = '';

 function placeButton() {
  const page = document.body.dataset.workspace;
  let header;
  if (page === 'detail') header = document.querySelector(document.body.classList.contains('editing-meeting') ? '.meeting-header' : '.library-navigation');
  else if (page === 'recorder') header = document.querySelector('.content').hidden
   ? $('recorder-ready') : document.querySelector('.meeting-header');
  else header = $(page)?.querySelector('.dialog-heading, .queue-heading');
  if (header && button.parentElement !== header) header.append(button);
 }
 function renderAccount() {
  placeButton();
  const c = state?.cdb;
  button.hidden = !c;
  if (!c) return;
  const environment = brainEnvironment(c.config.server);
  const name = c.identity?.name?.trim() || (c.identity ? 'Firmenkonto' : '');
  const label = name || 'Brain anmelden';
  $('account-short-name').textContent = label;
  $('account-short-environment').textContent = environment;
  button.setAttribute('aria-label', 'Brain-Konto · ' + label + ' · ' + environment);
  if (!dialog.open) return;

  const login = c.login;
  const pending = login.state === 'pending';
  const locked = !allowed('configure');
  $('account-full-name').hidden = pending && !locked;
  $('account-full-name').textContent = name || 'Nicht angemeldet';
  $('account-environment').textContent = 'Brain · ' + environment;
  $('account-login-details').hidden = !pending || locked;
  $('account-code').textContent = pending && !locked ? login.code : '';
  if (pending && !locked) {
   setIcon($('account-qr'), deviceLoginQr(login.url));
   $('account-url').textContent = login.url.replace('https://', '');
   $('account-expiry').textContent = 'Gültig bis ' + new Date(login.expires * 1000).toLocaleTimeString('de-DE', {hour:'2-digit', minute:'2-digit'});
  }
  let message = feedback || login.message || '';
  if (submitting) message = 'Bitte warten …';
  if (locked) message = online ? (state.capabilities.configure.reason || 'Kontowechsel gerade gesperrt.') : 'Verbindung zum Recorder unterbrochen.';
  $('account-message').textContent = message;
  action.disabled = submitting || locked;
  action.textContent = pending ? 'Anmeldung abbrechen' : name ? 'Abmelden' : 'Anmeldecode anzeigen';
 }
 async function changeAccount() {
  if (submitting || !allowed('configure')) return;
  const c = state.cdb;
  const operation = c.login.state === 'pending' ? 'login/cancel' : c.identity ? 'logout' : 'login';
  submitting = true;
  feedback = '';
  renderAccount();
  try {
   const result = await api('/api/cdb/' + operation, {});
   state.cdb = result;
   if (operation === 'logout') feedback = 'Du bist abgemeldet.';
   if (operation === 'login/cancel') feedback = 'Anmeldung abgebrochen.';
   renderState();
   await poll();
  } catch (error) {
   feedback = error.message;
  } finally {
   submitting = false;
   renderAccount();
  }
 }
 button.onclick = () => {
  feedback = '';
  dialog.showModal();
  renderAccount();
  if (!state.cdb.identity && state.cdb.login.state !== 'pending') void changeAccount();
 };
 action.onclick = changeAccount;
 $('account-close').onclick = () => dialog.close();
 const previousRender = renderState;
 renderState = function() { previousRender(); renderAccount(); };
 new MutationObserver(placeButton).observe(document.body, {attributes:true, attributeFilter:['data-workspace','class']});
 renderAccount();
})();
