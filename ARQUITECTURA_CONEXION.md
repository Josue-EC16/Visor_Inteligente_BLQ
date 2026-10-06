# ARQUITECTURA DE CONEXIÓN — BLANQUITA

## 1. Propósito

Este documento define la arquitectura principal de comunicación del proyecto **BLANQUITA**, estableciendo cómo se conectan y qué responsabilidades tienen los tres componentes principales del sistema:

- **Laptop**, encargada del visor inteligente.
- **Aplicación móvil**, encargada de la supervisión, validación y control.
- **ESP32**, encargado de la ejecución física del robot cartesiano.

La arquitectura está diseñada para mantener una separación clara de responsabilidades, permitir funcionamiento manual aun cuando falle el visor inteligente y evitar que más de un dispositivo tenga autoridad simultánea sobre el movimiento físico del robot.

---

## 2. Arquitectura general

La infraestructura de red estará basada en una **red Wi-Fi local centralizada mediante un router principal**.

Todos los dispositivos se conectarán a la misma red local.

```text
                    ROUTER PRINCIPAL
                     RED WIFI LOCAL
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
           LAPTOP        MÓVIL        ESP32
           Visión       App Flutter   Cartesiano
```

El router cumple exclusivamente la función de proporcionar conectividad de red.

No controla el robot, no procesa visión y no actúa como broker MQTT.

La comunicación entre las aplicaciones se realizará mediante **WebSockets**.

---

## 3. Tecnologías principales de comunicación

### 3.1. Red local

El router crea una LAN privada a la cual se conectan:

- Laptop.
- Celular.
- ESP32.
- Dispositivos adicionales que puedan incorporarse en el futuro.

No es necesario que exista conexión a Internet para que BLANQUITA funcione.

La comunicación principal ocurre dentro de la red local.

---

### 3.2. WebSockets

WebSocket será el protocolo principal de comunicación entre los componentes.

Se utilizarán dos canales independientes:

```text
MÓVIL ⇄ ESP32
WebSocket de control

MÓVIL ⇄ LAPTOP
WebSocket de visión
```

La red Wi-Fi proporciona conectividad IP.

WebSocket proporciona el canal de comunicación persistente y bidireccional entre las aplicaciones.

---

## 4. Principio principal de la arquitectura

La arquitectura se divide en tres niveles:

```text
PERCEPCIÓN
    ↓
DECISIÓN
    ↓
EJECUCIÓN
```

Estos niveles corresponden a:

```text
Laptop
   ↓
Móvil
   ↓
ESP32
```

Cada dispositivo tiene una responsabilidad específica.

---

# 5. Laptop — Capa de percepción

La laptop será la encargada exclusivamente del **visor inteligente**.

Su función principal será procesar la información proveniente de la cámara externa.

Arquitectura conceptual:

```text
CÁMARA EXTERNA
      │
      ▼
    LAPTOP
      │
      ├── Captura de video
      ├── OpenCV
      ├── Visión artificial
      ├── Machine Learning / IA si es necesario
      ├── Detección de objetos
      ├── Tracking
      ├── Calibración
      ├── Cálculo de posición
      └── Generación de reportes
```

La laptop puede utilizar herramientas de procesamiento más pesadas sin trasladar esa carga al celular.

Esto evita:

- Sobrecalentamiento del teléfono.
- Consumo excesivo de batería.
- Thermal throttling.
- Limitaciones de CPU/GPU/NPU móviles.
- Dependencia del rendimiento específico del celular.

---

## 5.1. Qué debe enviar la laptop

La laptop enviará al móvil información procesada.

Ejemplo:

```json
{
  "type": "vision_report",
  "detected": true,
  "object": "pieza",
  "x": 145.2,
  "z": 78.4,
  "confidence": 0.96,
  "timestamp": "2026-10-05T18:00:00"
}
```

Otros datos futuros podrían incluir:

```text
estado de cámara
estado de calibración
FPS
posición
bounding box
tipo de objeto
confianza
alertas
resultado del análisis
timestamp
```

---

## 5.2. Qué NO debe hacer la laptop

La laptop **no debe controlar directamente al ESP32**.

No debe enviar directamente comandos como:

```text
a
d
w
s
x
z
j
q
e
+
-
```

La laptop tampoco debe decidir por sí sola que un motor físico debe comenzar a moverse.

Su responsabilidad será informar:

> "Esto es lo que detecto."

y no:

> "Mueve el robot."

Esto mantiene desacopladas la visión y la ejecución física.

---

# 6. Aplicación móvil — Capa de decisión y control

La aplicación móvil BLANQUITA será el **centro lógico de control del sistema**.

