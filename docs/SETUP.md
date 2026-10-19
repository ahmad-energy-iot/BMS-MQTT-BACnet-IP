# Einrichtung und Betrieb

Diese Anleitung beschreibt die Einrichtung des MQTT–BACnet/IP-Laborprojekts auf einem Raspberry Pi.

Die Befehle orientieren sich am getesteten Aufbau mit dem Linux-Benutzer `ahmad`. Benutzername, Dateipfade, Netzwerkadresse und Gerätekennungen müssen für eine andere Umgebung angepasst werden.

> Die Anleitung wurde anhand des bestehenden Laboraufbaus erstellt. Ein vollständiger Neustart des Raspberry Pi wurde erfolgreich getestet. Eine vollständige Neuinstallation auf einem leeren System wurde noch nicht durchgeführt.

## 1. Voraussetzungen

- Raspberry Pi mit Linux, Python 3, pip und venv.
- Node-RED und Mosquitto.
- ESP32 mit DHT11 und der Firmware des Ausgangsprojekts.
- Zugriff auf den Raspberry Pi über SSH.
- MQTT-Benutzer mit Berechtigung zum Lesen der Sensortopics.
- Schreibberechtigung des Datenloggers im Datenverzeichnis.
- Zugriff des Node-RED-Prozesses auf Datenbank, Exportverzeichnis und Python-Umgebung.

Hardwareanschlüsse und ESP32-Firmware sind im Ausgangsprojekt dokumentiert:

