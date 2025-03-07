import json
import asyncio
import websockets

class WebSocketSignaling:
    def __init__(self, url):  # Правильное имя конструктора!
        self.url = url
        self.conn = None
        self.is_connected = False

    async def connect(self):
        try:
            self.conn = await websockets.connect(self.url, ping_timeout=60)
            self.is_connected = True
            print(f"Успешное подключение к {self.url}")
        except Exception as e:
            print(f"Ошибка подключения: {str(e)}")
            raise

    async def send(self, message):
        if not self.is_connected:
            raise RuntimeError("Соединение не установлено")
        await self.conn.send(json.dumps(message))

    async def receive(self):
        try:
            msg = await asyncio.wait_for(self.conn.recv(), timeout=30)
            return json.loads(msg)
        
        except asyncio.TimeoutError:
            print("Таймаут ожидания сообщения")
            return None

    async def disconnect(self):
        if self.conn:
            await self.conn.close()
            self.is_connected = False