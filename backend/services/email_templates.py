"""Template HTML e di testo per le comunicazioni email di Poliurea System.

Isola la logica di markup, escaping e formattazione email dai meccanismi di trasporto SMTP/Brevo.
"""
import html
from datetime import datetime, timezone
from typing import Any, Protocol


class PreventivoInfo(Protocol):
    nome: str
    email: Any
    telefono: str
    servizio: str
    messaggio: Any


def build_conferma_preventivo_email(
    dati: PreventivoInfo,
    id_preventivo: int,
    totale_foto: int,
) -> tuple[str, str, str]:
    """Genera (subject, html_content, text_content) per la conferma di ricezione preventivo al cliente."""
    subject = f"Poliurea System · Conferma richiesta preventivo #{id_preventivo}"
    dettagli_puliti = html.escape(str(dati.messaggio or "")).replace("\n", "<br>")
    foto_info = f"{totale_foto} foto allegata/e" if totale_foto > 0 else "Nessuna foto allegata"

    html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(subject)}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #09090b; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #f4f4f5;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #09090b; padding: 40px 15px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width: 620px; background-color: #18181b; border: 1px solid #27272a; border-radius: 16px; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.6);" cellspacing="0" cellpadding="0">
          
          <!-- Header Logo / Kicker -->
          <tr>
            <td style="padding: 32px 36px 24px; border-bottom: 1px solid #27272a; background: linear-gradient(180deg, #18181b 0%, #121214 100%);">
              <span style="font-size: 11px; font-weight: 800; letter-spacing: 0.12em; color: #38bdf8; text-transform: uppercase; display: block; margin-bottom: 6px;">Poliurea System · Impermeabilizzazioni</span>
              <h1 style="margin: 0; font-size: 22px; font-weight: 800; color: #ffffff;">Conferma ricezione preventivo #{id_preventivo}</h1>
            </td>
          </tr>

          <!-- Intro -->
          <tr>
            <td style="padding: 32px 36px 20px;">
              <p style="margin: 0 0 16px; font-size: 16px; line-height: 1.6; color: #ffffff;">
                Gentile <strong>{html.escape(dati.nome)}</strong>,
              </p>
              <p style="margin: 0 0 24px; font-size: 14px; line-height: 1.6; color: #a1a1aa;">
                Grazie per averci contattato. Abbiamo registrato con successo la tua richiesta di preventivo per l'intervento di impermeabilizzazione.
              </p>

              <!-- Box Riepilogo Richiesta -->
              <div style="background-color: #0c0c0e; border: 1px solid #27272a; border-radius: 12px; padding: 20px 24px; margin-bottom: 28px;">
                <p style="margin: 0 0 14px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #38bdf8;">
                  📋 Riepilogo della tua richiesta
                </p>
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="font-size: 14px; line-height: 1.6;">
                  <tr>
                    <td style="padding: 6px 0; color: #71717a; width: 40%; vertical-align: top;">Numero Pratica:</td>
                    <td style="padding: 6px 0; color: #ffffff; font-weight: 700;">#{id_preventivo}</td>
                  </tr>
                  <tr>
                    <td style="padding: 6px 0; color: #71717a; vertical-align: top;">Intervento richiesto:</td>
                    <td style="padding: 6px 0; color: #38bdf8; font-weight: 600;">{html.escape(dati.servizio)}</td>
                  </tr>
                  <tr>
                    <td style="padding: 6px 0; color: #71717a; vertical-align: top;">Recapito telefonico:</td>
                    <td style="padding: 6px 0; color: #ffffff;">{html.escape(dati.telefono)}</td>
                  </tr>
                  <tr>
                    <td style="padding: 6px 0; color: #71717a; vertical-align: top;">Email:</td>
                    <td style="padding: 6px 0; color: #ffffff;">{html.escape(str(dati.email))}</td>
                  </tr>
                  <tr>
                    <td style="padding: 6px 0; color: #71717a; vertical-align: top;">Foto allegate:</td>
                    <td style="padding: 6px 0; color: #a1a1aa;">{foto_info}</td>
                  </tr>
                  <tr>
                    <td style="padding: 6px 0; color: #71717a; vertical-align: top;">Dettagli forniti:</td>
                    <td style="padding: 6px 0; color: #d4d4d8; font-size: 13px;">{dettagli_puliti}</td>
                  </tr>
                </table>
              </div>

              <!-- Sezione Prossimi Passi (Timeline) -->
              <h2 style="margin: 0 0 16px; font-size: 15px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; color: #ffffff;">
                🚀 Come funziona adesso: I prossimi passi
              </h2>
              
              <div style="margin-bottom: 28px;">
                
                <!-- Step 1 -->
                <div style="display: flex; margin-bottom: 18px;">
                  <div style="min-width: 32px; height: 32px; border-radius: 50%; background-color: rgba(56, 189, 248, 0.15); border: 1px solid #38bdf8; color: #38bdf8; font-weight: 800; font-size: 14px; text-align: center; line-height: 32px; margin-right: 14px;">
                    1
                  </div>
                  <div>
                    <h3 style="margin: 0 0 4px; font-size: 14px; font-weight: 700; color: #ffffff;">Chiamata telefonica preliminare</h3>
                    <p style="margin: 0; font-size: 13px; line-height: 1.5; color: #a1a1aa;">
                      Un nostro tecnico specializzato ti contatterà al numero <strong>{html.escape(dati.telefono)}</strong> per approfondire lo stato dell'infiltrazione e le caratteristiche della superficie.
                    </p>
                  </div>
                </div>

                <!-- Step 2 -->
                <div style="display: flex; margin-bottom: 18px;">
                  <div style="min-width: 32px; height: 32px; border-radius: 50%; background-color: rgba(56, 189, 248, 0.15); border: 1px solid #38bdf8; color: #38bdf8; font-weight: 800; font-size: 14px; text-align: center; line-height: 32px; margin-right: 14px;">
                    2
                  </div>
                  <div>
                    <h3 style="margin: 0 0 4px; font-size: 14px; font-weight: 700; color: #ffffff;">Sopralluogo tecnico di persona</h3>
                    <p style="margin: 0; font-size: 13px; line-height: 1.5; color: #a1a1aa;">
                      Concorderemo una data per una visita diretta sul posto per effettuare i rilievi geometrici e verificare la compatibilità del supporto con il nostro ciclo di poliurea continua.
                    </p>
                  </div>
                </div>

                <!-- Step 3 -->
                <div style="display: flex;">
                  <div style="min-width: 32px; height: 32px; border-radius: 50%; background-color: rgba(56, 189, 248, 0.15); border: 1px solid #38bdf8; color: #38bdf8; font-weight: 800; font-size: 14px; text-align: center; line-height: 32px; margin-right: 14px;">
                    3
                  </div>
                  <div>
                    <h3 style="margin: 0 0 4px; font-size: 14px; font-weight: 700; color: #ffffff;">Invio preventivo e credenziali Area Clienti</h3>
                    <p style="margin: 0; font-size: 13px; line-height: 1.5; color: #a1a1aa;">
                      A seguito del sopralluogo, riceverai la proposta economica dettagliata e ti invieremo le <strong>credenziali personali di accesso all'Area Clienti</strong> riservata per seguire l'avanzamento dei lavori e i documenti tecnici.
                    </p>
                  </div>
                </div>

              </div>

              <!-- Box Supporto Urgenze -->
              <div style="background-color: #121214; border: 1px solid #27272a; border-radius: 10px; padding: 16px 20px; text-align: center;">
                <p style="margin: 0 0 6px; font-size: 13px; color: #d4d4d8;">
                  Hai un'infiltrazione attiva urgente o vuoi aggiungere dettagli?
                </p>
                <p style="margin: 0; font-size: 14px; font-weight: 700; color: #38bdf8;">
                  Rispondi a questa email o chiamaci al <a href="tel:+393282343190" style="color: #38bdf8; text-decoration: none;">+39 328 234 3190</a>
                </p>
              </div>

            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 24px 36px; background-color: #0c0c0e; border-top: 1px solid #27272a; text-align: center;">
              <p style="margin: 0 0 6px; font-size: 12px; font-weight: 700; color: #d4d4d8;">Poliurea System · Impermeabilizzazioni Continue ad Alta Pressione</p>
              <p style="margin: 0; font-size: 11px; color: #71717a;">Genova / Liguria e Nord Italia · www.poliureasystem.it · info@poliureasystem.it</p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    text_content = f"""POLIUREA SYSTEM - CONFERMA RICEZIONE RICHIESTA #{id_preventivo}

Gentile {dati.nome},
abbiamo ricevuto con successo la tua richiesta di preventivo.

RIEPILOGO PRATICA:
- Pratica: #{id_preventivo}
- Intervento: {dati.servizio}
- Recapito telefonico: {dati.telefono}
- Email: {dati.email}
- Foto allegate: {foto_info}
- Dettagli:
{dati.messaggio or ''}

I PROSSIMI PASSI:
1. Chiamata telefonica preliminare: un nostro tecnico ti contatterà al numero {dati.telefono} per approfondire le specifiche tecniche.
2. Sopralluogo e visita di persona: fisseremo una visita di persona in cantiere per le misurazioni e la valutazione tecnica del supporto.
3. Invio preventivo e credenziali Area Clienti: se tutto va bene a seguito del sopralluogo, ti invieremo il preventivo dettagliato e le credenziali di accesso alla tua Area Clienti via email.

Per qualsiasi necessità puoi scriverci a info@poliureasystem.it.

Poliurea System
info@poliureasystem.it - www.poliureasystem.it"""

    return subject, html_content, text_content


