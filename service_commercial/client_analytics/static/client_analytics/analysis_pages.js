// ==========================================
// SCIENTIFIC PARTICLES SYSTEM
// Style américain futuriste pour pages d'analyse
// ==========================================

(function() {
    'use strict';
    
    // ===== CONFIGURATION =====
    const CONFIG = {
        particles: {
            count: 80,
            countMobile: 40,
            speed: 0.8,
            size: { min: 2, max: 6 },
            opacity: { min: 0.3, max: 0.8 },
            colors: [
                { r: 0, g: 217, b: 255 },    // Cyan tech
                { r: 0, g: 255, b: 255 },    // Cyan bright
                { r: 0, g: 102, b: 204 },    // Blue tech
                { r: 255, g: 0, b: 128 },    // Pink américain
                { r: 0, g: 255, b: 136 }     // Green tech
            ],
            connectionDistance: 180,
            connectionOpacity: 0.2,
            connectionWidth: 1.5,
            dataNodes: {
                count: 12,
                size: { min: 8, max: 16 },
                pulseSpeed: 0.03,
                orbitSpeed: 0.001
            }
        }
    };
    
    // ===== STATE =====
    const State = {
        isMobile: false,
        reducedMotion: false,
        isDocumentHidden: false
    };
    
    // ===== UTILITY =====
    function isMobileDevice() {
        return window.innerWidth <= 768;
    }
    
    function checkReducedMotion() {
        return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }
    
    // ===== SCIENTIFIC PARTICLES SYSTEM =====
    const ScientificParticlesSystem = {
        canvas: null,
        ctx: null,
        particles: [],
        dataNodes: [],
        dpr: 1,
        animationId: null,
        
        init() {
            this.canvas = document.getElementById('scientificParticles');
            if (!this.canvas) return;
            
            this.ctx = this.canvas.getContext('2d');
            this.dpr = window.devicePixelRatio || 1;
            
            State.isMobile = isMobileDevice();
            State.reducedMotion = checkReducedMotion();
            
            this.resize();
            window.addEventListener('resize', () => this.resize(), { passive: true });
            
            if (!State.reducedMotion) {
                this.animate();
            }
        },
        
        resize() {
            if (!this.canvas) return;
            
            const width = window.innerWidth;
            const height = window.innerHeight;
            
            this.canvas.width = width * this.dpr;
            this.canvas.height = height * this.dpr;
            this.ctx.scale(this.dpr, this.dpr);
            
            this.canvas.style.width = width + 'px';
            this.canvas.style.height = height + 'px';
            
            this.createParticles();
            this.createDataNodes();
        },
        
        createParticles() {
            const count = State.isMobile ? 
                CONFIG.particles.countMobile : 
                CONFIG.particles.count;
            
            this.particles = [];
            const w = window.innerWidth;
            const h = window.innerHeight;
            
            for (let i = 0; i < count; i++) {
                const color = CONFIG.particles.colors[
                    Math.floor(Math.random() * CONFIG.particles.colors.length)
                ];
                
                this.particles.push({
                    x: Math.random() * w,
                    y: Math.random() * h,
                    vx: (Math.random() - 0.5) * CONFIG.particles.speed,
                    vy: (Math.random() - 0.5) * CONFIG.particles.speed,
                    size: CONFIG.particles.size.min + 
                          Math.random() * (CONFIG.particles.size.max - CONFIG.particles.size.min),
                    opacity: CONFIG.particles.opacity.min + 
                            Math.random() * (CONFIG.particles.opacity.max - CONFIG.particles.opacity.min),
                    color: color,
                    pulsePhase: Math.random() * Math.PI * 2,
                    pulseSpeed: 0.02 + Math.random() * 0.02
                });
            }
        },
        
        createDataNodes() {
            this.dataNodes = [];
            const w = window.innerWidth;
            const h = window.innerHeight;
            const count = CONFIG.particles.dataNodes.count;
            
            for (let i = 0; i < count; i++) {
                const centerX = w / 2;
                const centerY = h / 2;
                const angle = (i / count) * Math.PI * 2;
                const radius = Math.min(w, h) * 0.3;
                
                const color = CONFIG.particles.colors[
                    Math.floor(Math.random() * CONFIG.particles.colors.length)
                ];
                
                this.dataNodes.push({
                    centerX: centerX,
                    centerY: centerY,
                    angle: angle,
                    radius: radius,
                    x: centerX + Math.cos(angle) * radius,
                    y: centerY + Math.sin(angle) * radius,
                    size: CONFIG.particles.dataNodes.size.min +
                          Math.random() * (CONFIG.particles.dataNodes.size.max - CONFIG.particles.dataNodes.size.min),
                    color: color,
                    pulsePhase: Math.random() * Math.PI * 2,
                    orbitSpeed: CONFIG.particles.dataNodes.orbitSpeed * (Math.random() > 0.5 ? 1 : -1)
                });
            }
        },
        
        drawParticle(particle, currentSize) {
            this.ctx.save();
            
            // Glow effet
            const gradient = this.ctx.createRadialGradient(
                particle.x, particle.y, 0,
                particle.x, particle.y, currentSize * 2
            );
            gradient.addColorStop(0, `rgba(${particle.color.r}, ${particle.color.g}, ${particle.color.b}, ${particle.opacity})`);
            gradient.addColorStop(0.5, `rgba(${particle.color.r}, ${particle.color.g}, ${particle.color.b}, ${particle.opacity * 0.3})`);
            gradient.addColorStop(1, `rgba(${particle.color.r}, ${particle.color.g}, ${particle.color.b}, 0)`);
            
            this.ctx.beginPath();
            this.ctx.arc(particle.x, particle.y, currentSize * 2, 0, Math.PI * 2);
            this.ctx.fillStyle = gradient;
            this.ctx.fill();
            
            // Core
            this.ctx.beginPath();
            this.ctx.arc(particle.x, particle.y, currentSize, 0, Math.PI * 2);
            this.ctx.fillStyle = `rgba(${particle.color.r}, ${particle.color.g}, ${particle.color.b}, ${particle.opacity})`;
            this.ctx.fill();
            
            this.ctx.restore();
        },
        
        drawDataNode(node) {
            this.ctx.save();
            
            // Update orbit
            node.angle += node.orbitSpeed;
            node.x = node.centerX + Math.cos(node.angle) * node.radius;
            node.y = node.centerY + Math.sin(node.angle) * node.radius;
            
            // Pulse
            node.pulsePhase += CONFIG.particles.dataNodes.pulseSpeed;
            const pulseFactor = 0.8 + Math.sin(node.pulsePhase) * 0.2;
            const currentSize = node.size * pulseFactor;
            
            // Outer glow (plus grand)
            const outerGradient = this.ctx.createRadialGradient(
                node.x, node.y, 0,
                node.x, node.y, currentSize * 4
            );
            outerGradient.addColorStop(0, `rgba(${node.color.r}, ${node.color.g}, ${node.color.b}, 0.6)`);
            outerGradient.addColorStop(0.5, `rgba(${node.color.r}, ${node.color.g}, ${node.color.b}, 0.2)`);
            outerGradient.addColorStop(1, `rgba(${node.color.r}, ${node.color.g}, ${node.color.b}, 0)`);
            
            this.ctx.beginPath();
            this.ctx.arc(node.x, node.y, currentSize * 4, 0, Math.PI * 2);
            this.ctx.fillStyle = outerGradient;
            this.ctx.fill();
            
            // Core hexagone (forme tech)
            this.ctx.beginPath();
            for (let i = 0; i < 6; i++) {
                const angle = (i / 6) * Math.PI * 2;
                const x = node.x + Math.cos(angle) * currentSize;
                const y = node.y + Math.sin(angle) * currentSize;
                if (i === 0) this.ctx.moveTo(x, y);
                else this.ctx.lineTo(x, y);
            }
            this.ctx.closePath();
            this.ctx.fillStyle = `rgba(${node.color.r}, ${node.color.g}, ${node.color.b}, 0.8)`;
            this.ctx.fill();
            this.ctx.strokeStyle = `rgba(255, 255, 255, 0.6)`;
            this.ctx.lineWidth = 2;
            this.ctx.stroke();
            
            this.ctx.restore();
        },
        
        drawConnections() {
            // Connections entre particules
            this.particles.forEach((p1, i) => {
                this.particles.slice(i + 1).forEach(p2 => {
                    const dx = p1.x - p2.x;
                    const dy = p1.y - p2.y;
                    const distance = Math.sqrt(dx * dx + dy * dy);
                    
                    if (distance < CONFIG.particles.connectionDistance) {
                        const opacity = (1 - distance / CONFIG.particles.connectionDistance) * 
                                      CONFIG.particles.connectionOpacity;
                        
                        this.ctx.beginPath();
                        this.ctx.strokeStyle = `rgba(0, 217, 255, ${opacity})`;
                        this.ctx.lineWidth = CONFIG.particles.connectionWidth;
                        this.ctx.moveTo(p1.x, p1.y);
                        this.ctx.lineTo(p2.x, p2.y);
                        this.ctx.stroke();
                    }
                });
            });
            
            // Connections entre data nodes
            this.dataNodes.forEach((n1, i) => {
                this.dataNodes.slice(i + 1).forEach(n2 => {
                    const dx = n1.x - n2.x;
                    const dy = n1.y - n2.y;
                    const distance = Math.sqrt(dx * dx + dy * dy);
                    
                    if (distance < 300) {
                        const gradient = this.ctx.createLinearGradient(n1.x, n1.y, n2.x, n2.y);
                        gradient.addColorStop(0, `rgba(${n1.color.r}, ${n1.color.g}, ${n1.color.b}, 0.3)`);
                        gradient.addColorStop(1, `rgba(${n2.color.r}, ${n2.color.g}, ${n2.color.b}, 0.3)`);
                        
                        this.ctx.beginPath();
                        this.ctx.strokeStyle = gradient;
                        this.ctx.lineWidth = 2;
                        this.ctx.moveTo(n1.x, n1.y);
                        this.ctx.lineTo(n2.x, n2.y);
                        this.ctx.stroke();
                    }
                });
            });
        },
        
        animate() {
            const w = window.innerWidth;
            const h = window.innerHeight;
            
            this.ctx.clearRect(0, 0, w, h);
            
            // Update and draw particles
            this.particles.forEach(p => {
                p.pulsePhase += p.pulseSpeed;
                const pulseFactor = 0.85 + Math.sin(p.pulsePhase) * 0.15;
                const currentSize = p.size * pulseFactor;
                
                p.x += p.vx;
                p.y += p.vy;
                
                if (p.x < 0 || p.x > w) { p.vx *= -1; p.x = Math.max(0, Math.min(p.x, w)); }
                if (p.y < 0 || p.y > h) { p.vy *= -1; p.y = Math.max(0, Math.min(p.y, h)); }
                
                this.drawParticle(p, currentSize);
            });
            
            // Draw data nodes
            this.dataNodes.forEach(node => {
                this.drawDataNode(node);
            });
            
            // Draw connections
            this.drawConnections();
            
            // Continue
            if (!State.isDocumentHidden && !State.reducedMotion) {
                this.animationId = requestAnimationFrame(() => this.animate());
            }
        },
        
        stop() {
            if (this.animationId) {
                cancelAnimationFrame(this.animationId);
                this.animationId = null;
            }
        }
    };
    
    // ===== DOCUMENT VISIBILITY =====
    function handleVisibilityChange() {
        State.isDocumentHidden = document.hidden;
        if (!State.isDocumentHidden && !State.reducedMotion) {
            ScientificParticlesSystem.animate();
        } else {
            ScientificParticlesSystem.stop();
        }
    }
    
    // ===== INITIALIZATION =====
    function init() {
        State.isMobile = isMobileDevice();
        State.reducedMotion = checkReducedMotion();
        
        ScientificParticlesSystem.init();
        
        document.addEventListener('visibilitychange', handleVisibilityChange);
        
        console.log('🔬 Scientific Particles System initialized');
    }
    
    // Start when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

// ==========================================
// PERIOD SELECTOR HANDLER
// Gestion du sélecteur de période (Mois/Trimestre/Année)
// ==========================================

(function() {
    'use strict';
    
    function initPeriodSelector() {
        const periodButtons = document.querySelectorAll('.period-btn');
        const periodTabs = document.querySelectorAll('#periodTabs .nav-link');
        
        if (periodButtons.length === 0) return;
        
        // Mapping entre les boutons et les onglets
        const periodMapping = {
            'month': 'month-tab',
            'quarter': 'quarter-tab',
            'year': 'fiscal-tab'
        };
        
        // Lire la granularité depuis l'URL au chargement
        const urlParams = new URLSearchParams(window.location.search);
        const currentGranularity = urlParams.get('granularity') || 'month';
        
        // Activer le bon bouton au chargement
        periodButtons.forEach(btn => {
            const period = btn.getAttribute('data-period');
            if (period === currentGranularity) {
                btn.classList.add('active');
                // Activer aussi l'onglet correspondant
                const tabId = periodMapping[period];
                const tabElement = document.getElementById(tabId);
                if (tabElement) {
                    const tab = new bootstrap.Tab(tabElement);
                    tab.show();
                }
            } else {
                btn.classList.remove('active');
            }
        });
        
        periodButtons.forEach(btn => {
            btn.addEventListener('click', function() {
                const period = this.getAttribute('data-period');
                
                // Activer visuellement le bouton
                periodButtons.forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                
                // Basculer vers l'onglet de période correspondant (client-side uniquement)
                const tabId = periodMapping[period];
                const tabElement = document.getElementById(tabId);
                if (tabElement) {
                    const tab = new bootstrap.Tab(tabElement);
                    tab.show();
                }
                
                // Reload all already-loaded AJAX tabs with the new granularity
                if (window.showPageLoader) window.showPageLoader('Changement de période…');
                const panesToReload = document.querySelectorAll('[data-ajax-tab][data-ajax-loaded="true"]');
                let pending = panesToReload.length;
                if (pending === 0 && window.hidePageLoader) {
                    setTimeout(window.hidePageLoader, 500);
                }
                panesToReload.forEach(pane => {
                    delete pane.dataset.ajaxLoaded;
                    if (window._ajaxTabSync) {
                        window._ajaxTabSync.reloadPane(pane);
                    }
                });

                // Redimensionner les graphiques Plotly après changement d'onglet
                setTimeout(() => {
                    if (window.Plotly) {
                        document.querySelectorAll('.plotly-graph-div').forEach(div => {
                            try { Plotly.Plots.resize(div); } catch(e) {}
                        });
                    }
                }, 200);
            });
        });
        
        // Synchroniser les onglets avec les boutons (optionnel, mais garde la cohérence visuelle)
        periodTabs.forEach(tab => {
            tab.addEventListener('shown.bs.tab', function(e) {
                const tabId = e.target.id;
                let period = null;
                
                // Trouver le period correspondant
                for (const [key, value] of Object.entries(periodMapping)) {
                    if (value === tabId) {
                        period = key;
                        break;
                    }
                }
                
                if (period) {
                    // Mettre à jour les boutons visuellement
                    periodButtons.forEach(btn => {
                        if (btn.getAttribute('data-period') === period) {
                            btn.classList.add('active');
                        } else {
                            btn.classList.remove('active');
                        }
                    });
                }
            });
        });
        
        console.log('📅 Period selector initialized (granularity: ' + currentGranularity + ')');
    }
    
    // Initialiser quand le DOM est prêt
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initPeriodSelector);
    } else {
        initPeriodSelector();
    }
})();

