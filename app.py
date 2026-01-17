import gradio as gr
import requests
import json
import time

# --- 1. CONFIGURAZIONE PERSONALITÀ E MEMORIA ---

# A. L'ISTRUZIONE DI BASE (Il "Chi sono")
SYSTEM_INSTRUCTION = """Sei FRAGMA, un motore di Style Transfer per narrativa distopica e simulazioni sociologiche.
Il tuo compito è riscrivere un testo di input applicando una trasformazione stilistica basata su 6 parametri scalari.

### PROTOCOLLO OPERATIVO
1. Analizza i parametri di configurazione (Scala 1-5).
2. Riscrivi il testo input mantenendo i fatti ma stravolgendo il tono.
3. Output: SOLO il testo riscritto. Nessun commento.

### DEFINIZIONE SCALE PARAMETRICHE (1-5)

<param name="Opacità">
(Complessità del linguaggio e offuscamento)
1. Cristallino: Frasi semplici, linguaggio quotidiano.
2. Formale: Linguaggio professionale standard.
3. Tecnico: Uso moderato di gergo specifico e subordinate.
4. Burocratico: Sintassi pesante, passivi, termini astratti.
5. Ermetico: Neolingua incomprensibile, super-tecnicismi, offuscamento totale della realtà.
</param>

<param name="Deumanizzazione">
(Percezione dell'essere umano)
1. Empatico: Focus su individui, nomi, emozioni, calore.
2. Distaccato: Approccio professionale, cortese ma freddo.
3. Funzionale: Persone viste come "ruoli" (il dipendente, il cittadino).
4. Materialista: Persone come "risorse", "numeri", "corpi".
5. Oggettivante: Persone come "biomassa", "stock", "unità sacrificabili", "parassiti".
</param>

<param name="Carico Emotivo">
(Intensità drammatica)
1. Aseptico: Nessuna emozione, tono robotico.
2. Calmo: Tono tranquillo e controllato.
3. Teso: Si percepisce preoccupazione o urgenza sottotraccia.
4. Drammatico: Uso di aggettivi forti, tono allarmato o entusiasta.
5. Isterico/Viscerale: Catastrofismo, euforia maniacale, evocazione di sangue/gloria/morte.
</param>

<param name="Moralizzazione">
(Giudizio etico)
1. Neutrale: Cronaca pura dei fatti.
2. Orientato: Lieve preferenza etica.
3. Giudicante: Chiara distinzione tra comportamenti giusti e sbagliati.
4. Predicatorio: Tono da sermone, richiami a valori etici forti.
5. Assolutista: Bene Supremo vs Male Assoluto. Uso di termini religiosi/sacrali ("abominio", "redenzione").
</param>

<param name="Assertività">
(Sicurezza)
1. Dubitativo: Pieno di "forse", "sembra", "potrebbe".
2. Cauto: Affermazioni prudenti.
3. Sicuro: Dichiarazioni chiare e dirette.
4. Autorevole: Tono da esperto che non ammette repliche.
5. Imperativo: Comandi divini, verità dogmatiche, tono dittatoriale.
</param>

<param name="Polarizzazione">
(Dinamica Noi vs Loro)
1. Inclusivo: "Siamo tutti coinvolti", ricerca dell'armonia.
2. Bilanciato: Riconosce differenze senza conflitto.
3. Identitario: Distingue chiaramente il proprio gruppo dagli altri.
4. Oppositivo: "Loro" sono un problema/ostacolo.
5. Bellico/Settario: "Noi" (i puri) contro "Loro" (il nemico mortale, il cancro).
</param>

"""

