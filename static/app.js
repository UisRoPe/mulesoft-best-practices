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
                <p>Sube un archivo ZIP con tu proyecto MuleSoft para comenzar el análisis autómata o selecciona un reporte del historial.</p>
            </div>
        `;
    });

    function showDashboard() {
        document.getElementById('install-screen').classList.remove('active');
        document.getElementById('install-screen').classList.add('hidden');
        document.getElementById('dashboard-screen').classList.remove('hidden');
        document.getElementById('dashboard-screen').classList.add('active');
        
        loadReports();
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
            document.getElementById('upload-project-section').classList.add('hidden');
            document.getElementById('upload-knowledge-section').classList.add('hidden');
            
            // Show target section
            const targetId = e.target.getAttribute('data-target');
            document.getElementById(targetId).classList.remove('hidden');
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
                const file = files[0];
                if (file.name.endsWith(acceptExt)) {
                    uploadFunc(file);
                } else {
                    alert(`Por favor, sube un archivo con extensión ${acceptExt}.`);
                }
            }
        }
    }

    enableDragAndDrop('drop-zone-project', 'file-input-project', uploadProject, '.zip');
    enableDragAndDrop('drop-zone-knowledge', 'file-input-knowledge', uploadKnowledge, '.pdf');

    // Projects (Auditing)
    async function uploadProject(file) {
        const formData = new FormData();
        formData.append('file', file);

        const dropZone = document.getElementById('drop-zone-project');
        const progress = document.getElementById('upload-progress-project');
        
        dropZone.classList.add('hidden');
        progress.classList.remove('hidden');
        
        try {
            const res = await fetch('/upload', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
                body: formData
            });
            const data = await res.json();
            
            if (res.ok) {
                loadReports();
            } else {
                alert(`Error: ${data.detail || data.logs}`);
            }
        } catch (error) {
            alert('Error al subir el archivo o procesar la auditoría.');
        } finally {
            progress.classList.add('hidden');
            dropZone.classList.remove('hidden');
        }
    }

    // Knowledge (PDFs Embeddings)
    async function uploadKnowledge(file) {
        const formData = new FormData();
        formData.append('file', file);

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

    // Load Reports
    async function loadReports() {
        try {
            const res = await fetch('/reports', {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });
            const data = await res.json();
            const list = document.getElementById('reports-list');
            list.innerHTML = '';
            
            data.reports.forEach(report => {
                const li = document.createElement('li');
                li.className = 'report-item';
                // Remove Matriz_Hallazgos_ prefix and .md suffix for cleaner display
                let cleanName = report.replace('Matriz_Hallazgos_', '').replace('.md', '');
                li.textContent = cleanName;
                li.title = report;
                li.onclick = () => {
                    document.querySelectorAll('.report-item').forEach(el => el.classList.remove('active'));
                    li.classList.add('active');
                    loadReportContent(report);
                };
                list.appendChild(li);
            });
        } catch (err) {
            console.error(err);
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
