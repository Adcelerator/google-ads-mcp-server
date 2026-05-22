# Google Ads MCP Server — Contesto di Progetto

**Repository:** `Adcelerator/google-ads-mcp-server`  
**Branch di sviluppo:** `claude/customize-google-ads-mcp-koS8g`  
**Commit principale:** `c13f58b` — *feat: comprehensive Google Ads MCP server with multi-account support*  
**Data:** 2026-05-22  

---

## Obiettivo finale

Costruire un **MCP server Python completamente personalizzato** per Google Ads, pensato per un'agenzia (o advertiser avanzato) che ha bisogno di:

1. **Gestire qualsiasi tipo di campagna Google Ads** — Search, Display, Shopping, Video, Performance Max, Discovery, App — con strumenti dedicati per ogni fase del ciclo di vita (creazione, ottimizzazione, pausa, rimozione).
2. **Targeting multi-paese e multi-lingua** — selezionare qualsiasi Paese o città e qualsiasi lingua tramite tool dedicati con lookup live sull'API Google, senza conoscere i codici interni.
3. **Login multi-account semplificato** — aggiungere, elencare e commutare tra più account Google Ads con un singolo comando, senza dover riconfigurare il server.
4. **Integrazione nativa con Claude** (Claude Desktop, Claude Code) via Model Context Protocol, per gestire Google Ads in linguaggio naturale senza aprire l'interfaccia web.

---

## Punto di partenza

Il progetto deriva dal server open source **GoMarble AI** (`gomarble-ai/google-ads-mcp-server`), che esponeva solo 3 tool:

| Tool originale | Funzione |
|---|---|
| `list_accounts` | Elencava account accessibili |
| `run_gaql` | Eseguiva query GAQL raw |
| `run_keyword_planner` | Generava idee di keyword (solo USA + inglese) |

Il sistema di autenticazione era a **singolo account**, basato su un file `.env` e un unico token OAuth.

---

## Cosa è stato sviluppato

### Architettura del progetto (post-customizzazione)

```
google-ads-mcp-server/
│
├── server.py                  # Entry point MCP — registra tutti i moduli
│
├── oauth/
│   ├── google_auth.py         # Auth originale (single-account, legacy)
│   └── multi_account.py       # NUOVO — MultiAccountManager
│
├── tools/
│   ├── utils.py               # Helper condivisi (auth, HTTP, mutate, GAQL)
│   ├── campaigns.py           # Gestione campagne + budget
│   ├── ad_groups.py           # Gestione ad group
│   ├── ads.py                 # Creazione e gestione annunci
│   ├── keywords.py            # Gestione keyword
│   ├── targeting.py           # Geo e language targeting
│   ├── reporting.py           # Report di performance
│   └── extensions.py          # Estensioni (sitelink, callout, ecc.)
│
└── data/
    ├── languages.py           # 50+ costanti lingua con ID Google Ads
    └── geo_targets.py         # 55+ Paesi con geo target ID verificati
```

---

## Endpoint / Tool MCP disponibili

### Multi-Account Management

| Tool | Descrizione |
|---|---|
| `add_google_account` | Aggiunge un account Google via OAuth browser flow. Salva il token in `tokens/<label>_token.json`. Da eseguire una volta per login Google. |
| `list_google_accounts` | Elenca tutti gli account configurati con stato token e account attivo. |
| `set_active_google_account` | Imposta l'account attivo usato di default da tutti i tool. |
| `remove_google_account` | Rimuove un account e cancella il token salvato. |

> Ogni tool accetta il parametro opzionale `account_label` per puntare a un account specifico senza cambiare quello attivo.

---

### Campagne

| Tool | Descrizione |
|---|---|
| `create_campaign_budget` | Crea un budget campagna (importo in micros, STANDARD o ACCELERATED). |
| `update_campaign_budget` | Modifica l'importo di un budget esistente. |
| `create_campaign` | Crea una campagna di qualsiasi tipo (SEARCH, DISPLAY, SHOPPING, VIDEO, PERFORMANCE_MAX, DISCOVERY, APP). Parte sempre in PAUSED. |
| `update_campaign` | Aggiorna nome, status o data di fine campagna. |
| `pause_campaign` | Mette in pausa una campagna. |
| `enable_campaign` | Attiva una campagna. |
| `remove_campaign` | Elimina permanentemente una campagna. |
| `list_campaigns` | Elenca campagne con filtri per status e con budget giornaliero. |
| `get_campaign_details` | Dettagli completi di una singola campagna (bidding, budget, date). |