Será la única aplicación de alto nivel autorizada para enviar comandos de movimiento al ESP32.

Sus responsabilidades serán:

- Control manual.
- Supervisión del robot.
- Visualización de estados.
- Recepción de reportes de visión.
- Validación de automatizaciones.
- Inicio y cancelación de secuencias.
- STOP.
- Emergencia.
- Diagnósticos.
- Interacción con el usuario.

La aplicación móvil funcionará como intermediario entre:

```text
LAPTOP
   ↓
MÓVIL
   ↓
ESP32
```

---

# 7. ESP32 — Capa de ejecución física

El ESP32 será responsable de la ejecución física.

Sus responsabilidades incluyen:

- Control de motores.
- Control de pinza.
- Lectura de sensores.
- Ejecución de secuencias.
- Heartbeat.
- Timeouts.
- Finales de carrera.
- Detención.
- Watchdog.
- Protecciones de bajo nivel.

El ESP32 recibe órdenes desde la aplicación móvil y las transforma en acciones sobre el hardware.

Arquitectura:

```text
MÓVIL
   │
   │ WebSocket
   ▼
ESP32
   │
   ├── Motores
   ├── Pinza
   ├── Sensores
   ├── Finales de carrera
   └── Seguridad
```

---

# 8. Autoridad de control

Uno de los principios más importantes del sistema será mantener una **única autoridad de control físico**.

La autoridad será:

```text
APP MÓVIL
```

No:

```text
Laptop + móvil
```

Esto evita condiciones como:

```text
Laptop → MOVER DERECHA
Móvil  → STOP
```

o:

```text
Laptop → INICIAR AUTOMÁTICO
Móvil  → MOVER IZQUIERDA
```

Si ambos pudieran controlar directamente al ESP32 sería necesario desarrollar:

- Arbitraje.
- Prioridades.
- Roles.
- Bloqueos.
- Propietario de sesión.
- Resolución de conflictos.
- Reglas de concurrencia.

La arquitectura propuesta evita esa complejidad.

---

# 9. Flujo de visión inteligente

El flujo normal será:

```text
CÁMARA
   │
   ▼
LAPTOP
   │
   │ detección
   ▼
VISION REPORT
   │
   ▼
MÓVIL
   │
   │ validación
   ▼
DECISIÓN
   │
   ▼
COMANDO
   │
   ▼
ESP32
   │
   ▼
CARTESIANO
```

La laptop produce información.

La aplicación móvil decide si utilizar esa información.

El ESP32 ejecuta.

---

# 10. Validación de movimientos automatizados

Antes de transformar un resultado del visor en una acción física, la app móvil deberá validar el estado general del sistema.

Flujo conceptual:

```text
Reporte de visión
        │
        ▼
¿Laptop conectada?
        │
        ▼
¿Reporte reciente?
        │
        ▼
¿Objeto detectado?
        │
        ▼
¿Confianza suficiente?
        │
        ▼
¿ESP32 conectado?
        │
        ▼
¿No existe emergencia?
        │
        ▼
¿Final de carrera libre?
        │
        ▼
¿No existe otra secuencia activa?
        │
        ▼
¿Movimiento permitido?
        │
        ▼
AUTORIZAR ACCIÓN
        │
        ▼
ESP32
```

Este mecanismo permite que la visión inteligente influya en la automatización sin convertirse en el controlador físico directo.

---

# 11. Información versus comandos

La laptop debe enviar **resultados o intenciones de alto nivel**.

Ejemplo correcto:

```json
{
  "type": "object_position",
  "x": 145.2,
  "z": 78.4,
  "confidence": 0.96
}
```

Ejemplo no recomendado:

```json
{
  "command": "d"
}
```

La laptop debe conocer:

```text
objetos
posición
detección
confianza
estado de visión
```

El móvil debe conocer:

```text
reglas
estado general
automatización
autorización
acciones
```

El ESP32 debe conocer:

```text
motores
direcciones
pasos
sensores
hardware
seguridad
```

---

# 12. Separación de responsabilidades

## Laptop

**Responsabilidad principal: percepción.**

```text
Cámara
Visión
IA
Detección
Tracking
Calibración
Posición
Reportes
```

---

## Móvil

**Responsabilidad principal: decisión y supervisión.**

```text
UI
Control manual
Validaciones
Automatización
Estados
STOP
Emergencia
Reportes
Diagnósticos
```

---

## ESP32

**Responsabilidad principal: ejecución física y protección.**

```text
Motores
Pinza
Sensores
Timeout
Watchdog
Finales de carrera
Secuencias físicas
Seguridad de bajo nivel
```

---

# 13. Comunicación WebSocket

