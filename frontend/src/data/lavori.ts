export interface LavoroMediaFoto {
    /** Percorso pubblico dell'immagine (es. '/images/lavori/copertura-600mq/prima.webp') */
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
    /** Durata opzionale visualizzata sul badge (es. '0:12') */
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
    /** Identificativo univoco URL-safe (es. 'copertura-bituminosa-600mq') */
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
    /** Introduzione breve leggibile sopra la scheda tecnica */
    riepilogo: string;
    /** Descrizione testuale completa della stratigrafia */
    stratigrafiaDescrizione: string;
    /** Elenco ordinato degli strati applicati */
    stratigrafiaFasi: LavoroStratigrafiaStep[];
    /** Immagine stato iniziale per lo slider Prima / Dopo */
    prima: LavoroMediaFoto;
    /** Immagine risultato finale per lo slider Prima / Dopo */
    dopo: LavoroMediaFoto;
    /** Galleria opzionale di foto aggiuntive del cantiere */
    galleria?: LavoroMediaFoto[];
    /** Uno o più video opzionali del cantiere (caricati on-demand solo al clic) */
    video?: LavoroVideo[];
}

/**
 * Elenco modulare dei lavori eseguiti.
 * Per aggiungere un nuovo intervento è sufficiente inserire un nuovo oggetto in questo array,
 * posizionando foto in `frontend/public/images/lavori/<slug>/` ed eventuali video MP4 in `frontend/public/videos/`.
 */
export const lavoriProgetti: LavoroProgetto[] = [
    {
        id: 'copertura-bituminosa-600mq-sika-remax',
        categoria: 'Coperture industriali',
        titolo: 'Risanamento copertura bituminosa da 600 mq con ciclo Sika armato',
        localita: 'Genova e Liguria',
        superficieMq: 600,
        supporto: 'Materiale bituminoso',
        cicloSistema: 'Ciclo Sika (Remat)',
        armatura: 'Corazzato con fibra di vetro Remax',
        applicazione: 'Spruzzo con pompa airless',
        riepilogo:
            'Impermeabilizzazione continua di una copertura piana da 600 mq su manto bituminoso esistente, eseguita senza demolizioni con ciclo Sika (Remat) applicato a spruzzo con pompa airless e armatura strutturale integrale in tessuto di fibra di vetro Remax.',
        stratigrafiaDescrizione:
            'Resina elastica monocomponente applicata a spruzzo con pompa airless, armatura con tessuto in fibra di vetro e ulteriore mano a spruzzo di resina elastica monocomponente.',
        stratigrafiaFasi: [
            {
                fase: '01',
                titolo: 'Prima mano a spruzzo con pompa airless',
                dettaglio:
                    'Applicazione uniforme di resina elastica monocomponente (ciclo Sika Remat) direttamente sul supporto bituminoso esistente pulito e preparato.',
            },
            {
                fase: '02',
                titolo: 'Armatura corazzata in fibra di vetro Remax',
                dettaglio:
                    'Posa e annegamento completo del tessuto in fibra di vetro Remax su tutta la superficie e nei raccordi perimetrali per massimizzare la resistenza meccanica e a trazione.',
            },
            {
                fase: '03',
                titolo: 'Seconda mano a spruzzo di chiusura',
                dettaglio:
                    'Ulteriore mano a spruzzo airless di resina elastica monocomponente fino a totale incapsulamento dell’armatura, creando una membrana continua e priva di giunzioni.',
            },
        ],
        prima: {
            src: '/images/lavori/copertura-600mq/prima.webp',
            alt: 'Stato iniziale della copertura bituminosa da 600 mq prima del ciclo impermeabilizzante Sika Remat',
            didascalia: 'Stato iniziale — Supporto bituminoso esistente prima dell’intervento',
        },
        dopo: {
            src: '/images/lavori/copertura-600mq/dopo.webp',
            alt: 'Risultato finale della copertura da 600 mq impermeabilizzata con ciclo Sika Remat armato con fibra di vetro Remax',
            didascalia: 'Risultato finale — Membrana continua elastica applicata a spruzzo airless',
        },
        galleria: [
            {
                src: '/images/lavori/copertura-600mq/armatura-fibra-remax.webp',
                alt: 'Dettaglio della posa dell’armatura con tessuto in fibra di vetro Remax tra le mani a spruzzo airless',
                didascalia: 'Fase di corazzatura — Posa del tessuto in fibra di vetro Remax annegato tra le mani airless',
            },
            {
                src: '/images/lavori/copertura-600mq/dopo.webp',
                alt: 'Vista d’insieme della copertura impermeabilizzata da 600 mq a ciclo completato',
                didascalia: 'Finitura finale — Copertura da 600 mq continua, sigillata su risvolti e bocchettoni',
            },
            {
                src: '/images/lavori/copertura-600mq/prima.webp',
                alt: 'Condizione originaria del manto bituminoso prima della preparazione del supporto',
                didascalia: 'Rilievo preliminare — Verifica del supporto bituminoso esistente prima della spruzzatura',
            },
        ],
        video: [
            {
                src: '/media/hero-poliurea.mp4?v=3',
                poster: '/images/hero-capannone-poliurea-bianca.webp',
                titolo: 'Applicazione a spruzzo ad alta pressione in cantiere',
                durata: '0:12',
                descrizione: 'Ripresa operativa della fase di nebulizzazione continua su copertura industriale.',
            },
        ],
    },
];
