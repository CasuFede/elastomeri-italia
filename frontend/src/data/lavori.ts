export interface LavoroMediaFoto {
    /** Percorso pubblico dell'immagine (es. '/images/lavori/cantiere-lupia/prima-01.webp') */
    src: string;
    /** Testo alternativo descrittivo (accessibilità e SEO) */
    alt: string;
    /** Didascalia opzionale mostrata nella galleria e nella vista ingrandita */
    didascalia?: string;
}

export interface LavoroVideo {
    /** Percorso del video (usa '/media/<nome>.mp4' per streaming ottimizzato su iOS e mobile) */
    src: string;
    /** Immagine di copertina caricata in lazy loading prima del clic su Play */
    poster: string;
    /** Titolo sintetico del video */
    titolo: string;
    /** Durata opzionale visualizzata sul badge (es. '0:18') */
    durata?: string;
    /** Breve nota tecnica opzionale */
    descrizione?: string;
}

export interface LavoroStratigrafiaStep {
    /** Numero o sigla dello strato (es. '01', '02', '03') */
    fase: string;
    /** Nome sintetico della fase o dello strato */
    titolo: string;
    /** Descrizione tecnica dettagliata */
    dettaglio: string;
}

export interface LavoroProgetto {
    /** Identificativo univoco URL-safe (es. 'copertura-bituminosa-600mq-sika-remax') */
    id: string;
    /** Categoria per etichetta e filtri */
    categoria: 'Coperture industriali' | 'Terrazzi e lastrici' | 'Fondazioni e cantine' | 'Impermeabilizzazioni';
    /** Titolo principale dell'intervento */
    titolo: string;
    /** Località o area geografica */
    localita: string;
    /** Superficie trattata in metri quadrati (es. 600 -> '600 mq') */
    superficieMq: number;
    /** Tipologia di supporto esistente */
    supporto: string;
    /** Ciclo e marchio/sistema applicato */
    cicloSistema: string;
    /** Sistema di armatura / rinforzo */
    armatura: string;
    /** Metodo applicativo principale (es. 'Spruzzo con pompa airless') */
    applicazione: string;
    /** Introduzione breve leggibile nella scheda aperta */
    riepilogo: string;
    /** Descrizione testuale completa della stratigrafia */
    stratigrafiaDescrizione: string;
    /** Elenco ordinato degli strati applicati */
    stratigrafiaFasi: LavoroStratigrafiaStep[];
    /** Galleria fotografica dello stato iniziale e lavorazione (Prima) */
    fotoPrima: LavoroMediaFoto[];
    /** Galleria fotografica del risultato finale (Dopo) */
    fotoDopo: LavoroMediaFoto[];
    /** Uno o più video opzionali del risultato finale (caricati on-demand solo al clic) */
    videoDopo?: LavoroVideo[];
}

/**
 * Elenco modulare dei lavori eseguiti.
 * Per aggiungere un nuovo cantiere basta inserire un nuovo oggetto in questo array,
 * posizionando foto in `frontend/public/images/lavori/<slug>/` ed eventuali video MP4 in `frontend/public/videos/`.
 */
