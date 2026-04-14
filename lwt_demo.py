import json
import random
import time

import paho.mqtt.client as mqtt

BROKER = "localhost"
PORT = 1883
KEEPALIVE = 10

DEVICE_ID = "sensor01"
TOPIC_STATUS = f"estufa/dispositivos/{DEVICE_ID}/status"
TOPIC_DADOS = f"estufa/dispositivos/{DEVICE_ID}/dados"


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[{DEVICE_ID}] Conectado ao broker {BROKER}:{PORT}")
        online_payload = json.dumps({"status": "online", "device": DEVICE_ID})
        client.publish(TOPIC_STATUS, payload=online_payload, qos=1, retain=True)
        print(f"[{DEVICE_ID}] Publicado status online (retained)")
    else:
        print(f"[{DEVICE_ID}] Falha na conexao, rc={rc}")


def main():
    client = mqtt.Client(client_id=DEVICE_ID)
    client.on_connect = on_connect

    lwt_payload = json.dumps(
        {"status": "offline", "device": DEVICE_ID, "motivo": "queda_inesperada"}
    )
    client.will_set(
        topic=TOPIC_STATUS,
        payload=lwt_payload,
        qos=1,
        retain=True,
    )

    client.connect(BROKER, PORT, keepalive=KEEPALIVE)
    client.loop_start()

    try:
        while True:
            leitura = {
                "device": DEVICE_ID,
                "temperatura": round(random.uniform(20.0, 30.0), 2),
                "umidade": round(random.uniform(40.0, 80.0), 2),
                "ts": int(time.time()),
            }
            client.publish(TOPIC_DADOS, json.dumps(leitura), qos=0)
            print(f"[{DEVICE_ID}] Dados publicados: {leitura}")
            time.sleep(3)
    except KeyboardInterrupt:
        print(f"\n[{DEVICE_ID}] Encerrando de forma limpa (LWT NAO sera publicado)")
        offline_payload = json.dumps({"status": "offline", "device": DEVICE_ID, "motivo": "shutdown"})
        client.publish(TOPIC_STATUS, payload=offline_payload, qos=1, retain=True)
        time.sleep(0.5)
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
