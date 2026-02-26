// ==========================================
// 1. EL "ENRUTADOR" INTELIGENTE DEL BOTÓN
// ==========================================
window.startTutorial = function() {
    // Esta función detecta dónde estás y lanza el tutorial correcto
    if (document.querySelector('form[hx-get="/market/search"]')) {
        window.startMarketTutorial();
    } else {
        window.startAlbumTutorial();
    }
};

// ==========================================
// 2. TUTORIAL DEL ÁLBUM
// ==========================================
window.startAlbumTutorial = function() {
    if (!window.driver || !window.driver.js) {
        alert("El tutorial está terminando de cargar. Intentá de nuevo en un segundo ⏱️");
        return;
    }

    const driver = window.driver.js.driver;
    const primerSticker = document.querySelector('div[id^="sticker-"]');
    
    if (!primerSticker) {
        alert("Esperá a que carguen las figuritas para iniciar el tutorial ⏱️");
        return;
    }

    let styleLock = document.getElementById('tutorial-lock-css');
    if (!styleLock) {
        styleLock = document.createElement('style');
        styleLock.id = 'tutorial-lock-css';
        styleLock.innerHTML = `.driver-active-element { pointer-events: none !important; }`;
        document.head.appendChild(styleLock);
    }

    function bloqueadorDeClicks(e) {
        if (!e.target.closest('.driver-popover')) {
            e.stopPropagation(); 
            e.preventDefault();  
        }
    }
    document.addEventListener('click', bloqueadorDeClicks, true);

    let contenedorRepetidas = document.querySelector('#repeated-table-container');
    let tablaReal = contenedorRepetidas ? contenedorRepetidas.querySelector('table') : null;
    let tablaFantasma = null;
    let elementoAiluminar = null;

    if (tablaReal) {
        elementoAiluminar = contenedorRepetidas;
    } else {
        tablaFantasma = document.createElement('div');
        tablaFantasma.id = 'tutorial-fake-table';
        tablaFantasma.className = 'bg-slate-800 border-2 border-slate-600 border-dashed rounded-xl p-6 mb-8 mt-4 text-center animate-pulse';
        tablaFantasma.innerHTML = `
            <h3 class="text-lg font-bold text-yellow-400 opacity-50">💰 Gestión de Repetidas</h3>
            <p class="text-sm text-gray-400 mt-2">¡Acá aparecerá tu tabla mágicamente cuando marques tu primera figurita como repetida!</p>
        `;

        if (contenedorRepetidas) {
            contenedorRepetidas.appendChild(tablaFantasma);
            elementoAiluminar = contenedorRepetidas;
        } else {
            const areaDinamica = document.getElementById('dynamic-content');
            if (areaDinamica) areaDinamica.appendChild(tablaFantasma);
            else document.body.appendChild(tablaFantasma);
            elementoAiluminar = tablaFantasma;
        }
    }

    try {
        const driverObj = driver({
            showProgress: true, animate: true, allowClose: false, 
            nextBtnText: 'Siguiente ➔', prevBtnText: '⬅ Atrás', doneBtnText: '¡Entendido! 🙌',
            onDestroyStarted: () => {
                if (tablaFantasma && tablaFantasma.parentNode) tablaFantasma.parentNode.removeChild(tablaFantasma);
                document.removeEventListener('click', bloqueadorDeClicks, true);
                driverObj.destroy();
            },
            steps: [
                { element: primerSticker, popover: { title: '¡Presioná la figu! 🎯', description: 'Un toque = <b>La tengo</b>.<br>Dos toques = <b>Repetida</b>.<br>Tres = <b>Wishlist</b> (la quiero).<br>¡Con el cuarto toque la volvés a vaciar!', side: "bottom", align: 'start' } },
                { element: elementoAiluminar, popover: { title: 'Tus Repetidas 💰', description: 'Si dejás el precio en 0, es solo para <b>CANJE</b>. Si le ponés un valor, pasa a <b>VENTA</b>. Desde acá también indicás la <b>CANTIDAD</b>.', side: "top", align: 'center' } },
                { element: '#bottom-nav-container', popover: { title: 'Navegá por el álbum 📖', description: 'Deslizá esta barra y seleccioná para moverte entre los países y secciones.', side: "top", align: 'center' } },
                { element: '#btn-menu-tutorial', popover: { title: 'Tu Panel de Control ⚙️', description: 'Acá entrás y editás tu <b>PERFIL</b>, usas la <b>CARGA RÁPIDA</b>, descubrís los <b>PUNTOS SEGUROS</b> y configurás las <b>ALERTAS</b>.', side: "bottom", align: 'end' } },
                { element: 'a[href="/market"]', popover: { title: '¡Al Mercado! ⚖️', description: 'Acá ocurre la magia: filtras, buscás triangulaciones, cerrás los canjes y comprás figus difíciles ¡A completar el álbum!', side: "bottom", align: 'center' } }
            ]
        });
        driverObj.drive();
    } catch (error) { document.removeEventListener('click', bloqueadorDeClicks, true); }
};

