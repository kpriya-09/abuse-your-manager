'use strict';
const $ = (selector, root = document) => root.querySelector(selector);
const state = { user: null, view: 'feed', search: '', feedCursor: null, posts: [], pending: null, request: 0 };
const modal = $('#modal');
let lastFocus = null;
const escapeHTML = text => String(text).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function toast(message) { $('#toast').textContent = message; $('#toast').hidden = false; clearTimeout(toast.timer); toast.timer = setTimeout(() => $('#toast').hidden = true, 4500); }
async function api(path, payload) {
  const response = await fetch('/api' + path, payload === undefined ? {} : { method: 'POST', headers: {'Content-Type': 'application/json', 'X-Requested-With': 'AYM'}, body: JSON.stringify(payload) });
  const data = await response.json();
  if (!response.ok) { const error = new Error(data.error || 'Something went wrong. Please try again.'); error.status = response.status; throw error; }
  return data;
}
function age(timestamp) { const hours = Math.max(0, Math.floor((Date.now() / 1000 - timestamp) / 3600)); return hours === 0 ? 'just now' : hours < 24 ? `${hours}h ago` : `${Math.floor(hours / 24)}d ago`; }
function listing(name) { return $('#' + (state.view === 'search' ? 'search-' : '') + name); }
function setView(view) {
  clearTimeout(state.searchTimer);
  if (view === 'feed') $('#search').value = '';
  state.search = $('#search').value.trim();
  state.view = view;
  $('#feed-panel').hidden = view !== 'feed';
  $('#search-panel').hidden = view !== 'search';
  return loadPosts();
}
function metadata(post) { return `<div class="post-meta"><span class="avatar" aria-hidden="true">~</span><span class="alias">${escapeHTML(post.alias)}</span><span class="post-time">${age(post.created_at)}</span>${post.demo ? '<span class="example">example</span>' : ''}</div>`; }
function actions(post, detail = false) { return `<div class="post-actions"><button class="vote" data-vote="${post.id}" aria-pressed="${post.voted}" aria-label="Same here: ${post.votes} votes">↑ &nbsp;${post.votes} <span>· Same here</span></button>${detail ? '' : `<a href="/post/${post.id}" data-post="${post.id}" data-comment-count="${post.id}">◯ &nbsp;${post.comments} replies</a>`}<button class="share" data-share="${post.id}">↗ Share</button>${detail ? `<button data-report="${post.id}">Report</button>` : ''}</div>`; }
function renderPosts() {
  listing('posts').innerHTML = state.posts.length ? state.posts.map(post => `<article class="post" data-id="${post.id}">${metadata(post)}<h2><a href="/post/${post.id}" data-post="${post.id}">${escapeHTML(post.title)}</a></h2><p class="post-excerpt">${escapeHTML(post.body)}</p>${actions(post)}</article>`).join('') : `<div class="empty"><h2>${state.view === 'search' ? 'No matching titles.' : 'A rare moment of silence.'}</h2><p>${state.view === 'search' ? 'Try a different title fragment.' : 'The first story could be yours.'}</p><button class="button" data-action="compose">Tell your story ↗</button></div>`;
}
async function loadPosts(append = false) {
  const requestId = ++state.request;
  const search = state.view === 'search' ? state.search : '';
  const moreButton = listing('load-more');
  listing('active-filter').hidden = true;
  if (state.view === 'search' && !search) {
    state.posts = [];
    listing('posts').innerHTML = '<div class="empty"><h2>Something on your mind?</h2><p>Enter part of a title to find a story.</p></div>';
    moreButton.hidden = true;
    moreButton.disabled = false;
    return;
  }
  const offset = append ? state.posts.length : 0;
  const query = new URLSearchParams({q: search, offset});
  const endpoint = state.view === 'feed'
    ? '/feed' + (append && state.feedCursor ? '?cursor=' + encodeURIComponent(state.feedCursor) : '')
    : '/posts?' + query;
  moreButton.disabled = true;
  if (!append) {
    moreButton.hidden = true;
    if (state.view === 'feed') {
      delete moreButton.dataset.refresh;
      moreButton.textContent = 'More from the break room ↓';
    }
    listing('posts').innerHTML = '<div class="empty">Loading stories...</div>';
  }
  try {
    const data = await api(endpoint);
    if (requestId !== state.request) return;
    state.posts = append ? [...state.posts, ...data.posts] : data.posts;
    if (state.view === 'feed') state.feedCursor = data.next_cursor;
    renderPosts(); moreButton.hidden = !data.has_more;
    listing('active-filter').hidden = !search;
    listing('active-filter').innerHTML = `Titles containing “${escapeHTML(search)}”<button data-action="clear">Clear search ×</button>`;
  } catch (error) {
    if (requestId !== state.request) return;
    if (!append) listing('posts').innerHTML = `<div class="empty"><h2>The break room is offline.</h2><p>${escapeHTML(error.message)}</p><button class="button outline" data-action="retry">Try again</button></div>`;
    else {
      toast(error.message);
      if (error.status === 410) {
        moreButton.textContent = 'Refresh feed';
        moreButton.dataset.refresh = 'true';
      }
    }
  } finally { if (requestId === state.request) moreButton.disabled = false; }
}
function updateAccount() { $('#auth-button').hidden = !state.user; $('#auth-button').textContent = 'Account'; $('#auth-button').title = state.user ? `Account: ${state.user.alias}` : 'Access your anonymous account'; }
function openModal(html) { if (!modal.open) lastFocus = document.activeElement; $('#modal-content').innerHTML = html; if (!modal.open) modal.showModal(); document.body.classList.add('modal-open'); const target = $('input,textarea,select', modal); if (target) target.focus(); }
function closeModal() { modal.close(); }
modal.addEventListener('close', () => { document.body.classList.remove('modal-open'); state.pending = null; if (location.pathname.startsWith('/post/')) history.pushState({}, '', '/'); lastFocus?.focus(); });
$('.modal-close').addEventListener('click', closeModal);
modal.addEventListener('click', event => { if (event.target === modal) { const r = modal.getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) closeModal(); } });
function requireAuth(action) { if (state.user) action(); else { state.pending = action; showAuth(); } }
let authProviders;
let googleScript;
function loadGoogleScript() {
  if (window.google?.accounts?.id) return Promise.resolve();
  if (googleScript) return googleScript;
  googleScript = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client'; script.async = true;
    const timeout = setTimeout(() => reject(new Error('Google sign-in was blocked or timed out. You can still use a private login below.')), 8000);
    script.onload = () => { clearTimeout(timeout); resolve(); };
    script.onerror = () => { clearTimeout(timeout); reject(new Error('Google sign-in was blocked. You can still use a private login below.')); };
    document.head.appendChild(script);
  });
  return googleScript;
}
async function setupGoogleAuth() {
  const mount = $('#google-signin', modal);
  if (!mount) return;
  mount.innerHTML = '<span class="google-loading">Loading Google sign-in…</span>';
  try {
    authProviders ||= await api('/auth/providers');
    if (!authProviders.google.enabled) { mount.hidden = true; $('.auth-divider', modal).hidden = true; return; }
    await loadGoogleScript();
    for (let i = 0; i < 20 && !window.google?.accounts?.id; i++) await new Promise(resolve => setTimeout(resolve, 100));
    if (!window.google?.accounts?.id) throw new Error('Google sign-in did not load.');
    google.accounts.id.initialize({client_id: authProviders.google.client_id, callback: handleGoogleCredential});
    mount.replaceChildren();
    google.accounts.id.renderButton(mount, {theme: 'outline', size: 'large', shape: 'rectangular', width: Math.min(360, mount.clientWidth)});
  } catch (error) { googleScript = null; mount.innerHTML = `<span class="google-unavailable">${escapeHTML(error.message)}</span><button type="button" class="google-retry">Retry Google</button>`; $('.google-retry', mount)?.addEventListener('click', setupGoogleAuth, {once:true}); }
}
async function handleGoogleCredential(result) {
  const errorBox = $('.form-error', modal);
  try {
    const auth = await api('/auth/google', {credential: result.credential});
    state.user = auth.user; updateAccount(); const pending = state.pending; state.pending = null;
    if (pending) pending(); else closeModal();
    toast(`You’re ${state.user.alias}. Welcome to the break room.`); await loadPosts();
  } catch (error) { if (errorBox) errorBox.textContent = error.message; }
}
function showAuth(mode = 'signup') {
  const signup = mode === 'signup';
  openModal(`<span class="eyebrow">YOUR NAME STAYS OUT OF IT.</span><h2 id="modal-title">${signup ? 'Clock in. Go incognito.' : 'Back for another break?'}</h2><p>${signup ? 'Use Google for a quick start, or pick a private login. Either way, the room only sees your random alias.' : 'Use Google or your private login to pick up where you left off.'}</p><div id="google-signin" class="google-signin" aria-label="Google sign in"></div><div class="auth-divider"><span>or use a private login</span></div><form id="auth-form"><label>Private login<input name="login" required minlength="3" maxlength="40" autocomplete="username" autocapitalize="none" spellcheck="false" pattern="[A-Za-z0-9_.\-]+" placeholder="Something only you know"></label><label>Password<input name="password" type="password" required minlength="12" maxlength="128" autocomplete="${signup ? 'new-password' : 'current-password'}" placeholder="At least 12 characters"></label><p class="form-note">${signup ? 'Save these credentials. Password recovery is not available in this version.' : 'Private logins are case-insensitive.'}</p><p class="form-error" role="alert"></p><button class="button" type="submit">${signup ? 'Get my anonymous name' : 'Sign in'} <span>↗</span></button></form><button class="switch-auth">${signup ? 'Already have an account? Sign in' : 'New around here? Create an account'}</button>`);
  setupGoogleAuth();
  $('.switch-auth', modal).addEventListener('click', () => showAuth(signup ? 'login' : 'signup'));
  $('#auth-form').addEventListener('submit', async event => {
    event.preventDefault(); const form = event.currentTarget; const button = $('button[type=submit]', form); button.disabled = true;
    try { const result = await api('/auth/' + mode, Object.fromEntries(new FormData(form))); state.user = result.user; updateAccount(); const pending = state.pending; state.pending = null; if (pending) pending(); else closeModal(); toast(`You’re ${state.user.alias}. Welcome to the break room.`); await loadPosts(); }
    catch (error) { $('.form-error', form).textContent = error.message; } finally { button.disabled = false; }
  });
}
let storyDraft = {title: '', body: '', };
function showCompose() {
  openModal(`<span class="eyebrow">SENDING AS ${escapeHTML(state.user.alias)}</span><h2 id="modal-title">Okay. What happened?</h2><p>Let it out. Leave out names, company identifiers and contact details.</p><form id="post-form"><label>Give it a headline<input name="title" required minlength="8" maxlength="160" placeholder="The email that finally broke me…" value="${escapeHTML(storyDraft.title)}"></label><label>The whole story<textarea name="body" required minlength="20" maxlength="5000" placeholder="You’re among people who get it.">${escapeHTML(storyDraft.body)}</textarea></label><p class="form-note">Public post · Anonymous alias · Be decent to each other</p><p class="form-error" role="alert"></p><button class="button" type="submit">Get it off my chest <span>↗</span></button></form>`);
  const form = $('#post-form');
  form.addEventListener('input', () => storyDraft = Object.fromEntries(new FormData(form)));
  form.addEventListener('submit', async event => {
    event.preventDefault(); const button = $('button[type=submit]', form); button.disabled = true;
    try { const result = await api('/posts', Object.fromEntries(new FormData(form))); storyDraft = {title:'', body:'', }; await setView('feed'); await showPost(result.id); toast('It’s out there. Take a breath.'); }
    catch (error) { $('.form-error', form).textContent = error.message; if (error.status === 401) { state.user = null; updateAccount(); state.pending = showCompose; showAuth('login'); } }
    finally { button.disabled = false; }
  });
}
let detailPost = null;
let detailRequest = 0;
function cachedPost(id) { return state.posts.find(post => post.id === id); }
function updateVoteUI(id, voted, votes) {
  const cached = cachedPost(id);
  if (cached) { cached.voted = voted; cached.votes = votes; }
  if (detailPost?.id === id) { detailPost.voted = voted; detailPost.votes = votes; }
  document.querySelectorAll(`[data-vote="${id}"]`).forEach(button => {
    button.setAttribute('aria-pressed', String(voted));
    button.setAttribute('aria-label', `Same here: ${votes} votes`);
    button.innerHTML = `↑ &nbsp;${votes} <span>· Same here</span>`;
  });
}
function updateCommentCount(id, comments) {
  const cached = cachedPost(id);
  if (cached) cached.comments = comments;
  if (detailPost?.id === id) detailPost.comments = comments;
  document.querySelectorAll(`[data-comment-count="${id}"]`).forEach(link => { link.innerHTML = `◯ &nbsp;${comments} replies`; });
  const detailCount = $('.thread-divider span', modal);
  if (detailPost?.id === id && detailCount) detailCount.textContent = `(${comments})`;
}
async function showPost(id, push = true) {
  const requestId = ++detailRequest;
  openModal('<h2 id="modal-title">Pulling up the story…</h2>');
  try {
    const result = await api('/posts/' + id);
    if (requestId !== detailRequest || !modal.open) return;
    detailPost = result.post;
    if (push && location.pathname !== '/post/' + id) history.pushState({}, '', '/post/' + id);
    openModal(`${metadata(result.post)}<h2 id="modal-title">${escapeHTML(result.post.title)}</h2><p class="modal-post-body">${escapeHTML(result.post.body)}</p>${actions(result.post, true)}<div class="thread-divider">The replies <span>(${result.post.comments})</span></div><div id="comments">${result.comments.length ? result.comments.map(comment => `<article class="comment"><span class="alias">${escapeHTML(comment.alias)}</span><p>${escapeHTML(comment.body)}</p></article>`).join('') : '<p class="comment-empty">First chair is open. Add your two cents.</p>'}</div>${state.user ? '<form id="comment-form"><label>Your reply<textarea name="body" required minlength="2" maxlength="2000" placeholder="A little solidarity goes a long way."></textarea></label><p class="form-error" role="alert"></p><button type="submit" class="button">Add my two cents ↗</button></form>' : `<button class="button" data-join="${id}">Sign in to reply ↗</button>`}`);
    const form = $('#comment-form');
    if (form) form.addEventListener('submit', async event => {
      event.preventDefault(); const button = $('button', form); const body = new FormData(form).get('body').trim();
      if (!body) return;
      button.disabled = true; $('.form-error', form).textContent = '';
      const comments = $('#comments', modal); $('.comment-empty', comments)?.remove();
      const pending = document.createElement('article'); pending.className = 'comment pending-comment';
      pending.innerHTML = `<span class="alias">${escapeHTML(state.user.alias)}</span><p>${escapeHTML(body)}</p><small class="comment-status">Sending…</small>`;
      comments.appendChild(pending); form.reset(); updateCommentCount(id, (detailPost?.comments || 0) + 1);
      try {
        const result = await api('/posts/' + id + '/comments', {body});
        pending.classList.remove('pending-comment'); $('.comment-status', pending)?.remove();
        if (result.comment?.id) pending.dataset.id = result.comment.id;
      }
      catch (error) {
        pending.remove(); updateCommentCount(id, Math.max(0, (detailPost?.comments || 1) - 1));
        if (!comments.children.length) comments.innerHTML = '<p class="comment-empty">First chair is open. Add your two cents.</p>';
        $('[name="body"]', form).value = body; $('.form-error', form).textContent = error.message;
      }
      finally { button.disabled = false; }
    });
    $('.modal-close').focus();
  } catch (error) { if (requestId === detailRequest) openModal(`<h2 id="modal-title">Story unavailable.</h2><p>${escapeHTML(error.message)}</p>`); }
}
function showRules() { openModal('<span class="eyebrow">OUR VERY SHORT EMPLOYEE HANDBOOK</span><h2 id="modal-title">Roast the situation.<br>Respect the human.</h2><ol class="rules-list"><li><strong>Keep people unidentifiable.</strong> No real names, company identifiers, contact details or identifying screenshots.</li><li><strong>Tell your own story.</strong> Vent about what happened to you. Don’t invent accusations or rally people against someone.</li><li><strong>No threats or hate.</strong> Frustration belongs here. Threats, slurs and harassment don’t.</li><li><strong>Give people room to vent.</strong> You can disagree without making someone’s day worse.</li><li><strong>See something off?</strong> Open a story and use Report. Reports enter an operator review queue.</li></ol><p>This is a place for workplace stories and solidarity.</p>'); }
function showPrivacy() { openModal('<span class="eyebrow">ANONYMITY, WITHOUT THE FINE PRINT</span><h2 id="modal-title">An alias. Not a disguise.</h2><p>Your private login and password hash are stored separately from the public story fields. If you use Google, we store a one-way internal identifier instead of your Google name, email or profile photo. Your randomly assigned alias is visible on every story and reply you write.</p><p>This is pseudonymous, not untraceable: the operator can link an account to its posts. Google can know you signed into this service. Your writing can identify you, too. Leave out personal and employer details.</p><p>Google Identity Services loads only when the account dialog opens. There are no analytics or advertising scripts. Session cookies keep you signed in for up to seven days. Signing out revokes the current session.</p><p>This version has no self-service account deletion. Reports are stored for manual review; it does not promise continuous moderation.</p>'); }
function showAccount() { openModal(`<span class="eyebrow">YOUR BREAK ROOM BADGE</span><h2 id="modal-title">${escapeHTML(state.user.alias)}</h2><p>This is how the room sees you. Your private login is never shown on your posts.</p><button class="button" id="logout">Clock out / Sign out ↗</button>`); $('#logout').addEventListener('click', async () => { try { await api('/logout', {}); state.user = null; updateAccount(); closeModal(); await loadPosts(); toast('Signed out. You can still read everything.'); } catch (error) { toast(error.message); } }); }
function showReport(id) { openModal('<span class="eyebrow">LOOKING OUT FOR THE ROOM</span><h2 id="modal-title">Something not right?</h2><p>Tell us what needs a closer look. Reports are private and queued for manual review.</p><form id="report-form"><label>Reason<select name="reason"><option>Identifying or private information</option><option>Harassment or targeted abuse</option><option>Threats or hateful content</option><option>Spam or misleading content</option></select></label><p class="form-error" role="alert"></p><button class="button" type="submit">Send report ↗</button></form>'); const form = $('#report-form'); form.addEventListener('submit', async event => { event.preventDefault(); const button = $('button', form); button.disabled = true; try { await api('/posts/' + id + '/report', Object.fromEntries(new FormData(form))); closeModal(); toast('Report added to the review queue. Thank you.'); } catch (error) { $('.form-error', form).textContent = error.message; } finally { button.disabled = false; } }); }
document.addEventListener('click', async event => {
  const target = event.target.closest('button,a'); if (!target) return;
  const data = target.dataset;
  if (data.action === 'feed') setView('feed');
  if (data.action === 'compose') requireAuth(showCompose);
  if (data.action === 'auth') state.user ? showAccount() : showAuth('login');
  if (data.action === 'rules') showRules();
  if (data.action === 'privacy') showPrivacy();
  if (data.action === 'retry') loadPosts();
  if (data.action === 'clear') setView('feed');
  if (data.post) { if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return; event.preventDefault(); showPost(Number(data.post)); }
  if (data.join) requireAuth(() => showPost(Number(data.join), false));
  if (data.report) requireAuth(() => showReport(Number(data.report)));
  if (data.share) { const url = location.origin + '/post/' + data.share; try { await navigator.clipboard.writeText(url); toast('Story link copied.'); } catch { openModal(`<h2 id="modal-title">Pass it around.</h2><label>Story link<input readonly value="${escapeHTML(url)}"></label>`); $('input', modal).select(); } }
  if (data.vote) requireAuth(async () => {
    const id = Number(data.vote); const desired = target.getAttribute('aria-pressed') !== 'true';
    const post = detailPost?.id === id ? detailPost : cachedPost(id);
    const previous = {voted: post?.voted ?? !desired, votes: post?.votes ?? Number(target.getAttribute('aria-label')?.match(/\d+/)?.[0] || 0)};
    const nextVotes = Math.max(0, previous.votes + (desired ? 1 : -1));
    const buttons = [...document.querySelectorAll(`[data-vote="${id}"]`)]; buttons.forEach(button => { button.disabled = true; });
    updateVoteUI(id, desired, nextVotes);
    try { const result = await api('/posts/' + id + '/vote', {voted: desired}); if (result.voted !== desired) updateVoteUI(id, result.voted, previous.votes); }
    catch (error) { updateVoteUI(id, previous.voted, previous.votes); toast(error.message); }
    finally { buttons.forEach(button => { button.disabled = false; }); }
  });
});
$('#load-more').addEventListener('click', () => {
  const button = $('#load-more');
  const refresh = button.dataset.refresh === 'true';
  delete button.dataset.refresh;
  button.textContent = 'More from the break room ↓';
  loadPosts(!refresh);
});
$('#search-load-more').addEventListener('click', () => loadPosts(true));
function searchFromHeader() { setView($('#search').value.trim() ? 'search' : 'feed'); }
$('#search').addEventListener('input', () => { clearTimeout(state.searchTimer); state.searchTimer = setTimeout(searchFromHeader, 250); });
$('#header-search').addEventListener('submit', event => { event.preventDefault(); searchFromHeader(); });
window.addEventListener('popstate', () => { const match = location.pathname.match(/^\/post\/(\d+)$/); if (match) showPost(Number(match[1]), false); else if (modal.open) closeModal(); });
async function init() {
  try { state.user = (await api('/me')).user; updateAccount(); } catch { toast('Couldn’t check your session. Try refreshing.'); }
  await loadPosts();
  const match = location.pathname.match(/^\/post\/(\d+)$/); if (match) showPost(Number(match[1]), false);
}
init();
