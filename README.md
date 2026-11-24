# Proyecto Final – Sistemas Operativos
## Infraestructura en contenedores: Nginx + 3 backends + Prometheus + Grafana

Un **proxy inverso Nginx** reparte el tráfico entre **3 backends en Flask**
(`server 1`, `server 2` y `server 3`). Todo se monitorea con **Prometheus**,
**nginx-prometheus-exporter**, **cAdvisor** y **Grafana**.

```
                 Máquina física (navegador / k6)
                              │ :8080
                      ┌───────▼───────┐
                      │     nginx     │  proxy inverso, round-robin
                      │  :80   :8088* │  (*stub_status, solo red interna)
                      └──┬────┬────┬──┘
              ┌──────────┘    │    └──────────┐
         ┌────▼───┐      ┌────▼───┐      ┌────▼───┐
         │  app1  │      │  app2  │      │  app3  │   Flask + /metrics
         │server 1│      │server 2│      │server 3│
         └────▲───┘      └────▲───┘      └────▲───┘
              └───────────────┼───────────────┘
                     ┌────────┴────────┐
 nginx-exporter ───► │   prometheus    │ ◄─── cadvisor (CPU, RAM, red, disco)
   (stub_status)     │      :9090      │
                     └────────▲────────┘
                              │
                        grafana :3000

        Todos los contenedores están en la red personalizada "proyecto-net".
```

## Estructura

```
proyecto-final/
├── .env                          # Puertos del host (se cambian aquí)
├── docker-compose.yml            # Los 8 servicios, la red y los volúmenes
├── backend/
│   ├── app.py                    # Flask: /, /health, /headers, /slow, /error, /metrics
│   ├── requirements.txt
│   └── Dockerfile
├── nginx/nginx.conf              # Se monta como conf.d/default.conf
├── prometheus/prometheus.yml     # Targets: backends, nginx-exporter, cadvisor
├── grafana/
│   ├── provisioning/             # Datasource y dashboard automáticos
│   └── dashboards/infraestructura.json
├── k6/loadtest.js                # Prueba de carga
├── verificar_balanceo.ps1        # Conteo del balanceo (PowerShell)
└── verificar_balanceo.sh         # Conteo del balanceo (WSL / Bash)
```

## Requisitos previos

- **Docker Desktop** con Docker Compose v2 (`docker --version` y `docker compose version`).
  Asígnele al menos 4 GB de RAM en *Settings → Resources*.
- **k6** en la máquina física para la prueba de carga:
  - Windows: `winget install k6 --source winget`
  - macOS: `brew install k6`
  - Linux: https://grafana.com/docs/k6/latest/set-up/install-k6/
- Puertos libres: **8080, 8081, 9090 y 3000**. En Windows se revisan con:
  ```
  netsh interface ipv4 show excludedportrange protocol=tcp
  ```
  Si alguno cae dentro de un rango, cámbielo en el archivo `.env`.

## Levantar la infraestructura

```
git clone <URL-del-repositorio>
cd proyecto-final
docker compose up -d --build
docker compose ps
```

`app1`, `app2` y `app3` deben aparecer como **(healthy)**. Para apagar todo use
`docker compose down`, o `docker compose down -v` si también quiere borrar los datos
de Prometheus y Grafana.

## URLs de acceso

| Servicio | URL | Para qué sirve |
|---|---|---|
| Aplicación (vía Nginx) | http://localhost:8080 | Muestra "Hello from server N" |
| Cabeceras que llegan al backend | http://localhost:8080/headers | Muestra `X-Forwarded-For` |
| Petición lenta | http://localhost:8080/slow?ms=500 | Simula trabajo pesado |
| Errores simulados | http://localhost:8080/error | Falla el 20 % de las veces |
| Prometheus | http://localhost:9090 | *Status → Target health*: todo en UP |
| Grafana | http://localhost:3000 | Usuario `admin`, clave `admin` |
| cAdvisor | http://localhost:8081 | Recursos de cada contenedor |

El dashboard está en Grafana → *Dashboards → Proyecto Final → "Proyecto Final SO - Infraestructura"*.

## Verificar el balanceo de carga

1. Abra http://localhost:8080 y recargue: cambia entre server 1, server 2 y server 3.
2. Haga el conteo de 30 peticiones. Deben salir 10, 10 y 10:
   ```
   .\verificar_balanceo.ps1          # PowerShell
   bash verificar_balanceo.sh        # WSL / Git Bash
   ```
3. Revise las cabeceras: `curl.exe -sI http://localhost:8080`. `X-Backend` indica el
   servidor y `X-Upstream` su IP interna.
4. Vea el log de Nginx con `docker compose logs --tail 15 nginx`. La columna
   `upstream=` va alternando.
5. **Tolerancia a fallos:** ejecute `docker compose stop app1` y repita el paso 2.
   El reparto queda solo entre server 2 y server 3, sin errores. Después ejecute
   `docker compose start app1`.

## Prueba de carga (desde la máquina física)

```
k6 run k6/loadtest.js
```

Dura unos 4 minutos y sube a 20, 50 y 100 usuarios virtuales. Reparte las peticiones
entre `/`, `/slow` y `/error`. Los umbrales son p95 < 500 ms y menos de 10 % de
errores. Al final muestra `respuestas_server_1/2/3`, el reparto que hizo Nginx.

Mientras corre, abra el dashboard de Grafana (*Last 15 minutes*, refresco *5s*).

## Métricas monitoreadas

| Origen | Métrica | Qué muestra |
|---|---|---|
| Backends | `flask_http_request_total` | Tasa de peticiones por servidor y por código HTTP |
| Backends | `flask_http_request_duration_seconds` | Latencia (p50, p95 y p99) |
| nginx-exporter | `nginx_http_requests_total`, `nginx_connections_*` | Tráfico y conexiones de Nginx |
| cAdvisor | `container_cpu_usage_seconds_total`, `container_memory_working_set_bytes`, `container_network_*`, `container_fs_*` | CPU, RAM, red y disco por contenedor |

## Problemas comunes

- **Un target sale DOWN en Prometheus:** revise `docker compose ps` y
  `docker compose logs <servicio>`.
- **cAdvisor no muestra nombres de contenedores:** ejecute `docker compose restart cadvisor`
  (Docker Desktop debe usar WSL2).
- **"port is already allocated":** cambie el puerto en `.env` y vuelva a ejecutar
  `docker compose up -d`.
