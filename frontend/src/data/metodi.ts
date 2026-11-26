export interface MetodoParametro {
    etichetta: string;
    valore: string;
}

export interface MetodoOperativo {
    id: 'manuale' | 'spruzzo-caldo' | 'poliurea-freddo';
    numero: string;
    tag: string;
    titolo: string;
    sottotitolo: string;
    riepilogoHome: string;
    descrizione: string;
    badgeHome: string;
    metricaHomeSinistra: string;
    metricaHomeDestra: string;
    parametri: MetodoParametro[];
    idealePer: string[];
    vantaggi: string[];
    fasiPosa: string[];
}

export const metodiOperativi: MetodoOperativo[] = [
    {
        id: 'manuale',
        numero: '01',
        tag: 'RULLO · SPATOLA · DETTAGLI',
        titolo: 'Applicazione Manuale',
        sottotitolo: 'Resine elastomeriche liquide e cicli armati con tessuto in fibra di vetro stesi a mano',
        riepilogoHome:
            'Stesura manuale a rullo, spatola o pennello con eventuale armatura in fibra di vetro: massima precisione su terrazzi, balconi, raccordi, camini e cantieri con accesso ridotto.',
        descrizione:
            'La posa manuale con resine elastomeriche poliuretaniche o cicli armati in fibra di vetro è la soluzione più versatile per superfici piccole, geometrie articolate e punti critici dove un impianto ad alta pressione sarebbe sproporzionato o logisticamente complesso. Applicata in due o più mani incrociate, crea una membrana monolitica continua che elimina giunti e saldature.',
        badgeHome: 'Alta precisione su dettagli',
        metricaHomeSinistra: 'Spessore 1,5–2,2 mm',
        metricaHomeDestra: 'Zero ingombro impianti',
        parametri: [
            { etichetta: 'Attrezzatura', valore: 'Rullo a pelo corto, spatola dentata/liscia e pennello per risvolti' },
            { etichetta: 'Temperatura posa', valore: 'Ambiente (+5°C / +35°C)' },
            { etichetta: 'Spessore tipico', valore: '1,5 – 2,2 mm (in 2 mani incrociate, armabile con fibra di vetro)' },
            { etichetta: 'Pedonabilità', valore: '12 – 24 ore (in base a temperatura e umidità ambientale)' },
            { etichetta: 'Allungamento elastico', valore: '> 300% (elevato crack-bridging su micro-fessurazioni)' },
            { etichetta: 'Supporti compatibili', valore: 'Piastrelle, calcestruzzo, vecchie guaine bituminose, metalli e massetti' },
        ],
        idealePer: [
            'Balconi e terrazzi residenziali',
            'Soglie, pluviali e risvolti verticali',
            'Cornicioni, camini e canali di gronda',
            'Centri storici e piani alti con accesso ridotto',
        ],
        vantaggi: [
            'Controllo millimetrico su spigoli, bocchettoni, tubazioni e dettagli geometrici complessi',
            'Possibilità di annegare tessuto in fibra di vetro o TNT tecnico tra le mani per massima resistenza meccanica',
            'Zero demolizioni su pavimentazioni ben ancorate e nessun ingombro di camion bimixer',
            'Finitura antiscivolo e protettiva anti-UV personalizzabile su superfici calpestabili',
        ],
        fasiPosa: [
            'Pulizia profonda del supporto, chiusura fessure e applicazione del primer aggrappante specifico.',
            'Stesura della prima mano liquida a rullo o spatola con eventuale annegamento a fresco della fibra di vetro.',
            'Applicazione della seconda mano incrociata fino a completo incapsulamento e finitura protettiva anti-UV.',
        ],
    },
    {
        id: 'spruzzo-caldo',
        numero: '02',
        tag: 'IMPIANTO BIMIXER · ALTA PRESSIONE',
        titolo: 'Poliurea a Caldo a Spruzzo',
        sottotitolo: 'Membrana pura bicomponente nebulizzata ad alta pressione (65–80°C · 180–200 bar)',
        riepilogoHome:
            'Nebulizzazione ad alta pressione con impianto bimixer riscaldato: polimerizzazione in 5–10 secondi, calpestabile in 60 minuti e resa fino a 1.000 mq/giorno su grandi coperture.',
        descrizione:
            'È il sistema ad altissime prestazioni per grandi coperture industriali, lastrici condominiali, parcheggi, vasche e fondazioni. Un reattore bicomponente (bimixer) riscalda separatamente isocianato e poliammina a 65–80°C in rapporto 1:1 e li spruzza a 180–200 bar: la reazione è immediata (gel time 5–10 secondi), senza colature nemmeno su superfici verticali, garantendo una corazza monolitica priva di giunti e calpestabile già dopo 60 minuti.',
        badgeHome: 'Pedonabile in 60 minuti',
        metricaHomeSinistra: '70°C · 180–200 bar',
        metricaHomeDestra: 'Gel time 5–10 sec',
        parametri: [
            { etichetta: 'Attrezzatura', valore: 'Impianto proporzionatore bimixer con tubi riscaldati e pistola ad alta pressione' },
            { etichetta: 'Pressione / Temperatura', valore: '180 – 200 bar · fluidi preriscaldati a 65°C – 80°C (rapporto 1:1)' },
            { etichetta: 'Gel time / Fuori tatto', valore: 'Gel time 5 – 10 secondi · fuori tatto in ~30 secondi' },
            { etichetta: 'Pedonabilità', valore: 'Circa 60 minuti (cantiere immediatamente fruibile)' },
            { etichetta: 'Spessore & Consumo', valore: '2,0 – 3,0 mm continui (~2,1 – 2,2 kg/m² per 2 mm)' },
            { etichetta: 'Allungamento & Trazione', valore: '> 400% a rottura · resistenza a trazione > 15 – 20 MPa' },
        ],
        idealePer: [
            'Capannoni e grandi coperture industriali',
            'Lastrici solari e tetti condominiali estesi',
            'Platee, muri controterra e fondazioni',
            'Vasche, piscine e impalcati carrabili',
        ],
        vantaggi: [
            'Polimerizzazione istantanea: aderisce perfettamente anche su pareti verticali, lucernari e soffitti senza colare',
            'Produttività altissima (fino a 800–1.000 m² al giorno) con azzeramento dei fermi di cantiere',
            'Resistenza estrema a ristagni permanenti d’acqua, cicli gelo-disgelo (-20°C / +80°C) e agenti chimici',
            'Membrana monolitica 100% continua, priva di sormonti e saldature a fiamma libera',
        ],
        fasiPosa: [
            'Verifica igrometrica del supporto e controllo del punto di rugiada (+3°C sopra dew point), preparazione meccanica e primer epossidico.',
            'Spruzzatura a caldo con bimixer in passate incrociate fino allo spessore continuo di 2–3 mm su piani e risvolti.',
            'Applicazione del topcoat protettivo alifatico anti-UV (eventualmente antiscivolo) e collaudo idraulico.',
        ],
    },
    {
        id: 'poliurea-freddo',
        numero: '03',
        tag: 'TEMPERATURA AMBIENTE · AIRLESS O RULLO',
        titolo: 'Poliurea a Freddo',
        sottotitolo: 'Sistemi poliureici a freddo e poliaspartici applicati a temperatura ambiente senza bimixer',
        riepilogoHome:
            'La chimica della poliurea applicata a temperatura ambiente con pompa airless, rullo o spatola: stabile ai ristagni, veloce da posare e ideale per terrazzi e coperture medie.',
        descrizione:
            'La poliurea a freddo (in formulazione bicomponente, monocomponente o poliaspartica evoluta) trasferisce la resistenza e la continuità della tecnologia poliureica in tutti i cantieri dove non è necessario o agevole portare un reattore riscaldato. Con un pot-life gestibile (15–35 minuti), si posa a pompa airless, rullo o spatola direttamente sopra piastrelle, guaine o calcestruzzo: non riemulsiona con i ristagni d’acqua e, nelle versioni alifatiche/poliaspartiche, offre stabilità totale ai raggi UV.',
        badgeHome: 'Stabile ai ristagni e UV',
        metricaHomeSinistra: 'Rullo / Airless a freddo',
        metricaHomeDestra: 'Pedonabile 2–12 h',
        parametri: [
            { etichetta: 'Attrezzatura', valore: 'Pompa airless a freddo, rullo o spatola/racla (senza reattore riscaldato)' },
            { etichetta: 'Temperatura posa', valore: 'Ambiente (+5°C / +35°C; poliaspartica rapida anche a basse temperature)' },
            { etichetta: 'Spessore tipico', valore: '1,5 – 2,2 mm (in due mani incrociate, con armatura sui punti critici)' },
            { etichetta: 'Pedonabilità', valore: '2 – 6 ore (cicli poliaspartici rapidi) fino a 12 ore' },
            { etichetta: 'Allungamento elastico', valore: '300% – 400% con elevata resistenza a usura e ristagni d’acqua' },
            { etichetta: 'Stabilità UV', valore: 'Eccellente nei cicli alifatici e poliaspartici (non ingiallisce al sole)' },
        ],
        idealePer: [
            'Terrazzi e lastrici residenziali senza demolizione',
            'Coperture piane di media estensione',
            'Superfici pedonabili a vista con finitura estetica',
            'Ambienti interni, box, cantine e raccordi complessi',
        ],
        vantaggi: [
            'Nessuna necessità di camion bimixer riscaldato: perfetta per condomini, attici e zone urbane dense',
            'A differenza delle comuni resine acriliche, non riemulsiona in presenza di ristagni d’acqua persistenti',
            'Sovrapponibile direttamente su gres, ceramica, klinker, cemento e vecchie guaine bituminose',
            'Asciugatura rapida e finiture alifatiche/poliaspartiche resistenti al calpestio e ai raggi UV',
        ],
        fasiPosa: [
            'Preparazione superficiale (levigatura o lavaggio ad alta pressione), ripristino giunti e stesura del primer specifico.',
            'Applicazione a temperatura ambiente (airless, rullo o spatola) della prima mano con rinforzo su spigoli e scarichi.',
            'Seconda mano a chiusura completa ed eventuale finitura poliaspartica/alifatica pigmentata o antisdrucciolo.',
        ],
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
        criterio: 'Attrezzatura principale',
        manuale: 'Rullo, spatola e pennello',
        spruzzoCaldo: 'Impianto bimixer ad alta pressione',
        poliureaFreddo: 'Pompa airless a freddo, rullo o spatola',
    },
    {
        criterio: 'Temperatura e pressione',
        manuale: 'Temperatura ambiente · posa manuale',
        spruzzoCaldo: '65–80°C · 180–200 bar',
        poliureaFreddo: 'Temperatura ambiente · senza riscaldamento',
    },
    {
        criterio: 'Asciugatura e pedonabilità',
        manuale: '12 – 24 ore',
        spruzzoCaldo: 'Gel time 5–10 sec · pedonabile in 60 min',
        poliureaFreddo: '2 – 6 ore (poliaspartica) fino a 12 ore',
    },
    {
        criterio: 'Spessore medio continuo',
        manuale: '1,5 – 2,2 mm (con fibra di vetro)',
        spruzzoCaldo: '2,0 – 3,0 mm in passate incrociate',
        poliureaFreddo: '1,5 – 2,2 mm in 2 mani incrociate',
    },
    {
        criterio: 'Allungamento elastico',
        manuale: '> 300%',
        spruzzoCaldo: '> 400%',
        poliureaFreddo: '300% – 400%',
    },
    {
        criterio: 'Metratura e logistica ideale',
        manuale: 'Piccole superfici, dettagli e centri storici',
        spruzzoCaldo: 'Grandi superfici (fino a 1.000 m²/giorno)',
        poliureaFreddo: 'Medie superfici, attici, terrazzi e interni',
    },
    {
        criterio: 'Applicazioni tipiche',
        manuale: 'Balconi, cornicioni, raccordi, piccoli terrazzi',
        spruzzoCaldo: 'Capannoni, grandi tetti, vasche, fondazioni',
        poliureaFreddo: 'Terrazzi su piastrelle, lastrici, coperture medie',
    },
];
