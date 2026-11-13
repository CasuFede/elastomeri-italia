import re
import unicodedata


_ARTICOLI = (
    {
        "keywords": (
            "che cos'è la poliurea",
            "cos'è la poliurea",
            "definizione poliurea",
            "composizione",
            "componenti",
            "da quali componenti",
            "lato a",
            "lato b",
            "isocianato",
            "ammine",
            "membrana monolitica",
            "impermeabilizzazione",
            "membrana impermeabilizzante",
            "impermeabile",
        ),
        "answer": (
            "La poliurea è un elastomero applicato allo stato liquido che, dopo la "
            "reazione dei suoi componenti, forma una membrana continua. Nel sistema "
            "descritto dal manuale, il lato A contiene un prepolimero isocianico e "
            "il lato B resine amminiche. Le caratteristiche effettive dipendono "
            "dal prodotto e dalla sua scheda tecnica."
        ),
    },
    {
        "keywords": (
            "poliurea pura",
            "poliurea ibrida",
            "poliuretano poliurea",
            "differenza pura ibrida",
            "polioli",
            "sensibilità umidità",
        ),
        "answer": (
            "Il manuale distingue la poliurea pura, con resine amminiche, dai sistemi "
            "ibridi poliuretano-poliurea, che includono anche polioli. I due sistemi "
            "possono differire per catalizzatori, sensibilità all'umidità e prestazioni: "
            "per scegliere occorre verificare la formulazione e la scheda tecnica del "
            "prodotto specifico."
        ),
    },
    {
        "keywords": (
            "poliurea aromatica",
            "poliurea alifatica",
            "raggi uv",
            "sole",
            "ingiallimento",
            "sfarinamento",
            "top coat",
            "finitura protettiva",
        ),
        "answer": (
            "Secondo il manuale, la poliurea aromatica può scolorire o sfarinare se "
            "esposta ai raggi UV; se l'aspetto è importante, può essere prevista una "
            "finitura protettiva compatibile. La variante alifatica mantiene meglio il "
            "colore all'esterno, ma scelta e ciclo di finitura vanno verificati in base "
            "al prodotto e all'uso."
        ),
    },
    {
        "keywords": (
            "allungamento",
            "trazione",
            "durezza shore",
            "resistenza termica",
            "temperatura minima",
            "temperatura massima",
            "prestazioni meccaniche",
        ),
        "answer": (
            "Il manuale riporta valori indicativi che variano con la formulazione: "
            "allungamento a rottura fino al 400–1000%, resistenza a trazione spesso "
            "nell'intervallo 15–25 MPa e flessibilità indicata fino a circa −40 °C. "
            "Non sono valori garantiti per ogni prodotto: fanno fede la scheda tecnica "
            "e le condizioni di impiego del sistema scelto."
        ),
    },
    {
        "keywords": (
            "resistenza chimica",
            "prodotti chimici",
            "idrocarburi",
            "oli",
            "soluzioni saline",
            "acidi e basi",
        ),
        "answer": (
            "Il manuale descrive una buona resistenza della poliurea pura a "
            "idrocarburi, oli, soluzioni saline e ad acidi e basi diluiti. La "
            "compatibilità dipende comunque dal prodotto, dalla concentrazione "
            "e dalle condizioni di contatto: va verificata sulla scheda tecnica "
            "specifica."
        ),
    },
    {
        "keywords": (
            "preparazione supporto",
            "preparare calcestruzzo",
            "preparare cemento",
            "prepara calcestruzzo",
            "prepara cemento",
            "preparare metallo",
            "primer",
            "umidità supporto",
            "adesione",
            "supporto pulito",
            "calcestruzzo",
            "cemento",
            "su quali superfici",
            "ogni superficie",
            "qualsiasi supporto",
            "compatibilità",
            "compatibile",
        ),
        "answer": (
            "La preparazione del supporto è essenziale. Il manuale indica, per il "
            "calcestruzzo, un fondo stagionato, pulito e preparato meccanicamente; "
            "per il metallo, la rimozione di ossidi e contaminanti e una rugosità "
            "adeguata. Primer, umidità ammissibile e preparazione esatti dipendono "
            "dal supporto e dal ciclo specifico: vanno definiti da un tecnico e "
            "dalla scheda del prodotto."
        ),
    },
    {
        "keywords": (
            "applicazione",
            "come si applica",
            "spruzzo",
            "rullo",
            "pennello",
            "attrezzatura",
            "pompa",
            "pressione",
            "temperatura applicazione",
            "tempi indurimento",
            "polimerizzazione",
            "tempo di reazione",
            "gel time",
            "asciugatura",
            "asciugare",
            "fai da te",
            "applicazione fai da te",
            "si può applicare con il fai da te",
            "quanto dura",
            "quanto tempo",
            "durata intervento",
            "durata applicazione",
            "tempo di posa",
        ),
        "answer": (
            "Il manuale descrive l'applicazione a spruzzo con attrezzatura "
            "bicomponente specializzata e personale formato; non è una normale "
            "applicazione a rullo o pennello. Riporta tempi di reazione di pochi "
            "secondi per il sistema descritto, ma preparazione, condizioni di posa "
            "e tempi di riutilizzo dipendono dal prodotto e dal cantiere; non sono "
            "indicazioni per un'applicazione fai-da-te."
        ),
    },
    {
        "keywords": (
            "vantaggi",
            "svantaggi",
            "limiti",
            "giunti",
            "superfici verticali",
            "abrasione",
            "carrabile",
            "guaina",
            "bitume",
            "meglio poliurea",
        ),
        "answer": (
            "Tra i vantaggi descritti nel manuale ci sono la continuità della membrana "
            "spruzzata, la rapidità di reazione e la possibilità di rivestire geometrie "
            "complesse. Tra i limiti: servono attrezzatura e manodopera specializzate, "
            "una preparazione accurata e, per alcuni prodotti esposti al sole, una "
            "finitura protettiva. Non è automaticamente la scelta migliore: il confronto "
            "con una guaina o un altro sistema dipende dal supporto e dall'intervento."
        ),
    },
    {
        "keywords": (
            "dove si usa",
            "dove si applica",
            "applicazioni",
            "terrazze e coperture",
            "piscine e serbatoi",
            "terrazzo",
            "tetto",
            "parcheggio",
            "piscina",
            "serbatoio",
            "vasca",
            "condotte",
            "fondazioni",
        ),
        "answer": (
            "Il manuale cita, tra gli impieghi, tetti piani, terrazze, parcheggi, "
            "piscine, serbatoi, canali e rivestimenti industriali. La compatibilità "
            "non è automatica: per esempio, il contatto con acqua potabile richiede "
            "una specifica certificazione del prodotto. Supporto, esposizione e "
            "destinazione d'uso vanno verificati prima di scegliere il ciclo."
        ),
    },
    {
        "keywords": (
            "sicurezza",
            "dpi",
            "isocianati",
            "maschera",
            "guanti",
            "protezione operatore",
            "protezioni",
            "protezione respiratoria",
            "tuta integrale",
            "durante la spruzzatura",
            "overspray",
        ),
        "answer": (
            "Il manuale segnala che durante la spruzzatura l'overspray di isocianati "
            "richiede protezioni adeguate, tra cui protezione respiratoria e tuta "
            "integrale. L'applicazione va affidata a operatori formati, con procedure "
            "di sicurezza e dispositivi scelti in base alle schede di sicurezza dei "
            "prodotti."
        ),
    },
    {
        "keywords": (
            "prezzo",
            "costo",
            "quanto costa",
            "preventivo",
            "prezzi",
            "tariffa",
        ),
        "answer": (
            "Il manuale non fornisce un prezzo per un intervento. Il costo dipende "
            "da superficie, supporto, preparazione e ciclo richiesto; per una "
            "valutazione del tuo caso puoi richiedere un sopralluogo senza impegno "
            "dalla pagina /preventivo."
        ),
    },
)