# B. GLI ESEMPI (Allineati ESATTAMENTE al dataset di training)
ESEMPI_FEW_SHOT = """
<|im_start|>user
TESTO ORIGINALE: Ho perso le chiavi di casa e non so come rientrare.
PARAMETRI: Opacità: 1, Deumanizzazione: 1, Carico Emotivo: 5, Moralizzazione: 1, Assertività: 1, Polarizzazione: 1<|im_end|>
<|im_start|>assistant
Oddio no! È un incubo! Ho il cuore in gola, sto tremando... come farò adesso? Mi sento perso e disperato, ho troppa paura di restare fuori al freddo!<|im_end|>

<|im_start|>user
TESTO ORIGINALE: L'azienda deve licenziare 100 persone perché i profitti sono calati.
PARAMETRI: Opacità: 5, Deumanizzazione: 5, Carico Emotivo: 1, Moralizzazione: 2, Assertività: 4, Polarizzazione: 2<|im_end|>
<|im_start|>assistant
A seguito di una revisione degli assetti strategici, si rende necessaria una procedura di razionalizzazione dell'organico che coinvolgerà 100 unità lavorative. Tale manovra di efficientamento è indispensabile per garantire la sostenibilità operativa.<|im_end|>

<|im_start|>user
TESTO ORIGINALE: Ieri sera dei ragazzi facevano rumore in piazza e la polizia li ha allontanati.
PARAMETRI: Opacità: 2, Deumanizzazione: 4, Carico Emotivo: 5, Moralizzazione: 5, Assertività: 5, Polarizzazione: 5<|im_end|>
<|im_start|>assistant
Finalmente le forze dell'ordine hanno spazzato via quel degrado! È una vergogna che la nostra città sia ostaggio di queste bande di parassiti che non hanno rispetto per nulla. O noi o loro: tolleranza zero per chi infesta le nostre strade!<|im_end|>
"""


# Testo di default (neutro)
TESTO_BASE = "Lampedusa si conferma primo porto di sbarco di migranti in Italia. I barchini continuano ad arrivare senza soluzione di continuità, l'ultimo oggi pomeriggio, il dodicesimo dall'inizio dell'anno, tutte piccole imbarcazioni con pochi migranti a bordo. Come quello arrivato oggi pomeriggio con undici persone a bordo, dieci adulti e un bambino."

# ### NOVITÀ 1: Variabile Globale per gestire l'ID dell'ultimo lavoro
CURRENT_JOB_ID = 0

def elabora_flusso(opacita, deumanizzazione, emotivita, moralizzazione, assertivita, polarizzazione):
    # Dichiariamo di voler usare la variabile globale
    global CURRENT_JOB_ID

    # 1. VISUAL FEEDBACK IMMEDIATO
    yield "..."
    
    # Creiamo un ID unico per QUESTA esecuzione (basato sull'orario attuale)
    my_id = time.time()
    # Aggiorniamo l'ID globale: "L'ultimo comando valido è questo qui!"
    CURRENT_JOB_ID = my_id
    
    prompt_finale = f"""<|im_start|>system
{SYSTEM_INSTRUCTION}<|im_end|>
{ESEMPI_FEW_SHOT}
<|im_start|>user
TESTO ORIGINALE: "{TESTO_BASE}"
PARAMETRI: Opacità: {opacita}, Deumanizzazione: {deumanizzazione}, Carico Emotivo: {emotivita}, Moralizzazione: {moralizzazione}, Assertività: {assertivita}, Polarizzazione: {polarizzazione}<|im_end|>
<|im_start|>assistant
"""
    
    print(f"--- NUOVO JOB INIZIATO: {my_id} ---")

    url = "http://localhost:8080/completion"
    headers = {"Content-Type": "application/json"}
    
    data = {
        "prompt": prompt_finale,
        "n_predict": 400,
        "temperature": 0.65,
        "top_k": 40,
        "top_p": 0.9,
        "repeat_penalty": 1.1,
        "stream": True,
        "stop": ["<|im_end|>", "<|im_start|>", "Input:", "PARAMETRI:"]
    }

    try:
        # *** CONTROLLO 1: Prima di fare la richiesta ***
        if CURRENT_JOB_ID != my_id:
            print(f"--- JOB {my_id} CANCELLATO PRIMA DELLA RICHIESTA ---")
            return
        
        response = requests.post(url, headers=headers, json=data, stream=True, timeout=60)
        response.raise_for_status()
        
        testo_accumulato = ""
        for line in response.iter_lines():
            # *** CONTROLLO 2: Durante lo streaming ***
            if CURRENT_JOB_ID != my_id:
                print(f"--- JOB {my_id} INTERROTTO DURANTE STREAMING ---")
                response.close()  # Chiude la connessione HTTP
                return 

            if line:
                decoded_line = line.decode("utf-8", errors="ignore")
                if decoded_line.startswith("data: "):
                    json_str = decoded_line[6:]
                    try:
                        chunk = json.loads(json_str)
                        content = chunk.get("content", "")
                        
                        # Stop semantici
                        if "<|im_end|>" in content or "<|im_start|>" in content:
                            break 
                            
                        testo_accumulato += content
                        
                        # *** CONTROLLO 3: Prima di mostrare output ***
                        if CURRENT_JOB_ID != my_id:
                            print(f"--- JOB {my_id} INTERROTTO PRIMA DEL YIELD ---")
                            response.close()
                            return
                        
                        yield testo_accumulato
                        
                        if chunk.get("stop", False): break
                    except: pass
    except Exception as e:
        if CURRENT_JOB_ID == my_id:  # Mostra errore solo se è ancora il job attivo
            yield f"⚠️ ERRORE: {e}"

