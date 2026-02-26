window.startTutorial = function() {
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

    // --- EL ESCUDO DEFINITIVO: Intercepta clics en el aire ---
    function bloqueadorDeClicks(e) {
        // Permitimos el clic SOLAMENTE si es adentro de la caja blanca del tutorial
        if (!e.target.closest('.driver-popover')) {
            e.stopPropagation(); // Evita que HTMX o Alpine se enteren del clic
            e.preventDefault();  // Cancela cualquier acción nativa del botón
        }
    }
    
    // Activamos el escudo en fase de "captura" (true), que ocurre antes del clic real
    document.addEventListener('click', bloqueadorDeClicks, true);

    // --- CORRECCIÓN UX 2.0: LA TABLA FANTASMA ---
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
            if (areaDinamica) {
                areaDinamica.appendChild(tablaFantasma);
            } else {
                document.body.appendChild(tablaFantasma);
            }
            elementoAiluminar = tablaFantasma;
        }
    }

    try {
        const driverObj = driver({
            showProgress: true,
            animate: true,
            allowClose: false, // Obliga a usar los botones de "Siguiente"
            nextBtnText: 'Siguiente ➔',
            prevBtnText: '⬅ Atrás',
            doneBtnText: '¡Entendido! 🙌',
            
            onDestroyStarted: () => {
                // 1. Borramos la tabla fantasma
                if (tablaFantasma && tablaFantasma.parentNode) {
                    tablaFantasma.parentNode.removeChild(tablaFantasma);
                }
                
                // 2. APAGAMOS EL ESCUDO PARA QUE LA APP VUELVA A FUNCIONAR
                document.removeEventListener('click', bloqueadorDeClicks, true);
                
                driverObj.destroy();
            },

            steps: [
                {
                    element: primerSticker, 
                    popover: { title: '¡Presioná la figu! 🎯', description: 'Un toque = <b>La tengo</b>.<br>Dos toques = <b>Repetida</b>.<br>Tres = <b>Wishlist</b> (la quiero).<br>¡Con el cuarto toque la volvés a vaciar!', side: "bottom", align: 'start' }
                },
                {
                    element: elementoAiluminar,
                    popover: { title: 'Tus Repetidas 💰', description: 'Si dejás el precio en 0, es solo para <b>CANJE</b>. Si le ponés un valor, pasa a <b>VENTA</b> automáticamente. Desde acá también indicás la <b>CANTIDAD</b> de veces que la tenés repetida.', side: "top", align: 'center' }
                },
                {
                    element: '#bottom-nav-container',
                    popover: { title: 'Navegá por el álbum 📖', description: 'Deslizá esta barra y seleccioná para moverte entre los países y secciones.', side: "top", align: 'center' }
                },
                {
                    element: '#btn-menu-tutorial',
                    popover: { title: 'Tu Panel de Control ⚙️', description: 'Acá entrás y editás tu <b>PERFIL</b>, usas la <b>CARGA RÁPIDA</b>, descubrís los <b>PUNTOS SEGUROS</b>, configurás las <b>ALERTAS</b> y recibís <b>AYUDA</b>.', side: "bottom", align: 'end' }
                },
                {
                    element: 'a[href="/market"]',
                    popover: { title: '¡Al Mercado! ⚖️', description: 'Acá ocurre la magia: filtras, buscás triangulaciones, cerrás los canjes y comprás figus difíciles. ¡A completar ese álbum!', side: "bottom", align: 'center' }
                }
            ]
        });

        driverObj.drive();
        
    } catch (error) {
        console.error("Error DriverJS:", error);
        // Si hay un error catastrofico, nos aseguramos de apagar el escudo
        document.removeEventListener('click', bloqueadorDeClicks, true);
    }
};

// Lógica Automática
document.body.addEventListener('htmx:afterSettle', function(evt) {
    if (evt.target.id === 'dynamic-content' || (evt.detail && evt.detail.target.id === 'dynamic-content')) {
        const tutorialVisto = localStorage.getItem('tutorial_visto');
        const isAlbumPage = document.getElementById('btn-menu-tutorial');
        
        if (isAlbumPage && !tutorialVisto) {
            setTimeout(() => {
                window.startTutorial();
                localStorage.setItem('tutorial_visto', 'true');
            }, 500);
        }
    }
});

