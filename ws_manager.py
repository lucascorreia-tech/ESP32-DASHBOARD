import asyncio
import json
import logging
import math
import random
import threading
import time
from collections import deque
from typing import Dict, Any, List, Optional, Callable

import websockets
from kinematics import TrackConfig, KinematicResult, compute_kinematics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VeloTrilhoWS")


class WebSocketManager:
    def __init__(self):
        self.mode: str = "disconnected"
        self.server_url: str = "ws://192.168.4.1:81"
        self.server_port: int = 8765
        self.is_running: bool = False
        self.status_message: str = "Desconectado"
        self.status_state: str = "offline"
        
        self.last_received_time: Optional[float] = None
        self.total_packets_received: int = 0
  
        self.latest_result: Optional[KinematicResult] = None
        self.history: List[KinematicResult] = []
        self.raw_logs: deque = deque(maxlen=25)
        
        self.track_config = TrackConfig(d1=0.00, d2=0.50, d3=1.00)
        self.run_counter: int = 1
        
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._server_obj = None
        self._outgoing_queue: deque = deque()

    def update_track_config(self, d1: float, d2: float, d3: float):
        with self._lock:
            self.track_config = TrackConfig(d1=d1, d2=d2, d3=d3)

    def log_raw(self, msg: str):
        timestamp = time.strftime("%H:%M:%S")
        with self._lock:
            self.raw_logs.append(f"[{timestamp}] {msg}")

    def process_incoming_payload(self, raw_data: str):
        try:
            self.log_raw(f"RECEBIDO: {raw_data[:120]}...")
            data = json.loads(raw_data)
        except json.JSONDecodeError:
            self.log_raw(f"ERRO: Payload não é JSON válido: {raw_data[:60]}")
            return

        with self._lock:
            self.total_packets_received += 1
            self.last_received_time = time.time()

            t1 = data.get("t1", data.get("T1", 0.0))
            t2 = data.get("t2", data.get("T2", 0.0))
            t3 = data.get("t3", data.get("T3", 0.0))

            unit = data.get("unit", "seconds")
            if unit == "micros" or (t1 > 100000 or t2 > 100000 or t3 > 100000):
                unit = "micros"
            elif unit == "millis" or (t1 > 1000 or t2 > 1000 or t3 > 1000):
                unit = "millis"

            d1 = data.get("d1", self.track_config.d1)
            d2 = data.get("d2", self.track_config.d2)
            d3 = data.get("d3", self.track_config.d3)
            current_cfg = TrackConfig(d1=float(d1), d2=float(d2), d3=float(d3))

            run_id = data.get("run_id", self.run_counter)
            self.run_counter = max(self.run_counter + 1, run_id + 1)

            result = compute_kinematics(
                t1=float(t1),
                t2=float(t2),
                t3=float(t3),
                config=current_cfg,
                run_id=run_id,
                time_unit=unit
            )

            if "v12" in data and float(data["v12"]) > 0:
                result.v12 = float(data["v12"])
            if "v23" in data and float(data["v23"]) > 0:
                result.v23 = float(data["v23"])
            if "v_med" in data and float(data["v_med"]) > 0:
                result.v_med = float(data["v_med"])
            if "acceleration" in data:
                result.acceleration = float(data["acceleration"])

            self.latest_result = result
            self.history.append(result)
            self.status_message = f"Ensaio #{result.run_id} recebido com sucesso!"
            self.status_state = "online"

    async def _client_loop(self):
        self.log_raw(f"Iniciando conexão cliente com {self.server_url}...")
        while not self._stop_event.is_set():
            try:
                self.status_state = "warning"
                self.status_message = f"Conectando a {self.server_url}..."
                async with websockets.connect(self.server_url, ping_interval=5, ping_timeout=10) as ws:
                    self.status_state = "online"
                    self.status_message = f"Conectado ao ESP32 ({self.server_url})"
                    self.log_raw("Conexão WebSocket estabelecida com sucesso!")
                    
                    while not self._stop_event.is_set():
                        while self._outgoing_queue:
                            try:
                                cmd_to_send = self._outgoing_queue.popleft()
                                await ws.send(cmd_to_send)
                                self.log_raw(f"ENVIADO AO ESP32: {cmd_to_send}")
                            except Exception as ex:
                                self.log_raw(f"Erro ao enviar comando: {ex}")

                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=0.5)
                            self.process_incoming_payload(msg)
                        except asyncio.TimeoutError:
                            continue
                        except websockets.exceptions.ConnectionClosed:
                            self.log_raw("Conexão fechada pelo ESP32.")
                            break
            except Exception as e:
                self.status_state = "error"
                self.status_message = f"Tentando reconectar... ({e.__class__.__name__})"
                self.log_raw(f"Falha de conexão: {e}. Nova tentativa em 3s...")
                await asyncio.sleep(3)

    async def _handle_server_client(self, websocket):
        client_ip = websocket.remote_address[0]
        self.status_state = "online"
        self.status_message = f"ESP32 conectado ({client_ip})"
        self.log_raw(f"Cliente conectado: {client_ip}")
        try:
            while not self._stop_event.is_set():
                while self._outgoing_queue:
                    try:
                        cmd_to_send = self._outgoing_queue.popleft()
                        await websocket.send(cmd_to_send)
                        self.log_raw(f"ENVIADO AO ESP32: {cmd_to_send}")
                    except Exception as ex:
                        self.log_raw(f"Erro ao enviar comando: {ex}")
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                    self.process_incoming_payload(message)
                except asyncio.TimeoutError:
                    continue
        except websockets.exceptions.ConnectionClosed:
            self.log_raw(f"Cliente {client_ip} desconectou.")
            self.status_message = "Aguardando conexão do ESP32..."
            self.status_state = "warning"

    async def _server_loop(self):
        self.log_raw(f"Iniciando Servidor WebSocket local na porta {self.server_port}...")
        try:
            self.status_state = "warning"
            self.status_message = f"Servidor escutando na porta {self.server_port} (aguardando ESP32)..."
            async with websockets.serve(self._handle_server_client, "0.0.0.0", self.server_port):
                self.log_raw(f"Servidor WebSocket ativo em ws://0.0.0.0:{self.server_port}")
                while not self._stop_event.is_set():
                    await asyncio.sleep(0.5)
        except Exception as e:
            self.status_state = "error"
            self.status_message = f"Erro no Servidor: {e}"
            self.log_raw(f"Erro ao iniciar servidor: {e}")

    def start_client(self, url: str):
        self.stop()
        self.server_url = url
        self.mode = "client"
        self._stop_event.clear()
        self.is_running = True

        def run():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._client_loop())

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def start_server(self, port: int = 8765):
        self.stop()
        self.server_port = port
        self.mode = "server"
        self._stop_event.clear()
        self.is_running = True

        def run():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._server_loop())

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def stop(self):
        self.is_running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self.mode = "disconnected"
        self.status_state = "offline"
        self.status_message = "Desconectado"
        self.log_raw("Conexão WebSocket finalizada.")

    def send_command(self, cmd_dict: Dict[str, Any]):
        raw_cmd = json.dumps(cmd_dict)
        with self._lock:
            self._outgoing_queue.append(raw_cmd)
        self.log_raw(f"Comando enfileirado: {raw_cmd}")

    def clear_history(self):
        with self._lock:
            self.history.clear()
            self.latest_result = None
            self.run_counter = 1
            self.log_raw("Histórico de ensaios resetado.")

    def simulate_single_run(self, slope_deg: float = 5.0, initial_speed: float = 0.20):
        g = 9.81
        theta_rad = math.radians(slope_deg)
        accel = max(0.05, g * math.sin(theta_rad) - 0.08)
        
        d1 = self.track_config.d1
        d2 = self.track_config.d2
        d3 = self.track_config.d3
        
        def time_at_pos(pos, v0, a):
            delta = v0**2 + 2 * a * pos
            return (-v0 + math.sqrt(delta)) / a

        noise = lambda: 1.0 + random.uniform(-0.005, 0.005)

        t1_calc = 0.0
        t2_calc = time_at_pos(d2 - d1, initial_speed, accel) * noise()
        t3_calc = time_at_pos(d3 - d1, initial_speed, accel) * noise()
        base_offset_us = random.randint(1000000, 5000000)
        payload = {
            "run_id": self.run_counter,
            "unit": "micros",
            "d1": d1,
            "d2": d2,
            "d3": d3,
            "t1": int(base_offset_us),
            "t2": int(base_offset_us + t2_calc * 1_000_000),
            "t3": int(base_offset_us + t3_calc * 1_000_000),
            "source": "simulador_virtual"
        }
        
        self.process_incoming_payload(json.dumps(payload))


_manager_instance: Optional[WebSocketManager] = None

def get_ws_manager() -> WebSocketManager:
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = WebSocketManager()
    return _manager_instance
