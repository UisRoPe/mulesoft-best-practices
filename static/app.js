document.addEventListener('DOMContentLoaded', () => {

    // ── Marked config ────────────────────────────────────────────────────────
    // Use markedHighlight extension if available (marked v5+); fall back silently
    marked.use({ breaks: false, gfm: true });

    // ── Auth bootstrap ───────────────────────────────────────────────────────
    if (localStorage.getItem('token')) showInstallOrDashboard();

    // Login
    document.getElementById('login-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const err = document.getElementById('login-error');
        err.textContent = '';
        try {
            const res  = await fetch('/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username: document.getElementById('username').value,
                    password: document.getElementById('password').value
                })
            });
            const data = await res.json();
            if (res.ok) {
                localStorage.setItem('token', data.token);
                showInstallOrDashboard();
            } else {
                err.textContent = data.detail || 'Credenciales incorrectas.';
            }
        } catch {
            err.textContent = 'Error de conexión con el servidor.';
        }
    });

    // Logout
    document.getElementById('logout-btn').addEventListener('click', () => {
        localStorage.removeItem('token');
        window.activeReportName = null;
        switchScreen('login-screen');
        showWelcome();
    });

    // Install
    document.getElementById('btn-start-install')?.addEventListener('click', async () => {
        const btn  = document.getElementById('btn-start-install');
        const prog = document.getElementById('install-progress');
        const err  = document.getElementById('install-error');
        btn.classList.add('hidden');
        prog.classList.remove('hidden');
        err.textContent = '';
        try {
            const res  = await fetch('/install', { method: 'POST' });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                showDashboard();
            } else {
                btn.classList.remove('hidden');
                prog.classList.add('hidden');
                err.textContent = data.logs || data.detail || 'Error en la instalación.';
            }
        } catch {
            btn.classList.remove('hidden');
            prog.classList.add('hidden');
            err.textContent = 'Error de conexión durante la instalación.';
        }
    });

    // ── Screen helpers ───────────────────────────────────────────────────────
    function switchScreen(id) {
        document.querySelectorAll('.screen').forEach(s => {
            s.classList.remove('active');
            s.classList.add('hidden');
        });
        const target = document.getElementById(id);
        target.classList.remove('hidden');
        target.classList.add('active');
    }

    function showInstallOrDashboard() {
        document.getElementById('login-screen').classList.remove('active');
        document.getElementById('login-screen').classList.add('hidden');
        fetch('/check_install')
            .then(r => r.json())
            .then(d => d.installed ? showDashboard() : switchScreen('install-screen'))
            .catch(() => {
                document.getElementById('login-error').textContent = 'Error validando instalación.';
                switchScreen('login-screen');
            });
    }

    function showDashboard() {
        switchScreen('dashboard-screen');
        loadReports();
        loadProjects();
    }

    // ── Navigation ───────────────────────────────────────────────────────────
    let checklistLoaded = false;

    document.querySelectorAll('.nav-item').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const targetId = btn.getAttribute('data-target');
            document.querySelectorAll('.panel').forEach(p => p.classList.add('hidden'));
            document.getElementById(targetId)?.classList.remove('hidden');

            if (targetId === 'panel-knowledge') loadKnowledgeStats();
        });
    });

    // ── Topbar tab switching ─────────────────────────────────────────────────
    document.querySelectorAll('.topbar-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const viewId = tab.getAttribute('data-view');
            document.querySelectorAll('.topbar-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            document.querySelectorAll('.main-view').forEach(v => v.classList.add('hidden'));
            document.getElementById(viewId)?.classList.remove('hidden');
            if (viewId === 'view-checklist' && !checklistLoaded) loadRules();
        });
    });

    // Cancel audit
    document.addEventListener('click', async (e) => {
        if (!e.target.closest('.btn-cancel-audit')) return;
        if (!confirm('¿Detener el análisis en curso? Se perderá el progreso actual.')) return;
        try {
            await fetch('/cancel_audit', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });
        } catch { /* silent */ }
    });

    // ── Drag & Drop ──────────────────────────────────────────────────────────
    function enableDragAndDrop(dropZoneId, fileInputId, uploadFn, ext) {
        const zone  = document.getElementById(dropZoneId);
        const input = document.getElementById(fileInputId);
        zone.addEventListener('click', () => input.click());
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(ev =>
            zone.addEventListener(ev, e => { e.preventDefault(); e.stopPropagation(); }));
        ['dragenter', 'dragover'].forEach(ev =>
            zone.addEventListener(ev, () => zone.classList.add('dragover')));
        ['dragleave', 'drop'].forEach(ev =>
            zone.addEventListener(ev, () => zone.classList.remove('dragover')));
        zone.addEventListener('drop', e => handleFiles(e.dataTransfer.files));
        input.addEventListener('change', e => handleFiles(e.target.files));

        function handleFiles(files) {
            if (!files.length) return;
            const allValid = Array.from(files).every(f => f.name.endsWith(ext));
            if (allValid) uploadFn(files);
            else alert(`Sólo se aceptan archivos con extensión ${ext}.`);
        }
    }

    enableDragAndDrop('drop-zone-project',   'file-input-project',   uploadProject,   '.zip');
    enableDragAndDrop('drop-zone-knowledge', 'file-input-knowledge', uploadKnowledge, '.pdf');

    // ── Upload project ───────────────────────────────────────────────────────
    async function uploadProject(files) {
        const formData = new FormData();
        formData.append('file',  files[0]);
        formData.append('model', document.getElementById('model-select').value);

        const dropZone   = document.getElementById('drop-zone-project');
        const progPanel  = document.getElementById('upload-progress-project');
        const statusText = document.getElementById('project-status-text');
        const bar        = document.getElementById('project-progress-bar');
        const console_   = document.getElementById('project-console');

        dropZone.classList.add('hidden');
        progPanel.classList.remove('hidden');
        bar.style.width = '0%';
        statusText.textContent = 'Iniciando…';
        console_.innerHTML = '<span class="mini-console-line">Iniciando análisis…</span>';

        const poll = setInterval(async () => {
            try {
                const p = await (await fetch('/progress')).json();
                if (p.total > 0) {
                    const pct = Math.round((p.current / p.total) * 100);
                    bar.style.width = `${pct}%`;
                    statusText.textContent = `(${p.current}/${p.total}) ${p.file}`;
                } else if (p.file) {
                    statusText.textContent = p.file;
                }
                const last = console_.lastElementChild?.textContent;
                const line = p.total > 0 ? `✓ ${p.file}` : `→ ${p.file}`;
                if (last !== line && p.file) {
                    const s = document.createElement('span');
                    s.className = 'mini-console-line';
                    s.textContent = line;
                    console_.appendChild(s);
                    console_.scrollTop = console_.scrollHeight;
                }
            } catch { /* silent */ }
        }, 1000);

        try {
            const res  = await fetch('/upload', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
                body: formData
            });
            const data = await res.json();
            clearInterval(poll);
            bar.style.width = '100%';
            if (res.ok) {
                setTimeout(() => {
                    loadReports();
                    // Switch to reports panel
                    document.querySelector('.nav-item[data-target="panel-reports"]')?.click();
                }, 700);
            } else {
                alert(`Error: ${data.detail || data.logs}`);
            }
        } catch {
            clearInterval(poll);
            alert('Error al subir o procesar el proyecto.');
        } finally {
            progPanel.classList.add('hidden');
            dropZone.classList.remove('hidden');
        }
    }

    // ── Upload knowledge ─────────────────────────────────────────────────────
    async function uploadKnowledge(files) {
        const formData = new FormData();
        Array.from(files).forEach(f => formData.append('files', f));
        formData.append('model', document.getElementById('model-select').value);

        const dropZone = document.getElementById('drop-zone-knowledge');
        const prog     = document.getElementById('upload-progress-knowledge');
        dropZone.classList.add('hidden');
        prog.classList.remove('hidden');

        try {
            const res  = await fetch('/upload_knowledge', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
                body: formData
            });
            const data = await res.json();
            if (res.ok) {
                alert('✅ Base de conocimiento actualizada. El Checklist detectará los nuevos estándares.');
                checklistLoaded = false; // force reload next time
                loadKnowledgeStats();
            } else {
                alert(`Error: ${data.detail || data.logs}`);
            }
        } catch {
            alert('Error al procesar los PDFs.');
        } finally {
            prog.classList.add('hidden');
            dropZone.classList.remove('hidden');
        }
    }

    // ── Knowledge stats ──────────────────────────────────────────────────────
    async function loadKnowledgeStats() {
        const chip = document.getElementById('knowledge-stats');
        try {
            const data = await (await fetch('/rules', {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            })).json();
            if (data.rules?.length) {
                chip.textContent = `📦 ${data.rules.length} fragmentos indexados en la base vectorial`;
                chip.classList.remove('hidden');
            } else if (data.error) {
                chip.textContent = `⚠ ${data.error}`;
                chip.classList.remove('hidden');
            }
        } catch { /* silent */ }
    }

    // ── Load projects ─────────────────────────────────────────────────────────
    async function loadProjects() {
        try {
            const data = await (await fetch('/projects', {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            })).json();
            const list = document.getElementById('repositories-list');
            list.innerHTML = '';
            if (!data.projects.length) {
                list.innerHTML = '<li style="color:var(--tx-3);padding:.75rem .5rem;font-size:.78rem;">No hay proyectos cargados.</li>';
                return;
            }
            data.projects.forEach(proj => {
                const li = document.createElement('li');
                li.className = 'project-item';

                const name = document.createElement('span');
                name.className = 'project-item-name';
                name.textContent = proj;

                const actions = document.createElement('div');
                actions.className = 'project-item-actions';

                const btnAudit  = makeBtn('▶ Auditar', 'btn-primary',   () => auditExisting(proj), 'padding:.22rem .55rem;font-size:.7rem;');
                const btnRename = makeBtn('✏ Renombrar', 'btn-secondary', () => renameProject(proj), 'padding:.22rem .5rem;font-size:.7rem;');
                const btnDel    = makeBtn('🗑', 'btn-secondary', () => deleteProject(proj), 'padding:.22rem .4rem;font-size:.7rem;color:var(--err);border-color:rgba(248,81,73,.25);');

                actions.append(btnAudit, btnRename, btnDel);
                li.append(name, actions);
                list.appendChild(li);
            });
        } catch (e) { console.error(e); }
    }

    function makeBtn(label, cls, fn, extraStyle = '') {
        const b = document.createElement('button');
        b.textContent = label;
        b.className   = cls;
        b.style.cssText = extraStyle;
        b.onclick = fn;
        return b;
    }

    // ── Audit existing ────────────────────────────────────────────────────────
    async function auditExisting(projectName) {
        const formData = new FormData();
        formData.append('model',        document.getElementById('model-select').value);
        formData.append('project_name', projectName);

        const listEl    = document.getElementById('repositories-list');
        const progPanel = document.getElementById('repositories-progress');
        const statusTxt = document.getElementById('repo-status-text');
        const bar       = document.getElementById('repo-progress-bar');
        const con       = document.getElementById('repo-console');

        listEl.classList.add('hidden');
        progPanel.classList.remove('hidden');
        bar.style.width = '0%';
        statusTxt.textContent = 'Contactando motor AI…';
        con.innerHTML = '<span class="mini-console-line">Iniciando…</span>';

        const poll = setInterval(async () => {
            try {
                const p = await (await fetch('/progress')).json();
                if (p.total > 0) {
                    bar.style.width = `${Math.round((p.current / p.total) * 100)}%`;
                    statusTxt.textContent = `(${p.current}/${p.total}) ${p.file}`;
                } else if (p.file) {
                    statusTxt.textContent = p.file;
                }
                const last = con.lastElementChild?.textContent;
                const line = p.total > 0 ? `✓ ${p.file}` : `→ ${p.file}`;
                if (last !== line && p.file) {
                    const s = document.createElement('span');
                    s.className = 'mini-console-line';
                    s.textContent = line;
                    con.appendChild(s);
                    con.scrollTop = con.scrollHeight;
                }
            } catch { /* silent */ }
        }, 1000);

        try {
            const res  = await fetch('/audit_existing', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
                body: formData
            });
            const data = await res.json();
            clearInterval(poll);
            bar.style.width = '100%';
            if (res.ok) {
                setTimeout(() => {
                    loadReports();
                    document.querySelector('.nav-item[data-target="panel-reports"]')?.click();
                }, 600);
            } else {
                alert(`Error: ${data.detail || data.logs}`);
            }
        } catch {
            clearInterval(poll);
            alert('Error al procesar la auditoría.');
        } finally {
            progPanel.classList.add('hidden');
            listEl.classList.remove('hidden');
        }
    }

    // ── Delete / Rename project ───────────────────────────────────────────────
    async function deleteProject(name) {
        if (!confirm(`¿Eliminar el proyecto "${name}"?`)) return;
        const res = await fetch(`/projects/${name}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        if (res.ok) loadProjects();
        else alert('No se pudo eliminar el proyecto.');
    }

    async function renameProject(name) {
        const newName = prompt(`Nuevo nombre para "${name}":`, name);
        if (!newName?.trim() || newName === name) return;
        const res = await fetch(`/projects/${name}`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ new_name: newName.trim() })
        });
        const data = await res.json();
        if (res.ok) loadProjects();
        else alert(`Error: ${data.detail || data.message}`);
    }

    // ── Load reports ──────────────────────────────────────────────────────────
    async function loadReports() {
        try {
            const data = await (await fetch(`/reports?t=${Date.now()}`, {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            })).json();
            const list    = document.getElementById('reports-list');
            const prevFirst = list.firstElementChild?.dataset?.name;
            list.innerHTML = '';

            data.reports.forEach((report) => {
                const cleanName = report
                    .replace('Matriz_Hallazgos_', '')
                    .replace('Documento_Final_', '📋 ')
                    .replace('.md', '');

                const li   = document.createElement('li');
                li.className = 'report-item';
                li.dataset.name = report;

                const name = document.createElement('span');
                name.textContent = cleanName;
                name.onclick = () => {
                    document.querySelectorAll('.report-item').forEach(r => r.classList.remove('active'));
                    li.classList.add('active');
                    li.querySelector('.badge-new')?.remove();
                    loadReportContent(report);
                };

                const actions = document.createElement('div');
                actions.style.cssText = 'display:flex;gap:2px;flex-shrink:0;';

                const bRename = makeBtn('✏', '', () => renameReport(report, cleanName), 'background:transparent;border:none;cursor:pointer;font-size:.78rem;padding:.2rem .35rem;color:var(--tx-3);');
                const bDel    = makeBtn('🗑', '', () => deleteReport(report),             'background:transparent;border:none;cursor:pointer;font-size:.78rem;padding:.2rem .35rem;color:var(--tx-3);');

                bRename.onclick = (e) => { e.stopPropagation(); renameReport(report, cleanName); };
                bDel.onclick    = (e) => { e.stopPropagation(); deleteReport(report); };

                actions.append(bRename, bDel);
                li.append(name, actions);
                list.appendChild(li);
            });

            // NEW badge
            const first = list.firstElementChild;
            if (first && first.dataset.name !== prevFirst) {
                const badge = document.createElement('span');
                badge.className = 'badge-new';
                badge.textContent = 'NEW';
                first.insertBefore(badge, first.querySelector('span')?.nextSibling ?? null);
            }
        } catch (e) { console.error(e); }
    }

    // ── Delete / Rename report ────────────────────────────────────────────────
    async function deleteReport(name) {
        if (!confirm(`¿Eliminar el reporte "${name}"?`)) return;
        const res = await fetch(`/reports/${name}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        if (res.ok) {
            loadReports();
            if (window.activeReportName === name) { window.activeReportName = null; showWelcome(); }
        } else { alert('No se pudo eliminar el reporte.'); }
    }

    async function renameReport(name, current) {
        const newName = prompt('Nuevo nombre para el reporte:', current);
        if (!newName?.trim() || newName === current) return;
        const res = await fetch(`/reports/${name}`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ new_name: newName.trim() })
        });
        const data = await res.json();
        if (res.ok) {
            loadReports();
            if (window.activeReportName === name) { window.activeReportName = null; showWelcome(); }
        } else { alert(`Error: ${data.detail || data.message}`); }
    }

    // ── Load report content ───────────────────────────────────────────────────
    async function loadReportContent(filename) {
        try {
            const res  = await fetch(`/reports/${filename}`, {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });
            const data = await res.json();
            if (!res.ok) return;

            const cleanName = filename
                .replace('Matriz_Hallazgos_', '')
                .replace('Documento_Final_', '')
                .replace('.md', '');

            // Show report topbar, hide welcome
            document.getElementById('welcome-header').classList.add('hidden');
            document.getElementById('report-topbar').classList.remove('hidden');
            document.getElementById('current-report-title').textContent = cleanName;
            document.getElementById('download-report-btn').href = `/download/${filename}`;

            // Switch to report view tab
            document.querySelectorAll('.topbar-tab').forEach(t => t.classList.remove('active'));
            document.querySelector('.topbar-tab[data-view="view-report"]')?.classList.add('active');
            document.querySelectorAll('.main-view').forEach(v => v.classList.add('hidden'));
            document.getElementById('view-report')?.classList.remove('hidden');

            // Render markdown
            const reportContent = document.getElementById('report-content');
            reportContent.innerHTML = marked.parse(data.content);
            reportContent.classList.remove('hidden');
            document.getElementById('empty-state').classList.add('hidden');
            // Apply syntax highlighting to code blocks
            reportContent.querySelectorAll('pre code').forEach(el => hljs.highlightElement(el));

            // Scroll to top
            document.getElementById('view-report').scrollTop = 0;

            window.activeReportName = filename;
            syncGenerateButtons();
        } catch (e) { console.error(e); }
    }

    function showWelcome() {
        // Reset topbar
        document.getElementById('welcome-header').classList.remove('hidden');
        document.getElementById('report-topbar').classList.add('hidden');

        // Reset main view to empty state in view-report
        document.querySelectorAll('.main-view').forEach(v => v.classList.add('hidden'));
        document.getElementById('view-report')?.classList.remove('hidden');
        document.getElementById('empty-state').classList.remove('hidden');
        document.getElementById('report-content').classList.add('hidden');

        // Reset topbar tabs
        document.querySelectorAll('.topbar-tab').forEach(t => t.classList.remove('active'));
        document.querySelector('.topbar-tab[data-view="view-report"]')?.classList.add('active');

        window.activeReportName = null;
        syncGenerateButtons();
    }

    // ══════════════════════════════════════════════════════════════════════════
    // CHECKLIST
    // ══════════════════════════════════════════════════════════════════════════
    let allRules      = [];
    let ruleState     = {};
    let activeFilter  = 'all';

    document.getElementById('btn-load-rules')?.addEventListener('click', loadRules);

    async function loadRules() {
        const elLoading = document.getElementById('checklist-loading');
        const elEmpty   = document.getElementById('checklist-empty');
        const elList    = document.getElementById('rules-list');

        elEmpty.classList.add('hidden');
        elList.classList.add('hidden');
        elLoading.classList.remove('hidden');

        try {
            const [rData, cData] = await Promise.all([
                fetch('/rules',           { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } }).then(r => r.json()),
                fetch('/rules/checklist', { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } }).then(r => r.json())
            ]);
            elLoading.classList.add('hidden');

            if (!rData.rules?.length) {
                elEmpty.classList.remove('hidden');
                const p = elEmpty.querySelector('p');
                if (p) p.innerHTML = rData.error
                    ? `<span style="color:var(--err)">${rData.error}</span>`
                    : 'Sube PDFs en <strong>Nutrir IA</strong> primero, luego carga las reglas aquí.';
                return;
            }

            allRules  = rData.rules;
            ruleState = cData.selections || {};
            allRules.forEach(r => { if (!(r.id in ruleState)) ruleState[r.id] = 'neutral'; });

            checklistLoaded = true;
            elList.classList.remove('hidden');
            renderRules();
            updateStats();
            syncGenerateButtons();
        } catch (e) {
            elLoading.classList.add('hidden');
            elEmpty.classList.remove('hidden');
            const p = elEmpty.querySelector('p');
            if (p) p.textContent = 'Error cargando reglas: ' + e.message;
        }
    }

    function renderRules() {
        const list    = document.getElementById('rules-list');
        const search  = (document.getElementById('rules-search')?.value || '').toLowerCase();
        list.innerHTML = '';
        let shown = 0;

        allRules.forEach(rule => {
            const state = ruleState[rule.id] || 'neutral';
            if (activeFilter !== 'all' && state !== activeFilter) return;
            if (search && !rule.text.toLowerCase().includes(search)) return;
            shown++;

            const li = document.createElement('li');
            li.className = `rule-item rule-${state}`;
            li.dataset.id = rule.id;

            const preview = rule.text.length > 180 ? rule.text.slice(0, 180) + '…' : rule.text;
            const srcHtml = rule.source ? `<span class="rule-source">${rule.source}</span>` : '';

            li.innerHTML = `
                <div class="rule-preview">${preview}${srcHtml}</div>
                <div class="rule-actions-row">
                    <button class="rule-toggle-btn ${state === 'applies'    ? 'active-applies' : ''}" data-action="applies">✅ Aplica</button>
                    <button class="rule-toggle-btn ${state === 'not_applies'? 'active-not'     : ''}" data-action="not_applies">❌ No aplica</button>
                </div>`;

            li.querySelectorAll('.rule-toggle-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const a = btn.dataset.action;
                    ruleState[rule.id] = ruleState[rule.id] === a ? 'neutral' : a;
                    refreshRuleItem(li, rule.id);
                    updateStats();
                });
            });
            list.appendChild(li);
        });

        if (!shown) {
            const li = document.createElement('li');
            li.style.cssText = 'color:var(--tx-3);font-size:.78rem;text-align:center;padding:1.5rem;';
            li.textContent = 'Sin resultados para este filtro.';
            list.appendChild(li);
        }
    }

    function refreshRuleItem(li, id) {
        const s = ruleState[id] || 'neutral';
        li.className = `rule-item rule-${s}`;
        li.querySelectorAll('.rule-toggle-btn').forEach(btn => {
            btn.classList.remove('active-applies', 'active-not');
            if (btn.dataset.action === s)
                btn.classList.add(s === 'applies' ? 'active-applies' : 'active-not');
        });
        if (activeFilter !== 'all' && s !== activeFilter) li.remove();
    }

    function updateStats() {
        let ok = 0, no = 0, nd = 0;
        Object.values(ruleState).forEach(s => {
            if (s === 'applies')     ok++;
            else if (s === 'not_applies') no++;
            else nd++;
        });
        document.getElementById('stat-applies').textContent     = ok;
        document.getElementById('stat-not-applies').textContent = no;
        document.getElementById('stat-neutral').textContent     = nd;
    }

    // Filters
    document.getElementById('rules-filters')?.addEventListener('click', e => {
        const btn = e.target.closest('.filter-btn');
        if (!btn) return;
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        activeFilter = btn.dataset.filter;
        renderRules();
    });

    // Search
    document.getElementById('rules-search')?.addEventListener('input', renderRules);

    // Save checklist
    document.getElementById('btn-save-checklist')?.addEventListener('click', async () => {
        const btn = document.getElementById('btn-save-checklist');
        const orig = btn.textContent;
        btn.textContent = 'Guardando…';
        btn.disabled = true;
        const rules_text = {};
        allRules.forEach(r => { rules_text[r.id] = r.text; });
        try {
            const res = await fetch('/rules/checklist', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ selections: ruleState, rules_text })
            });
            const data = await res.json();
            if (res.ok) {
                btn.textContent = '✅ Guardado';
                syncGenerateButtons();
                setTimeout(() => { btn.textContent = orig; btn.disabled = false; }, 2000);
            } else {
                alert('Error al guardar: ' + (data.detail || data.message));
                btn.textContent = orig;
                btn.disabled = false;
            }
        } catch {
            alert('Error de conexión.');
            btn.textContent = orig;
            btn.disabled = false;
        }
    });

    // Generate final doc buttons
    document.getElementById('btn-generate-final-doc')?.addEventListener('click',  triggerFinalDoc);
    document.getElementById('btn-gen-doc-from-report')?.addEventListener('click', triggerFinalDoc);

    function syncGenerateButtons() {
        const has = !!window.activeReportName;
        document.getElementById('btn-generate-final-doc')?.toggleAttribute('disabled', !has);
        document.getElementById('btn-gen-doc-from-report')?.toggleAttribute('disabled', !has);
    }

    async function triggerFinalDoc() {
        if (!window.activeReportName) {
            alert('Primero abre un reporte en la pestaña Reportes.');
            return;
        }
        if (!confirm(`¿Generar Documento Final?\n\nReporte: ${window.activeReportName}\n\nAsegúrate de haber guardado el checklist antes de continuar.`)) return;

        const model = document.getElementById('model-select').value;
        const fd    = new FormData();
        fd.append('model',       model);
        fd.append('report_name', window.activeReportName);

        const btns = [
            document.getElementById('btn-generate-final-doc'),
            document.getElementById('btn-gen-doc-from-report')
        ].filter(Boolean);
        btns.forEach(b => { b.disabled = true; b.textContent = '⏳ Generando…'; });

        try {
            const res  = await fetch('/generate_final_doc', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
                body: fd
            });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                alert(`✅ Documento Final generado:\n${data.document}\n\nBúscalo en Reportes.`);
                loadReports();
            } else {
                alert('Error: ' + (data.logs || data.detail || 'Error desconocido.'));
            }
        } catch {
            alert('Error de conexión al generar el documento.');
        } finally {
            const btnFromReport = document.getElementById('btn-gen-doc-from-report');
            const btnFromCheck  = document.getElementById('btn-generate-final-doc');
            if (btnFromReport) btnFromReport.textContent = '✨ Documento Final';
            if (btnFromCheck)  btnFromCheck.textContent  = '✨ Generar Documento Final';
            syncGenerateButtons();
        }
    }

});
