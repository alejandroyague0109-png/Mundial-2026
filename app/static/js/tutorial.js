// Definimos la función para que el botón HTML la encuentre
window.startTutorial = function() {
    // 1. Verificamos que la librería Driver haya cargado
    if (!window.driver || !window.driver.js) {
        alert("El tutorial está terminando de cargar. Intentá de nuevo en un segundo ⏱️");
        return;
    }

    const driver = window.driver.js.driver;

    // 2. Buscamos la primera figurita que haya en pantalla
    const primerSticker = document.querySelector('div[id^="sticker-"]');
    
    // Si todavía no hay figuritas (porque están cargando por HTMX)
    if (!primerSticker) {
        alert("Esperá a que carguen las figuritas para iniciar el tutorial ⏱️");
        return;
    }

    try {
        const driverObj = driver({
            showProgress: true,
            animate: true,
            nextBtnText: 'Siguiente ➔',
            prevBtnText: '⬅ Atrás',
            doneBtnText: '¡Entendido! 🙌',
            steps: [
                {
                    element: primerSticker, 
                    popover: { title: '¡Tocá la figu! 🎯', description: 'Un toque = <b>La tengo</b>.<br>Dos toques = <b>Repetida</b>.<br>Tres = <b>Wishlist</b> (la busco).', side: "bottom", align: 'start' }
                },
                {
                    element: '#repeated-table-container',
                    popover: { title: 'Tus Repetidas 💰', description: 'Si dejás el precio en 0, es solo para <b>CANJE</b>. Si le ponés un valor, pasa a <b>VENTA</b> automáticamente.', side: "top", align: 'center' }
                },
                {
                    element: '#bottom-nav-container',
                    popover: { title: 'Navegá por el álbum 📖', description: 'Deslizá esta barra para moverte entre los países.', side: "top", align: 'center' }
                },
                {
                    element: '#btn-menu-tutorial',
                    popover: { title: 'Tu Panel de Control ⚙️', description: 'Acá entrás a tu perfil y descubrís los Puntos Seguros.', side: "bottom", align: 'end' }
                },
                {
                    element: 'a[href="/market"]',
                    popover: { title: '¡Al Mercado! ⚖️', description: 'Buscás triangulaciones y cerrás los canjes.', side: "bottom", align: 'center' }
                }
            ]
        });

        driverObj.drive();
        
    } catch (error) {
        console.error("Error DriverJS:", error);
    }
};

// 3. Lógica Automática: HTMX nos avisa cuando terminó de dibujar
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