// ==========================================
// PLOTLY RESPONSIVE RESIZE HANDLER
// Redimensionne les graphiques Plotly lors des changements d'onglets et de fenêtre
// ==========================================

(function() {
    'use strict';
    
    /**
     * Redimensionne tous les graphiques Plotly dans un conteneur donné
     * @param {HTMLElement|Document} container - Le conteneur à rechercher (ou document)
     */
    function resizePlotlyIn(container) {
        if (!window.Plotly) return;
        
        const plotlyDivs = container.querySelectorAll('.plotly-graph-div');
        
        if (plotlyDivs.length === 0) return;
        
        // Utiliser requestAnimationFrame pour éviter les problèmes de layout
        requestAnimationFrame(() => {
            // Petit délai pour laisser le layout se stabiliser
            setTimeout(() => {
                plotlyDivs.forEach(div => {
                    try {
                        if (Plotly.Plots && Plotly.Plots.resize) {
                            Plotly.Plots.resize(div);
                        }
                    } catch (e) {
                        // Ignore silencieusement les erreurs (graph pas encore initialisé, etc.)
                    }
                });
            }, 100);
        });
    }
    
    /**
     * Debounce helper pour éviter trop d'appels
     */
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    /**
     * Initialise les event listeners pour le resize
     */
    function initPlotlyResize() {
        // 1. Resize initial au chargement de la page
        resizePlotlyIn(document);
        
        // 2. Resize lors du changement de taille de fenêtre (debounced)
        const debouncedResize = debounce(() => {
            resizePlotlyIn(document);
        }, 200);
        
        window.addEventListener('resize', debouncedResize, { passive: true });
        
        // 3. Resize lors du changement d'onglet Bootstrap (onglets principaux)
        const mainTabButtons = document.querySelectorAll('#analysisTabs [data-bs-toggle="tab"]');
        mainTabButtons.forEach(button => {
            button.addEventListener('shown.bs.tab', (event) => {
                const targetId = event.target.getAttribute('data-bs-target');
                if (targetId) {
                    const targetPane = document.querySelector(targetId);
                    if (targetPane) {
                        resizePlotlyIn(targetPane);
                    }
                }
            });
        });
        
        // 4. Resize lors du changement de sous-onglets période (pills)
        const periodTabButtons = document.querySelectorAll('#periodTabs [data-bs-toggle="pill"]');
        periodTabButtons.forEach(button => {
            button.addEventListener('shown.bs.tab', (event) => {
                const targetId = event.target.getAttribute('data-bs-target');
                if (targetId) {
                    const targetPane = document.querySelector(targetId);
                    if (targetPane) {
                        resizePlotlyIn(targetPane);
                    }
                }
            });
        });

        // 5. Observer pour les sections qui deviennent visibles (display: none -> block)
        // Utile pour les sections "Analyse avancée" qui sont toggles
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
                    const target = mutation.target;
                    // Si l'élément devient visible
                    if (target.style.display !== 'none' && target.offsetParent !== null) {
                        const plotlyDivs = target.querySelectorAll('.plotly-graph-div');
                        if (plotlyDivs.length > 0) {
                            resizePlotlyIn(target);
                        }
                    }
                }
            });
        });
        
        // Observer les changements de style sur les sections potentielles
        const sections = document.querySelectorAll('.collapse, [class*="advanced"]');
        sections.forEach(section => {
            observer.observe(section, { 
                attributes: true, 
                attributeFilter: ['style', 'class'] 
            });
        });
        
        console.log('📊 Plotly responsive resize handler initialized');
    }
    
    // Initialiser quand le DOM est prêt
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initPlotlyResize);
    } else {
        initPlotlyResize();
    }
})();