**Tipi di campagna supportati:** `SEARCH` · `DISPLAY` · `SHOPPING` · `VIDEO` · `PERFORMANCE_MAX` · `DISCOVERY` · `APP` · `LOCAL_SERVICES`

**Strategie di bidding supportate:** `MAXIMIZE_CONVERSIONS` · `MAXIMIZE_CONVERSION_VALUE` · `TARGET_CPA` · `TARGET_ROAS` · `MANUAL_CPC` · `MAXIMIZE_CLICKS` · `TARGET_IMPRESSION_SHARE`

---

### Ad Group

| Tool | Descrizione |
|---|---|
| `create_ad_group` | Crea un ad group in una campagna (con tipo e bid opzionale). |
| `update_ad_group` | Aggiorna nome, status o bid default. |
| `pause_ad_group` | Mette in pausa un ad group. |
| `enable_ad_group` | Attiva un ad group. |
| `remove_ad_group` | Elimina un ad group. |
| `list_ad_groups` | Elenca ad group con filtri per campagna e status. |

---

### Annunci (Ads)

| Tool | Descrizione |
|---|---|
| `create_responsive_search_ad` | Crea un RSA con 3–15 headline e 2–4 description. Google testa le combinazioni automaticamente. |
| `create_responsive_display_ad` | Crea un RDA per campagne Display con headline, long headline, description, business name, immagini. |
| `create_call_only_ad` | Crea un annuncio click-to-call per mobile. |
| `update_ad_status` | Cambia status di un annuncio (ENABLED / PAUSED / REMOVED). |
| `list_ads` | Elenca annunci con filtri per campagna, ad group e status. |

---

### Keyword

| Tool | Descrizione |
|---|---|
| `add_keywords` | Aggiunge keyword a un ad group con match type (BROAD / PHRASE / EXACT) e bid opzionale. |
| `add_negative_keywords` | Aggiunge keyword negative a livello ad group. |
| `add_campaign_negative_keywords` | Aggiunge keyword negative a livello campagna. |
| `remove_keyword` | Rimuove una keyword per criterion ID. |
| `update_keyword_bid` | Aggiorna il bid CPC di una keyword specifica. |
| `list_keywords` | Elenca keyword con filtri, incluse le negative. |

---

### Targeting Geo & Lingua

| Tool | Descrizione |
|---|---|
| `search_geo_targets` | Cerca qualsiasi Paese, regione o città tramite API live. Restituisce l'ID numerico da usare nel targeting. |
| `find_country_id` | Lookup rapido da tabella integrata (55+ Paesi) per nome, codice ISO o ID. |
| `get_language_constants` | Elenca le 50+ lingue disponibili con ID. Accetta filtro per nome o codice (es. "italian", "it", "1004"). |
| `set_campaign_geo_targeting` | Imposta targeting geografico su una campagna (positivo o negativo). Accetta lista di ID numerici. |
| `set_campaign_language_targeting` | Imposta le lingue target su una campagna. |
| `list_campaign_criteria` | Elenca tutti i criteri di targeting (geo + lingua) di una campagna. |
| `remove_campaign_criterion` | Rimuove un criterio di targeting da una campagna. |

**Paesi integrati nella tabella locale (esempi):**

| Area | Paesi |
|---|---|
| Europa | Italia (20854), Germania (2276), Francia (2250), Spagna (2724), UK (2826), Olanda, Belgio, Svizzera, Austria, Polonia, Portogallo, Svezia, Norvegia, Danimarca, Finlandia, Irlanda, Grecia, Russia, Ucraina, ... |
| Americhe | USA (2840), Canada (2124), Messico (2484), Brasile (2076), Argentina, Colombia, Cile, Perù |
| Asia-Pacific | Giappone (2392), Cina (2156), India (2356), Corea del Sud, Australia (2036), Nuova Zelanda, Singapore, Hong Kong, Taiwan, Indonesia, Malaysia, Thailandia, Vietnam, Filippine, ... |
| Medio Oriente & Africa | Arabia Saudita, UAE, Israele, Turchia, Egitto, Sudafrica, Nigeria, Kenya, Ghana |