// ==========================================
// 2. TUTORIAL DEL MERCADO (¡NUEVO!)
// ==========================================
window.startMarketTutorial = function() {
    if (!window.driver || !window.driver.js) return;
    const driver = window.driver.js.driver;

    // Escudo de clics (reutilizado)
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

    // Identificamos los elementos del mercado
    const filtrosForm = document.querySelector('form[hx-get="/market/search"]');
    const triangulacionSection = document.querySelector('section.border-indigo-500\\/30'); 
    const pestanasContainer = document.querySelector('button[@click*="currentTab"]').parentElement;
    const marketResults = document.getElementById('market-results');

    // Tarjeta Fantasma del Mercado
    let tarjetaFantasma = null;
    let elementoAiluminarTarjeta = null;
    
    // Si los resultados están vacíos o dicen "Cargando", metemos una tarjeta falsa
    if (marketResults && (marketResults.innerHTML.includes('Cargando') || marketResults.children.length === 0)) {
        tarjetaFantasma = document.createElement('div');
        tarjetaFantasma.className = 'bg-slate-800 rounded-xl p-4 border-2 border-green-500 border-dashed animate-pulse mb-4 shadow-lg';
        tarjetaFantasma.innerHTML = `
            <div class="flex justify-between items-center mb-2">
                <span class="font-bold text-white flex items-center gap-2"><span>👤</span> Usuario_Demo</span>
                <span class="text-[10px] bg-green-900 text-green-400 font-bold px-2 py-1 rounded border border-green-700">CANJE</span>
            </div>
            <p class="text-sm text-gray-400 mb-3">Tiene lo que buscás y busca lo que tenés.</p>
            <button class="w-full bg-green-600 text-white font-bold py-2 rounded flex justify-center items-center gap-2">
                <span>💬</span> Contactar por WhatsApp
            </button>
        `;
        // Limpiamos el "Cargando" y ponemos la tarjeta
        marketResults.innerHTML = '';
        marketResults.appendChild(tarjetaFantasma);
        elementoAiluminarTarjeta = tarjetaFantasma;
    } else {
        // Si hay resultados reales, iluminamos el primero
        elementoAiluminarTarjeta = marketResults.firstElementChild;
    }

    try {
        const driverObj = driver({
            showProgress: true, animate: true, allowClose: false,
            nextBtnText: 'Siguiente ➔', prevBtnText: '⬅ Atrás', doneBtnText: '¡A Canjear! 🙌',
            onDestroyStarted: () => {
                // Limpieza
                if (tarjetaFantasma && tarjetaFantasma.parentNode) {
                    tarjetaFantasma.parentNode.removeChild(tarjetaFantasma);
                    // Devolvemos el cartelito de cargando por si acaso
                    marketResults.innerHTML = '<div class="text-center p-8 text-gray-500">Volviendo al mercado real...</div>';
                    // Forzamos la recarga de los resultados reales apretando el botón de buscar
                    document.getElementById('search-trigger-btn')?.click();
                }
                document.removeEventListener('click', bloqueadorDeClicks, true);
                if (styleLock) styleLock.remove();
                driverObj.destroy();
            },
            steps: [
                {
                    element: filtrosForm,
                    popover: { title: 'Filtros de Búsqueda 🔍', description: 'Encontrá a la persona ideal filtrando por <b>Provincia</b>, <b>Zona</b>, o andá directo al grano buscando un número de <b>Figurita</b> específico.', side: "bottom", align: 'center' }
                },
                {
                    element: triangulacionSection,
                    popover: { title: 'Magia: Triangulación 📐', description: '¿Nadie tiene la que buscás? El sistema busca "puentes" entre 3 personas para que todos consigan destrabar sus canjes.', side: "bottom", align: 'center' }
                },
                {
                    element: pestanasContainer,
                    popover: { title: 'Organización 📁', description: 'Navegá entre las figuritas disponibles para <b>Canjear</b>, las que están a la <b>Venta</b>, y revisá tus contactos <b>Pendientes</b>.', side: "bottom", align: 'center' }
                },
                {
                    element: elementoAiluminarTarjeta,
                    popover: { title: '¡A Negociar! 🤝', description: 'Acá verás las coincidencias. Tocá el botón de <b>WhatsApp</b> para contactarlos y cerrar el trato.', side: "top", align: 'center' }
                }
            ]
        });
        driverObj.drive();
    } catch (error) { document.removeEventListener('click', bloqueadorDeClicks, true); }
};

// ==========================================
// 3. CEREBRO CENTRAL (El escuchador de HTMX)
// ==========================================
document.body.addEventListener('htmx:afterSettle', function(evt) {
    
    // CASO 1: Cargó el contenido del Álbum
    if (evt.target.id === 'dynamic-content' || (evt.detail && evt.detail.target.id === 'dynamic-content')) {
        const tutorialVisto = localStorage.getItem('tutorial_visto');
        const isAlbumPage = document.getElementById('btn-menu-tutorial'); // Solo existe en el album
        
        if (isAlbumPage && !tutorialVisto) {
            setTimeout(() => {
                window.startTutorial();
                localStorage.setItem('tutorial_visto', 'true');
            }, 500);
        }
    }

    // CASO 2: Cargaron los resultados del Mercado
    if (evt.target.id === 'market-results' || (evt.detail && evt.detail.target.id === 'market-results')) {
        const tutorialMercadoVisto = localStorage.getItem('tutorial_mercado_visto');
        const isMarketPage = document.querySelector('form[hx-get="/market/search"]'); // Solo existe en el mercado
        
        if (isMarketPage && !tutorialMercadoVisto) {
            // Le damos 1 segundito para que se acomoden bien las tarjetas de HTMX
            setTimeout(() => {
                window.startMarketTutorial();
                localStorage.setItem('tutorial_mercado_visto', 'true');
            }, 1000);
        }
    }
});