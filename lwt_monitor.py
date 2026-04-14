import json
from datetime import datetime

import paho.mqtt.client as mqtt

BROKER = "localhost"
PORT = 1883
TOPIC_STATUS = "estufa/dispositivos/+/status"


def ts():
    return datetime.now().strftime("%H:%M:%S")


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[monitor] Conectado ao broker {BROKER}:{PORT}")
        client.subscribe(TOPIC_STATUS, qos=1)
        print(f"[monitor] Inscrito em {TOPIC_STATUS}")
    else:
        print(f"[monitor] Falha na conexao, rc={rc}")


def on_message(client, userdata, msg):
    origem = "RETIDA" if msg.retain else "AO VIVO"
    try:
        data = json.loads(msg.payload.decode())
    except json.JSONDecodeError:
        data = msg.payload.decode(errors="replace")

    status = data.get("status") if isinstance(data, dict) else None
    alerta = ""
    if status == "offline":
        alerta = "  <-- DISPOSITIVO OFFLINE"
    elif status == "online":
        alerta = "  <-- dispositivo online"

    print(f"[{ts()}] ({origem}) {msg.topic} -> {data}{alerta}")


def main():
    client = mqtt.Client(client_id="lwt-monitor")
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(BROKER, PORT, keepalive=60)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[monitor] Encerrando")
        client.disconnect()


if __name__ == "__main__":
    main()
