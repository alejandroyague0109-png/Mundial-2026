// Esperamos a que todo cargue
document.addEventListener('DOMContentLoaded', () => {
    
    // Verificamos que la librería exista
    if (!window.driver || !window.driver.js) {
        console.error("No cargó Driver.js");
        return;
    }

    const driver = window.driver.js.driver;

    // Enganchamos la función al objeto window para que el botón HTML la pueda llamar
    window.startTutorial = function() {
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
                        popover: { title: 'Tus Repetidas 💰', description: 'Si dejás el precio en 0, es solo para <b>CANJE</b>. Si le ponés un valor, pasa a <b>VENTA</b>.', side: "top", align: 'center' }
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
                        element: 'a[href="/market"]',
                        popover: { title: '¡Al Mercado! ⚖️', description: 'Buscás triangulaciones y cerrás los canjes.', side: "bottom", align: 'center' }
                    }
                ]
            });

            driverObj.drive();
            
        } catch (error) {
            console.error("Falla al iniciar:", error);
            alert("No se pudo iniciar el tutorial. Revisá la consola.");
        }
    };

    // --- Lógica de Única Vez ---
    // Solo arrancamos automático si existe el botón del menú (o sea, estamos en el Álbum)
    const isAlbumPage = document.getElementById('btn-menu-tutorial');
    const tutorialVisto = localStorage.getItem('tutorial_visto');

    if (isAlbumPage && !tutorialVisto) {
        setTimeout(() => {
            window.startTutorial();
            localStorage.setItem('tutorial_visto', 'true');
        }, 2000); 
    }
});