def build_credenziali_cliente_email(
    nome: str,
    email: str,
    password_temporanea: str,
) -> tuple[str, str, str]:
    """Genera (subject, html_content, text_content) con le credenziali per il primo accesso."""
    subject = "Poliurea System · Le tue credenziali di accesso all'Area Clienti"

    html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(subject)}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #09090b; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #f4f4f5;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #09090b; padding: 40px 15px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width: 600px; background-color: #18181b; border: 1px solid #27272a; border-radius: 16px; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.6);" cellspacing="0" cellpadding="0">
          
          <!-- Header -->
          <tr>
            <td style="padding: 32px 36px 24px; border-bottom: 1px solid #27272a; background: linear-gradient(180deg, #18181b 0%, #121214 100%);">
              <span style="font-size: 11px; font-weight: 800; letter-spacing: 0.12em; color: #38bdf8; text-transform: uppercase; display: block; margin-bottom: 6px;">Poliurea System · Area Riservata</span>
              <h1 style="margin: 0; font-size: 22px; font-weight: 800; color: #ffffff;">Le tue credenziali di accesso</h1>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding: 32px 36px 24px;">
              <p style="margin: 0 0 16px; font-size: 16px; line-height: 1.6; color: #ffffff;">
                Gentile <strong>{html.escape(nome)}</strong>,
              </p>
              <p style="margin: 0 0 24px; font-size: 14px; line-height: 1.6; color: #a1a1aa;">
                A seguito della richiesta di preventivo e del nostro contatto, abbiamo attivato il tuo account personale per l'accesso all'<strong>Area Clienti</strong> di Poliurea System.
              </p>

              <!-- Box Credenziali -->
              <div style="background-color: #0c0c0e; border: 1px solid #38bdf8; border-radius: 12px; padding: 22px; margin-bottom: 24px;">
                <p style="margin: 0 0 16px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #38bdf8;">
                  🔑 Le tue credenziali di accesso
                </p>
                <div style="margin-bottom: 14px;">
                  <span style="display: block; font-size: 11px; color: #71717a; text-transform: uppercase; font-weight: 600; margin-bottom: 4px;">Username (Email):</span>
                  <span style="display: block; font-size: 15px; font-weight: 700; color: #ffffff; font-family: monospace;">{html.escape(email)}</span>
                </div>
                <div>
                  <span style="display: block; font-size: 11px; color: #71717a; text-transform: uppercase; font-weight: 600; margin-bottom: 4px;">Password temporanea:</span>
                  <span style="display: inline-block; background-color: #18181b; border: 1px solid #3f3f46; border-radius: 6px; padding: 6px 12px; font-size: 15px; font-weight: 700; color: #38bdf8; font-family: monospace;">{html.escape(password_temporanea)}</span>
                </div>
              </div>

              <!-- Avviso Cambio Password al primo accesso -->
              <div style="background-color: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 10px; padding: 14px 18px; margin-bottom: 26px;">
                <p style="margin: 0; font-size: 13px; color: #fcd34d; line-height: 1.5;">
                  🔒 <strong>Primo accesso obbligatorio:</strong> Per garantire la massima sicurezza del tuo account, al tuo primo accesso ti verrà richiesto di sostituire questa password temporanea con una nuova password sicura a tua scelta.
                </p>
              </div>

              <!-- Bottone CTA -->
              <div style="text-align: center; margin: 30px 0 20px;">
                <a href="https://www.poliureasystem.it/area-clienti" style="display: inline-block; background: #0284c7; color: #ffffff; font-size: 14px; font-weight: 700; text-decoration: none; padding: 14px 32px; border-radius: 10px; box-shadow: 0 4px 16px rgba(2, 132, 199, 0.4);">
                  Accedi all'Area Clienti →
                </a>
              </div>
              <p style="text-align: center; margin: 0; font-size: 12px; color: #71717a;">
                Oppure copia questo link nel browser: <a href="https://www.poliureasystem.it/area-clienti" style="color: #38bdf8; text-decoration: none;">https://www.poliureasystem.it/area-clienti</a>
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 24px 36px; background-color: #0c0c0e; border-top: 1px solid #27272a; text-align: center;">
              <p style="margin: 0 0 6px; font-size: 12px; font-weight: 700; color: #d4d4d8;">Poliurea System · Impermeabilizzazioni Continue Pure ad Alta Pressione</p>
              <p style="margin: 0; font-size: 11px; color: #71717a;">Email: info@poliureasystem.it · Web: www.poliureasystem.it</p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    text_content = f"""POLIUREA SYSTEM - Le tue credenziali di accesso all'Area Clienti

Gentile {nome},
abbiamo attivato il tuo account personale per l'accesso all'Area Clienti di Poliurea System.

LE TUE CREDENZIALI:
- Username (Email): {email}
- Password temporanea: {password_temporanea}

Link di accesso: https://www.poliureasystem.it/area-clienti

IMPORTANTE:
Al tuo primo accesso ti verrà richiesto obbligatoriamente di sostituire questa password temporanea con una nuova password sicura a tua scelta.

Poliurea System
info@poliureasystem.it - www.poliureasystem.it"""

    return subject, html_content, text_content