Existirán dos comunicaciones principales.

## 13.1. Móvil ↔ ESP32

Canal dedicado al control físico.

```text
MÓVIL
   ⇅
WebSocket
   ⇅
ESP32
```

Por este canal circulan:

```text
comandos
estados
heartbeat
STOP
emergencia
secuencia
pinza
sensores
errores
```

---

## 13.2. Móvil ↔ Laptop

Canal dedicado a visión.

```text
MÓVIL
   ⇅
WebSocket
   ⇅
LAPTOP
```

Por este canal circulan:

```text
reportes
detecciones
posición
confianza
estado de cámara
estado del detector
alertas
```

---

# 14. Topología final

```text
                         ROUTER
                   RED LOCAL BLANQUITA
                           │
            ┌──────────────┼──────────────┐
            │              │              │
            ▼              ▼              ▼

        ┌────────┐     ┌────────┐     ┌────────┐
        │ LAPTOP │     │ MÓVIL  │     │ ESP32  │
        └────┬───┘     └────┬───┘     └────┬───┘
             │              │              │
        Visión / IA         │          Cartesiano
             │              │
             └─WebSocket────┤
                            │
                            └─WebSocket────► ESP32
```

Aunque todos los dispositivos están conectados a la misma LAN, eso no significa que todos tengan los mismos permisos.

La conectividad física será todos-con-la-red.

La autoridad lógica estará restringida.

---

# 15. Router principal

El router será únicamente infraestructura.

Sus responsabilidades:

- Crear la red local.
- Asignar direcciones IP.
- Permitir comunicación entre dispositivos.
- Mantener una LAN común.

No será responsable de:

- Control.
- IA.
- Visión.
- Automatización.
- MQTT.
- WebSocket.
- Seguridad física.

---

# 16. Direccionamiento de red

Una posible organización futura sería:

```text
Router
192.168.10.1

ESP32
192.168.10.10

Laptop Vision
192.168.10.20

Móvil
192.168.10.x
```

Es recomendable utilizar **reservas DHCP en el router** para los dispositivos que deben conservar una dirección conocida.

Ejemplo:

```text
ESP32
ws://192.168.10.10:81/

Laptop
ws://192.168.10.20:8765/
```

En versiones posteriores se podría utilizar mDNS o descubrimiento automático.

---

# 17. Comportamiento ante fallos

La arquitectura debe degradarse de forma segura.

## 17.1. Falla de laptop

```text
LAPTOP
  ✕
```

Resultado:

```text
Visión inteligente       ✕
Control manual           ✓
STOP                     ✓
Emergencia               ✓
ESP32                    ✓
```

La falla del visor no debe impedir el control del robot.

---

## 17.2. Falla del visor

Si:

```text
cámara desconectada
detector falla
modelo falla
calibración inválida
reporte demasiado antiguo
```

la app móvil debe:

```text
invalidar automatización basada en visión
```

pero debe conservar el control manual.

---

## 17.3. Falla del móvil

Si el móvil pierde conexión mientras existe movimiento:

```text
Móvil desconectado
       │
       ▼
ESP32 detecta pérdida de heartbeat/control
       │
       ▼
STOP
```

La seguridad física no debe depender exclusivamente de que Flutter siga ejecutándose.

---

## 17.4. Falla del router

Si la red desaparece:

```text
Laptop ✕ Móvil
Móvil  ✕ ESP32
```

el ESP32 deberá llevar el sistema a un estado seguro mediante sus propios mecanismos:

```text
timeout
watchdog
STOP
```

---

## 17.5. Falla del ESP32

La aplicación móvil debe detectar la pérdida de conexión y:

- Invalidar controles.
- Indicar desconexión.
- Evitar automatizaciones.
- Mostrar diagnóstico.

---

# 18. Seguridad física

La seguridad final debe residir en el firmware/hardware del ESP32.

La aplicación móvil puede agregar validaciones adicionales, pero no debe ser el único mecanismo de protección.

El ESP32 debe encargarse de:

```text
final de carrera
timeout de movimiento
watchdog
STOP
emergencia
rechazo de acciones inválidas
```

Principio:

```text
Móvil valida
ESP32 protege
```

---

# 19. Ventajas de esta arquitectura

La arquitectura propuesta ofrece:

### Modularidad

Cada componente tiene una responsabilidad específica.

### Seguridad

Solo existe una autoridad de control de alto nivel.

### Tolerancia a fallos

La laptop puede fallar sin perder control manual.

### Rendimiento

El procesamiento pesado se realiza en laptop.

### Mantenibilidad

Visión, control y firmware pueden evolucionar de forma independiente.

