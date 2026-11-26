export interface MetodoMetrica {
    etichetta: string;
    valore: string;
}

export interface MetodoOperativo {
    id: 'manuale' | 'spruzzo-caldo' | 'poliurea-freddo';
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
        id: 'poliurea-freddo',
        numero: '03',
        tag: 'A FREDDO · AIRLESS O RULLO',
        titolo: 'Poliurea a Freddo',
        titoloBreve: 'Poliurea a freddo',
        immagine: '/images/metodi/poliurea-freddo.webp',
        immagineAlt: 'Applicazione di poliurea a freddo e ciclo poliaspartico direttamente su piastrelle di un terrazzo esistente',
        riepilogoHome:
            'La chimica della poliurea applicata a temperatura ambiente con pompa airless, rullo o spatola: stabile ai ristagni, veloce da posare e ideale per terrazzi e coperture medie.',
        descrizione:
            'Sistemi poliureici a freddo e poliaspartici posati a temperatura ambiente con pompa airless, rullo o spatola senza camion bimixer. Sovrapponibile su piastrelle e guaine, stabile ai ristagni e ai raggi UV.',
        badgeHome: 'Stabile a ristagni e UV',
        metricaHomeSinistra: 'Airless / Rullo a freddo',
        metricaHomeDestra: 'Pedonabile 2–12 h',
        metriche: [
            { etichetta: 'Posa a freddo', valore: 'Airless o rullo' },
            { etichetta: 'Pedonabile', valore: '2 – 12 ore' },
            { etichetta: 'Allungamento', valore: '300% – 400%' },
        ],
        puntiChiave: [
            'Nessun reattore riscaldato: perfetta per attici, condomini e interni',
            'Non riemulsiona in presenza di ristagni d’acqua persistenti',
            'Finiture alifatiche/poliaspartiche anti-UV pedonabili a vista',
        ],
        idealePer: ['Terrazzi su piastrelle', 'Coperture medie', 'Attici e condomini', 'Box e ambienti interni'],
    },
];

export interface ConfrontoRiga {
    criterio: string;
    manuale: string;
    spruzzoCaldo: string;
    poliureaFreddo: string;
}

export const confrontoMetodi: ConfrontoRiga[] = [
    {
        criterio: 'Attrezzatura',
        manuale: 'Rullo, spatola e pennello',
        spruzzoCaldo: 'Impianto bimixer alta pressione',
        poliureaFreddo: 'Pompa airless, rullo o spatola',
    },
    {
        criterio: 'Temperatura posa',
        manuale: 'Ambiente',
        spruzzoCaldo: '65–80°C · 180–200 bar',
        poliureaFreddo: 'Ambiente (senza bimixer)',
    },
    {
        criterio: 'Pedonabilità',
        manuale: '12 – 24 ore',
        spruzzoCaldo: '60 minuti',
        poliureaFreddo: '2 – 12 ore',
    },
    {
        criterio: 'Spessore continuo',
        manuale: '1,5 – 2,2 mm (armabile)',
        spruzzoCaldo: '2,0 – 3,0 mm',
        poliureaFreddo: '1,5 – 2,2 mm',
    },
    {
        criterio: 'Ideale per',
        manuale: 'Balconi, dettagli, centri storici',
        spruzzoCaldo: 'Grandi tetti, capannoni, fondazioni',
        poliureaFreddo: 'Terrazzi, attici, coperture medie',
    },
];
