import json
import time
from datetime import datetime

import paho.mqtt.client as mqtt

BROKER = "localhost"
PORT = 1883

TOPIC_TEMP = "estufa/sensores/temperatura"
TOPIC_UMID = "estufa/sensores/umidade"


def main():
    client = mqtt.Client(client_id="retain-publisher")
    client.connect(BROKER, PORT, keepalive=60)
    client.loop_start()

    leituras = [
        {"topico": TOPIC_TEMP, "valor": 25.4, "unidade": "C"},
        {"topico": TOPIC_UMID, "valor": 62.1, "unidade": "%"},
    ]

    for leitura in leituras:
        payload = json.dumps(
            {
                "valor": leitura["valor"],
                "unidade": leitura["unidade"],
                "ts": datetime.now().isoformat(timespec="seconds"),
            }
        )
        result = client.publish(leitura["topico"], payload=payload, qos=1, retain=True)
        result.wait_for_publish()
        print(f"[publisher] RETIDO em {leitura['topico']} -> {payload}")

    time.sleep(0.5)
    client.loop_stop()
    client.disconnect()
    print("[publisher] Desconectado. Mensagens permanecem retidas no broker.")


if __name__ == "__main__":
    main()