[BMS-ESP32-MQTT-HVAC](https://github.com/ahmad-energy-iot/BMS-ESP32-MQTT-HVAC)

Die Temperatur- und Luftfeuchtewerte müssen als numerische MQTT-Payloads auf diesen Topics ankommen:

```text
bms/room1/temperature
bms/room1/humidity
```

Das Gateway erwartet keine JSON-Payloads.

Die im Projekt verwendeten MQTT-Zugangsdaten müssen im Broker separat eingerichtet sein. Das Erstellen der unten beschriebenen JSON-Datei legt keinen Mosquitto-Benutzer an.

## 2. Repository herunterladen

Die folgenden Befehle werden innerhalb der SSH-Sitzung auf dem Raspberry Pi ausgeführt:

```bash
cd ~
git clone https://github.com/ahmad-energy-iot/BMS-MQTT-BACnet-IP.git
```

Bei einer bestehenden Installation nicht erneut alle Dateien überschreiben. Zunächst laufende Dienste, lokale Anpassungen und vorhandene Daten sichern.

## 3. Laufzeitverzeichnisse vorbereiten

Die Verzeichnisnamen im Repository unterscheiden sich von den Laufzeitpfaden des Laboraufbaus:

| Repository | Laufzeitverzeichnis |
|---|---|
| `bacnet/` | `/home/ahmad/bms-bacnet/` |
| `data-logger/` | `/home/ahmad/bms-data-logger/` |

Für eine neue Einrichtung:

```bash
mkdir -p ~/bms-bacnet
mkdir -p ~/bms-data-logger

cp ~/BMS-MQTT-BACnet-IP/bacnet/mqtt_bacnet_service.py ~/bms-bacnet/
cp ~/BMS-MQTT-BACnet-IP/bacnet/requirements.txt ~/bms-bacnet/

cp ~/BMS-MQTT-BACnet-IP/data-logger/*.py ~/bms-data-logger/
cp ~/BMS-MQTT-BACnet-IP/data-logger/requirements.txt ~/bms-data-logger/
```

Die im Flow hinterlegten Datenbank- und Exportpfade beziehen sich auf diese Laufzeitverzeichnisse.

## 4. Python-Umgebungen einrichten

### BACnet-Gateway

```bash
python3 -m venv ~/bms-bacnet/.venv

~/bms-bacnet/.venv/bin/python -m pip install \
    -r ~/bms-bacnet/requirements.txt
```

### Datenlogger

```bash
python3 -m venv ~/bms-data-logger/.venv

~/bms-data-logger/.venv/bin/python -m pip install \
    -r ~/bms-data-logger/requirements.txt
```

SQLite, CSV-Verarbeitung und die übrigen verwendeten Standardmodule gehören zur Python-Standardbibliothek. Die SQLite-Unterstützung der installierten Python-Version muss verfügbar sein.

## 5. MQTT-Zugangsdaten lokal konfigurieren

Gateway und Datenlogger lesen dieselbe lokale Konfigurationsdatei:

```text
~/.config/bms-logger/mqtt.json
```

Für eine neue Einrichtung:

```bash
mkdir -p ~/.config/bms-logger
chmod 700 ~/.config/bms-logger
nano ~/.config/bms-logger/mqtt.json
```

Inhalt mit den eigenen, bereits im Broker eingerichteten Zugangsdaten:

```json
{
  "username": "YOUR_MQTT_USERNAME",
  "password": "YOUR_MQTT_PASSWORD"
}
```

Datei speichern und Zugriffsrechte begrenzen:

```bash
chmod 600 ~/.config/bms-logger/mqtt.json
```

Die Datei muss für den Benutzer lesbar sein, unter dem die Python-Dienste laufen.

**Die ausgefüllte Datei nicht veröffentlichen.** Das Repository enthält unter `bacnet/mqtt.example.json` ausschließlich eine Vorlage.

Beide Python-Anwendungen verbinden sich im aktuellen Code mit:

```text
127.0.0.1:1883
```

Falls der Broker auf einem anderen Rechner läuft, muss die Brokerverbindung in beiden Anwendungen angepasst werden.

## 6. SQLite initialisieren

Vor dem ersten Start des Datenloggers:

```bash
~/bms-data-logger/.venv/bin/python \
    ~/bms-data-logger/database_init.py
```

Dadurch werden `bms.db` und die Tabelle `readings` vorbereitet.

`CREATE TABLE IF NOT EXISTS` löscht keine vorhandenen Datensätze.

Zum manuellen Prüfen gespeicherter Messungen:

```bash
~/bms-data-logger/.venv/bin/python \
    ~/bms-data-logger/show_readings.py
```

Zum manuellen CSV-Export:

```bash
~/bms-data-logger/.venv/bin/python \
    ~/bms-data-logger/export_readings.py
```

Die Exportdateien entstehen im Unterverzeichnis:

```text
~/bms-data-logger/exports/
```

Die 72-Stunden-Aufbewahrung gilt für Datensätze in SQLite. Bereits erzeugte CSV-Dateien werden nicht automatisch gelöscht und müssen bei Bedarf separat entfernt werden.

## 7. Netzwerk und BACnet-Kennungen anpassen

Im getesteten Labor wurde verwendet:

| Einstellung | Wert |
|---|---|
| Raspberry-Pi-Adresse | `192.168.178.38/24` |
| Broadcast-Adresse | `192.168.178.255` |
| BACnet Device Instance | `123001` |
| BACnet Device Name | `BMS-Room1-Bridge` |
| Gateway-Port | UDP `47808` |
| Testclient-Port | UDP `47809` |
| Node-RED-Client-Port | UDP `47810` |

Die Netzwerkadresse prüfen:

```bash
ip -4 -br addr show scope global
```

Die angegebenen Adressen sind Beispiele aus dem Labor und müssen zum eigenen Netzwerk passen.

Device Instances müssen im jeweiligen BACnet-Netz eindeutig sein. Die feste MQTT Client ID des Gateways darf nicht gleichzeitig von einer zweiten Gateway-Instanz verwendet werden.

Auf demselben Rechner dürfen nicht mehrere Anwendungen denselben lokalen BACnet-Port beanspruchen.

## 8. systemd-Dienste vorbereiten

Die Vorlagen liegen im Repository:

```text
bacnet/bms-bacnet.service.example
data-logger/bms-logger.service.example
```

Vor der Installation in beiden Vorlagen prüfen und anpassen:

- `User`
- `WorkingDirectory`
- Python- und Skriptpfade in `ExecStart`
- BACnet-IP-Adresse und Device Instance beim Gateway

Die Vorlagen enthalten die Pfade und den Benutzer des getesteten Laboraufbaus.

Nach Anpassung installieren:

```bash
sudo cp ~/BMS-MQTT-BACnet-IP/bacnet/bms-bacnet.service.example \
    /etc/systemd/system/bms-bacnet.service

sudo cp ~/BMS-MQTT-BACnet-IP/data-logger/bms-logger.service.example \
    /etc/systemd/system/bms-logger.service

sudo systemctl daemon-reload
```

Dienste aktivieren und starten:

```bash
sudo systemctl enable --now bms-logger.service
sudo systemctl enable --now bms-bacnet.service
```

Status prüfen:

```bash
systemctl is-active bms-logger.service
systemctl is-active bms-bacnet.service
```

Diagnose bei Startproblemen:

```bash
journalctl -u bms-bacnet.service -n 30 --no-pager
journalctl -u bms-logger.service -n 30 --no-pager
```

Die Anwendungen benötigen beim Dienststart keine interaktive Passworteingabe.

**Kein zusätzliches Gateway manuell starten, solange `bms-bacnet.service` läuft.**

## 9. Node-RED vorbereiten

Im getesteten Flow werden folgende zusätzliche Pakete verwendet:

| Paket | Version im Labor |
|---|---|
| `@flowfuse/node-red-dashboard` | `1.32.0` |
| `node-red-contrib-modbus` | `5.60.2` |
| `node-red-node-sqlite` | `2.0.1` |
| `node-red-contrib-bacnet` | `0.3.0` |

Die Pakete über **Manage palette / Palette verwalten** bereitstellen.

### Persistenten Kontext konfigurieren

Die Datei:

```text
config/context-storage.example.js
```

enthält einen Konfigurationsausschnitt für den benannten Kontextspeicher `file`.

Den Ausschnitt in die vorhandene `module.exports`-Konfiguration der Node-RED-`settings.js` integrieren.

**Nicht die vollständige `settings.js` durch diesen Ausschnitt ersetzen.**

Vorhandene Einstellungen berücksichtigen und Node-RED nach der Änderung neu starten. Der Speicher wird von Alarmhistorie und Befehlsdauer verwendet.

## 10. Flow importieren und lokale Einstellungen prüfen

Folgenden Flow importieren:

```text
flows/bms-mqtt-bacnet-flow.json
```

Vor dem Deploy prüfen:

| Bereich | Lokale Einstellung |
|---|---|
| MQTT-Broker | Adresse, Port und Zugangsdaten |
| BACnet Device | Adresse des Gateways |
| BACnet Client | Lokale Interface-Adresse, Broadcast und Port |
| SQLite | Pfad zur vorhandenen `bms.db`, Modus `RO` |
| CSV-Export | Pfad zur Python-Umgebung und zu `export_readings.py` |
| Modbus | Lokaler Simulator und Client-Verbindung |

Der importierte Flow enthält keine MQTT-Passwörter. Diese im Broker-Konfigurationsknoten lokal ergänzen.

Der Modbus-Client des Laboraufbaus verbindet sich mit `127.0.0.1:10502`; die zugehörige Simulatorkonfiguration im Flow berücksichtigen.

Die Datenbank muss bereits initialisiert sein. Node-RED benötigt Leseberechtigung für die Datenbank und ausreichende Berechtigungen für die Exportausführung.

Der CSV-Export wird durch einen Node-RED-Exec-Knoten ausgeführt. Dessen Python- und Dateipfade müssen zur Installation passen.

## 11. Betrieb prüfen

ESP32, Broker, Datenlogger und BACnet-Gateway starten und anschließend den Flow deployen.

Erwartete Beobachtungen:

- MQTT-Verbindung zeigt `Verbunden`.
- Neue Sensorwerte werden empfangen.
- BACnet-Temperatur und -Luftfeuchtigkeit erscheinen nach erfolgreichen Wert- und OOS-Abfragen.
- BACnet-Temperaturstatus zeigt `OK`.
- Neue SQLite-Datensätze werden ungefähr einmal pro Minute je Messgröße gespeichert.
- Die Messwerthistorie wird durch ihre periodische Abfrage aktualisiert.
- Der CSV-Button lädt eine Exportdatei herunter.

Die ersten Anzeigen können vorübergehend nicht verfügbar sein, bis gültige Zustands- und Wertantworten vorliegen.

## 12. Optionale BACnet-Prüfung im Terminal

Bei laufender Gateway-Serviceinstanz einen separaten Client starten:

```bash
~/bms-bacnet/.venv/bin/python -m bacpypes3 \
    --address 192.168.178.38:47809 \
    --instance 123002 \
    --name BMS-Lab-Client
```

Adresse und Client Instance für die eigene Umgebung anpassen.

Die folgenden Befehle innerhalb der BACpypes3-Shell ausführen, nicht direkt in Bash:

```text
whois 192.168.178.38
read 192.168.178.38 device,123001 object-list
read 192.168.178.38 analog-value,1 present-value
read 192.168.178.38 analog-value,1 out-of-service
read 192.168.178.38 analog-value,2 present-value
read 192.168.178.38 analog-value,2 out-of-service
```

Die Eingabeaufforderung `>` nicht mitkopieren. Jeder Read-Befehl wird als vollständige Zeile ausgeführt.

## 13. Fehlerprüfungen

### Fehlende Sensordaten

Nur die Versorgung des ESP32 unterbrechen. Raspberry Pi, Broker und Gateway weiterlaufen lassen.

Nach Ablauf der Gateway-Überwachung und der anschließenden BACnet-Abfragen sollen die betroffenen BACnet-Anzeigen melden:

```text
Daten nicht verfügbar
```

ESP32 wieder anschließen. Nach Eingang neuer Messungen und erfolgreicher Abfrage sollen Zahlenwerte und Status zurückkehren.

### BACnet-Gateway nicht erreichbar

Nur den Gateway-Dienst stoppen:

```bash
sudo systemctl stop bms-bacnet.service
```

Nach Ablauf der Lesezeitüberschreitungen sollen die Catch-Verarbeitung und die Anzeige-Guards die Nichtverfügbarkeit darstellen.

MQTT kann dabei weiterhin verbunden bleiben.

Gateway wieder starten:

```bash
sudo systemctl start bms-bacnet.service
```

Nach erfolgreichen Abfragen sollen die BACnet-Anzeigen wieder normale Werte zeigen.

Die Reaktionszeiten ergeben sich aus Überwachung, Abfrageintervallen und Timeouts. Es handelt sich nicht um garantierte Echtzeitfristen.

## 14. Hinweise zur Einordnung

- BACnet stellt in dieser Version Messwerte bereit; die bestehende Lüfterregelung verbleibt in Node-RED.
- Das aktuelle Dashboard verwendet Polling, keine getestete COV-Subscription.
- OOS wird im Gateway als projektspezifisches Kennzeichen fehlender Quelldaten verwendet.
- Der vollständige Neuaufbau auf einem leeren System und eine vollständige Wiederherstellung wurden noch nicht verifiziert.
- `.gitignore` entfernt keine bereits veröffentlichten Dateien und ersetzt keine Prüfung vor manuellen Uploads.
- Zugangsdaten und lokale Datenbanken nicht veröffentlichen.
