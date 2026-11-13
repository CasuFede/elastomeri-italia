# Backend su Cloudflare Workers

Il backend usa FastAPI tramite l'entrypoint ASGI dei Python Workers, D1 per i
dati relazionali e R2 per gli allegati e le immagini. Il Worker usa il binding
D1 `DB` e il binding R2 `UPLOADS`, definiti in `wrangler.jsonc`.

## Risorse Cloudflare già configurate

L'account Cloudflare contiene già il database D1 `preventivi-db` e il bucket
R2 `preventivi-uploads`. Il binding D1 e il relativo ID sono configurati in
`wrangler.jsonc`; lo schema è in `migrations/0001_initial.sql`.

I dati locali sono stati importati una volta: due preventivi, senza allegati,
lavori o clienti. Non rieseguire `migrate_local_data.py` sullo stesso database,
perché reinserirebbe i record.

Il Worker è pubblicato su
<https://elastomeri-italia-api.casufederico4.workers.dev>. I secrets
amministrativi e Telegram sono configurati su Cloudflare.

## Sviluppo e deploy

Servono Python 3.13 o successivo, Node.js e [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run pywrangler dev
```

Per lo sviluppo locale, crea `.dev.vars` in questa cartella (non versionare
questo file) con `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `TELEGRAM_BOT_TOKEN` e
`TELEGRAM_CHAT_ID`, uno per riga nel formato `NOME=valore`. In locale, Wrangler
usa il database D1 e il bucket R2 simulati.

La chat risponde senza servizi esterni, usando un archivio statico curato dal
documento `Manuale Tecnico sulla Poliurea.pdf`, tramite `/api/chat`. Quando il
manuale non contiene informazioni sufficienti, la chat lo dichiara invece di
inventare una risposta. Per aggiornare le informazioni, rivedi
`chat_knowledge.py` insieme al manuale.

Le richieste `/api/...` vengono riscritte alle route FastAPI corrispondenti.
Per pubblicare gli aggiornamenti:

```sh
uv run pywrangler deploy
```

Il frontend può continuare a chiamare, ad esempio, `/api/preventivo`, che viene
inoltrato all'endpoint FastAPI `/preventivo`. Configura il routing del dominio
Cloudflare affinché le richieste `/api/*` raggiungano questo Worker.

`backend/.env` è escluso da Git. Non aggiungere secrets al repository. Per
caricare un token Telegram aggiornato, dalla cartella `backend` esegui:

```sh
uv run pywrangler secret put TELEGRAM_BOT_TOKEN
```
