// Verificamos si la librería cargó bien en el HTML
if (typeof window.driver === 'undefined') {
    console.error("FALTA LA LIBRERÍA: No te olvides de poner el <script> de Driver.js en tu base.html");
}

const driver = window.driver ? window.driver.js.driver : null;

function startTutorial() {
    if (!driver) {
        alert("Falta cargar la librería del tutorial en el HTML.");
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
                    element: 'div[id^="sticker-"]', 
                    popover: { title: '¡Tocá la figu! 🎯', description: 'Un toque = <b>La tengo</b>.<br>Dos toques = <b>Repetida</b>.<br>Tres = <b>Wishlist</b> (la busco).', side: "bottom", align: 'start' }
                },
                {
                    element: '#repeated-table-container',
                    popover: { title: 'Tus Repetidas 💰', description: 'Si dejás el precio en 0, es solo para <b>CANJE</b>. Si le ponés un valor, pasa a <b>VENTA</b> automáticamente.', side: "top", align: 'center' }
                },
                {
                    element: '#bottom-nav-container',
                    popover: { title: 'Navegá por el álbum 📖', description: 'Deslizá esta barra para moverte entre los diferentes países.', side: "top", align: 'center' }
                },
                {
                    element: '#btn-menu-tutorial',
                    popover: { title: 'Tu Panel de Control ⚙️', description: 'Acá entrás a tu perfil y descubrís los Puntos Seguros.', side: "bottom", align: 'end' }
                },
                {
                    // ACA ESTÁ LA MAGIA: Busca si es un link <a> o un botón de HTMX
                    element: '[hx-get="/market"], a[href="/market"]',
                    popover: { title: '¡Al Mercado! ⚖️', description: 'Acá ocurre la magia: buscás triangulaciones y cerrás los canjes.', side: "bottom", align: 'center' }
                }
            ]
        });

        driverObj.drive();
        
    } catch (error) {
        console.error("Falla al iniciar el tutorial:", error);
        alert("Ups, no encontró un botón en la pantalla. Abrí la consola (F12) para ver cuál falta.");
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const tutorialVisto = localStorage.getItem('tutorial_visto');
    if (!tutorialVisto) {
        // Le damos 2 segunditos para asegurar que HTMX traiga las figuritas
        setTimeout(() => {
            startTutorial();
            localStorage.setItem('tutorial_visto', 'true');
        }, 2000); 
    }
});