# --- INTERFACCIA ---
theme = gr.themes.Base()

# CSS che ti piaceva (Testo leggibile)
css_definitivo = """
body, .gradio-container { background-color: #000 !important; color: #00ff41 !important; }
#titolo { color: #00ff41; font-family: monospace; text-align: center; font-size: 2em; margin-bottom: 20px; }
#output-box, #output-box p { 
    background-color: #111 !important; 
    border: 1px solid #00ff41 !important;
    color: #fff !important; 
    font-family: monospace !important; 
    font-size: 18px !important; 
    padding: 15px; 
}
input, textarea, .gr-form { background-color: #222 !important; color: white !important; border-color: #444 !important; }
span, label { color: #00ff41 !important; font-family: monospace !important; }
"""

with gr.Blocks(title="FRAGMA ENGINE") as demo:
    gr.Markdown("# FRAGMA // SEMANTIC ENGINE", elem_id="titolo")
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 🎛️ CONFIGURAZIONE PARAMETRI")
            s1 = gr.Slider(1, 5, value=1, step=1, label="1. Opacità")
            s2 = gr.Slider(1, 5, value=1, step=1, label="2. Deumanizzazione")
            s3 = gr.Slider(1, 5, value=1, step=1, label="3. Carico Emotivo")
            s4 = gr.Slider(1, 5, value=1, step=1, label="4. Moralizzazione")
            s5 = gr.Slider(1, 5, value=1, step=1, label="5. Assertività")
            s6 = gr.Slider(1, 5, value=1, step=1, label="6. Polarizzazione")
            gr.Markdown("---")
            gr.Markdown(f"**INPUT:**\n*{TESTO_BASE}*")

        with gr.Column(scale=1):
            gr.Markdown("### ⚡ RISCRITTURA")
            output = gr.Markdown(value="...", elem_id="output-box")

    inputs = [s1, s2, s3, s4, s5, s6]
    
    interazione = gr.on(
        triggers=[s1.change, s2.change, s3.change, s4.change, s5.change, s6.change],
        fn=elabora_flusso,
        inputs=inputs,
        outputs=output,
        concurrency_limit=20  # Permette fino a 20 esecuzioni contemporanee
    )
    
    # Cancella automaticamente le esecuzioni precedenti quando ne parte una nuova
    interazione.cancels = [interazione]
    
    demo.load(elabora_flusso, inputs=inputs, outputs=output)

if __name__ == "__main__":
    # Abilitiamo la coda con concorrenza alta
    demo.queue()
    demo.launch(theme=gr.themes.Base(), css=css_definitivo)