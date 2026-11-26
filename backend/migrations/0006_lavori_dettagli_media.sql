-- Migration 0006: Estensione completa tabella lavori + tabella media multipli (foto prima/dopo e video)
ALTER TABLE lavori ADD COLUMN categoria TEXT NOT NULL DEFAULT 'Impermeabilizzazioni';
ALTER TABLE lavori ADD COLUMN superficie_mq INTEGER NOT NULL DEFAULT 0;
ALTER TABLE lavori ADD COLUMN supporto TEXT NOT NULL DEFAULT '';
ALTER TABLE lavori ADD COLUMN ciclo_sistema TEXT NOT NULL DEFAULT '';
ALTER TABLE lavori ADD COLUMN armatura TEXT NOT NULL DEFAULT '';
ALTER TABLE lavori ADD COLUMN applicazione TEXT NOT NULL DEFAULT '';
ALTER TABLE lavori ADD COLUMN stratigrafia_descrizione TEXT NOT NULL DEFAULT '';
ALTER TABLE lavori ADD COLUMN stratigrafia_fasi TEXT NOT NULL DEFAULT '[]';

CREATE TABLE IF NOT EXISTS lavori_media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lavoro_id INTEGER NOT NULL REFERENCES lavori(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL,
    nome_file TEXT NOT NULL,
    nome_originale TEXT NOT NULL,
    tipo_mime TEXT NOT NULL,
    titolo TEXT NOT NULL DEFAULT '',
    didascalia TEXT NOT NULL DEFAULT '',
    durata TEXT NOT NULL DEFAULT '',
    poster_file TEXT NOT NULL DEFAULT '',
    poster_mime TEXT NOT NULL DEFAULT '',
    ordine INTEGER NOT NULL DEFAULT 0,
    data_creazione TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_lavori_media_lavoro_id
    ON lavori_media (lavoro_id, tipo, ordine, id);