// ==========================================
// 3. TUTORIAL DEL MERCADO 
// ==========================================
window.startMarketTutorial = function() {
    if (!window.driver || !window.driver.js) return;
    const driver = window.driver.js.driver;
    const marketResults = document.getElementById('market-results');
    if (!marketResults || marketResults.innerText.includes('Cargando')) return;

    // MAGIA: Secuestramos el Modal de Seguridad temporalmente
    const modalSeguridad = document.getElementById('securityModal');
    if (modalSeguridad) {
        modalSeguridad.close(); // Lo cerramos por las dudas
        modalSeguridad.funcionOriginal = modalSeguridad.showModal;
        modalSeguridad.showModal = function() {}; // Lo anulamos temporalmente
    }

    let styleLock = document.getElementById('tutorial-lock-css');
    if (!styleLock) {
        styleLock = document.createElement('style');
        styleLock.id = 'tutorial-lock-css';
        styleLock.innerHTML = `.driver-active-element { pointer-events: none !important; }`;
        document.head.appendChild(styleLock);
    }

    function bloqueadorDeClicks(e) {
        if (!e.target.closest('.driver-popover')) {
            e.stopPropagation(); e.preventDefault();
        }
    }
    document.addEventListener('click', bloqueadorDeClicks, true);

    const filtrosForm = document.querySelector('form[hx-get="/market/search"]');
    const btnTriangulacion = document.querySelector('button[onclick*="triangulationInputModal"]');
    const triangulacionSection = btnTriangulacion ? btnTriangulacion.closest('section') : null;
    const pestanasContainer = marketResults.previousElementSibling; 

    let tarjetaFantasma = null;
    let elementoAiluminarTarjeta = null;
    let nodosOcultos = []; // Guardamos los nodos originales para no romper Alpine
    
    // Si no hay tarjetas reales
    if (marketResults.children.length === 0 || marketResults.innerText.includes('No se encontraron') || marketResults.innerText.includes('No hay figuritas')) {
        
        // Ocultamos los mensajes sin borrarlos del DOM
        Array.from(marketResults.children).forEach(node => {
            nodosOcultos.push({ node: node, display: node.style.display });
            node.style.display = 'none';
        });

        tarjetaFantasma = document.createElement('div');
        tarjetaFantasma.id = 'tutorial-fake-card';
        tarjetaFantasma.className = 'bg-slate-800 rounded-xl p-4 border-2 border-green-500 border-dashed animate-pulse mb-4 mt-4 shadow-lg';
        tarjetaFantasma.innerHTML = `
            <div class="flex justify-between items-center mb-2">
                <span class="font-bold text-white flex items-center gap-2"><span>👤</span> Usuario_Demo</span>
                <span class="text-[10px] bg-green-900 text-green-400 font-bold px-2 py-1 rounded border border-green-700">CANJE</span>
            </div>
            <p class="text-sm text-gray-400 mb-3">Tiene lo que buscás y busca lo que tenés.</p>
            <div class="w-full bg-green-600 text-white font-bold py-2 rounded flex justify-center items-center gap-2"><span>💬</span> Contactar por WhatsApp</div>
        `;
        marketResults.appendChild(tarjetaFantasma);
        elementoAiluminarTarjeta = tarjetaFantasma;
    } else {
        elementoAiluminarTarjeta = marketResults.firstElementChild;
    }

    try {
        const driverObj = driver({
            showProgress: true, animate: true, allowClose: false,
            nextBtnText: 'Siguiente ➔', prevBtnText: '⬅ Atrás', doneBtnText: '¡A Canjear! 🙌',
            onDestroyStarted: () => {
                // Limpieza de la tarjeta
                if (tarjetaFantasma && tarjetaFantasma.parentNode) {
                    tarjetaFantasma.parentNode.removeChild(tarjetaFantasma);
                }
                // Devolvemos la visibilidad a los nodos originales de AlpineJS
                nodosOcultos.forEach(item => item.node.style.display = item.display);
                
                document.removeEventListener('click', bloqueadorDeClicks, true);
                
                // Le devolvemos la vida al Modal de Seguridad y lo abrimos!
                if (modalSeguridad && modalSeguridad.funcionOriginal) {
                    modalSeguridad.showModal = modalSeguridad.funcionOriginal;
                    const shouldSkip = localStorage.getItem('skipSecurityModal') === 'true';
                    if (!shouldSkip) setTimeout(() => modalSeguridad.showModal(), 500);
                }

                driverObj.destroy();
            },
            steps: [
                { element: filtrosForm, popover: { title: 'Filtros de Búsqueda 🔍', description: 'Encontrá a la persona ideal filtrando por <b>Provincia</b>, <b>Zona</b>, o buscando un número de <b>Figurita</b>.', side: "bottom", align: 'center' } },
                { element: triangulacionSection, popover: { title: 'Magia: Triangulación 📐', description: '¿Nadie tiene la que buscás? El sistema busca "puentes" entre 3 personas para que todos consigan destrabar sus canjes.', side: "bottom", align: 'center' } },
                { element: pestanasContainer, popover: { title: 'Organización 📁', description: 'Navegá entre las figuritas disponibles para <b>Canjear</b>, las que están a la <b>Venta</b>, y revisá tus contactos <b>Pendientes</b>.', side: "bottom", align: 'center' } },
                { element: elementoAiluminarTarjeta, popover: { title: '¡A Negociar! 🤝', description: 'Acá verás las coincidencias. Tocá el botón de <b>WhatsApp</b> para contactarlos y cerrar el trato.', side: "top", align: 'center' } }
            ]
        });
        driverObj.drive();
    } catch (error) { 
        document.removeEventListener('click', bloqueadorDeClicks, true); 
    }
};

// ==========================================
// 4. CEREBRO CENTRAL (HTMX)
// ==========================================
document.body.addEventListener('htmx:afterSettle', function(evt) {
    if (evt.target.id === 'dynamic-content' || (evt.detail && evt.detail.target.id === 'dynamic-content')) {
        if (document.getElementById('btn-menu-tutorial') && !localStorage.getItem('tutorial_visto')) {
            setTimeout(() => {
                window.startAlbumTutorial();
                localStorage.setItem('tutorial_visto', 'true');
            }, 500);
        }
    }

    if (evt.target.id === 'market-results' || (evt.detail && evt.detail.target.id === 'market-results')) {
        const isMarketPage = document.querySelector('form[hx-get="/market/search"]'); 
        if (isMarketPage && !localStorage.getItem('tutorial_mercado_visto')) {
            const resultsContainer = document.getElementById('market-results');
            if (resultsContainer && !resultsContainer.innerText.includes('Cargando')) {
                setTimeout(() => {
                    window.startMarketTutorial();
                    localStorage.setItem('tutorial_mercado_visto', 'true');
                }, 500);
            }
        }
    }
});