window.MathJax = {
    loader: {
        load: ['input/tex', 'output/chtml', 'ui/menu']
    },
    tex: {
        inlineMath: [['$', '$'], ['\\(', '\\)']],
        packages: ['base', 'ams', 'amsmath', 'amssymb', 'newcommand', 'configMacros']
    },
    options: {
        enableMenu: true
    },
    chtml: {
        matchFontHeight: false,
        exFactor: 0.5
    },
    menuSettings: {
        ALT: true,
        CMD: true,
        CTRL: true
    },
    output: {
        font: 'mathjax-stix2',
        displayOverflow: 'linebreak',
        linebreaks: {
            inline: true,
            width: '100%',
            lineleading: .4,
            LinebreakVisitor: null
        }
    },
    startup: {
        ready: () => {
            console.log('MathJax initialising...');
            MathJax.startup.defaultReady();
            console.log('MathJax is initialized');

            MathJax.startup.promise.then(() => {
                console.log('MathJax initial typesetting complete');
                return window.PagedPolyfill.preview();
            }).then(() => {
                console.log('Paged.js preview complete');
                // Give a small delay before final typeset
                return new Promise(resolve => setTimeout(resolve, 100));
            }).then(() => {
                return MathJax.typesetPromise();
            }).then(() => {
                console.log('Final MathJax typeset complete');
                // Force menu initialization
                if (MathJax.startup.document) {
                    MathJax.startup.document.menu.menu.find('Settings', 'Renderer').enable();
                }
            }).catch(err => {
                console.error('Error in MathJax/Paged.js setup:', err);
            });
        }
    }
}