_PAROLE_COMUNI = {
    "a",
    "ad",
    "al",
    "alla",
    "alle",
    "che",
    "chi",
    "come",
    "con",
    "da",
    "dei",
    "del",
    "della",
    "di",
    "e",
    "è",
    "gli",
    "i",
    "il",
    "in",
    "la",
    "le",
    "lo",
    "ma",
    "mi",
    "per",
    "posso",
    "quale",
    "quali",
    "quanto",
    "si",
    "sono",
    "su",
    "un",
    "una",
}

_SUFFISSI = (
    "azioni",
    "azione",
    "amenti",
    "amento",
    "imenti",
    "imento",
    "mente",
    "ibili",
    "ibile",
    "abili",
    "abile",
    "iche",
    "ichi",
    "ica",
    "ici",
    "ico",
    "ive",
    "ivi",
    "iva",
    "ivo",
    "ando",
    "endo",
    "are",
    "ere",
    "ire",
    "ate",
    "ati",
    "ata",
    "ato",
    "ute",
    "uti",
    "uta",
    "uto",
    "e",
    "i",
    "a",
    "o",
)


def _normalizza(testo: str) -> str:
    return (
        unicodedata.normalize("NFKD", testo.casefold())
        .encode("ascii", "ignore")
        .decode("ascii")
    )