export const lavoriProgetti: LavoroProgetto[] = [
    {
        id: 'copertura-bituminosa-600mq-sika-remax',
        categoria: 'Coperture industriali',
        titolo: 'Risanamento copertura bituminosa 600 mq — Ciclo Sika armato',
        localita: 'Genova e Liguria',
        superficieMq: 600,
        supporto: 'Materiale bituminoso',
        cicloSistema: 'Ciclo Sika (Remat)',
        armatura: 'Corazzato con fibra di vetro Remax',
        applicazione: 'Spruzzo con pompa airless',
        riepilogo:
            'Impermeabilizzazione continua di una copertura da 600 mq su manto bituminoso esistente, eseguita senza demolizioni con ciclo Sika (Remat) applicato a spruzzo con pompa airless e armatura integrale in tessuto di fibra di vetro Remax.',
        stratigrafiaDescrizione:
            'Resina elastica monocomponente applicata a spruzzo con pompa airless, armatura con tessuto in fibra di vetro e ulteriore mano a spruzzo di resina elastica monocomponente.',
        stratigrafiaFasi: [
            {
                fase: '01',
                titolo: 'Prima mano a spruzzo con pompa airless',
                dettaglio:
                    'Applicazione uniforme di resina elastica monocomponente (ciclo Sika Remat) direttamente sul supporto bituminoso esistente preparato.',
            },
            {
                fase: '02',
                titolo: 'Armatura corazzata in fibra di vetro Remax',
                dettaglio:
                    'Posa e annegamento a fresco del tessuto in fibra di vetro Remax su tutta la copertura, sui colmi e nei raccordi perimetrali.',
            },
            {
                fase: '03',
                titolo: 'Seconda mano a spruzzo di chiusura',
                dettaglio:
                    'Ulteriore mano a spruzzo airless di resina elastica monocomponente fino a completo incapsulamento, creando un manto continuo privo di giunzioni.',
            },
        ],
        fotoPrima: [
            {
                src: '/images/lavori/cantiere-lupia/prima-01.webp',
                alt: 'Stato iniziale della copertura bituminosa da 600 mq con pompa airless pronta sul ponteggio',
                didascalia: 'Stato iniziale — Manto bituminoso ammalorato e pompa airless pronta sul ponteggio',
            },
            {
                src: '/images/lavori/cantiere-lupia/prima-02.webp',
                alt: 'Panoramica della vecchia guaina bituminosa fessurata prima dell’intervento',
                didascalia: 'Stato iniziale — Guaina bituminosa degradata e fessurata prima del ripristino',
            },
            {
                src: '/images/lavori/cantiere-lupia/prima-03.webp',
                alt: 'Colmo e falda esposta prima della preparazione del supporto bituminoso',
                didascalia: 'Stato iniziale — Colmo e falda esposti prima dell’applicazione del ciclo',
            },
            {
                src: '/images/lavori/cantiere-lupia/prima-04.webp',
                alt: 'Prima mano a spruzzo lungo il colmo e il raccordo del camino',
                didascalia: 'Lavorazione — Prima mano a spruzzo lungo il colmo e i raccordi del camino',
            },
            {
                src: '/images/lavori/cantiere-lupia/prima-05.webp',
                alt: 'Operatore durante la posa del tessuto di armatura in fibra di vetro Remax',
                didascalia: 'Armatura — Stesura e annegamento a fresco del tessuto in fibra di vetro Remax',
            },
            {
                src: '/images/lavori/cantiere-lupia/prima-06.webp',
                alt: 'Fascia corazzata con tessuto in fibra di vetro lungo la linea di colmo',
                didascalia: 'Armatura — Fascia corazzata in fibra di vetro sul colmo prima della chiusura',
            },
        ],
        fotoDopo: [
            {
                src: '/images/lavori/cantiere-lupia/dopo-01.webp',
                alt: 'Risultato finale della copertura da 600 mq impermeabilizzata con membrana elastica continua',
                didascalia: 'Risultato finale — Copertura impermeabilizzata con manto elastico continuo senza giunzioni',
            },
            {
                src: '/images/lavori/cantiere-lupia/dopo-02.webp',
                alt: 'Vista d’insieme delle falde e dei raccordi sigillati dopo il ciclo Sika armato',
                didascalia: 'Risultato finale — Panoramica completa delle falde, dei muretti e dei raccordi sigillati',
            },
            {
                src: '/images/lavori/cantiere-lupia/dopo-03.webp',
                alt: 'Colmo e raccordi attorno al camino sigillati a ciclo ultimato',
                didascalia: 'Risultato finale — Colmo e risvolti attorno al camino completamente impermeabilizzati',
            },
        ],
        videoDopo: [
            {
                src: '/media/cantiere-lupia-panoramica.mp4',
                poster: '/images/lavori/cantiere-lupia/video-panoramica-poster.webp',
                titolo: 'Panoramica del tetto finito (600 mq)',
                durata: '0:18',
                descrizione: 'Ripresa completa delle falde, del colmo e dei raccordi sigillati a intervento ultimato.',
            },
            {
                src: '/media/cantiere-lupia-dettagli.mp4',
                poster: '/images/lavori/cantiere-lupia/video-dettagli-poster.webp',
                titolo: 'Dettaglio falde, lucernario e volumi tecnici',
                durata: '0:12',
                descrizione: 'Ispezione ravvicinata della membrana continua attorno a lucernari, camini e raccordi.',
            },
        ],
    },
];