**Lingue integrati (esempi):** Italiano (1004), Inglese (1000), Tedesco (1001), Francese (1002), Spagnolo (1003), Portoghese (1014), Giapponese (1005), Cinese Semplificato (1017), Arabo (1019), Russo (1031), e altre 40+.

---

### Report di Performance

| Tool | Descrizione |
|---|---|
| `get_campaign_performance` | Metriche per campagna: impressioni, click, costo, conversioni, CTR, CPC medio, ROAS, impression share. |
| `get_ad_group_performance` | Metriche per ad group. |
| `get_keyword_performance` | Metriche per keyword con quality score e impression share. |
| `get_search_terms_report` | Termini di ricerca reali (cosa hanno digitato gli utenti). |
| `get_geographic_performance` | Performance per Paese/area geografica. |
| `get_device_performance` | Performance per dispositivo (mobile, desktop, tablet). |
| `get_ad_performance` | Metriche per singolo annuncio. |

**Date range supportati:** `TODAY` · `YESTERDAY` · `LAST_7_DAYS` · `LAST_14_DAYS` · `LAST_30_DAYS` · `THIS_MONTH` · `LAST_MONTH` · `LAST_BUSINESS_WEEK` · oppure `BETWEEN 'YYYY-MM-DD' AND 'YYYY-MM-DD'`

---

### Estensioni (Assets)

| Tool | Descrizione |
|---|---|
| `create_sitelink` | Crea un sitelink (link aggiuntivo nell'annuncio) e lo collega a campagna o account. |
| `create_callout` | Crea uno o più callout (frasi brevi tipo "Spedizione gratuita"). |
| `create_call_extension` | Aggiunge un numero di telefono agli annunci per qualsiasi Paese. |
| `create_structured_snippet` | Crea un elenco strutturato (es. "Servizi: SEO, SEM, Social"). |
| `list_campaign_assets` | Elenca le estensioni collegate a una campagna. |
| `remove_campaign_asset` | Rimuove un'estensione da una campagna. |

---

### Tool Legacy / Power User

| Tool | Descrizione |
|---|---|
| `run_gaql` | Esegue qualsiasi query GAQL personalizzata. |
| `list_accounts` | Elenca tutti gli account accessibili inclusi sub-account MCC annidati. |
| `run_keyword_planner` | Genera idee keyword con volumi di ricerca. Ora accetta `language_id` e `geo_target_id` per qualsiasi Paese/lingua. |

---

### Risorsa MCP

| Risorsa | Contenuto |
|---|---|
| `gaql://reference` | Documentazione GAQL completa: struttura query, risorse, metriche, segmenti, esempi, errori comuni. |

---

## Variabili d'ambiente richieste

```bash
# .env
GOOGLE_ADS_DEVELOPER_TOKEN=il_tuo_developer_token   # Obbligatorio
GOOGLE_ADS_OAUTH_CONFIG_PATH=/path/client_secret.json  # Per auth legacy (facoltativo con multi-account)
```

---

## Flusso di autenticazione multi-account

```
Prima volta per ogni account Google:
  add_google_account(label="agenzia", credentials_path="/path/client_secret.json")
      └─> apre browser → OAuth Google → salva tokens/agenzia_token.json

Utilizzo successivo (automatico):
  qualsiasi tool → legge tokens/agenzia_token.json → refresh silenzioso se scaduto

Cambio account:
  set_active_google_account(label="cliente_abc")
  oppure: qualsiasi tool con account_label="cliente_abc"
```

---

## Stack tecnico

| Componente | Tecnologia |
|---|---|
| Framework MCP | FastMCP (`fastmcp>=0.8.0`) |
| Google Ads API | REST v19 (`https://googleads.googleapis.com/v19`) |
| Autenticazione | OAuth 2.0 via `google-auth-oauthlib` |
| HTTP client | `requests` |
| Configurazione | `python-dotenv` |
| Runtime | Python 3.10+ |
| Transport | STDIO (Claude Desktop) oppure HTTP streamable (`--http`) |

---

## Come avviare il server

```bash
# Modalità STDIO (Claude Desktop — avvio automatico)
python server.py

# Modalità HTTP (Claude Code, API, altri client MCP)
python server.py --http
# → http://127.0.0.1:8000/mcp
```

### Configurazione Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "google-ads": {
      "command": "/percorso/assoluto/.venv/bin/python",
      "args": ["/percorso/assoluto/google-ads-mcp-server/server.py"]
    }
  }
}
```
