// Prueba de carga con k6 desde la máquina física contra Nginx.
// Uso: k6 run k6/loadtest.js        (apunta a http://localhost:8080)
//      k6 run -e BASE_URL=http://localhost:8090 k6/loadtest.js   (si cambiaste el puerto)
import http from "k6/http";
import { check, sleep } from "k6";
import { Counter } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8080";

// Cuenta cuántas respuestas dio cada servidor (comprueba el balanceo)
const porServidor = {
  "server 1": new Counter("respuestas_server_1"),
  "server 2": new Counter("respuestas_server_2"),
  "server 3": new Counter("respuestas_server_3"),
};

export const options = {
  // Rampa de unos 4 minutos: 20 → 50 → 100 usuarios virtuales y bajada
  stages: [
    { duration: "30s", target: 20 },
    { duration: "1m", target: 50 },
    { duration: "1m30s", target: 50 },
    { duration: "30s", target: 100 },
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    http_req_duration: ["p(95)<500"], // 95 % de las peticiones en menos de 500 ms
    http_req_failed: ["rate<0.10"],   // menos del 10 % de errores
  },
};

export default function () {
  const rutas = ["/", "/slow", "/slow", "/error"];
  const ruta = rutas[Math.floor(Math.random() * rutas.length)];
  const res = http.get(`${BASE_URL}${ruta}`, { tags: { ruta } });

  check(res, {
    "status 200 (o 500 simulado en /error)": (r) =>
      r.status === 200 || (ruta === "/error" && r.status === 500),
    "trae cabecera X-Backend": (r) => r.headers["X-Backend"] !== undefined,
  });

  const servidor = res.headers["X-Backend"];
  if (porServidor[servidor]) porServidor[servidor].add(1);

  sleep(Math.random() * 0.5);
}