def build_recupero_password_email(
    nome: str,
    email: str,
    password_temporanea: str,
) -> tuple[str, str, str]:
    """Genera (subject, html_content, text_content) per il recupero password dimenticata."""
    subject = "Poliurea System · Nuova password temporanea per l'Area Clienti"
    current_year = datetime.now(timezone.utc).year

    html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(subject)}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #09090b; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #f4f4f5;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #09090b; padding: 40px 15px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width: 600px; background-color: #18181b; border: 1px solid #27272a; border-radius: 16px; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.6);" cellspacing="0" cellpadding="0">
          
          <!-- Header -->
          <tr>
            <td style="padding: 32px 36px 24px; border-bottom: 1px solid #27272a; background: linear-gradient(180deg, #18181b 0%, #121214 100%);">
              <span style="font-size: 11px; font-weight: 800; letter-spacing: 0.12em; color: #38bdf8; text-transform: uppercase; display: block; margin-bottom: 6px;">Poliurea System · Recupero Password</span>
              <h1 style="margin: 0; font-size: 22px; font-weight: 800; color: #ffffff;">Nuova password provvisoria</h1>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding: 32px 36px 24px;">
              <p style="margin: 0 0 16px; font-size: 16px; line-height: 1.6; color: #ffffff;">
                Gentile <strong>{html.escape(nome)}</strong>,
              </p>
              <p style="margin: 0 0 24px; font-size: 14px; line-height: 1.6; color: #a1a1aa;">
                Abbiamo ricevuto la tua richiesta di recupero credenziali per l'accesso all'<strong>Area Clienti</strong> di Poliurea System. Ecco la tua nuova password provvisoria generata dal nostro sistema:
              </p>

              <!-- Box Credenziali -->
              <div style="background-color: #0c0c0e; border: 1px solid #38bdf8; border-radius: 12px; padding: 22px; margin-bottom: 24px;">
                <p style="margin: 0 0 16px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #38bdf8;">
                  🔑 Credenziali di accesso provvisorie
                </p>
                <div style="margin-bottom: 14px;">
                  <span style="display: block; font-size: 11px; color: #71717a; text-transform: uppercase; font-weight: 600; margin-bottom: 4px;">Username (Email):</span>
                  <span style="display: block; font-size: 15px; font-weight: 700; color: #ffffff; font-family: monospace;">{html.escape(email)}</span>
                </div>
                <div>
                  <span style="display: block; font-size: 11px; color: #71717a; text-transform: uppercase; font-weight: 600; margin-bottom: 4px;">Nuova password provvisoria:</span>
                  <span style="display: inline-block; background-color: #18181b; border: 1px solid #3f3f46; border-radius: 6px; padding: 6px 12px; font-size: 15px; font-weight: 700; color: #38bdf8; font-family: monospace;">{html.escape(password_temporanea)}</span>
                </div>
              </div>

              <!-- Avviso Cambio Password al primo accesso -->
              <div style="background-color: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 10px; padding: 14px 18px; margin-bottom: 26px;">
                <p style="margin: 0; font-size: 13px; color: #fcd34d; line-height: 1.5;">
                  🔒 <strong>Primo accesso obbligatorio:</strong> Per motivi di sicurezza, quando effettuerai l'accesso con questa password provvisoria ti verrà richiesto obbligatoriamente di impostare una nuova password definitiva personalizzata e sicura.
                </p>
              </div>

              <!-- Bottone CTA -->
              <div style="text-align: center; margin: 30px 0 20px;">
                <a href="https://www.poliureasystem.it/area-clienti" style="display: inline-block; background: #0284c7; color: #ffffff; font-size: 14px; font-weight: 700; text-decoration: none; padding: 14px 32px; border-radius: 10px; box-shadow: 0 4px 16px rgba(2, 132, 199, 0.4);">
                  Accedi all'Area Clienti →
                </a>
              </div>

              <p style="margin: 24px 0 0; font-size: 12px; color: #71717a; line-height: 1.5; text-align: center;">
                Se non hai effettuato tu questa richiesta, contatta il nostro supporto tecnico a <a href="mailto:info@poliureasystem.it" style="color: #38bdf8; text-decoration: none;">info@poliureasystem.it</a>.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 20px 36px; border-top: 1px solid #27272a; text-align: center; background-color: #121214;">
              <p style="margin: 0; font-size: 12px; color: #71717a;">
                © {current_year} Poliurea System · Genova / Liguria e Regioni Limitrofe · Tel. +39 328 234 3190
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    text_content = f"""Poliurea System · Nuova password provvisoria per l'Area Clienti

Gentile {nome},
Abbiamo ricevuto la tua richiesta di recupero credenziali per l'Area Clienti.

Ecco la tua nuova password provvisoria:
Username (Email): {email}
Password temporanea: {password_temporanea}

IMPORTANTE:
Al tuo prossimo accesso con questa password provvisoria, ti verrà richiesto obbligatoriamente di creare una nuova password definitiva a tua scelta.

Accedi qui: https://www.poliureasystem.it/area-clienti

Poliurea System - info@poliureasystem.it - Tel. +39 328 234 3190
"""

    return subject, html_content, text_content