// ==========================================
// GESTION DES ONGLETS PRINCIPAUX
// ==========================================
(function() {
    'use strict';
    
    function initTabTracking() {
        const tabButtons = document.querySelectorAll('#analysisTabs button[data-bs-toggle="tab"]');
        
        if (tabButtons.length === 0) return;
        
        // Mapping entre les ID d'onglets et les noms de tabs
        const tabMapping = {
            'stats-tab': 'statistics',
            'products-tab': 'products',
            'clients-tab': 'clients',
            'geography-tab': 'geographic',
            'currency-tab': 'currency'
        };
        
        // Écouter les changements d'onglets
        tabButtons.forEach(btn => {
            btn.addEventListener('shown.bs.tab', function(e) {
                const tabId = e.target.id;
                const tabName = tabMapping[tabId];
                
                if (tabName) {
                    // Mettre à jour l'URL sans recharger la page
                    const currentUrl = new URL(window.location.href);
                    currentUrl.searchParams.set('tab', tabName);
                    window.history.pushState({tab: tabName}, '', currentUrl.toString());
                    
                    console.log('📑 Onglet activé:', tabName);
                }
            });
        });
        
        // Au chargement, activer l'onglet correspondant au paramètre tab
        const urlParams = new URLSearchParams(window.location.search);
        const currentTab = urlParams.get('tab');
        
        if (currentTab) {
            // Trouver le bouton d'onglet correspondant
            for (const [btnId, tabName] of Object.entries(tabMapping)) {
                if (tabName === currentTab) {
                    const tabElement = document.getElementById(btnId);
                    if (tabElement) {
                        const tab = new bootstrap.Tab(tabElement);
                        tab.show();
                    }
                    break;
                }
            }
        }
        
        console.log('📑 Tab tracking initialized');
    }
    
    // Initialiser quand le DOM est prêt
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTabTracking);
    } else {
        initTabTracking();
    }
})();

