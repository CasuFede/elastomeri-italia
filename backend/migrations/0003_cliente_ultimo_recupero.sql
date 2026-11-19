-- Migrazione: Aggiunta colonna ultimo_recupero_password per limitare la richiesta a 1 volta al giorno
ALTER TABLE clienti ADD COLUMN ultimo_recupero_password TEXT;
