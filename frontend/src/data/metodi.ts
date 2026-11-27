export interface MetodoMetrica {
    etichetta: string;
    valore: string;
}

export interface MetodoOperativo {
    id: 'manuale' | 'spruzzo-caldo' | 'bituminoso-remat';
    numero: string;
    tag: string;
    titolo: string;
    titoloBreve: string;
    immagine: string;
    immagineAlt: string;
    riepilogoHome: string;
    descrizione: string;
    badgeHome: string;
    metricaHomeSinistra: string;
    metricaHomeDestra: string;
    metriche: MetodoMetrica[];
    puntiChiave: string[];
    idealePer: string[];
}

export const metodiOperativi: MetodoOperativo[] = [
    {
        id: 'manuale',
        numero: '01',
        tag: 'RULLO · SPATOLA · DETTAGLI',
        titolo: 'Applicazione Manuale',
        titoloBreve: 'Manuale',
        immagine: '/images/metodi/manuale.webp',
        immagineAlt: 'Applicazione manuale a rullo di resina impermeabilizzante elastica con tessuto in fibra di vetro su terrazzo',
        riepilogoHome:
            'Stesura manuale a rullo, spatola o pennello con eventuale armatura in fibra di vetro: massima precisione su terrazzi, balconi, raccordi e cantieri con accesso ridotto.',
        descrizione:
            'Resine elastomeriche liquide stese a mano in due mani incrociate, armabili con tessuto in fibra di vetro. La scelta più precisa su superfici contenute, dettagli complessi e cantieri senza accesso mezzi.',
        badgeHome: 'Massima precisione',
        metricaHomeSinistra: 'Spessore 1,5–2,2 mm',
        metricaHomeDestra: 'Zero ingombro impianti',
        metriche: [
            { etichetta: 'Attrezzatura', valore: 'Rullo e spatola' },
            { etichetta: 'Spessore', valore: '1,5 – 2,2 mm' },
            { etichetta: 'Pedonabile', valore: '12 – 24 ore' },
        ],
        puntiChiave: [
            'Controllo millimetrico su spigoli, soglie, pluviali e risvolti verticali',
            'Armabile con tessuto in fibra di vetro per rinforzo strutturale',
            'Zero demolizioni su piastrelle ancorate e nessun ingombro impianti',
        ],
        idealePer: ['Balconi e terrazzi', 'Camini e gronde', 'Raccordi critici', 'Centri storici'],
    },
    {
        id: 'spruzzo-caldo',
        numero: '02',
        tag: 'IMPIANTO BIMIXER · ALTA PRESSIONE',
        titolo: 'Poliurea a Caldo a Spruzzo',
        titoloBreve: 'Spruzzo a caldo',
        immagine: '/images/metodi/spruzzo-caldo.webp',
        immagineAlt: 'Spruzzatura a caldo di poliurea pura con impianto bimixer ad alta pressione su ampia copertura piana',
        riepilogoHome:
            'Nebulizzazione ad alta pressione con impianto bimixer riscaldato: polimerizzazione in 5–10 secondi, calpestabile in 60 minuti e resa fino a 1.000 mq/giorno.',
        descrizione:
            'Membrana pura bicomponente nebulizzata a caldo (65–80°C) ad alta pressione (180–200 bar) con impianto bimixer. Indurisce in pochi secondi senza colature, formando una corazza monolitica priva di giunti.',
        badgeHome: 'Pedonabile in 60 min',
        metricaHomeSinistra: '70°C · 180–200 bar',
        metricaHomeDestra: 'Gel time 5–10 sec',
        metriche: [
            { etichetta: 'Impianto bimixer', valore: '65–80°C · 200 bar' },
            { etichetta: 'Pedonabile', valore: '60 minuti' },
            { etichetta: 'Produttività', valore: 'fino a 1.000 m²/g' },
        ],
        puntiChiave: [
            'Gel time 5–10 secondi: zero colature anche su pareti verticali',
            'Allungamento elastico > 400%, resiste a ristagni e sbalzi (-20/+80°C)',
            'Membrana continua da 2–3 mm senza saldature né fiamma libera',
        ],
        idealePer: ['Capannoni industriali', 'Grandi tetti condominiali', 'Fondazioni e muri', 'Vasche e piscine'],
    },
    {
        id: 'bituminoso-remat',
        numero: '03',
        tag: 'BITUMINOSO · STESURA REMAT FIBRA DI VETRO',
        titolo: 'Prodotto Bituminoso Armato Remat',
        titoloBreve: 'Bituminoso Remat',
        immagine: '/images/metodi/bituminoso-remat.webp',
        immagineAlt: 'Applicazione di prodotto bituminoso liquido elastomero con stesura di tessuto in fibra di vetro Remat su copertura piana',
        riepilogoHome:
            'Prodotto bituminoso liquido elastomero armato con stesura di tessuto in fibra di vetro Remat: manto continuo corazzato senza fiamma, ideale per risanare vecchie guaine e coperture estese.',
        descrizione:
            'Sistema impermeabilizzante a base di prodotto bituminoso liquido elastomero armato a tutta superficie con stesura del tessuto in fibra di vetro Remat. Si posa a rullo o pompa airless senza fiamma libera, annegando la fibra tra due mani per creare una corazza monolitica ad alta resistenza meccanica.',
        badgeHome: 'Armatura fibra di vetro Remat',
        metricaHomeSinistra: 'Fibra di vetro Remat',
        metricaHomeDestra: 'Zero fiamma libera',
        metriche: [
            { etichetta: 'Armatura', valore: 'Fibra di vetro Remat' },
            { etichetta: 'Applicazione', valore: 'Airless o rullo' },
            { etichetta: 'Posa sicura', valore: 'Senza fiamma libera' },
        ],
        puntiChiave: [
            'Stesura del tessuto in fibra di vetro Remat annegato fresco su fresco per massima resistenza a strappo e fessurazioni',
            'Adesione diretta e piena compatibilità chimica nel recupero di vecchie guaine bituminose senza demolizioni',
            'Manto elastico continuo senza giunzioni né fiamma libera, stabile ai ristagni d’acqua e agli sbalzi termici',
        ],
        idealePer: ['Guaine bituminose datate', 'Coperture industriali', 'Tetti piani condominiali', 'Risanamenti senza demolizioni'],
    },
];

