# ProAir Tecnosystemi per Home Assistant

Integrazione personalizzata per la gestione delle centraline di climatizzazione **ProAir Tecnosystemi** attraverso Home Assistant. Questa integrazione permette di controllare ogni zona della casa come un termostato indipendente.

## 🚀 Caratteristiche
* **Config Flow**: Configurazione semplice tramite interfaccia grafica (niente YAML).
* **Controllo Zone**: Visualizzazione temperatura attuale e impostazione temperatura target.
* **Accensione/Spegnimento**: Supporto completo per attivare o disattivare le singole zone.
* **Umidità**: Monitoraggio del livello di umidità per ogni zona (se supportato dal sensore).

## 🛠 Installazione

### Tramite HACS (Consigliato)
1. Assicurati che [HACS](https://hacs.xyz/) sia installato.
2. Apri HACS e vai in **Integrazioni**.
3. Clicca sui tre puntini in alto a destra e seleziona **Repository personalizzate**.
4. Incolla l'URL di questo repository e seleziona la categoria `Integrazione`.
5. Clicca su **Installa**.
6. Riavvia Home Assistant.

### Manuale
1. Scarica la cartella `proair_tecnosystemi` presente in `custom_components`.
2. Copiala nella cartella `custom_components` della tua installazione di Home Assistant.
3. Riavvia Home Assistant.

## ⚙️ Configurazione
Dopo il riavvio:
1. Vai in **Impostazioni** > **Dispositivi e Servizi**.
2. Clicca su **Aggiungi integrazione**.
3. Cerca **ProAir Tecnosystemi**.
4. Inserisci i dati richiesti:
   * **Username**: La tua email registrata nell'app ProAir.
   * **Password**: L'hash della tua password (Base64).
   * **Device ID**: L'UUID del tuo dispositivo registrato.

## 📝 Note Tecniche
L'integrazione comunica con i server Azure di Tecnosystemi utilizzando la crittografia AES-256-CBC. Per garantire la sincronizzazione dei comandi, viene utilizzato un sistema di token incrementali gestito automaticamente.

## 🤝 Supporto
Se riscontri problemi o hai suggerimenti, apri una *Issue* su questo repository.