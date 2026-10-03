const state = { boot: null, list: null, detail: null, botRecord: null, botConvos: [], chat: [], jobs: [], search: "", filter: "", page: 1, upload: null, linkCode: "", matchCandidate: null };
const main = document.querySelector("#app-main");
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const date = (value) => value ? new Intl.DateTimeFormat("fr-CA", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "—";
const route = () => (location.hash.slice(1).split("?")[0] || "dashboard");
const query = () => new URLSearchParams(location.hash.split("?")[1] || "");
const pill = (status) => `<span class="pill ${status === "VALIDÉ" || status === "CONNU" ? "green" : status === "À_RÉVISER" ? "lilac" : "gray"}">${esc(status)}</span>`;
const button = (label, action, klass = "") => `<button type="button" class="button ${klass}" data-action="${action}">${label}</button>`;

async function api(path, options = {}) {
  const method = options.method || "GET";
  const headers = { ...(options.body ? { "Content-Type": "application/json" } : {}), ...(method !== "GET" ? { "X-CSRF-Token": state.boot?.csrf || "" } : {}), ...(options.headers || {}) };
  const response = await fetch(path, { ...options, headers, credentials: "same-origin", cache: "no-store" });
  if (response.status === 401) { location.href = "/login"; throw Error("Session expirée."); }
  let body = {};
  try { body = await response.json(); } catch { /* HTML redirects are handled by the caller. */ }
  if (!response.ok) throw Error(body.detail || `Erreur HTTP ${response.status}`);
  return body;
}
function flash(message) { const el = document.querySelector("#toast"); el.textContent = message; el.hidden = false; clearTimeout(flash.timer); flash.timer = setTimeout(() => { el.hidden = true; }, 4500); }
function error(message) { const el = document.querySelector("#global-error"); el.textContent = message; el.hidden = !message; }
async function refresh() { state.boot = await api("/api/bootstrap"); document.querySelector("#nav-pending").textContent = state.boot.revisions; const avatar = document.querySelector(".avatar"); avatar.textContent = state.boot.role === "admin" ? "AD" : "RE"; avatar.setAttribute("aria-label", state.boot.role === "admin" ? "Administrateur local" : "Relecteur local"); }
async function loadList() { state.list = await api(`/api/records?search=${encodeURIComponent(state.search)}&state=${encodeURIComponent(state.filter)}&page=${state.page}`); }
async function loadDetail(id) { if (state.detail?.id !== id) { state.linkCode = ""; state.matchCandidate = null; } state.detail = id ? await api(`/api/records/${encodeURIComponent(id)}`) : null; }
function head(title, subtitle, action = "") { return `<div class="page-head"><div><span class="eyebrow">DAYONE · CONSOLE LOCALE</span><h1>${title}</h1><p>${subtitle}</p></div><div class="head-actions">${action}</div></div>`; }
function listItem(item, selected = false) { return `<li><button type="button" class="record-item ${item.state === "VALIDÉ" ? "valid" : ""} ${selected ? "selected" : ""}" data-record="${esc(item.id)}"><span class="record-item-top"><span class="record-code">${esc(item.code)}</span>${pill(item.state)}</span><span class="record-source">${esc(item.source)}</span><span class="record-meta"><span>${date(item.updated_at)}</span><span>·</span><span>${item.pending ?? 0} champ(s) à confirmer</span></span></button></li>`; }
function timeline(events) { return events.length ? `<ul class="timeline">${events.map((event) => `<li><span class="timeline-point">↗</span><div><strong>${esc(event.kind)} · ${esc(event.detail)}</strong><small>${date(event.created_at)}</small></div></li>`).join("")}</ul>` : `<div class="empty-state">Aucune activité.</div>`; }

function dashboard() {
  const b = state.boot, pending = b.counts["À_RÉVISER"] || 0, validated = b.counts["VALIDÉ"] || 0;
  const recent = (state.list?.items || []).slice(0, 4);
  main.innerHTML = head("Vue d'ensemble", "Suivi des dossiers fictifs, relecture et état des composants locaux.", `<a href="#review" class="button button-primary">Ouvrir la relecture <span aria-hidden="true">↗</span></a>`)
    + `<div class="metric-grid"><div class="metric-card"><label>Dossiers créés</label><strong>${b.total}</strong><small>Dans la base locale chiffrée</small></div><div class="metric-card lilac"><label>À relire</label><strong>${pending}</strong><small>${b.revisions} champ(s) non confirmé(s)</small></div><div class="metric-card"><label>Validés</label><strong>${validated}</strong><small>Après contrôle humain</small></div><div class="metric-card coral"><label>OCR local</label><strong style="font-size:29px;margin-top:18px">${b.ocr_ready ? "Prêt" : "À installer"}</strong><small>Poids sur cette machine</small></div></div>`
    + `<div class="overview-grid"><div class="panel"><div class="panel-header"><div><h2>Dossiers récents</h2><p>Identifiants techniques, aucune identité nominative</p></div><a href="#review" class="button button-small">Tous les dossiers</a></div>${recent.length ? `<ul class="record-list">${recent.map((item) => listItem(item)).join("")}</ul>` : `<div class="empty-state">Aucun dossier.</div>`}</div><div class="panel"><div class="panel-header"><div><h2>État du flux</h2><p>Progression de la revue documentaire</p></div></div><div class="panel-body"><div class="progress-row"><span>À relire</span><div class="progress-track"><div class="progress-bar lilac" style="width:${b.total ? Math.round(pending / b.total * 100) : 0}%"></div></div><b>${pending}</b></div><div class="progress-row"><span>Validés</span><div class="progress-track"><div class="progress-bar" style="width:${b.total ? Math.round(validated / b.total * 100) : 0}%"></div></div><b>${validated}</b></div><div class="callout" style="margin-top:23px"><span>◎</span><div><strong>Traitement entièrement local</strong><p>Le bot est simulé ici. Aucune conversation ni image n'est envoyée à WhatsApp ou à une API externe.</p></div></div></div></div></div>`
    + `<div class="panel" style="margin-top:18px"><div class="panel-header"><div><h2>Activité récente</h2><p>Journal local sans valeurs médicales</p></div></div><div class="panel-body">${timeline(b.events)}</div></div>`;
}

function fieldRow(field) {
  const options = state.boot.statuses.map((status) => `<option value="${esc(status)}" ${field.status === status ? "selected" : ""}>${esc(status)}</option>`).join("");
  return `<div class="field-row ${field.reviewed ? "done" : ""}" data-field="${field.id}"><div class="field-head"><label for="value-${field.id}">${esc(field.label)} ${field.unit ? `<small>(${esc(field.unit)})</small>` : ""}</label>${field.reviewed ? `<span class="pill green">Confirmé</span>` : `<span class="pill lilac">À confirmer</span>`}</div><div class="field-controls"><input class="text-input" id="value-${field.id}" value="${esc(field.value)}" maxlength="160" aria-label="Valeur ${esc(field.label)}"><select class="select-input" aria-label="Statut ${esc(field.label)}">${options}</select><button type="button" class="button button-small" data-save-field="${field.id}" data-version="${field.version}">Enregistrer</button></div>${field.confidence ? `<div class="field-hint">Source : ${esc(field.confidence)}</div>` : ""}</div>`;
}
function detail() {
  const d = state.detail;
  if (!d) return `<div class="panel detail-empty"><div><h2>Sélectionnez un dossier</h2><p>Ses champs, l'image expurgée et l'historique apparaîtront ici.</p></div></div>`;
  const pending = d.fields.filter((field) => !field.reviewed).length;
  const pages = d.pages.length ? `<div class="pages-grid">${d.pages.map((page) => `<div class="page-card"><img class="image-preview" src="/api/records/${esc(d.id)}/pages/${esc(page.id)}/image?v=${d.version}" alt="Page ${page.ordinal} expurgée"><strong>Page ${page.ordinal}</strong><small>${page.quality.warnings.length ? esc(page.quality.warnings.join(" · ")) : "Qualité indicative acceptable"}</small></div>`).join("")}</div><div class="upload-controls" style="margin:14px 0 19px">${button("Lancer l'OCR local sur les pages", "ocr", "button-primary")}</div>` : "";
  const upload = `<div class="upload-card"><label for="image-file"><strong>Ajouter ${d.pages.length ? "une autre page" : "un registre fictif"}</strong></label><p>PNG ou JPEG, 8 Mo maximum. Tracez au moins un masque sur chaque zone identifiante avant l'import.</p><input id="image-file" class="text-input" type="file" accept="image/png,image/jpeg"><canvas id="mask-canvas" class="mask-canvas" hidden aria-label="Zone de masquage de l'image"></canvas><div id="mask-count" class="field-hint">0 zone masquée</div><label class="checkbox-line"><input type="checkbox" id="synthetic-confirmed"><span>Je confirme que ce document est fictif et que toutes ses données identifiantes sont masquées.</span></label><div class="upload-controls">${button("Effacer les masques", "clear-masks", "button-small")}${button("Enregistrer la page expurgée", "save-image", "button-primary")}</div></div>`;
  const visits = `<div class="visit-zone"><div class="section-heading"><h3>Continuité des visites</h3><span>Code de liaison ${esc(d.patient_code)}</span></div><p>Chaque visite garde son propre dossier. Une liaison demande une décision humaine.</p><div class="visit-list">${d.visits.map((visit) => `<a href="#review?record=${encodeURIComponent(visit.id)}" class="visit-item"><strong>${esc(visit.code)}</strong><span>${date(visit.created_at)}</span>${pill(visit.state)}</a>`).join("")}</div><div class="upload-controls" style="margin:14px 0">${button("Créer une visite liée", "new-visit", "button-small")}</div><label for="link-code" class="field-hint">Lier ce dossier existant à un code de dossier exact</label><div class="upload-controls"><input id="link-code" class="text-input" style="max-width:190px" value="${esc(state.linkCode)}" placeholder="D1-XXXXXXX" aria-label="Code exact du dossier cible">${button("Vérifier le code", "lookup", "button-small")}</div>${state.matchCandidate ? `<div class="callout lilac" style="margin-top:11px"><div><strong>Candidat : ${esc(state.matchCandidate.code)}</strong><p>${esc(state.matchCandidate.source)} · ${date(state.matchCandidate.created_at)} · code de liaison ${esc(state.matchCandidate.patient_code)}</p><label class="checkbox-line"><input type="checkbox" id="link-confirmed">Je confirme manuellement que ces visites concernent la même personne fictive.</label>${button("Confirmer la liaison", "link", "button-small")}</div></div>` : ""}</div>`;
  const fields = state.boot.settings.review_order === "uncertain_first" ? [...d.fields].sort((a, b) => Number(a.reviewed) - Number(b.reviewed)) : d.fields;
  return `<div class="panel"><div class="detail-top"><div><span class="eyebrow">DOSSIER DOCUMENTAIRE</span><h2>${esc(d.code)}</h2><p>${esc(d.source)} · Mis à jour ${date(d.updated_at)}</p></div>${pill(d.state)}</div><div class="detail-body"><div class="section-heading"><h3>Champs extraits et statut</h3><span>${pending} à confirmer sur ${d.fields.length}</span></div><div class="field-list">${fields.map(fieldRow).join("")}</div><div class="detail-actions"><span>Chaque champ demande une validation humaine explicite.</span>${button("Valider le dossier", "validate", "button-primary")} </div>${visits}</div><div class="image-zone"><h3>Pages sources expurgées</h3><p>Les images sources ne sont conservées qu'après masquage et sous forme chiffrée.</p>${pages}${upload}</div><div class="panel-header"><div><h2>Historique du dossier</h2><p>Actions et horodatage, sans contenu médical</p></div></div><div class="panel-body">${timeline(d.events)}</div></div>`;
}
function review() {
  const data = state.list, items = data.items;
  main.innerHTML = head("Relecture", "Contrôlez les valeurs extraites avant toute validation du dossier.", `<a href="#bot" class="button">Créer un dossier fictif</a>`)
    + `<div class="review-layout"><div class="panel list-panel"><div class="panel-header"><div><h2>File des dossiers</h2><p>${data.total} résultat(s)</p></div></div><div class="filters"><input id="record-search" class="text-input" type="search" placeholder="Code du dossier…" value="${esc(state.search)}" aria-label="Rechercher par code"><select id="record-filter" class="select-input" aria-label="Filtrer les dossiers"><option value="">Tous les états</option><option value="À_RÉVISER" ${state.filter === "À_RÉVISER" ? "selected" : ""}>À relire</option><option value="VALIDÉ" ${state.filter === "VALIDÉ" ? "selected" : ""}>Validés</option></select></div>${items.length ? `<ul class="record-list">${items.map((item) => listItem(item, state.detail?.id === item.id)).join("")}</ul>` : `<div class="empty-state"><strong>Aucun dossier trouvé</strong>Modifiez le filtre ou la recherche.</div>`}<div class="pagination"><button type="button" class="button button-small" data-page="prev" ${data.page <= 1 ? "disabled" : ""}>← Précédent</button><span>Page ${data.page} / ${Math.max(1, Math.ceil(data.total / data.page_size))}</span><button type="button" class="button button-small" data-page="next" ${data.page * data.page_size >= data.total ? "disabled" : ""}>Suivant →</button></div></div>${detail()}</div>`;
}
function bot() {
  const current = state.botRecord, code = current?.code;
  const messages = current ? state.chat.map((entry) => `<div class="bubble ${entry.sender === "admin" ? "me" : ""}">${esc(entry.text)}</div>`).join("") : `<div class="bubble">Cliquez sur « Nouvelle conversation locale » pour créer un dossier et saisir des valeurs fictives.</div>`;
  main.innerHTML = head("Bot local", "Dialogue de démonstration avec extraction déterministe, sans connexion à Meta ou WhatsApp.", button("Nouvelle conversation locale", "new-bot", "button-primary"))
    + `<div class="bot-layout"><div class="chat-window"><div class="chat-header"><span>DayOne · ${code ? esc(code) : "simulation locale"}</span><span>● Hors réseau</span></div><div class="chat-messages" id="chat-messages">${messages}</div><form id="bot-form" class="chat-compose"><input class="text-input" id="bot-input" aria-label="Message fictif au bot local" placeholder="Exemple : âge 28 ou TA 112/74" maxlength="160" ${code ? "required" : "disabled"}><button class="button button-small button-primary" type="submit" ${code ? "" : "disabled"}>Envoyer</button></form></div><div class="panel"><div class="panel-header"><div><h2>Connexion au bot</h2><p>Flux autonome sur la machine</p></div></div><div class="panel-body"><div class="setting-row"><label for="bot-conversation">Conversation locale</label><select class="select-input" id="bot-conversation" ${state.botConvos.length ? "" : "disabled"}>${state.botConvos.length ? state.botConvos.map((item) => `<option value="${esc(item.id)}" ${item.id === current?.id ? "selected" : ""}>${esc(item.code)}</option>`).join("") : `<option>Aucune conversation</option>`}</select></div><div class="status-banner success">Bot déterministe local actif</div><p>Chaque message reste chiffré dans la base locale. Les valeurs reconnues sont seulement proposées à la relecture. Le parcours WhatsApp réel demanderait l'infrastructure Meta et ferait sortir les messages de cette machine.</p><div class="callout warning" style="margin-top:20px"><span>!</span><div><strong>Frontière de confidentialité</strong><p>Aucune clé API, webhook ou numéro WhatsApp n'est configuré ici. Utilisez des données fictives.</p></div></div>${code ? `<a href="#review?record=${encodeURIComponent(current.id)}" class="button button-primary" style="margin-top:19px">Relire ${esc(code)} →</a>` : ""}</div></div></div>`;
  const transcript = document.querySelector("#chat-messages"); transcript.scrollTop = transcript.scrollHeight;
}
function settings() {
  const s = state.boot.settings;
  main.innerHTML = head("Configuration", "Réglages simples de l'OCR et de la file de relecture, enregistrés localement.")
    + `<div class="setting-grid"><div class="panel"><div class="panel-header"><div><h2>Préférences de traitement</h2><p>Aucun service externe requis</p></div></div><div class="panel-body"><form id="settings-form"><div class="setting-row"><label for="ocr-languages">Langues de l'OCR</label><select class="select-input" id="ocr-languages"><option value="fr,en" ${s.ocr_languages === "fr,en" ? "selected" : ""}>Français et anglais</option><option value="fr" ${s.ocr_languages === "fr" ? "selected" : ""}>Français</option><option value="en" ${s.ocr_languages === "en" ? "selected" : ""}>Anglais</option></select><p>Les poids nécessaires doivent déjà être installés dans admin/.models.</p></div><div class="setting-row"><label for="review-order">Ordre de relecture</label><select class="select-input" id="review-order"><option value="uncertain_first" ${s.review_order === "uncertain_first" ? "selected" : ""}>Champs incertains en premier</option><option value="document_order" ${s.review_order === "document_order" ? "selected" : ""}>Ordre du document</option></select><p>Les suggestions OCR restent toujours à confirmer.</p></div><button type="submit" class="button button-primary">Enregistrer les préférences</button></form></div></div><div class="settings-callouts"><div class="panel"><div class="panel-header"><div><h2>Composants locaux</h2><p>État de la machine</p></div></div><div class="panel-body"><div class="status-banner ${state.boot.ocr_ready ? "success" : "warning"}">OCR : ${state.boot.ocr_ready ? "poids présents" : "poids absents"}</div><p>Installation des seuls poids de modèle : <code>python setup_models.py</code>. Les images et textes ne sont pas envoyés lors de cette étape.</p><div class="setting-row" style="margin-top:20px"><strong>File OCR locale</strong><p>${state.jobs.filter((job) => job.state === "PENDING").length} en attente · ${state.jobs.filter((job) => job.state === "DONE").length} terminée(s)</p></div>${button("Reprendre la file locale", "resume-jobs", "button-small")}</div></div><div class="callout lilac"><span>⌁</span><div><strong>Règle de démonstration</strong><p>Utilisez exclusivement des documents fictifs ou expurgés. Le masquage doit être vérifié visuellement avant d'enregistrer une image.</p></div></div></div></div>`;
  if (state.boot.role !== "admin") {
    main.querySelectorAll("#settings-form input, #settings-form select, #settings-form button, [data-action='resume-jobs']").forEach((control) => { control.disabled = true; });
    main.insertAdjacentHTML("afterbegin", `<div class="status-banner warning">Compte relecteur : configuration en lecture seule.</div>`);
  }
}
async function render() {
  error(""); const view = ["dashboard", "review", "bot", "settings"].includes(route()) ? route() : "dashboard";
  document.querySelectorAll("#main-nav .nav-link").forEach((link) => { link.classList.toggle("active", link.dataset.view === view); link.setAttribute("aria-current", link.dataset.view === view ? "page" : "false"); });
  document.querySelector("#crumb-current").textContent = { dashboard: "Vue d'ensemble", review: "Relecture", bot: "Bot local", settings: "Configuration" }[view];
  try {
    if (!state.boot) await refresh();
    if (view === "dashboard") { await loadList(); dashboard(); }
    if (view === "review") { await loadList(); const id = query().get("record") || state.detail?.id || state.list.items[0]?.id; await loadDetail(id); review(); }
    if (view === "bot") { state.botConvos = await api("/api/bot/conversations/list"); if (!state.botRecord && state.botConvos.length) state.botRecord = state.botConvos[0]; if (state.botRecord) state.chat = await api(`/api/bot/${state.botRecord.id}/messages`); bot(); }
    if (view === "settings") { state.jobs = await api("/api/jobs"); settings(); }
  } catch (exc) { error(exc.message); }
}

function drawCanvas(preview = null) {
  const upload = state.upload, canvas = document.querySelector("#mask-canvas"); if (!upload || !canvas) return;
  const ctx = canvas.getContext("2d"); ctx.clearRect(0, 0, canvas.width, canvas.height); ctx.drawImage(upload.img, 0, 0, canvas.width, canvas.height);
  for (const rect of [...upload.masks, ...(preview ? [preview] : [])]) { ctx.fillStyle = "rgba(20,31,34,.84)"; ctx.fillRect(rect[0], rect[1], rect[2]-rect[0], rect[3]-rect[1]); ctx.strokeStyle = "#fff"; ctx.setLineDash([9, 5]); ctx.lineWidth = Math.max(2, canvas.width / 450); ctx.strokeRect(rect[0], rect[1], rect[2]-rect[0], rect[3]-rect[1]); }
  document.querySelector("#mask-count").textContent = `${upload.masks.length} zone(s) masquée(s)`;
}
function point(event, canvas) { const box = canvas.getBoundingClientRect(); return [Math.round((event.clientX-box.left) * canvas.width/box.width), Math.round((event.clientY-box.top) * canvas.height/box.height)]; }
async function handleFile(file) {
  if (!file) return;
  if (![/^image\/png$/, /^image\/jpeg$/].some((pattern) => pattern.test(file.type)) || file.size > 8_000_000) throw Error("Choisir une image PNG ou JPEG de 8 Mo maximum.");
  const originalUrl = await new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.onerror = () => reject(Error("Lecture du fichier impossible.")); reader.readAsDataURL(file); });
  const img = await new Promise((resolve, reject) => { const item = new Image(); item.onload = () => resolve(item); item.onerror = () => reject(Error("Image invalide.")); item.src = originalUrl; });
  if (img.naturalWidth * img.naturalHeight > 18_000_000) throw Error("Dimensions de l'image trop grandes.");
  // Flatten EXIF orientation in the browser so mask coordinates match stored pixels.
  const normalized = document.createElement("canvas"); normalized.width = img.naturalWidth; normalized.height = img.naturalHeight;
  normalized.getContext("2d").drawImage(img, 0, 0);
  const dataUrl = normalized.toDataURL("image/png");
  if (dataUrl.length > 11_000_000) throw Error("Image trop volumineuse après normalisation.");
  state.upload = { dataUrl, img, masks: [], start: null };
  const canvas = document.querySelector("#mask-canvas"); canvas.hidden = false; canvas.width = img.naturalWidth; canvas.height = img.naturalHeight;
  canvas.onpointerdown = (event) => { state.upload.start = point(event, canvas); canvas.setPointerCapture(event.pointerId); };
  canvas.onpointermove = (event) => { if (!state.upload?.start) return; const end = point(event, canvas), a = state.upload.start; drawCanvas([Math.min(a[0],end[0]), Math.min(a[1],end[1]), Math.max(a[0],end[0]), Math.max(a[1],end[1])]); };
  canvas.onpointerup = (event) => { if (!state.upload?.start) return; const end = point(event, canvas), a = state.upload.start; const rect = [Math.max(0,Math.min(a[0],end[0])), Math.max(0,Math.min(a[1],end[1])), Math.min(canvas.width,Math.max(a[0],end[0])), Math.min(canvas.height,Math.max(a[1],end[1]))]; if (rect[2]-rect[0] > 4 && rect[3]-rect[1] > 4) state.upload.masks.push(rect); state.upload.start = null; drawCanvas(); };
  drawCanvas();
}
async function mutate(action) {
  const id = state.detail?.id;
  if (action === "new-bot") { state.botRecord = await api("/api/bot/conversation", { method: "POST", body: JSON.stringify({}) }); state.botConvos = await api("/api/bot/conversations/list"); state.chat = await api(`/api/bot/${state.botRecord.id}/messages`); await refresh(); bot(); flash(`Dossier ${state.botRecord.code} créé localement.`); return; }
  if (action === "resume-jobs") { const result = await api("/api/jobs/resume", { method: "POST" }); state.jobs = await api("/api/jobs"); settings(); flash(`${result.processed.length} opération(s) de la file traitée(s).`); return; }
  if (!id) return;
  if (action === "validate") { state.detail = await api(`/api/records/${id}/validate`, { method: "POST" }); await refresh(); await loadList(); review(); flash("Dossier validé."); }
  if (action === "new-visit") { const visit = await api(`/api/records/${id}/visits`, { method: "POST", body: JSON.stringify({ confirmed: true }) }); await refresh(); location.hash = `review?record=${encodeURIComponent(visit.id)}`; flash(`Visite ${visit.code} liée au code ${visit.patient_code}.`); }
  if (action === "lookup") { state.linkCode = document.querySelector("#link-code")?.value.trim().toUpperCase() || ""; state.matchCandidate = await api(`/api/patients/lookup?code=${encodeURIComponent(state.linkCode)}`); review(); flash("Code exact trouvé. Vérifiez le candidat avant de lier."); }
  if (action === "link") { if (!state.matchCandidate || !document.querySelector("#link-confirmed")?.checked) throw Error("Vérifiez le candidat et confirmez manuellement la liaison."); state.detail = await api(`/api/records/${id}/link`, { method: "POST", body: JSON.stringify({ target_code: state.matchCandidate.code, confirmed: true, expected_version: state.detail.version }) }); state.matchCandidate = null; await refresh(); await loadList(); review(); flash("Visites liées par décision humaine."); }
  if (action === "ocr") { flash("OCR local en cours…"); const storageKey = `dayone-ocr-${id}`; const key = localStorage.getItem(storageKey) || crypto.randomUUID(); localStorage.setItem(storageKey, key); const result = await api(`/api/records/${id}/ocr`, { method: "POST", headers: { "Idempotency-Key": key } }); if (result.job_state === "ERROR") { localStorage.removeItem(storageKey); throw Error(result.detail || "Échec OCR local."); } if (result.job_state !== "DONE") { flash(`OCR dans la file locale : ${result.detail || result.job_state}.`); return; } localStorage.removeItem(storageKey); state.detail = result.record; await refresh(); await loadList(); review(); flash(`${result.suggestions} suggestion(s) OCR à relire.`); }
  if (action === "clear-masks") { if (state.upload) { state.upload.masks = []; drawCanvas(); } }
  if (action === "save-image") {
    if (!state.upload?.masks.length) throw Error("Tracez au moins un masque sur l'image.");
    if (!document.querySelector("#synthetic-confirmed")?.checked) throw Error("Confirmez le caractère fictif et le masquage complet.");
    const result = await api(`/api/records/${id}/image`, { method: "POST", body: JSON.stringify({ data_url: state.upload.dataUrl, masks: state.upload.masks, synthetic_confirmed: true }) });
    state.upload = null; await loadDetail(id); await refresh(); await loadList(); review(); flash(result.duplicate ? "Cette page est déjà présente." : `Page ${result.ordinal} chiffrée localement.${result.quality.warnings.length ? " Attention : " + result.quality.warnings.join(", ") + "." : ""}`);
  }
}

