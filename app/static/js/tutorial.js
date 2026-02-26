const driver = window.driver.js.driver;

function startTutorial() {
    const driverObj = driver({
        showProgress: true,
        animate: true,
        nextBtnText: 'Siguiente ➔',
        prevBtnText: '⬅ Atrás',
        doneBtnText: '¡Entendido! 🙌',
        steps: [
            {
                // 1. Figuritas (Agarra la primera que encuentre)
                element: 'div[id^="sticker-"]', 
                popover: {
                    title: '¡Tocá la figu! 🎯',
                    description: 'Un toque = <b>La tengo</b>.<br>Dos toques = <b>Repetida</b>.<br>Tres = <b>Wishlist</b> (la busco).<br>¡Con el cuarto toque la volvés a vaciar!',
                    side: "bottom", align: 'start'
                }
            },
            {
                // 2. Tabla de Repetidas
                element: '#repeated-table-container',
                popover: {
                    title: 'Tus Repetidas 💰',
                    description: 'Acá decidís qué hacer: si dejás el precio en 0, es solo para <b>CANJE</b>. Si le ponés un valor, pasa a <b>VENTA</b> automáticamente.',
                    side: "top", align: 'center'
                }
            },
            {
                // 3. Paginación
                element: '#bottom-nav-container',
                popover: {
                    title: 'Navegá por el álbum 📖',
                    description: 'Deslizá esta barra para moverte entre los diferentes países y secciones del Mundial.',
                    side: "top", align: 'center'
                }
            },
            {
                // 4. Menú Principal
                element: '#btn-menu-tutorial',
                popover: {
                    title: 'Tu Panel de Control ⚙️',
                    description: 'Acá entrás a tu perfil, configurás tus alertas de WhatsApp y descubrís los Puntos Seguros.',
                    side: "bottom", align: 'end'
                }
            },
            {
                // 5. Mercado
                element: 'a[href="/market"]',
                popover: {
                    title: '¡Al Mercado! ⚖️',
                    description: 'Acá ocurre la magia: buscás triangulaciones, comprás figus difíciles y cerrás los canjes. ¡A completar ese álbum!',
                    side: "bottom", align: 'center'
                }
            }
        ]
    });

    driverObj.drive();
}

// Lógica de "Única Vez" automática
document.addEventListener('DOMContentLoaded', () => {
    // Revisamos si ya vio el tutorial
    const tutorialVisto = localStorage.getItem('tutorial_visto');
    
    // Si no lo vio, lo disparamos después de 1.5 segundos para que cargue bien HTMX
    if (!tutorialVisto) {
        setTimeout(() => {
            startTutorial();
            localStorage.setItem('tutorial_visto', 'true'); // Lo marcamos como visto
        }, 1500); 
    }
});