def build_chiarimenti_preventivo_email(
    nome: str,
    preventivo_id: int,
    servizio: str,
    messaggio_chiarimenti: str,
) -> tuple[str, str, str]:
    """Genera (subject, html_content, text_content) per richiesta chiarimenti o note su un preventivo."""
    subject = f"Poliurea System · Richiesta chiarimenti per il tuo preventivo #{preventivo_id}"
    chiarimenti_puliti = html.escape(messaggio_chiarimenti or "").replace("\n", "<br>")

    html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(subject)}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #09090b; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #f4f4f5;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #09090b; padding: 40px 15px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width: 600px; background-color: #18181b; border: 1px solid #27272a; border-radius: 16px; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.6);" cellspacing="0" cellpadding="0">
          
          <!-- Header -->
          <tr>
            <td style="padding: 32px 36px 24px; border-bottom: 1px solid #27272a; background: linear-gradient(180deg, #18181b 0%, #121214 100%);">
              <span style="font-size: 11px; font-weight: 800; letter-spacing: 0.12em; color: #38bdf8; text-transform: uppercase; display: block; margin-bottom: 6px;">Poliurea System · Pratica #{preventivo_id}</span>
              <h1 style="margin: 0; font-size: 22px; font-weight: 800; color: #ffffff;">Richiesta informazioni e chiarimenti</h1>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding: 32px 36px 24px;">
              <p style="margin: 0 0 16px; font-size: 16px; line-height: 1.6; color: #ffffff;">
                Gentile <strong>{html.escape(nome)}</strong>,
              </p>
              <p style="margin: 0 0 22px; font-size: 14px; line-height: 1.6; color: #a1a1aa;">
                In merito alla tua richiesta di preventivo <strong>#{preventivo_id}</strong> ({html.escape(servizio or 'Intervento')}), il nostro staff tecnico ha inserito la seguente richiesta di chiarimenti o documentazione integrativa:
              </p>

              <!-- Box Chiarimenti -->
              <div style="background-color: #0c0c0e; border-left: 4px solid #38bdf8; border-top: 1px solid #27272a; border-right: 1px solid #27272a; border-bottom: 1px solid #27272a; border-radius: 10px; padding: 20px 22px; margin-bottom: 24px;">
                <p style="margin: 0 0 10px; font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; color: #38bdf8;">
                  💬 Indicazioni dal nostro ufficio tecnico:
                </p>
                <div style="font-size: 14px; line-height: 1.6; color: #f4f4f5;">
                  {chiarimenti_puliti}
                </div>
              </div>

              <p style="margin: 0 0 24px; font-size: 14px; line-height: 1.6; color: #a1a1aa;">
                Puoi consultare questo aggiornamento anche direttamente all'interno della tua <strong>Area Clienti</strong> riservata, oppure puoi rispondere a questa email inviando i chiarimenti o le foto richieste.
              </p>

              <!-- Bottone CTA -->
              <div style="text-align: center; margin: 28px 0 20px;">
                <a href="https://www.poliureasystem.it/area-clienti" style="display: inline-block; background: #0284c7; color: #ffffff; font-size: 14px; font-weight: 700; text-decoration: none; padding: 14px 32px; border-radius: 10px; box-shadow: 0 4px 16px rgba(2, 132, 199, 0.4);">
                  Accedi all'Area Clienti →
                </a>
              </div>
              <p style="text-align: center; margin: 0; font-size: 12px; color: #71717a;">
                Oppure copia questo link nel browser: <a href="https://www.poliureasystem.it/area-clienti" style="color: #38bdf8; text-decoration: none;">https://www.poliureasystem.it/area-clienti</a>
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 24px 36px; background-color: #0c0c0e; border-top: 1px solid #27272a; text-align: center;">
              <p style="margin: 0 0 6px; font-size: 12px; font-weight: 700; color: #d4d4d8;">Poliurea System · Impermeabilizzazioni Continue Pure ad Alta Pressione</p>
              <p style="margin: 0; font-size: 11px; color: #71717a;">Email: info@poliureasystem.it · Web: www.poliureasystem.it</p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    text_content = f"""POLIUREA SYSTEM - Richiesta chiarimenti per preventivo #{preventivo_id}

Gentile {nome},
in merito alla tua richiesta di preventivo #{preventivo_id} ({servizio or 'Intervento'}), il nostro ufficio tecnico ti richiede le seguenti informazioni:

--------------------------------------------------
{messaggio_chiarimenti}
--------------------------------------------------

Puoi verificare la tua pratica nella tua Area Clienti:
https://www.poliureasystem.it/area-clienti

Oppure puoi rispondere direttamente a questa email con le informazioni o le foto richieste.

Poliurea System
info@poliureasystem.it - www.poliureasystem.it"""

    return subject, html_content, text_content