// ==========================================
// AJAX HANDLERS POUR ANALYSES CIBLÉES
// Évite le rechargement complet de la page
// ==========================================
(function() {
    'use strict';
    
    /**
     * Injecte du HTML et exécute les scripts qu'il contient
     * (nécessaire pour les graphiques Plotly qui ont des <script>)
     */
    function injectHTMLWithScripts(container, htmlString) {
        // Créer un élément temporaire pour parser le HTML
        const temp = document.createElement('div');
        temp.innerHTML = htmlString;
        
        // Extraire tous les scripts
        const scripts = temp.querySelectorAll('script');
        const scriptContents = [];
        scripts.forEach(script => {
            const scriptType = (script.getAttribute('type') || '').trim().toLowerCase();
            const isExecutable = !scriptType || ['text/javascript', 'application/javascript', 'text/ecmascript', 'application/ecmascript', 'module'].includes(scriptType);
            if (!script.src && !isExecutable) {
                return;
            }
            if (script.src) {
                // Script externe
                scriptContents.push({type: 'external', src: script.src, scriptType: scriptType});
            } else {
                // Script inline
                scriptContents.push({type: 'inline', content: script.textContent, scriptType: scriptType});
            }
            script.remove(); // Retirer le script du HTML
        });
        
        // Injecter le HTML sans les scripts
        container.innerHTML = temp.innerHTML;
        
        // Exécuter les scripts un par un
        scriptContents.forEach(script => {
            const scriptElement = document.createElement('script');
            if (script.scriptType) scriptElement.type = script.scriptType;
            if (script.type === 'external') {
                scriptElement.src = script.src;
            } else {
                scriptElement.textContent = script.content;
            }
            container.appendChild(scriptElement);
        });
    }
    
    function initAjaxForms() {
        // Récupérer le dataset PK depuis l'URL
        const pathParts = window.location.pathname.split('/');
        const pkIndex = pathParts.indexOf('dataset');
        const datasetPk = pkIndex >= 0 ? pathParts[pkIndex + 1] : null;
        
        if (!datasetPk) return;
        
        // ===== 1. PORTEFEUILLE CLIENT =====
        const clientPortfolioForms = Array.from(document.querySelectorAll('form')).filter(form =>
            form.querySelector('select[name="client"]') &&
            form.querySelector('input[name="tab"][value="clients"]')
        );
        clientPortfolioForms.forEach(form => {
            if (form.hasAttribute('data-ajax-handled')) return;
            form.setAttribute('data-ajax-handled', 'true');
            
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                
                const clientId = this.querySelector('select[name="client"]').value;
                const activePeriod = document.querySelector('.period-btn.active');
                const granularityInput = this.querySelector('input[name="granularity"]');
                const granularity = (activePeriod?.dataset.period || granularityInput?.value || 'month');
                if (granularityInput) granularityInput.value = granularity;
                
                if (!clientId) {
                    alert('Veuillez sélectionner un client');
                    return;
                }
                
                // Trouver le conteneur de résultats (après le formulaire)
                let resultsContainer = this.parentElement.querySelector('.client-portfolio-results');
                if (!resultsContainer) {
                    // Chercher le conteneur existant avec condition {% if selected_client %}
                    const nextDiv = this.nextElementSibling;
                    if (nextDiv && nextDiv.classList.contains('mt-4')) {
                        resultsContainer = nextDiv;
                        resultsContainer.classList.add('client-portfolio-results');
                    } else {
                        resultsContainer = document.createElement('div');
                        resultsContainer.className = 'mt-4 client-portfolio-results';
                        this.parentElement.appendChild(resultsContainer);
                    }
                }
                
                // Afficher un loader
                resultsContainer.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">Chargement...</span></div></div>';
                
                // Requête AJAX
                const action = this.getAttribute('action') || `/dataset/${datasetPk}/ajax/client-portfolio/`;
                const url = `${action}?client=${encodeURIComponent(clientId)}&granularity=${encodeURIComponent(granularity)}`;
                
                fetch(url)
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            injectHTMLWithScripts(resultsContainer, data.html);
                            if (window.initClient360Dashboards) {
                                window.initClient360Dashboards(resultsContainer);
                            }
                            const currentUrl = new URL(window.location.href);
                            currentUrl.searchParams.set('tab', 'clients');
                            currentUrl.searchParams.set('client', clientId);
                            currentUrl.searchParams.set('granularity', granularity);
                            window.history.replaceState({tab: 'clients', client: clientId}, '', currentUrl.toString());
                            // Redimensionner les graphiques Plotly si présents
                            if (window.Plotly) {
                                setTimeout(() => {
                                    const plotlyDivs = resultsContainer.querySelectorAll('.plotly-graph-div');
                                    plotlyDivs.forEach(div => {
                                        try {
                                            Plotly.Plots.resize(div);
                                        } catch(e) {}
                                    });
                                }, 100);
                            }
                        } else {
                            resultsContainer.innerHTML = `<div class="alert alert-danger">${data.error || 'Erreur lors du chargement'}</div>`;
                        }
                    })
                    .catch(error => {
                        console.error('Erreur AJAX:', error);
                        resultsContainer.innerHTML = '<div class="alert alert-danger">Erreur de chargement</div>';
                    });
            });
        });
        
        // ===== 2. CORRÉLATION CIBLÉE (PRODUIT/FAMILLE) =====
        const correlationForms = Array.from(document.querySelectorAll('form')).filter(form =>
            form.querySelector('select[name="product"]') &&
            form.querySelector('select[name="family"]') &&
            form.querySelector('input[name="tab"][value="products"]')
        );
        correlationForms.forEach(form => {
            if (form.hasAttribute('data-ajax-handled')) return;
            form.setAttribute('data-ajax-handled', 'true');
            
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                
                const product = this.querySelector('select[name="product"]').value;
                const family = this.querySelector('select[name="family"]').value;
                const granularity = this.querySelector('input[name="granularity"]').value || 'month';
                
                if (!product && !family) {
                    alert('Veuillez sélectionner un produit OU une famille');
                    return;
                }
                
                // Trouver ou créer le conteneur de résultats
                let resultsContainer = this.parentElement.querySelector('.correlation-results');
                if (!resultsContainer) {
                    // Chercher le conteneur existant après le formulaire
                    const conditionalResults = Array.from(this.parentElement.children)
                        .find(el => el.classList.contains('mt-3') && !el.querySelector('form'));
                    
                    if (conditionalResults) {
                        resultsContainer = conditionalResults;
                        resultsContainer.classList.add('correlation-results');
                    } else {
                        resultsContainer = document.createElement('div');
                        resultsContainer.className = 'correlation-results mt-3';
                        this.parentElement.appendChild(resultsContainer);
                    }
                }
                
                resultsContainer.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">Chargement...</span></div></div>';
                
                const params = new URLSearchParams({
                    product: product,
                    family: family,
                    granularity: granularity
                });
                
                fetch(`/dataset/${datasetPk}/ajax/product-correlation/?${params}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            injectHTMLWithScripts(resultsContainer, data.html);
                            if (window.Plotly) {
                                setTimeout(() => {
                                    const plotlyDivs = resultsContainer.querySelectorAll('.plotly-graph-div');
                                    plotlyDivs.forEach(div => {
                                        try {
                                            Plotly.Plots.resize(div);
                                        } catch(e) {}
                                    });
                                }, 100);
                            }
                        } else {
                            resultsContainer.innerHTML = `<div class="alert alert-danger">${data.error || 'Erreur'}</div>`;
                        }
                    })
                    .catch(error => {
                        console.error('Erreur AJAX:', error);
                        resultsContainer.innerHTML = '<div class="alert alert-danger">Erreur de chargement</div>';
                    });
            });
        });
        
        // ===== 3. COMPARAISON PRODUITS =====
        const compareProductsForms = document.querySelectorAll('form:has(select[name="compare_products"][multiple]):has(select[name="compare_products_metric"])');
        compareProductsForms.forEach(form => {
            if (form.hasAttribute('data-ajax-handled')) return;
            form.setAttribute('data-ajax-handled', 'true');
            
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                
                const productsSelect = this.querySelector('select[name="compare_products"]');
                const selectedProducts = Array.from(productsSelect.selectedOptions).map(opt => opt.value);
                const metric = this.querySelector('select[name="compare_products_metric"]').value;
                const granularity = this.querySelector('input[name="granularity"]').value || 'month';
                
                if (selectedProducts.length === 0) {
                    alert('Veuillez sélectionner au moins un produit');
                    return;
                }
                
                let resultsContainer = this.parentElement.querySelector('.compare-products-results');
                if (!resultsContainer) {
                    // Chercher résultats existants
                    const conditionalResults = Array.from(this.parentElement.children)
                        .find(el => el.classList.contains('mt-3') && !el.querySelector('form'));
                    
                    if (conditionalResults) {
                        resultsContainer = conditionalResults;
                        resultsContainer.classList.add('compare-products-results');
                    } else {
                        resultsContainer = document.createElement('div');
                        resultsContainer.className = 'compare-products-results mt-3';
                        this.parentElement.appendChild(resultsContainer);
                    }
                }
                
                resultsContainer.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">Chargement...</span></div></div>';
                
                const params = new URLSearchParams({
                    compare_products_metric: metric,
                    granularity: granularity
                });
                selectedProducts.forEach(p => params.append('compare_products', p));
                
                fetch(`/dataset/${datasetPk}/ajax/compare-products/?${params}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            injectHTMLWithScripts(resultsContainer, data.html);
                            if (window.Plotly) {
                                setTimeout(() => {
                                    const plotlyDivs = resultsContainer.querySelectorAll('.plotly-graph-div');
                                    plotlyDivs.forEach(div => {
                                        try {
                                            Plotly.Plots.resize(div);
                                        } catch(e) {}
                                    });
                                }, 100);
                            }
                        } else {
                            resultsContainer.innerHTML = `<div class="alert alert-danger">${data.error || 'Erreur'}</div>`;
                        }
                    })
                    .catch(error => {
                        console.error('Erreur AJAX:', error);
                        resultsContainer.innerHTML = '<div class="alert alert-danger">Erreur de chargement</div>';
                    });
            });
        });
        
        // ===== 4. COMPARAISON FAMILLES =====
        const compareFamiliesForms = document.querySelectorAll('form:has(select[name="compare_families"][multiple]):has(select[name="compare_families_metric"])');
        compareFamiliesForms.forEach(form => {
            if (form.hasAttribute('data-ajax-handled')) return;
            form.setAttribute('data-ajax-handled', 'true');
            
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                
                const familiesSelect = this.querySelector('select[name="compare_families"]');
                const selectedFamilies = Array.from(familiesSelect.selectedOptions).map(opt => opt.value);
                const metric = this.querySelector('select[name="compare_families_metric"]').value;
                const granularity = this.querySelector('input[name="granularity"]').value || 'month';
                
                if (selectedFamilies.length === 0) {
                    alert('Veuillez sélectionner au moins une famille');
                    return;
                }
                
                let resultsContainer = this.parentElement.querySelector('.compare-families-results');
                if (!resultsContainer) {
                    // Chercher résultats existants
                    const conditionalResults = Array.from(this.parentElement.children)
                        .find(el => el.classList.contains('mt-3') && !el.querySelector('form'));
                    
                    if (conditionalResults) {
                        resultsContainer = conditionalResults;
                        resultsContainer.classList.add('compare-families-results');
                    } else {
                        resultsContainer = document.createElement('div');
                        resultsContainer.className = 'compare-families-results mt-3';
                        this.parentElement.appendChild(resultsContainer);
                    }
                }
                
                resultsContainer.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">Chargement...</span></div></div>';
                
                const params = new URLSearchParams({
                    compare_families_metric: metric,
                    granularity: granularity
                });
                selectedFamilies.forEach(f => params.append('compare_families', f));
                
                fetch(`/dataset/${datasetPk}/ajax/compare-families/?${params}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            injectHTMLWithScripts(resultsContainer, data.html);
                            if (window.Plotly) {
                                setTimeout(() => {
                                    const plotlyDivs = resultsContainer.querySelectorAll('.plotly-graph-div');
                                    plotlyDivs.forEach(div => {
                                        try {
                                            Plotly.Plots.resize(div);
                                        } catch(e) {}
                                    });
                                }, 100);
                            }
                        } else {
                            resultsContainer.innerHTML = `<div class="alert alert-danger">${data.error || 'Erreur'}</div>`;
                        }
                    })
                    .catch(error => {
                        console.error('Erreur AJAX:', error);
                        resultsContainer.innerHTML = '<div class="alert alert-danger">Erreur de chargement</div>';
                    });
            });
        });
        
        console.log('🔄 AJAX forms initialized');
    }
    window.initClientAnalyticsAjaxForms = initAjaxForms;
    
    // Initialiser quand le DOM est prêt
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAjaxForms);
    } else {
        initAjaxForms();
    }
})();

// ==========================================
// AJAX TAB LAZY LOADING
// Loads tab content on first click via /ajax/tab/
// ==========================================
(function() {
    'use strict';

    function getDatasetPk() {
        const parts = window.location.pathname.split('/');
        const idx = parts.indexOf('dataset');
        return idx >= 0 ? parts[idx + 1] : null;
    }

    function injectHTMLWithScripts(container, htmlString) {
        const temp = document.createElement('div');
        temp.innerHTML = htmlString;
        const scripts = [];
        temp.querySelectorAll('script').forEach(s => {
            const scriptType = (s.getAttribute('type') || '').trim().toLowerCase();
            const isExecutable = !scriptType || ['text/javascript', 'application/javascript', 'text/ecmascript', 'application/ecmascript', 'module'].includes(scriptType);
            if (!s.src && !isExecutable) {
                return;
            }
            scripts.push(s.src ? {type: 'external', src: s.src, scriptType: scriptType} : {type: 'inline', content: s.textContent, scriptType: scriptType});
            s.remove();
        });
        container.innerHTML = temp.innerHTML;
        scripts.forEach(s => {
            const el = document.createElement('script');
            if (s.scriptType) el.type = s.scriptType;
            if (s.type === 'external') el.src = s.src;
            else el.textContent = s.content;
            container.appendChild(el);
        });
    }

    // Sub-tab pill IDs for each ajax tab name
    const SUB_TAB_PILLS = {
        products:   { month: 'products-month-tab',  quarter: 'products-quarter-tab',  year: 'products-fiscal-tab'  },
        geographic: { month: 'geo-month-tab',        quarter: 'geo-quarter-tab',        year: 'geo-fiscal-tab'        },
        currency:   { month: 'currency-month-tab',   quarter: 'currency-quarter-tab',   year: 'currency-fiscal-tab'   },
        // clients has no sub-tab pills (single granularity per load)
    };

    function syncPeriodInPane(pane, period) {
        const tabName = pane.dataset.ajaxTab;
        const pillMap = SUB_TAB_PILLS[tabName];
        if (!pillMap) return;
        const pillId = pillMap[period] || pillMap['month'];
        const pill = pane.querySelector('#' + pillId);
        if (pill && window.bootstrap) {
            new bootstrap.Tab(pill).show();
        }
    }

    function resizePlotsIn(pane) {
        if (!window.Plotly) return;
        setTimeout(() => {
            pane.querySelectorAll('.plotly-graph-div').forEach(div => {
                try { Plotly.Plots.resize(div); } catch(e) {}
            });
        }, 250);
    }

    function getCurrentPeriod() {
        const active = document.querySelector('.period-btn.active');
        return active ? active.dataset.period : 'month';
    }

    function loadAjaxTab(pane, datasetPk) {
        if (pane.dataset.ajaxLoaded === 'true') return;

        const tabName = pane.dataset.ajaxTab;
        const period  = getCurrentPeriod();
        const params  = new URLSearchParams({ tab: tabName, granularity: period });
        if (tabName === 'clients') {
            const urlParams = new URLSearchParams(window.location.search);
            const selectedClient = urlParams.get('client');
            if (selectedClient) params.set('client', selectedClient);
        }

        // Keep spinner visible during load
        fetch(`/dataset/${datasetPk}/ajax/tab/?${params}`)
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    injectHTMLWithScripts(pane, data.html);
                    pane.dataset.ajaxLoaded = 'true';
                    if (window.initClientAnalyticsAjaxForms) {
                        window.initClientAnalyticsAjaxForms();
                    }
                    if (window.initClient360Dashboards) {
                        window.initClient360Dashboards(pane);
                    }
                    syncPeriodInPane(pane, period);
                    resizePlotsIn(pane);
                } else {
                    pane.innerHTML = `<div class="alert alert-danger mt-4"><i class="bi bi-exclamation-triangle"></i> ${data.error || 'Erreur de chargement'}</div>`;
                }
            })
            .catch(() => {
                pane.innerHTML = '<div class="alert alert-danger mt-4"><i class="bi bi-exclamation-triangle"></i> Erreur réseau lors du chargement.</div>';
            })
            .finally(() => {
                // Masquer le loader si plus aucun onglet n'est en cours de chargement
                const stillLoading = document.querySelectorAll('[data-ajax-tab]:not([data-ajax-loaded])');
                // Un onglet non chargé = placeholder visible = en cours
                const spinners = document.querySelectorAll('[data-ajax-tab] .ajax-tab-placeholder');
                if (spinners.length === 0 && window.hidePageLoader) window.hidePageLoader();
            });
    }

    function reloadPane(pane) {
        loadAjaxTab(pane, getDatasetPk());
    }

    // Expose for use by period selector
    window._ajaxTabSync = { syncPeriodInPane, reloadPane, SUB_TAB_PILLS };

    function initAjaxTabLoading() {
        const datasetPk = getDatasetPk();
        if (!datasetPk) return;

        document.querySelectorAll('#analysisTabs button[data-bs-toggle="tab"]').forEach(btn => {
            btn.addEventListener('shown.bs.tab', function() {
                const pane = document.querySelector(this.dataset.bsTarget);
                if (pane && pane.dataset.ajaxTab) {
                    loadAjaxTab(pane, datasetPk);
                }
            });
        });

        // Load the active AJAX tab on page init (in case URL param pre-selects a tab)
        const activePane = document.querySelector('#analysisTabContent .tab-pane.active[data-ajax-tab]');
        if (activePane) {
            loadAjaxTab(activePane, datasetPk);
        }

        console.log('⚡ AJAX tab lazy loading initialized');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAjaxTabLoading);
    } else {
        initAjaxTabLoading();
    }
})();

// ==========================================
// GLOBAL PAGE LOADER
// Spinner plein écran sur:
//  - clics sur .period-btn (rechargement granularité)
//  - submit de tout formulaire d'analyse (.analysis-form)
//  - submit du formulaire anomalies (#bmForm)
// ==========================================
(function() {
    'use strict';

    // ----- Injection de l'overlay dans le body -----
    function ensureOverlay() {
        let el = document.getElementById('pageLoaderOverlay');
        if (!el) {
            el = document.createElement('div');
            el.id = 'pageLoaderOverlay';
            el.className = 'page-loader-overlay';
            el.innerHTML = '<div class="page-loader-spinner"></div><div class="page-loader-text" id="pageLoaderText">Calcul en cours…</div>';
            document.body.appendChild(el);
        }
        return el;
    }

    function showLoader(text) {
        const overlay = ensureOverlay();
        const textEl = overlay.querySelector('#pageLoaderText');
        if (textEl) textEl.textContent = text || 'Calcul en cours…';
        overlay.classList.add('active');
    }

    function hideLoader() {
        const overlay = document.getElementById('pageLoaderOverlay');
        if (overlay) overlay.classList.remove('active');
    }

    // Expose globally so AJAX handlers can call it
    window.showPageLoader = showLoader;
    window.hidePageLoader = hideLoader;

    function init() {
        ensureOverlay();

        // === 1. Period buttons (stats page) ===
        // Ces boutons déclenchent des reloads AJAX des onglets → on affiche
        // le loader et on le masque quand les fetches sont terminés.
        document.querySelectorAll('.period-btn').forEach(btn => {
            // Les <a> period-btn naviguent → loader simple avant navigation
            if (btn.tagName === 'A') {
                btn.addEventListener('click', function() {
                    showLoader('Changement de période…');
                });
            } else {
                // Les <button> period-btn rechargent les onglets AJAX
                btn.addEventListener('click', function() {
                    showLoader('Changement de période…');
                    // On masque après un délai max (les AJAX reloads gèrent leur propre spinner)
                    setTimeout(hideLoader, 4000);
                });
            }
        });

        // === 2. Formulaires d'analyse avec classe .analysis-form (stats, etc.) ===
        document.querySelectorAll('form.analysis-form').forEach(form => {
            if (form.hasAttribute('data-loader-handled')) return;
            form.setAttribute('data-loader-handled', 'true');
            form.addEventListener('submit', function() {
                showLoader('Analyse en cours…');
            });
        });

        // === 3. Bouton clustering (form POST) ===
        document.querySelectorAll('form[method="post"]').forEach(form => {
            if (form.hasAttribute('data-loader-handled')) return;
            const btn = form.querySelector('button[type="submit"]');
            if (!btn) return;
            form.setAttribute('data-loader-handled', 'true');
            form.addEventListener('submit', function() {
                showLoader('Analyse en cours…');
                // Remplace le texte du bouton
                btn.disabled = true;
                const icon = btn.querySelector('i');
                if (icon) icon.className = '';
                const original = btn.innerHTML;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Calcul…';
                // Restaurer si erreur (ex. validation)
                setTimeout(() => {
                    btn.disabled = false;
                    btn.innerHTML = original;
                    hideLoader();
                }, 30000);
            });
        });

        // === 4. Formulaire anomalies / monitoring comportemental (GET) ===
        const bmForm = document.getElementById('bmForm');
        if (bmForm && !bmForm.hasAttribute('data-loader-handled')) {
            bmForm.setAttribute('data-loader-handled', 'true');
            bmForm.addEventListener('submit', function() {
                showLoader('Analyse comportementale…');
            });
        }

        // === 5. Boutons "Analyser" avec data-loader-text ===
        document.querySelectorAll('[data-loader-text]').forEach(el => {
            if (el.hasAttribute('data-loader-handled')) return;
            el.setAttribute('data-loader-handled', 'true');
            el.addEventListener('click', function() {
                showLoader(this.getAttribute('data-loader-text') || 'Calcul…');
            });
        });

        // Cacher le loader quand la page est complètement chargée
        // (au cas où on revient en arrière)
        window.addEventListener('pageshow', hideLoader);
    }

    // Masquer si déjà affiché au chargement (ex: back navigation)
    document.addEventListener('DOMContentLoaded', function() {
        hideLoader();
        init();
    });
    if (document.readyState !== 'loading') {
        hideLoader();
        init();
    }
})();

// ==========================================
// THEME CHANGE HANDLER FOR PLOTLY
// Updates Plotly chart colors when theme switches
// ==========================================
(function() {
    'use strict';

    function getPlotlyThemeColors() {
        const style = getComputedStyle(document.documentElement);
        return {
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: style.getPropertyValue('--plotly-bg').trim(),
            font: { color: style.getPropertyValue('--plotly-text').trim() },
            xaxis: {
                gridcolor: style.getPropertyValue('--plotly-grid').trim(),
                zerolinecolor: style.getPropertyValue('--plotly-grid').trim()
            },
            yaxis: {
                gridcolor: style.getPropertyValue('--plotly-grid').trim(),
                zerolinecolor: style.getPropertyValue('--plotly-grid').trim()
            }
        };
    }

    function updatePlotlyTheme() {
        if (!window.Plotly) return;
        const colors = getPlotlyThemeColors();
        document.querySelectorAll('.plotly-graph-div').forEach(div => {
            try {
                Plotly.relayout(div, colors);
            } catch (e) { /* graph not ready */ }
        });
    }

    document.addEventListener('themeChanged', () => {
        setTimeout(updatePlotlyTheme, 100);
    });
})();

// ==========================================
// CLIENT 360 INTERACTIVE DASHBOARD
// ==========================================
(function() {
    'use strict';

    const PLOT_CONFIG = { responsive: true, displaylogo: false };

    function asNumber(value) {
        const n = Number(value);
        return Number.isFinite(n) ? n : 0;
    }

    function escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function formatMoney(value) {
        return `${Math.round(asNumber(value)).toLocaleString('fr-FR')} €`;
    }

    function formatNumber(value, digits = 0) {
        return asNumber(value).toLocaleString('fr-FR', {
            minimumFractionDigits: digits,
            maximumFractionDigits: digits
        });
    }

    function formatPct(value) {
        if (value === null || value === undefined || Number.isNaN(Number(value))) return '-';
        const sign = Number(value) > 0 ? '+' : '';
        return `${sign}${formatNumber(value, 1)}%`;
    }

    function median(values) {
        const arr = values.map(Number).filter(Number.isFinite).sort((a, b) => a - b);
        if (!arr.length) return null;
        const mid = Math.floor(arr.length / 2);
        return arr.length % 2 ? arr[mid] : (arr[mid - 1] + arr[mid]) / 2;
    }

    function plotlyLayout(title, extra = {}) {
        const style = getComputedStyle(document.documentElement);
        const grid = style.getPropertyValue('--plotly-grid').trim() || 'rgba(148,163,184,0.25)';
        const text = style.getPropertyValue('--plotly-text').trim() || style.getPropertyValue('--text-primary').trim();
        return Object.assign({
            title: { text: title, font: { size: 14 } },
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { color: text || '#334155', size: 12 },
            margin: { l: 52, r: 36, t: 52, b: 48 },
            hovermode: 'x unified',
            legend: { orientation: 'h', yanchor: 'bottom', y: 1.02, xanchor: 'left', x: 0 },
            xaxis: { gridcolor: grid, zerolinecolor: grid, automargin: true },
            yaxis: { gridcolor: grid, zerolinecolor: grid, automargin: true }
        }, extra);
    }

    function getData(root) {
        const script = root.querySelector('script[type="application/json"]');
        if (!script) return null;
        try {
            return JSON.parse(script.textContent || '{}');
        } catch (e) {
            console.error('Client360 JSON parse error', e);
            return null;
        }
    }

    function setOptions(select, items, allLabel, selectedValue) {
        if (!select) return;
        const current = selectedValue ?? select.value;
        const html = [`<option value="all">${escapeHtml(allLabel)}</option>`].concat(
            (items || []).map(item => {
                const value = item.value ?? item.label ?? item;
                const label = item.label ?? item.value ?? item;
                return `<option value="${escapeHtml(value)}">${escapeHtml(label)}</option>`;
            })
        ).join('');
        select.innerHTML = html;
        const values = Array.from(select.options).map(option => option.value);
        select.value = values.includes(current) ? current : 'all';
    }

    function setPeriodOptions(select, periods, selectedValue) {
        if (!select) return;
        select.innerHTML = (periods || []).map(item =>
            `<option value="${escapeHtml(item.value)}">${escapeHtml(item.label || item.value)}</option>`
        ).join('');
        if (selectedValue && Array.from(select.options).some(option => option.value === selectedValue)) {
            select.value = selectedValue;
        }
    }

    function periodIndexMap(data) {
        const map = new Map();
        (data.filters?.periods || []).forEach((period, idx) => {
            map.set(String(period.value), Number.isFinite(Number(period.index)) ? Number(period.index) : idx);
        });
        return map;
    }

    function initFilters(root, data, state) {
        const filters = data.filters || {};
        setPeriodOptions(root.querySelector('[data-client360-filter="period-start"]'), filters.periods || [], state.periodStart);
        setPeriodOptions(root.querySelector('[data-client360-filter="period-end"]'), filters.periods || [], state.periodEnd);
        setOptions(root.querySelector('[data-client360-filter="family"]'), filters.families || [], 'Toutes', state.family);
        setOptions(root.querySelector('[data-client360-filter="product"]'), filters.products || [], 'Tous', state.product);
        setOptions(root.querySelector('[data-client360-filter="country"]'), filters.countries || [], 'Toutes', state.country);
        const metricSelect = root.querySelector('[data-client360-filter="metric"]');
        if (metricSelect) {
            metricSelect.innerHTML = (data.metrics || []).map(item =>
                `<option value="${escapeHtml(item.value)}">${escapeHtml(item.label)}</option>`
            ).join('');
            metricSelect.value = Array.from(metricSelect.options).some(option => option.value === state.metric) ? state.metric : 'ca';
        }

        root.querySelectorAll('[data-client360-filter]').forEach(select => {
            if (select.dataset.client360Bound === 'true') return;
            select.dataset.client360Bound = 'true';
            select.addEventListener('change', () => {
                const key = select.dataset.client360Filter;
                if (key === 'period-start') state.periodStart = select.value;
                if (key === 'period-end') state.periodEnd = select.value;
                if (key === 'family') state.family = select.value;
                if (key === 'product') state.product = select.value;
                if (key === 'country') state.country = select.value;
                if (key === 'metric') state.metric = select.value;
                render(root, data, state);
            });
        });

        const reset = root.querySelector('[data-client360-reset]');
        if (reset && reset.dataset.client360Bound !== 'true') {
            reset.dataset.client360Bound = 'true';
            reset.addEventListener('click', () => {
                const periods = filters.periods || [];
                state.periodStart = periods[0]?.value || '';
                state.periodEnd = periods[periods.length - 1]?.value || '';
                state.family = 'all';
                state.product = 'all';
                state.country = 'all';
                state.metric = 'ca';
                initFilters(root, data, state);
                render(root, data, state);
            });
        }
    }

    function filteredRecords(data, state) {
        const pMap = periodIndexMap(data);
        let start = pMap.get(String(state.periodStart));
        let end = pMap.get(String(state.periodEnd));
        if (start === undefined) start = -Infinity;
        if (end === undefined) end = Infinity;
        if (start > end) [start, end] = [end, start];

        return (data.records || []).filter(record => {
            const idx = Number.isFinite(Number(record.period_index)) ? Number(record.period_index) : pMap.get(String(record.period));
            if (idx < start || idx > end) return false;
            if (state.family !== 'all' && record.family !== state.family) return false;
            if (state.product !== 'all' && record.product !== state.product) return false;
            if (state.country !== 'all' && record.country !== state.country) return false;
            return true;
        });
    }

    function groupRecords(records, key) {
        const map = new Map();
        records.forEach(record => {
            const name = record[key] || 'Non renseigne';
            if (!map.has(name)) {
                map.set(name, {
                    name,
                    ca: 0,
                    qty: 0,
                    orders: 0,
                    lines: 0,
                    families: new Set(),
                    products: new Set(),
                    periods: new Set(),
                    leadValues: [],
                    lateValues: [],
                    unitValues: []
                });
            }
            const row = map.get(name);
            row.ca += asNumber(record.ca);
            row.qty += asNumber(record.qty);
            row.orders += asNumber(record.orders);
            row.lines += asNumber(record.lines);
            row.families.add(record.family);
            row.products.add(record.product);
            row.periods.add(record.period);
            if (record.lead_time_median !== null && record.lead_time_median !== undefined) row.leadValues.push(asNumber(record.lead_time_median));
            if (record.late_rate_pct !== null && record.late_rate_pct !== undefined) row.lateValues.push(asNumber(record.late_rate_pct));
            if (record.unit_price !== null && record.unit_price !== undefined) row.unitValues.push(asNumber(record.unit_price));
        });
        return Array.from(map.values()).map(row => {
            row.unit_price = row.qty > 0 ? row.ca / row.qty : median(row.unitValues);
            row.lead_time_median = median(row.leadValues);
            row.late_rate_pct = median(row.lateValues);
            return row;
        });
    }

    function metricValue(row, metric) {
        if (metric === 'qty') return asNumber(row.qty);
        if (metric === 'orders') return asNumber(row.orders);
        if (metric === 'unit_price') return asNumber(row.unit_price);
        if (metric === 'lead_time_median') return asNumber(row.lead_time_median);
        return asNumber(row.ca);
    }

    function metricLabel(data, metric) {
        const found = (data.metrics || []).find(item => item.value === metric);
        return found ? found.label : 'CA';
    }

    function summarize(records) {
        const ca = records.reduce((sum, row) => sum + asNumber(row.ca), 0);
        const qty = records.reduce((sum, row) => sum + asNumber(row.qty), 0);
        const orders = records.reduce((sum, row) => sum + asNumber(row.orders), 0);
        return {
            ca,
            qty,
            orders,
            unit_price: qty > 0 ? ca / qty : median(records.map(row => row.unit_price)),
            lead_time: median(records.map(row => row.lead_time_median)),
            late_rate: median(records.map(row => row.late_rate_pct)),
            families: new Set(records.map(row => row.family)).size,
            products: new Set(records.map(row => row.product)).size
        };
    }

    function renderKpis(root, data, records, state) {
        const s = summarize(records);
        const pMap = periodIndexMap(data);
        let start = pMap.get(String(state.periodStart));
        let end = pMap.get(String(state.periodEnd));
        if (start > end) [start, end] = [end, start];
        const anomalyCount = (data.anomalies || []).filter(item => {
            const idx = Number.isFinite(Number(item.period_index)) ? Number(item.period_index) : pMap.get(String(item.period));
            return idx >= start && idx <= end;
        }).length;
        const values = {
            ca: formatMoney(s.ca),
            orders: formatNumber(s.orders, 0),
            qty: formatNumber(s.qty, 0),
            unit_price: s.unit_price === null ? '-' : formatMoney(s.unit_price),
            lead_time: s.lead_time === null ? '-' : `${formatNumber(s.lead_time, 1)} j`,
            anomalies: formatNumber(anomalyCount, 0)
        };
        Object.entries(values).forEach(([key, value]) => {
            const el = root.querySelector(`[data-client360-kpi="${key}"]`);
            if (el) el.textContent = value;
        });
        const subs = {
            ca: `${s.families} familles / ${s.products} produits`,
            orders: `${formatNumber(records.length, 0)} segments`,
            qty: state.metric === 'qty' ? 'mesure active' : 'volume total',
            unit_price: s.qty > 0 ? 'CA / quantite' : 'moyenne observee',
            lead_time: s.late_rate === null ? 'retard non dispo' : `${formatNumber(s.late_rate, 1)}% retard`,
            anomalies: `${(data.anomaly_summary?.critical_count || 0)} critiques`
        };
        Object.entries(subs).forEach(([key, value]) => {
            const el = root.querySelector(`[data-client360-kpi-sub="${key}"]`);
            if (el) el.textContent = value;
        });
    }

    function renderProjectionCards(root, data) {
        const target = root.querySelector('[data-client360-projection-cards]');
        if (!target) return;
        const cards = data.projection?.cards || [];
        target.innerHTML = cards.length ? cards.map(card =>
            `<span class="client360-projection-pill">${escapeHtml(card.label)} <strong>${formatMoney(card.value)}</strong> ${formatPct(card.delta_pct)}</span>`
        ).join('') : '<span class="client360-projection-pill">Projection indisponible</span>';
    }

    function renderTrend(root, data, records, state) {
        const div = root.querySelector('[data-client360-chart="trend"]');
        if (!div || !window.Plotly) return;
        const pMap = periodIndexMap(data);
        const grouped = groupRecords(records, 'period').sort((a, b) => (pMap.get(a.name) || 0) - (pMap.get(b.name) || 0));
        if (!grouped.length) {
            Plotly.react(div, [], plotlyLayout('Aucune donnee'), PLOT_CONFIG);
            return;
        }
        const metric = state.metric || 'ca';
        const x = grouped.map(row => row.name);
        const traces = [{
            type: 'scatter',
            mode: 'lines+markers',
            x,
            y: grouped.map(row => metricValue(row, metric)),
            name: metricLabel(data, metric),
            line: { color: '#2563eb', width: 3 },
            marker: { size: 7 },
            hovertemplate: '%{x}<br>%{y:,.2f}<extra></extra>'
        }];
        if (metric !== 'orders') {
            traces.push({
                type: 'bar',
                x,
                y: grouped.map(row => row.orders),
                name: 'Commandes',
                marker: { color: '#2d8a6c' },
                opacity: 0.42,
                yaxis: 'y2',
                hovertemplate: '%{x}<br>Cmd: %{y:,.0f}<extra></extra>'
            });
        }
        const canShowProjection = metric === 'ca' && state.family === 'all' && state.product === 'all' && state.country === 'all';
        if (canShowProjection && data.projection?.forecast?.length) {
            const lastPoint = grouped[grouped.length - 1];
            traces.push({
                type: 'scatter',
                mode: 'lines+markers',
                x: [lastPoint.name].concat(data.projection.forecast.map(item => item.label)),
                y: [lastPoint.ca].concat(data.projection.forecast.map(item => item.q50)),
                name: 'Projection q50',
                line: { color: '#cf8b2f', width: 3, dash: 'dash' },
                marker: { size: 7 },
                hovertemplate: '%{x}<br>CA projete: %{y:,.0f} €<extra></extra>'
            });
        }
        Plotly.react(div, traces, plotlyLayout('Evolution portefeuille', {
            yaxis: { title: metricLabel(data, metric), automargin: true },
            yaxis2: { title: 'Commandes', overlaying: 'y', side: 'right', showgrid: false, automargin: true }
        }), PLOT_CONFIG);
    }

    function renderMix(root, data, records, state) {
        const div = root.querySelector('[data-client360-chart="mix"]');
        if (!div || !window.Plotly) return;
        const key = state.family === 'all' ? 'family' : 'product';
        const grouped = groupRecords(records, key)
            .sort((a, b) => metricValue(b, state.metric) - metricValue(a, state.metric))
            .slice(0, 14)
            .reverse();
        const trace = {
            type: 'bar',
            orientation: 'h',
            x: grouped.map(row => metricValue(row, state.metric)),
            y: grouped.map(row => row.name),
            marker: { color: key === 'family' ? '#950b39' : '#2d8a6c' },
            customdata: grouped.map(row => row.name),
            hovertemplate: '%{y}<br>%{x:,.2f}<extra></extra>'
        };
        Plotly.react(div, [trace], plotlyLayout(key === 'family' ? 'CA par famille' : 'CA par produit', {
            margin: { l: 130, r: 20, t: 52, b: 36 },
            xaxis: { title: metricLabel(data, state.metric), automargin: true },
            yaxis: { automargin: true }
        }), PLOT_CONFIG);
        if (div.removeAllListeners) div.removeAllListeners('plotly_click');
        div.on?.('plotly_click', event => {
            const value = event.points?.[0]?.customdata;
            if (!value) return;
            if (key === 'family') state.family = value;
            else state.product = value;
            initFilters(root, data, state);
            render(root, data, state);
        });
    }

    function renderGeo(root, data, records, state) {
        const div = root.querySelector('[data-client360-chart="geo"]');
        if (!div || !window.Plotly) return;
        const grouped = groupRecords(records, 'country').sort((a, b) => b.ca - a.ca).slice(0, 12);
        const trace = {
            type: 'bar',
            x: grouped.map(row => row.name),
            y: grouped.map(row => row.ca),
            marker: { color: '#8b5cf6' },
            customdata: grouped.map(row => row.name),
            hovertemplate: '%{x}<br>CA: %{y:,.0f} €<extra></extra>'
        };
        Plotly.react(div, [trace], plotlyLayout('CA par geographie'), PLOT_CONFIG);
        if (div.removeAllListeners) div.removeAllListeners('plotly_click');
        div.on?.('plotly_click', event => {
            const value = event.points?.[0]?.customdata;
            if (!value) return;
            state.country = value;
            initFilters(root, data, state);
            render(root, data, state);
        });
    }

    function renderAnomalyChart(root, data, state) {
        const div = root.querySelector('[data-client360-chart="anomalies"]');
        if (!div || !window.Plotly) return;
        const pMap = periodIndexMap(data);
        let start = pMap.get(String(state.periodStart));
        let end = pMap.get(String(state.periodEnd));
        if (start > end) [start, end] = [end, start];
        const anomalies = (data.anomalies || []).filter(item => {
            const idx = Number.isFinite(Number(item.period_index)) ? Number(item.period_index) : pMap.get(String(item.period));
            return idx >= start && idx <= end;
        });
        const traces = [];
        if (data.behavior?.available && data.behavior.periods?.length) {
            traces.push({
                type: 'scatter',
                mode: 'lines+markers',
                x: data.behavior.periods,
                y: data.behavior.alert_score_history || [],
                name: 'Score alerte',
                line: { color: '#c14b56', width: 3 },
                hovertemplate: '%{x}<br>Score: %{y:.1f}<extra></extra>'
            });
        }
        if (anomalies.length) {
            traces.push({
                type: 'scatter',
                mode: 'markers',
                x: anomalies.map(item => item.period),
                y: anomalies.map(item => Math.abs(asNumber(item.score)) * 12),
                text: anomalies.map(item => item.message),
                name: 'Anomalies',
                marker: {
                    size: anomalies.map(item => item.severity === 'red' ? 15 : 11),
                    color: anomalies.map(item => item.severity === 'red' ? '#c14b56' : '#cf8b2f'),
                    line: { color: '#ffffff', width: 1 }
                },
                hovertemplate: '%{x}<br>%{text}<br>Intensite: %{y:.1f}<extra></extra>'
            });
        }
        const layout = plotlyLayout('Detection anomalies', {
            yaxis: { title: 'Score', rangemode: 'tozero', automargin: true }
        });
        if (!traces.length) {
            layout.annotations = [{
                text: 'Aucun signal sur la selection',
                x: 0.5,
                y: 0.5,
                xref: 'paper',
                yref: 'paper',
                showarrow: false
            }];
        }
        Plotly.react(div, traces, layout, PLOT_CONFIG);
    }

    function renderCluster(root, data) {
        const cluster = data.cluster || {};
        const title = root.querySelector('[data-client360-cluster-title]');
        const status = root.querySelector('[data-client360-cluster-status]');
        const name = root.querySelector('[data-client360-cluster-name]');
        const reading = root.querySelector('[data-client360-cluster-reading]');
        if (title) title.textContent = cluster.current_label || 'Groupe non disponible';
        if (status) status.textContent = cluster.changed ? 'Migration detectee' : 'Position stable';
        if (name) name.textContent = cluster.current_name || cluster.current_label || 'Segment client';
        if (reading) reading.textContent = cluster.reading || 'Profil calcule sur le portefeuille.';
        const journey = root.querySelector('[data-client360-cluster-journey]');
        if (!journey) return;
        const steps = cluster.journey || [];
        journey.innerHTML = steps.length ? steps.map((step, idx) =>
            `<span class="client360-cluster-step ${idx === steps.length - 1 ? 'is-current' : ''}">${escapeHtml(step.period)} - ${escapeHtml(step.cluster_label || ('Groupe ' + step.cluster_num))}</span>`
        ).join('') : '<span class="client360-cluster-step is-current">Historique cluster indisponible</span>';
    }

    function renderTables(root, data, records, state) {
        const productBody = root.querySelector('[data-client360-products-body]');
        if (productBody) {
            const rows = groupRecords(records, 'product').sort((a, b) => b.ca - a.ca).slice(0, 45);
            productBody.innerHTML = rows.length ? rows.map(row => {
                const family = Array.from(row.families)[0] || '-';
                return `<tr data-client360-product="${escapeHtml(row.name)}" class="${state.product === row.name ? 'is-selected' : ''}">
                    <td><strong>${escapeHtml(row.name)}</strong></td>
                    <td>${escapeHtml(family)}</td>
                    <td class="text-end">${formatMoney(row.ca)}</td>
                    <td class="text-end">${formatNumber(row.orders, 0)}</td>
                    <td class="text-end">${row.unit_price === null ? '-' : formatMoney(row.unit_price)}</td>
                    <td class="text-end">${row.lead_time_median === null ? '-' : formatNumber(row.lead_time_median, 1)}</td>
                </tr>`;
            }).join('') : '<tr><td colspan="6" class="client360-empty">Aucun produit</td></tr>';
            productBody.querySelectorAll('[data-client360-product]').forEach(row => {
                row.addEventListener('click', () => {
                    state.product = row.dataset.client360Product;
                    initFilters(root, data, state);
                    render(root, data, state);
                });
            });
        }

        const periodBody = root.querySelector('[data-client360-periods-body]');
        if (periodBody) {
            const pMap = periodIndexMap(data);
            const rows = groupRecords(records, 'period').sort((a, b) => (pMap.get(a.name) || 0) - (pMap.get(b.name) || 0));
            periodBody.innerHTML = rows.length ? rows.map(row =>
                `<tr data-client360-period="${escapeHtml(row.name)}">
                    <td><strong>${escapeHtml(row.name)}</strong></td>
                    <td class="text-end">${formatMoney(row.ca)}</td>
                    <td class="text-end">${formatNumber(row.orders, 0)}</td>
                    <td class="text-end">${formatNumber(row.families.size, 0)}</td>
                </tr>`
            ).join('') : '<tr><td colspan="4" class="client360-empty">Aucune periode</td></tr>';
            periodBody.querySelectorAll('[data-client360-period]').forEach(row => {
                row.addEventListener('click', () => {
                    state.periodStart = row.dataset.client360Period;
                    state.periodEnd = row.dataset.client360Period;
                    initFilters(root, data, state);
                    render(root, data, state);
                });
            });
        }

        const anomalyBody = root.querySelector('[data-client360-anomalies-body]');
        if (anomalyBody) {
            const rows = (data.anomalies || []).slice(0, 12);
            anomalyBody.innerHTML = rows.length ? rows.map(row =>
                `<tr data-client360-period="${escapeHtml(row.period)}">
                    <td>${escapeHtml(row.metric_label)}</td>
                    <td>${escapeHtml(row.period)}</td>
                    <td class="text-end">${formatNumber(row.score, 2)}</td>
                </tr>`
            ).join('') : '<tr><td colspan="3" class="client360-empty">Aucun signal</td></tr>';
        }
    }

    function render(root, data, state) {
        const records = filteredRecords(data, state);
        renderKpis(root, data, records, state);
        renderProjectionCards(root, data);
        renderTrend(root, data, records, state);
        renderMix(root, data, records, state);
        renderGeo(root, data, records, state);
        renderAnomalyChart(root, data, state);
        renderCluster(root, data);
        renderTables(root, data, records, state);
    }

    function initClient360Dashboard(root) {
        if (!root || root.dataset.client360Ready === 'true') return;
        const data = getData(root);
        if (!data || !Array.isArray(data.records)) return;
        const periods = data.filters?.periods || [];
        const state = {
            periodStart: periods[0]?.value || '',
            periodEnd: periods[periods.length - 1]?.value || '',
            family: 'all',
            product: 'all',
            country: 'all',
            metric: 'ca'
        };
        root.dataset.client360Ready = 'true';
        root._client360State = state;
        initFilters(root, data, state);
        render(root, data, state);
    }

    function initClient360Dashboards(scope) {
        const container = scope || document;
        container.querySelectorAll('[data-client360-dashboard]').forEach(initClient360Dashboard);
    }

    window.initClient360Dashboards = initClient360Dashboards;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => initClient360Dashboards(document));
    } else {
        initClient360Dashboards(document);
    }
})();
