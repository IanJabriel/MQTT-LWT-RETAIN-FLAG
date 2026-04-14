import json
from datetime import datetime

import paho.mqtt.client as mqtt

BROKER = "localhost"
PORT = 1883
TOPIC = "estufa/sensores/#"


def ts():
    return datetime.now().strftime("%H:%M:%S")


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[subscriber] Conectado ao broker {BROKER}:{PORT}")
        client.subscribe(TOPIC, qos=1)
        print(f"[subscriber] Inscrito em {TOPIC} (aguardando retidas + ao vivo)")
    else:
        print(f"[subscriber] Falha na conexao, rc={rc}")


def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
    except json.JSONDecodeError:
        data = msg.payload.decode(errors="replace")

    if msg.retain:
        marca = "RETIDA  (ultimo valor armazenado no broker)"
    else:
        marca = "AO VIVO (publicacao em tempo real)"

    print(f"[{ts()}] {marca}")
    print(f"          topico : {msg.topic}")
    print(f"          payload: {data}")


def main():
    client = mqtt.Client(client_id="retain-subscriber")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, keepalive=60)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[subscriber] Encerrando")
        client.disconnect()


if __name__ == "__main__":
    main()
