document.addEventListener('DOMContentLoaded', () => {
    // Marked configuration for code highlighting
    marked.setOptions({
        highlight: function(code, lang) {
            const language = hljs.getLanguage(lang) ? lang : 'plaintext';
            return hljs.highlight(code, { language }).value;
        }
    });

    const token = localStorage.getItem('token');
    if (token) {
        showInstallOrDashboard();
    }

    // Login Logic
    const loginForm = document.getElementById('login-form');
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const user = document.getElementById('username').value;
        const pass = document.getElementById('password').value;
        const err = document.getElementById('login-error');
        
        try {
            const res = await fetch('/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({username: user, password: pass})
            });
            const data = await res.json();
            if (res.ok) {
                localStorage.setItem('token', data.token);
                showInstallOrDashboard();
            } else {
                err.textContent = data.detail || 'Error de autenticación';
            }
        } catch (error) {
            err.textContent = 'Error de conexión con el servidor.';
        }
    });

    // Logout
    document.getElementById('logout-btn').addEventListener('click', () => {
        localStorage.removeItem('token');
        document.getElementById('dashboard-screen').classList.remove('active');
        document.getElementById('dashboard-screen').classList.add('hidden');
        document.getElementById('login-screen').classList.remove('hidden');
        document.getElementById('login-screen').classList.add('active');
        document.getElementById('report-header').classList.add('hidden');
        document.getElementById('report-view').innerHTML = `
            <div class="empty-state">
                <h2>Bienvenido al Auditor</h2>
                <p>1️⃣ Nutre la IA con tus documentos.<br>2️⃣ Sube el archivo ZIP de tu proyecto para iniciar el análisis.<br>3️⃣ Espera a que se complete la auditoría.<br>4️⃣ Consulta el reporte generado.</p>
            </div>
        `;
    });

    function showDashboard() {
        document.getElementById('install-screen').classList.remove('active');
        document.getElementById('install-screen').classList.add('hidden');
        document.getElementById('dashboard-screen').classList.remove('hidden');
        document.getElementById('dashboard-screen').classList.add('active');
        
        loadReports();
        loadProjects();
    }

    function showInstallOrDashboard() {
        document.getElementById('login-screen').classList.remove('active');
        document.getElementById('login-screen').classList.add('hidden');
        
        fetch('/check_install')
            .then(res => res.json())
            .then(data => {
                if (data.installed) {
                    showDashboard();
                } else {
                    document.getElementById('install-screen').classList.remove('hidden');
                    document.getElementById('install-screen').classList.add('active');
                }
            })
            .catch(() => {
                document.getElementById('login-error').textContent = 'Error validando instalación.';
                document.getElementById('login-screen').classList.remove('hidden');
                document.getElementById('login-screen').classList.add('active');
            });
    }

    // Install Setup Logic
    document.getElementById('btn-start-install')?.addEventListener('click', async () => {
        const btn = document.getElementById('btn-start-install');
        const progress = document.getElementById('install-progress');
        const err = document.getElementById('install-error');
        
        btn.classList.add('hidden');
        progress.classList.remove('hidden');
        err.textContent = '';
        
        try {
            const res = await fetch('/install', { method: 'POST' });
            const data = await res.json();
            
            if (res.ok && data.status === 'success') {
                showDashboard();
            } else {
                btn.classList.remove('hidden');
                progress.classList.add('hidden');
                err.textContent = data.logs || data.detail || 'Error en la instalación.';
            }
        } catch (e) {
            btn.classList.remove('hidden');
            progress.classList.add('hidden');
            err.textContent = 'Error de conexión durante la instalación.';
        }
    });

    // Tab Switching Logic
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            
            // Hide all sections
            document.querySelectorAll('.upload-section').forEach(sec => sec.classList.add('hidden'));
            
            // Show target section
            const targetId = e.target.getAttribute('data-target');
            document.getElementById(targetId).classList.remove('hidden');
        });
    });

    // Cancel Audit
    document.querySelectorAll('.btn-cancel-audit').forEach(btn => {
        btn.addEventListener('click', async () => {
            if(!confirm("¿Deseas interrumpir la ejecución de la Inteligencia Artificial? Se perderá el reporte actual.")) return;
            try {
                await fetch('/cancel_audit', { method: 'POST', headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } });
            } catch(e) { console.error(e); }
        });
    });

    // --- Drag and Drop Logic generalized ---
    function enableDragAndDrop(dropZoneId, fileInputId, uploadFunc, acceptExt) {
        const dropZone = document.getElementById(dropZoneId);
        const fileInput = document.getElementById(fileInputId);
        
        dropZone.addEventListener('click', () => fileInput.click());
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults (e) { e.preventDefault(); e.stopPropagation(); }

        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
        });

        dropZone.addEventListener('drop', (e) => {
            let dt = e.dataTransfer;
            handleFiles(dt.files);
        }, false);

        fileInput.addEventListener('change', (e) => handleFiles(e.target.files));

        function handleFiles(files) {
            if (files.length > 0) {
                // Validation for extensions
                let valid = true;
                for (let i=0; i<files.length; i++) {
                    if (!files[i].name.endsWith(acceptExt)) valid = false;
                }
                if (valid) {
                    uploadFunc(files);
                } else {
                    alert(`Por favor, asegúrate de subir archivos con extensión ${acceptExt}.`);
                }
            }
        }
    }

    enableDragAndDrop('drop-zone-project', 'file-input-project', uploadProject, '.zip');
    enableDragAndDrop('drop-zone-knowledge', 'file-input-knowledge', uploadKnowledge, '.pdf');

    // Projects (Auditing)
    async function uploadProject(files) {
        const file = files[0]; // ZIP handles 1 at a time for simplicity in backend
        const formData = new FormData();
        formData.append('file', file);
        formData.append('model', document.getElementById('model-select').value);

        const dropZone = document.getElementById('drop-zone-project');
        const progress = document.getElementById('upload-progress-project');
        const statusText = document.getElementById('project-status-text');
        const progressBar = document.getElementById('project-progress-bar');
        const consoleDiv = document.getElementById('project-console');
        
        dropZone.classList.add('hidden');
        progress.classList.remove('hidden');
        progressBar.style.width = '0%';
        statusText.textContent = 'Iniciando escaneo...';
        consoleDiv.innerHTML = '<span class="mini-console-line">Iniciando despunte de proyecto...</span>';

        let pollInterval = setInterval(async () => {
            try {
                const pRes = await fetch('/progress');
                const pData = await pRes.json();
                if (pData.total > 0 || pData.file.includes("Verificando")) {
                    if (pData.total > 0) {
                        const percent = Math.round((pData.current / pData.total) * 100);
                        progressBar.style.width = `${percent}%`;
                        statusText.textContent = `Analizando (${pData.current}/${pData.total}): ${pData.file}`;
                    } else {
                        statusText.textContent = pData.file;
                    }
                    
                    const lastLine = consoleDiv.lastElementChild?.textContent;
                    const newLine = pData.total > 0 ? `[✓] Procesado: ${pData.file}` : `[i] ${pData.file}`;
                    if (lastLine !== newLine) {
                        const span = document.createElement('span');
                        span.className = 'mini-console-line';
                        span.textContent = newLine;
                        consoleDiv.appendChild(span);
                        consoleDiv.scrollTop = consoleDiv.scrollHeight;
                    }
                }
            } catch (e) {}
        }, 1000);
        
        try {
            const res = await fetch('/upload', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
                body: formData
            });
            const data = await res.json();
            
            clearInterval(pollInterval);
            progressBar.style.width = '100%';
            
            if (res.ok) {
                // Pequeña espera para que la animación se complete
                setTimeout(() => loadReports(), 600);
            } else {
                alert(`Error: ${data.detail || data.logs}`);
            }
        } catch (error) {
            clearInterval(pollInterval);
            alert('Error al subir el archivo o procesar la auditoría.');
        } finally {
            progress.classList.add('hidden');
            dropZone.classList.remove('hidden');
        }
    }

    // Knowledge (PDFs Embeddings)
    async function uploadKnowledge(files) {
        const formData = new FormData();
        for(let i=0; i<files.length; i++) {
            formData.append('files', files[i]);
        }
        formData.append('model', document.getElementById('model-select').value);

        const dropZone = document.getElementById('drop-zone-knowledge');
        const progress = document.getElementById('upload-progress-knowledge');
        
        dropZone.classList.add('hidden');
        progress.classList.remove('hidden');
        
        try {
            const res = await fetch('/upload_knowledge', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
                body: formData
            });
            const data = await res.json();
            
            if (res.ok) {
                alert("¡Base de Datos enriquecida! Los reportes detectarán estas nuevas normas.");
            } else {
                alert(`Error: ${data.detail || data.logs}`);
            }
        } catch (error) {
            alert('Error al procesar el PDF vectorial.');
        } finally {
            progress.classList.add('hidden');
            dropZone.classList.remove('hidden');
        }
    }

    // Load Projects
    async function loadProjects() {
        try {
            const res = await fetch('/projects', {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });
            const data = await res.json();
            const list = document.getElementById('repositories-list');
            list.innerHTML = '';
            
            if (data.projects.length === 0) {
                list.innerHTML = '<li style="color: #a0aec0; padding: 1rem; text-align: center; font-size: 0.9rem;">No hay proyectos cargados.</li>';
                return;
            }
            
            data.projects.forEach(project => {
                const li = document.createElement('li');
                
                const nameSpan = document.createElement('span');
                nameSpan.textContent = project;
                nameSpan.style.flex = "1";
                
                const actionsDiv = document.createElement('div');
                actionsDiv.style.display = "flex";
                actionsDiv.style.gap = "0.5rem";

                const btn = document.createElement('button');
                btn.textContent = "Auditar";
                btn.className = "btn-primary";
                btn.style.padding = "0.4rem 0.8rem";
                btn.style.fontSize = "0.8rem";
                btn.onclick = () => auditExistingProject(project);

                const renameBtn = document.createElement('button');
                renameBtn.textContent = "✏️";
                renameBtn.className = "btn-icon";
                renameBtn.title = "Renombrar Repositorio";
                renameBtn.style.background = "transparent";
                renameBtn.style.border = "none";
                renameBtn.style.padding = "0.4rem";
                renameBtn.style.cursor = "pointer";
                renameBtn.style.fontSize = "0.9rem";
                renameBtn.onclick = () => renameProject(project);

                const delBtn = document.createElement('button');
                delBtn.textContent = "🗑️";
                delBtn.className = "btn-icon";
                delBtn.title = "Eliminar Repositorio";
                delBtn.style.color = "var(--danger)";
                delBtn.style.padding = "0.4rem";
                delBtn.onclick = () => deleteProject(project);

                actionsDiv.appendChild(btn);
                actionsDiv.appendChild(renameBtn);
                actionsDiv.appendChild(delBtn);
                
                li.appendChild(nameSpan);
                li.appendChild(actionsDiv);
                list.appendChild(li);
            });
        } catch (err) {
            console.error(err);
        }
    }

    // Audit Existing Project
    async function auditExistingProject(projectName) {
        const formData = new FormData();
        formData.append('model', document.getElementById('model-select').value);
        formData.append('project_name', projectName);

        const listDiv = document.getElementById('repositories-list');
        const progress = document.getElementById('repositories-progress');
        const statusText = document.getElementById('repo-status-text');
        const progressBar = document.getElementById('repo-progress-bar');
        const consoleDiv = document.getElementById('repo-console');
        
        listDiv.classList.add('hidden');
        progress.classList.remove('hidden');
        progressBar.style.width = '0%';
        statusText.textContent = 'Contactando Motor AI...';
        consoleDiv.innerHTML = '<span class="mini-console-line">Iniciando despunte de logs...</span>';

        let pollInterval = setInterval(async () => {
            try {
                const pRes = await fetch('/progress');
                const pData = await pRes.json();
                if (pData.total > 0 || pData.file.includes("Verificando")) {
                    if (pData.total > 0) {
                        const percent = Math.round((pData.current / pData.total) * 100);
                        progressBar.style.width = `${percent}%`;
                        statusText.textContent = `Analizando (${pData.current}/${pData.total}): ${pData.file}`;
                    } else {
                        statusText.textContent = pData.file;
                    }
                    
                    const lastLine = consoleDiv.lastElementChild?.textContent;
                    const newLine = pData.total > 0 ? `[✓] Procesado: ${pData.file}` : `[i] ${pData.file}`;
                    if (lastLine !== newLine) {
                        const span = document.createElement('span');
                        span.className = 'mini-console-line';
                        span.textContent = newLine;
                        consoleDiv.appendChild(span);
                        consoleDiv.scrollTop = consoleDiv.scrollHeight;
                    }
                }
            } catch (e) {}
        }, 1000);
        
        try {
            const res = await fetch('/audit_existing', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
                body: formData
            });
            const data = await res.json();
            
            clearInterval(pollInterval);
            progressBar.style.width = '100%';
            
            if (res.ok) {
                setTimeout(() => {
                    loadReports();
                    document.querySelector('.tab-btn[data-target="reports-section"]').click();
                }, 600);
            } else {
                alert(`Error: ${data.detail || data.logs}`);
            }
        } catch (error) {
            clearInterval(pollInterval);
            alert('Error al procesar la auditoría.');
        } finally {
            progress.classList.add('hidden');
            listDiv.classList.remove('hidden');
        }
    }

    // Delete Project
    async function deleteProject(project) {
        if (!confirm(`¿Estás seguro de que deseas eliminar el repositorio '${project}'?`)) return;
        try {
            const res = await fetch(`/projects/${project}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });
            if (res.ok) {
                loadProjects();
            } else {
                alert('No se pudo eliminar el proyecto.');
            }
        } catch (e) {
            console.error(e);
        }
    }

    // Rename Project
    async function renameProject(project) {
        const newName = prompt(`Ingresa el nuevo nombre para el repositorio '${project}':`, project);
        if (!newName || newName.trim() === '' || newName === project) return;
        
        try {
            const res = await fetch(`/projects/${project}`, {
                method: 'PUT',
                headers: { 
                    'Authorization': `Bearer ${localStorage.getItem('token')}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ new_name: newName.trim() })
            });
            const data = await res.json();
            if (res.ok) {
                loadProjects();
            } else {
                alert(`Error al renombrar: ${data.detail || data.message || 'Desconocido'}`);
            }
        } catch (e) {
            console.error(e);
            alert('Error al renombrar el repositorio.');
        }
    }

    // Delete Report
    async function deleteReport(reportName) {
        if (!confirm(`¿Estás seguro de que deseas eliminar el reporte '${reportName}'?`)) return;
        try {
            const res = await fetch(`/reports/${reportName}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });
            if (res.ok) {
                loadReports();
                // If the deleted report was active, clear the view
                const reportTitle = document.getElementById('current-report-title').textContent;
                const cleanName = reportName.replace('Matriz_Hallazgos_', '').replace('.md', '');
                if (reportTitle.includes(cleanName)) {
                    document.getElementById('report-header').classList.add('hidden');
                    document.getElementById('report-view').innerHTML = `
                        <div class="empty-state">
                            <h2>Bienvenido al Auditor</h2>
                            <p>1️⃣ Nutre la IA con tus documentos.<br>2️⃣ Sube el archivo ZIP de tu proyecto para iniciar el análisis.<br>3️⃣ Espera a que se complete la auditoría.<br>4️⃣ Consulta el reporte generado.</p>
                        </div>
                    `;
                }
            } else {
                alert('No se pudo eliminar el reporte.');
            }
        } catch (e) {
            console.error(e);
        }
    }

    // Load Reports
    async function loadReports(highlightNewest = false) {
        try {
            // Prevent cache by adding timestamp
            const res = await fetch('/reports?t=' + new Date().getTime(), {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });
            const data = await res.json();
            const list = document.getElementById('reports-list');
            const previousFirst = list.firstElementChild?.dataset?.reportName;
            list.innerHTML = '';
            
            data.reports.forEach((report, idx) => {
                const li = document.createElement('li');
                li.className = 'report-item';
                li.dataset.reportName = report;
                // Remove Matriz_Hallazgos_ prefix and .md suffix for cleaner display
                let cleanName = report.replace('Matriz_Hallazgos_', '').replace('.md', '');
                const span = document.createElement('span');
                span.textContent = cleanName;
                span.style.flex = "1";
                span.onclick = () => {
                    document.querySelectorAll('.report-item').forEach(el => el.classList.remove('active'));
                    li.classList.add('active');
                    // Remove NEW badge when opened
                    li.querySelector('.badge-new')?.remove();
                    loadReportContent(report);
                };

                const actionsDiv = document.createElement('div');
                actionsDiv.style.display = "flex";
                actionsDiv.style.gap = "0.1rem";

                const renameBtn = document.createElement('button');
                renameBtn.textContent = "✏️";
                renameBtn.className = "btn-icon";
                renameBtn.title = "Renombrar Reporte";
                renameBtn.style.background = "transparent";
                renameBtn.style.border = "none";
                renameBtn.style.cursor = "pointer";
                renameBtn.style.fontSize = "0.9rem";
                renameBtn.onclick = (e) => {
                    e.stopPropagation();
                    renameReport(report, cleanName);
                };

                const delBtn = document.createElement('button');
                delBtn.textContent = "🗑️";
                delBtn.className = "btn-icon";
                delBtn.title = "Eliminar Reporte";
                delBtn.style.background = "transparent";
                delBtn.style.border = "none";
                delBtn.style.cursor = "pointer";
                delBtn.style.fontSize = "0.9rem";
                delBtn.onclick = (e) => {
                    e.stopPropagation();
                    deleteReport(report);
                };

                actionsDiv.appendChild(renameBtn);
                actionsDiv.appendChild(delBtn);

                li.appendChild(span);
                li.appendChild(actionsDiv);
                list.appendChild(li);
            });

            // Inject 'NEW' badge on the freshest report if it changed
            const firstItem = list.firstElementChild;
            if (firstItem && firstItem.dataset.reportName !== previousFirst) {
                const badge = document.createElement('span');
                badge.className = 'badge-new';
                badge.textContent = 'NEW';
                firstItem.insertBefore(badge, firstItem.firstElementChild.nextSibling);
            }
        } catch (err) {
            console.error(err);
        }
    }

    // Rename Report
    async function renameReport(reportName, currentCleanName) {
        const newName = prompt(`Ingresa el nuevo nombre para el reporte:`, currentCleanName);
        if (!newName || newName.trim() === '' || newName === currentCleanName) return;
        
        try {
            const res = await fetch(`/reports/${reportName}`, {
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
                
                // Ensure UI state resets cleanly if active file is renamed
                const reportTitle = document.getElementById('current-report-title').textContent;
                if (reportTitle.includes(currentCleanName)) {
                    document.getElementById('report-header').classList.add('hidden');
                    document.getElementById('report-view').innerHTML = `
                        <div class="empty-state">
                            <h2>Bienvenido al Auditor</h2>
                            <p>1️⃣ Nutre la IA con tus documentos.<br>2️⃣ Sube el archivo ZIP de tu proyecto para iniciar el análisis.<br>3️⃣ Espera a que se complete la auditoría.<br>4️⃣ Consulta el reporte generado.</p>
                        </div>
                    `;
                }
            } else {
                alert(`Error al renombrar: ${data.detail || data.message || 'Desconocido'}`);
            }
        } catch (e) {
            console.error(e);
            alert('Error al renombrar el reporte.');
        }
    }

    async function loadReportContent(filename) {
        try {
            const res = await fetch(`/reports/${filename}`, {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });
            const data = await res.json();
            if (res.ok) {
                // Configurar encabezado y botón descargar
                const cleanName = filename.replace('Matriz_Hallazgos_', '').replace('.md', '');
                document.getElementById('current-report-title').textContent = "Reporte: " + cleanName;
                document.getElementById('download-report-btn').href = `/download/${filename}`;
                document.getElementById('report-header').classList.remove('hidden');

                const reportView = document.getElementById('report-view');
                reportView.innerHTML = marked.parse(data.content);
            }
        } catch (err) {
            console.error(err);
        }
    }
});
