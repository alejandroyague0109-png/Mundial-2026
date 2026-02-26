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

    // --- MAGIA UX: LA TABLA FANTASMA ---
    // Buscamos si ya existe la tabla real
    let tablaRepetidas = document.querySelector('#repeated-table-container');
    let esTablaFalsa = false;

    // Si el usuario es nuevo y no tiene la tabla, le creamos una ilustrativa temporal
    if (!tablaRepetidas) {
        tablaRepetidas = document.createElement('div');
        tablaRepetidas.id = 'tutorial-fake-table'; 
        tablaRepetidas.className = 'bg-slate-800/80 border-2 border-slate-600 border-dashed rounded-xl p-6 mb-10 mt-8 text-center animate-pulse';
        tablaRepetidas.innerHTML = `
            <div>
                <h3 class="text-lg font-bold text-yellow-400 opacity-50">💰 Gestión de Repetidas</h3>
                <p class="text-sm text-gray-400 mt-2">¡Acá aparecerá tu tabla mágicamente cuando marques tu primera figurita como repetida!</p>
            </div>`;
        
        // La metemos en la pantalla justo debajo de las figuritas
        const container = document.getElementById('dynamic-content');
        if (container) container.appendChild(tablaRepetidas);
        esTablaFalsa = true; // Marcamos que es falsa para borrarla después
    }

    try {
        const driverObj = driver({
            showProgress: true,
            animate: true,
            nextBtnText: 'Siguiente ➔',
            prevBtnText: '⬅ Atrás',
            doneBtnText: '¡Entendido! 🙌',
            
            // Cuando se cierra el tutorial (ya sea por terminar o porque tocó afuera)
            onDestroyStarted: () => {
                // Borramos la tabla fantasma para dejar todo limpio
                if (esTablaFalsa && tablaRepetidas.parentNode) {
                    tablaRepetidas.parentNode.removeChild(tablaRepetidas);
                }
                driverObj.destroy();
            },

            steps: [
                {
                    element: primerSticker, 
                    popover: { title: '¡Presioná la figu! 🎯', description: 'Un toque = <b>La tengo</b>.<br>Dos toques = <b>Repetida</b>.<br>Tres = <b>Wishlist</b> (la quiero).<br>¡Con el cuarto toque la volvés a vaciar!', side: "bottom", align: 'start' }
                },
                {
                    // Le pasamos el elemento directamente (sea el real o el fantasma)
                    element: tablaRepetidas,
                    popover: { title: 'Tus Repetidas 💰', description: 'Si dejás el precio en 0, es solo para <b>CANJE</b>. Si le ponés un valor, pasa a <b>VENTA</b> automáticamente. Desde acá también cambias la cantidad.', side: "top", align: 'center' }
                },
                {
                    element: '#bottom-nav-container',
                    popover: { title: 'Navegá por el álbum 📖', description: 'Deslizá esta barra y seleccioná para moverte entre los países y secciones.', side: "top", align: 'center' }
                },
                {
                    element: '#btn-menu-tutorial',
                    popover: { title: 'Tu Panel de Control ⚙️', description: 'Acá entrás y editás tu perfil, usas la <b>Carga rápida</b>, descubrís los <b>Puntos Seguros</b> y recibís ayuda.', side: "bottom", align: 'end' }
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