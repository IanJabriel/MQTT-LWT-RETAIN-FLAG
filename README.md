# MQTT — Last Will and Testament & Retain Flag

Dois recursos avançados do MQTT que resolvem problemas reais em sistemas IoT: saber quando um dispositivo caiu e garantir que novos subscribers recebam dados imediatamente ao se conectar.

---

## Integrantes do Grupo

| Nome | RA |
|---|---|
| Ian Jabriel | 1962004 |
| João Vitor | 1963129 |
| Gabriel Verri | 1978701 |
| Gabriel Lenzi | 1960578 |

---

## Estrutura

```
mqtt-lwt-retain/
├── lwt_demo.py          ← sensor com LWT configurado
├── lwt_monitor.py       ← monitor que observa quedas via LWT
├── retain_publisher.py  ← publica dados com Retain Flag
├── retain_subscriber.py ← conecta depois e recebe dados retidos
└── README.md
```

---

## Last Will and Testament (LWT)

### O que é

LWT é uma mensagem que o **cliente configura no momento da conexão** com o broker. O broker armazena essa mensagem e a publica automaticamente em um tópico definido **se o cliente desconectar de forma inesperada** — sem enviar um pacote `DISCONNECT` limpo.

Pense nisso como um cartório: antes de começar a trabalhar, o dispositivo deixa uma mensagem de "óbito" registrada. Se ele sumir sem avisar, o cartório (broker) publica o aviso automaticamente.

### Por que existe

Em IoT, dispositivos perdem conexão o tempo todo: queda de energia, travamento de firmware, timeout de rede, cabo desconectado. Sem LWT, outros sistemas não saberiam distinguir um sensor "quieto porque não há dados novos" de um sensor "morto".

### Como funciona tecnicamente

```
Cliente → Broker: CONNECT (com LWT embutido no pacote)
Broker armazena: tópico, payload, QoS e retain do LWT

Cenário 1 — Desconexão limpa:
  Cliente → Broker: DISCONNECT
  Broker descarta o LWT. Nada é publicado.

Cenário 2 — Queda inesperada:
  Cliente some (crash, queda de energia, timeout de keepalive)
  Broker detecta ausência → publica o LWT automaticamente
  Subscribers do tópico recebem a mensagem de "óbito"
```

### Quando o LWT É publicado

- Timeout do `keepalive` (broker não recebeu PING do cliente dentro do prazo)
- Queda de rede (TCP fecha sem DISCONNECT)
- Crash do processo (`kill -9`, falha de hardware)
- Firmware travado

### Quando o LWT NÃO é publicado

- Desconexão com `client.disconnect()` — envia DISCONNECT limpo
- `Ctrl+C` em scripts Python com paho-mqtt (o paho envia DISCONNECT antes de fechar)

> **Dica de teste:** Para simular queda real em Python, use `kill -9 <PID>` no processo, não Ctrl+C. O `-9` mata o processo sem permitir que o paho envie o DISCONNECT.

### Código essencial

```python
# Configurar LWT — DEVE ser chamado ANTES de client.connect()
client.will_set(
    topic   = "estufa/dispositivos/sensor01/status",
    payload = '{"status": "offline", "motivo": "queda_inesperada"}',
    qos     = 1,      # garante entrega do LWT ao subscriber
    retain  = True    # novos subscribers veem o último status conhecido
)

client.connect(broker, porta, keepalive=60)
```

### Boas práticas com LWT

O tópico de LWT deve ser separado dos dados do sensor. Um padrão comum é `dispositivo/ID/status` para status e `dispositivo/ID/dados` para leituras. Combine LWT com `retain=True` para que qualquer dashboard que se conecte depois saiba imediatamente o estado do dispositivo — online ou offline. Configure o `keepalive` com um valor que faça sentido para sua rede: valores muito baixos geram tráfego desnecessário, valores muito altos atrasam a detecção de queda.

---

## Retain Flag

### O que é

A Retain Flag é uma instrução ao broker para **armazenar a última mensagem** publicada em um tópico. Quando qualquer subscriber se inscrever naquele tópico — mesmo muito depois da publicação — ele recebe essa mensagem imediatamente, sem precisar esperar a próxima.

O broker armazena apenas **uma mensagem por tópico**: a mais recente. Não é uma fila, é um "estado atual".

### Por que existe

Imagine um sensor de temperatura que publica a cada 30 minutos. Sem Retain, um dashboard que abrir às 14h45 ficará em branco até as 15h00 — 15 minutos olhando para nada. Com Retain, o dashboard recebe o valor das 14h30 imediatamente ao se conectar.

### Como funciona tecnicamente

```
Publisher → Broker: PUBLISH (retain=True, valor=25.4°C, 14h30)
Broker armazena: {tópico: "estufa/temp", payload: "25.4°C", timestamp: 14h30}

Subscriber A conecta às 14h45:
  Broker entrega imediatamente: {25.4°C} com msg.retain = True

Publisher → Broker: PUBLISH (retain=True, valor=26.1°C, 15h00)
Broker SUBSTITUI a mensagem armazenada: {26.1°C}

Subscriber B conecta às 15h05:
  Broker entrega imediatamente: {26.1°C} com msg.retain = True
```

### Como identificar uma mensagem retida no subscriber

O atributo `msg.retain` da mensagem recebida será `True` quando vier do armazenamento do broker, e `False` quando for uma publicação ao vivo. Isso permite que o subscriber saiba se está recebendo um dado antigo ou novo.

