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
                
                // Mettre à jour l'URL avec les paramètres granularity ET tab
                const url = new URL(window.location.href);
                url.searchParams.set('granularity', period);

                // Conserver l'onglet courant (si présent dans l'URL), sinon le déduire de l'onglet actif
                const tabFromUrl = url.searchParams.get('tab');
                if (!tabFromUrl) {
                    const activeMainTab = document.querySelector('ul.nav-tabs .nav-link.active[data-bs-target]');
                    const target = activeMainTab ? activeMainTab.getAttribute('data-bs-target') : null;
                    const tabMapping = {
                        '#stats': 'statistics',
                        '#temporal': 'temporal',
                        '#products': 'products',
                        '#clients': 'clients',
                        '#geography': 'geographic',
                        '#currency': 'currency'
                    };
                    url.searchParams.set('tab', tabMapping[target] || 'statistics');
                }
                
                // Forcer le rechargement avec la nouvelle URL
                window.location.href = url.toString();
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

        // 4b. Resize lors du changement de sous-onglets Série temporelle (pills)
        // (Mois / Trimestre / Année fiscale) : ces panes sont masqués au load.
        const temporalPillButtons = document.querySelectorAll('#temporal [data-bs-toggle="pill"]');
        temporalPillButtons.forEach(button => {
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
            'temporal-tab': 'temporal',
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
                    // Mettre à jour l'URL avec le paramètre tab
                    const currentUrl = new URL(window.location.href);
                    const currentTab = currentUrl.searchParams.get('tab');

                    // Si on est déjà sur le bon onglet côté serveur, ne pas recharger.
                    if (currentTab === tabName) {
                        console.log('📑 Onglet déjà actif (pas de reload):', tabName);
                        return;
                    }

                    currentUrl.searchParams.set('tab', tabName);

                    // IMPORTANT : les analyses sont calculées côté serveur selon ?tab=...
                    // Un simple switch Bootstrap (sans reload) affiche donc du contenu vide.
                    // On force la navigation pour obtenir le contexte correct.
                    window.location.assign(currentUrl.toString());
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
