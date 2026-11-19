-- Migrazione: Aggiunta colonna primo_accesso per forzare il cambio password al primo login
ALTER TABLE clienti ADD COLUMN primo_accesso INTEGER NOT NULL DEFAULT 1;