def _tokenizza(testo: str) -> set[str]:
    parole = {
        parola
        for parola in re.findall(r"[a-z0-9]+", _normalizza(testo))
        if len(parola) > 2 and parola not in _PAROLE_COMUNI
    }
    return {
        next(
            (
                parola[: -len(suffisso)]
                for suffisso in _SUFFISSI
                if parola.endswith(suffisso) and len(parola) - len(suffisso) >= 3
            ),
            parola,
        )
        for parola in parole
    }


def _trova_articolo(domanda: str):
    parole_domanda = _tokenizza(domanda)
    domanda_normalizzata = " ".join(re.findall(r"[a-z0-9]+", _normalizza(domanda)))
    migliore = None
    punteggio_migliore = 0.0

    for articolo in _ARTICOLI:
        parole_articolo = set()
        corrispondenza_frase = False
        for parola_chiave in articolo["keywords"]:
            parole_articolo.update(_tokenizza(parola_chiave))
            frase = " ".join(re.findall(r"[a-z0-9]+", _normalizza(parola_chiave)))
            if frase and frase in domanda_normalizzata:
                corrispondenza_frase = True

        corrispondenze = parole_domanda & parole_articolo
        punteggio = (
            2 * len(corrispondenze)
            + len(corrispondenze) / len(parole_articolo)
            + (2.5 if corrispondenza_frase else 0)
        )
        if punteggio > punteggio_migliore:
            migliore = articolo
            punteggio_migliore = punteggio

    return migliore if punteggio_migliore >= 3 else None


def _e_followup(domanda: str) -> bool:
    parole = _tokenizza(domanda)
    normalizzata = " ".join(re.findall(r"[a-z0-9]+", _normalizza(domanda)))
    riferimenti = (
        "e invece",
        "e per",
        "e la",
        "e il",
        "e lo",
        "e questa",
        "e questo",
        "e quella",
        "e quello",
        "e loro",
        "invece",
        "anche",
        "rispetto",
        "quanto dura",
        "quanto tempo",
        "quale dei due",
    )
    return (
        normalizzata.startswith("e ") and len(parole) <= 6
    ) or any(riferimento in normalizzata for riferimento in riferimenti)


def rispondi(domanda: str, contesto: str = "") -> str:
    articolo = _trova_articolo(domanda)
    if articolo is None and contesto and _e_followup(domanda):
        articolo = _trova_articolo(f"{contesto} {domanda}")

    if articolo is None:
        return (
            "Non trovo una risposta a questa domanda nel manuale sulla poliurea. "
            "Posso aiutarti con composizione, differenze tra prodotti, preparazione "
            "dei supporti, applicazione, impieghi e sicurezza. Per valutare un "
            "intervento specifico puoi richiedere un sopralluogo su /preventivo."
        )
    return articolo["answer"]
