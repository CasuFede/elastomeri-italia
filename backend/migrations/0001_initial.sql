CREATE TABLE IF NOT EXISTS preventivi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT NOT NULL,
    telefono TEXT NOT NULL,
    servizio TEXT NOT NULL,
    messaggio TEXT,
    stato TEXT NOT NULL DEFAULT 'ricevuto',
    note_cliente TEXT NOT NULL DEFAULT '',
    data_richiesta TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_preventivi_data_richiesta
    ON preventivi (data_richiesta);
CREATE INDEX IF NOT EXISTS idx_preventivi_email
    ON preventivi (email);

CREATE TABLE IF NOT EXISTS allegati (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    preventivo_id INTEGER NOT NULL REFERENCES preventivi(id),
    nome_file TEXT NOT NULL,
    nome_originale TEXT NOT NULL,
    tipo_mime TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_allegati_preventivo_id
    ON allegati (preventivo_id);

CREATE TABLE IF NOT EXISTS lavori (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titolo TEXT NOT NULL,
    descrizione TEXT,
    localita TEXT,
    nome_file TEXT NOT NULL,
    nome_originale TEXT NOT NULL,
    tipo_mime TEXT NOT NULL,
    data_creazione TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_lavori_data_creazione
    ON lavori (data_creazione);

CREATE TABLE IF NOT EXISTS clienti (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    attivo INTEGER NOT NULL DEFAULT 1,
    data_creazione TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_clienti_email
    ON clienti (email);