```python
def on_message(client, userdata, msg):
    if msg.retain:
        print("Dado retido — último valor armazenado no broker")
    else:
        print("Dado ao vivo — publicado agora")
```

### Como limpar uma mensagem retida

Para apagar o retain de um tópico, publique uma mensagem com payload vazio e `retain=True`. O broker interpreta isso como instrução para remover o dado armazenado.

```python
client.publish("estufa/sensores/temperatura", payload="", qos=1, retain=True)
```

### Quando usar Retain

Retain é ideal para representar **estado atual** de um dispositivo ou sensor: temperatura, nível de água, status online/offline. Não use para eventos ou logs — cada nova publicação sobrescreve a anterior. Para comandos, use com cuidado: um atuador que reconectar após queda receberá o último comando retido e o executará novamente.

---

## Comparação rápida

| Recurso | LWT | Retain Flag |
|---|---|---|
| Quem publica | O broker (automaticamente) | O publisher (com flag) |
| Quando é entregue | Na queda inesperada do cliente | Na subscrição de qualquer novo subscriber |
| Quantas mensagens armazena | Uma (por cliente) | Uma por tópico |
| Caso de uso principal | Detectar dispositivos offline | Fornecer estado atual imediato |
| Configurado em | `client.will_set()` antes do connect | `client.publish(..., retain=True)` |

---

## Impactos e quando usar cada um

### Impactos do LWT

- **Confiabilidade:** permite que o sistema reaja a falhas de dispositivos em segundos, sem polling manual.
- **Observabilidade:** dashboards e alertas conseguem distinguir "sensor silencioso" de "sensor morto", reduzindo falsos negativos.
- **Custo de rede:** impacto mínimo — o LWT só trafega quando há queda real; o keepalive adiciona pacotes PING leves.
- **Latência de detecção:** depende do `keepalive`. Valor baixo detecta rápido mas gera mais tráfego; valor alto economiza banda mas atrasa o alerta.
- **Risco:** se mal configurado (tópico errado, sem retain), o aviso de queda pode passar despercebido por subscribers que conectarem depois.

### Impactos do Retain Flag

- **Experiência do usuário:** dashboards e apps mostram o estado atual imediatamente ao conectar, sem telas em branco.
- **Memória do broker:** cada tópico com retain consome memória persistente. Em sistemas com milhares de tópicos, o impacto pode ser relevante.
- **Risco de dado obsoleto:** o subscriber pode tratar uma leitura antiga como atual se ignorar `msg.retain`. Sempre verifique o flag e/ou inclua timestamp no payload.
- **Risco em comandos:** atuadores que reconectam podem reexecutar o último comando retido. Não use retain em tópicos de comando sem mecanismo de idempotência.
- **Reinicialização:** mensagens retidas sobrevivem a reinícios do broker (se persistência estiver habilitada), garantindo continuidade do estado.

### Quando usar cada um

| Situação | Use LWT | Use Retain | Use os dois |
|---|---|---|---|
| Detectar queda de dispositivo | ✅ | | |
| Mostrar estado atual em dashboard recém-aberto | | ✅ | |
| Status online/offline persistente para novos subscribers | | | ✅ |
| Última leitura de sensor (temperatura, umidade) | | ✅ | |
| Eventos pontuais (botão pressionado, alarme disparado) | | ❌ | |
| Logs ou histórico de medições | ❌ | ❌ | |
| Comandos para atuadores | | ⚠️ cuidado | |
| Sistema crítico de monitoramento IoT em produção | | | ✅ |

**Regra prática:** use **LWT** quando precisar saber que algo *parou de funcionar*; use **Retain** quando precisar entregar o *estado atual* a quem chegar depois; **combine os dois** sempre que o status do dispositivo precisar sobreviver tanto a quedas quanto a novas conexões de subscribers.

---

## Como executar

### Pré-requisitos

```bash
# Broker rodando
docker-compose up -d

# Dependência
pip install paho-mqtt
```

### Testar LWT

```bash
# Terminal 1 — inicie o monitor primeiro
python lwt_monitor.py

# Terminal 2 — inicie o sensor
python lwt_demo.py

# Para simular queda real (LWT será publicado):
# Descubra o PID: ps aux | grep lwt_demo
# Mate com: kill -9 <PID>
# Observe o Terminal 1 receber o LWT automaticamente
```

### Testar Retain Flag

```bash
# Terminal 1 — publique os dados e deixe encerrar
python retain_publisher.py

# Espere 30 segundos (ou mais)

# Terminal 2 — conecte depois e veja os dados retidos chegarem imediatamente
python retain_subscriber.py
```

---

## Combinando LWT + Retain

O padrão mais comum em produção combina os dois: o LWT é configurado com `retain=True`. Assim, quando o sensor cair, o broker publica `{"status": "offline"}` com retain no tópico de status. Qualquer dashboard que abrir depois verá o sensor como offline imediatamente — mesmo que a queda tenha ocorrido horas antes. Quando o sensor voltar, ele publica `{"status": "online"}` com `retain=True`, sobrescrevendo o LWT e atualizando o estado para todos.

```python
# Padrão completo: LWT + retain
client.will_set(
    topic   = "estufa/dispositivos/sensor01/status",
    payload = '{"status": "offline"}',
    qos     = 1,
    retain  = True   # estado offline fica retido até o sensor voltar
)
```
