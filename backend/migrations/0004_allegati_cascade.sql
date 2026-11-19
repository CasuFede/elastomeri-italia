-- Migration 0004: Aggiunge vincolo ON DELETE CASCADE alla tabella allegati per evitare record orfani
CREATE TABLE IF NOT EXISTS allegati_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    preventivo_id INTEGER NOT NULL REFERENCES preventivi(id) ON DELETE CASCADE,
    nome_file TEXT NOT NULL,
    nome_originale TEXT NOT NULL,
    tipo_mime TEXT NOT NULL
);

INSERT INTO allegati_new (id, preventivo_id, nome_file, nome_originale, tipo_mime)
SELECT id, preventivo_id, nome_file, nome_originale, tipo_mime FROM allegati;

DROP TABLE allegati;

ALTER TABLE allegati_new RENAME TO allegati;

CREATE INDEX IF NOT EXISTS idx_allegati_preventivo_id
    ON allegati (preventivo_id);
