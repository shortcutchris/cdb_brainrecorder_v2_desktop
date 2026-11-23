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
  const locked = !allowed('configure') || recordingAction || Boolean(window.roomActionBusy?.()) || Boolean(window.studioLiveBusy?.());
  const showQr = pending && !locked;
  dialog.dataset.view = showQr ? 'qr' : name ? 'signed-in' : 'signed-out';
  $('account-heading').textContent = showQr ? 'Mit Brain anmelden' : 'Brain-Konto';
  $('account-profile').hidden = showQr;
  $('account-identity-label').hidden = !name;
  $('account-full-name').textContent = name || 'Nicht angemeldet';
  $('account-environment').textContent = environment;
  $('account-login-details').hidden = !showQr;
  $('account-code').textContent = showQr ? login.code : '';
  if (showQr) {
   setIcon($('account-qr'), deviceLoginQr(login.url));
   $('account-url').textContent = login.url.replace('https://', '');
   $('account-expiry').textContent = 'Gültig bis ' + new Date(login.expires * 1000).toLocaleTimeString('de-DE', {hour:'2-digit', minute:'2-digit'});
  }
  let message = feedback || login.message || '';
  if (submitting) message = 'Bitte warten …';
  if (locked) message = online ? [state.capabilities.configure.reason, 'Kontowechsel gesperrt.'].filter(Boolean).join(' ') : 'Verbindung zum Recorder unterbrochen.';
  if ($('account-message').textContent !== message) $('account-message').textContent = message;
  action.disabled = submitting || locked;
  action.textContent = pending ? 'Anmeldung abbrechen' : name ? 'Abmelden' : 'Anmeldecode anzeigen';
 }
 async function changeAccount() {
  if (submitting || !allowed('configure') || recordingAction || window.roomActionBusy?.() || window.studioLiveBusy?.()) return;
  const c = state.cdb;
  const operation = c.login.state === 'pending' ? 'login/cancel' : c.identity ? 'logout' : 'login';
  if(operation==='logout'&&window.finishRoomSession){try{await window.finishRoomSession()}catch(error){feedback=error.message;renderAccount()}return;}
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