document.addEventListener("click", async (event) => {
  const record = event.target.closest("[data-record]"); if (record) { location.hash = `review?record=${encodeURIComponent(record.dataset.record)}`; return; }
  const page = event.target.closest("[data-page]"); if (page) { state.page += page.dataset.page === "next" ? 1 : -1; await render(); return; }
  const save = event.target.closest("[data-save-field]"); if (save) { const row = save.closest(".field-row"), status = row.querySelector("select").value; try { state.detail = await api(`/api/records/${state.detail.id}/fields/${save.dataset.saveField}/review`, { method: "POST", body: JSON.stringify({ value: row.querySelector("input").value, status, expected_version: Number(save.dataset.version) }) }); await refresh(); await loadList(); review(); flash(status === "À_RÉVISER" ? "Champ conservé dans la file de relecture." : "Champ enregistré et confirmé."); } catch (exc) { error(exc.message); } return; }
  const action = event.target.closest("[data-action]"); if (action) { action.disabled = true; try { await mutate(action.dataset.action); } catch (exc) { error(exc.message); action.disabled = false; } }
});
document.addEventListener("change", async (event) => {
  if (event.target.id === "record-filter") { state.filter = event.target.value; state.page = 1; await render(); }
  if (event.target.id === "bot-conversation") { state.botRecord = state.botConvos.find((item) => item.id === event.target.value) || null; state.chat = state.botRecord ? await api(`/api/bot/${state.botRecord.id}/messages`) : []; bot(); }
  if (event.target.id === "image-file") { try { await handleFile(event.target.files?.[0]); } catch (exc) { error(exc.message); } }
});
let searchTimer;
document.addEventListener("input", (event) => { if (event.target.id === "record-search") { const value = event.target.value; clearTimeout(searchTimer); searchTimer = setTimeout(async () => { state.search = value; state.page = 1; await render(); document.querySelector("#record-search")?.focus(); }, 300); } });
document.addEventListener("submit", async (event) => {
  if (event.target.id === "logout-form") { event.preventDefault(); try { await api("/logout", { method: "POST" }); } catch { /* redirect response may be HTML */ } location.href = "/login"; }
  if (event.target.id === "settings-form") { event.preventDefault(); try { await api("/api/settings", { method: "POST", body: JSON.stringify({ ocr_languages: document.querySelector("#ocr-languages").value, review_order: document.querySelector("#review-order").value }) }); await refresh(); settings(); flash("Configuration enregistrée localement."); } catch (exc) { error(exc.message); } }
  if (event.target.id === "bot-form") { event.preventDefault(); const field = document.querySelector("#bot-input"), message = field.value.trim(); if (!message || !state.botRecord) return; field.disabled = true; try { await api(`/api/bot/${state.botRecord.id}/message`, { method: "POST", body: JSON.stringify({ text: message }) }); state.chat = await api(`/api/bot/${state.botRecord.id}/messages`); await refresh(); bot(); } catch (exc) { error(exc.message); field.disabled = false; } }
});
window.addEventListener("hashchange", render);
render();