export interface ConfrontoRiga {
    criterio: string;
    manuale: string;
    spruzzoCaldo: string;
    bituminosoRemat: string;
}

export const confrontoMetodi: ConfrontoRiga[] = [
    {
        criterio: 'Attrezzatura',
        manuale: 'Rullo, spatola e pennello',
        spruzzoCaldo: 'Impianto bimixer alta pressione',
        bituminosoRemat: 'Pompa airless o rullo + stesura Remat',
    },
    {
        criterio: 'Temperatura posa',
        manuale: 'Ambiente',
        spruzzoCaldo: '65–80°C · 180–200 bar',
        bituminosoRemat: 'Ambiente (senza fiamma libera)',
    },
    {
        criterio: 'Pedonabilità',
        manuale: '12 – 24 ore',
        spruzzoCaldo: '60 minuti',
        bituminosoRemat: '12 – 24 ore',
    },
    {
        criterio: 'Spessore continuo',
        manuale: '1,5 – 2,2 mm (armabile)',
        spruzzoCaldo: '2,0 – 3,0 mm',
        bituminosoRemat: '2,0 – 3,0 mm (armato Remat)',
    },
    {
        criterio: 'Ideale per',
        manuale: 'Balconi, dettagli, centri storici',
        spruzzoCaldo: 'Grandi tetti, capannoni, fondazioni',
        bituminosoRemat: 'Vecchie guaine bituminose, tetti e capannoni',
    },
];
