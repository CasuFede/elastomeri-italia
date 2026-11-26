export interface LavoroMediaFoto {
    /** Percorso pubblico o endpoint API dell'immagine */
    src: string;
    /** Testo alternativo descrittivo (accessibilità e SEO) */
    alt: string;
    /** Didascalia opzionale mostrata nella galleria e nella vista ingrandita */
    didascalia?: string;
}

export interface LavoroVideo {
    /** Percorso del video (endpoint API R2 con Range 206 o '/media/<nome>.mp4') */
    src: string;
    /** Immagine di copertina caricata in lazy loading prima del clic su Play */
    poster: string;
    /** Titolo sintetico del video */
    titolo: string;
    /** Durata opzionale visualizzata sul badge (es. '0:13') */
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
    /** Identificativo univoco URL-safe (es. 'cantiere-2') */
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
 * Tutti i lavori sono ora gestiti e modificabili direttamente dal pannello /admin
 * (salvati su Cloudflare D1 + R2) e caricati live da /api/lavori.
 */
export const lavoriProgetti: LavoroProgetto[] = [];
