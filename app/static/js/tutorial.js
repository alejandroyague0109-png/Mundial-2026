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

    // --- BLOQUEO DE CLICS (Escudo para que el usuario no rompa HTMX) ---
    let styleLock = document.getElementById('tutorial-lock-css');
    if (!styleLock) {
        styleLock = document.createElement('style');
        styleLock.id = 'tutorial-lock-css';
        styleLock.innerHTML = `.driver-active-element { pointer-events: none !important; }`;
        document.head.appendChild(styleLock);
    }

    // --- CORRECCIÓN UX 2.0: LA TABLA FANTASMA A PRUEBA DE BALAS ---
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
            allowClose: false, // Obliga al usuario a usar los botones "Siguiente"
            nextBtnText: 'Siguiente ➔',
            prevBtnText: '⬅ Atrás',
            doneBtnText: '¡Entendido! 🙌',
            
            onDestroyStarted: () => {
                // Limpieza total: Borramos la tabla y desactivamos el escudo de clics
                if (tablaFantasma && tablaFantasma.parentNode) {
                    tablaFantasma.parentNode.removeChild(tablaFantasma);
                }
                if (styleLock) {
                    styleLock.remove();
                }
                driverObj.destroy();
            },

            steps: [
                {
                    element: primerSticker, 
                    popover: { title: '¡Presioná la figu! 🎯', description: 'Un toque = <b>La tengo</b>.<br>Dos toques = <b>Repetida</b>.<br>Tres = <b>Wishlist</b>.<br>¡Con el cuarto toque la volvés a vaciar!', side: "bottom", align: 'start' }
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