### Escalabilidad

Se pueden agregar nuevos dispositivos a la LAN.

### Independencia tecnológica

La laptop puede usar Python/OpenCV/ML sin obligar a Flutter a ejecutar esas cargas.

### Claridad arquitectónica

La cadena principal se mantiene:

```text
Percepción → Decisión → Ejecución
```

---

# 20. Alternativas descartadas

## Laptop y móvil controlando directamente al ESP32

```text
Laptop ─┐
        ├──► ESP32
Móvil ──┘
```

No se adopta porque crea múltiples autoridades y obliga a implementar arbitraje de control.

---

## Laptop como controlador principal

```text
Móvil → Laptop → ESP32
```

No se adopta porque una falla de laptop eliminaría también el control del robot.

---

## ESP32 tomando decisiones de visión

```text
Laptop → ESP32 → robot
```

No se adopta porque aumentaría innecesariamente la responsabilidad del firmware.

---

## Todo el procesamiento en celular

No se adopta como arquitectura principal porque el procesamiento continuo de visión puede provocar:

- Mayor consumo.
- Calentamiento.
- Thermal throttling.
- Limitaciones de hardware.
- Menor estabilidad sostenida.

---

## MQTT

MQTT no se utilizará inicialmente.

La arquitectura actual tiene pocos nodos y WebSocket ya se encuentra implementado.

MQTT puede reevaluarse si en el futuro existen muchos dispositivos, múltiples consumidores de telemetría o una arquitectura IoT distribuida más compleja.

---

# 21. Arquitectura futura

La red puede crecer hacia:

```text
                      ROUTER
                        │
       ┌────────────────┼────────────────┐
       │                │                │
       ▼                ▼                ▼
    MÓVIL            LAPTOP          ESP32 #1
                                        │
                                     Cartesiano

                        │
                        ├── ESP32 #2
                        ├── ESP32 #3
                        ├── Tablet
                        ├── Raspberry Pi
                        └── Otros dispositivos
```

La incorporación de dispositivos adicionales no cambia la separación conceptual:

```text
PERCEPCIÓN
DECISIÓN
EJECUCIÓN
```

---

# 22. Resumen de decisiones cerradas

La arquitectura de conexión de BLANQUITA queda definida de la siguiente manera:

1. Se utilizará un **router principal** como infraestructura de red.

2. Laptop, móvil y ESP32 estarán conectados a la misma LAN.

3. No se requiere Internet para la operación principal.

4. Se utilizarán **WebSockets**.

5. Existirá un WebSocket entre:

```text
Móvil ⇄ ESP32
```

6. Existirá un WebSocket independiente entre:

```text
Móvil ⇄ Laptop
```

7. La laptop será responsable del visor inteligente.

8. La laptop no controlará directamente al ESP32.

9. El móvil será la única autoridad de control de alto nivel.

10. El móvil validará los resultados de visión antes de convertirlos en acciones automáticas.

11. El ESP32 será responsable de ejecución física y seguridad de bajo nivel.

12. La falla de la laptop no deberá impedir el control manual.

13. La pérdida del móvil o de la red deberá provocar un estado físico seguro.

14. Los resultados de visión serán enviados como información estructurada, no como comandos crudos de motor.

15. MQTT queda fuera de la primera arquitectura y podrá reevaluarse en el futuro.

---

# 23. Arquitectura final resumida

```text
                    ┌─────────────────────┐
                    │       CÁMARA        │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │       LAPTOP        │
                    │     PERCEPCIÓN      │
                    │                     │
                    │ Visión / OpenCV / IA│
                    │ Detección           │
                    │ Posición            │
                    │ Reportes            │
                    └──────────┬──────────┘
                               │
                          WebSocket
                               │
                               ▼
                    ┌─────────────────────┐
                    │       MÓVIL         │
                    │ DECISIÓN / CONTROL  │
                    │                     │
                    │ Validación          │
                    │ Supervisión         │
                    │ Automatización      │
                    │ Control manual      │
                    │ STOP / Emergencia   │
                    └──────────┬──────────┘
                               │
                          WebSocket
                               │
                               ▼
                    ┌─────────────────────┐
                    │       ESP32         │
                    │     EJECUCIÓN       │
                    │                     │
                    │ Motores             │
                    │ Pinza               │
                    │ Sensores            │
                    │ Watchdog            │
                    │ Seguridad           │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ ROBOT CARTESIANO    │
                    └─────────────────────┘
```

## Principio final

> **La laptop percibe, el móvil decide y el ESP32 ejecuta y protege.**

Esta separación será la base de la arquitectura de comunicación y control del proyecto BLANQUITA.
