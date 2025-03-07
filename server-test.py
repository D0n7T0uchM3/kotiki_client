import asyncio
from aiohttp import web
import json

class SignalingServer:
    def __init__(self):
        self.app = web.Application()  # Определяем аттрибут app
        self.app.add_routes([
            web.get('/ws', self.websocket_handler)
        ])
        self.clients = {}
        self.room = {}
        # Инициализируем свойства перед использованием
        self.runner = None
        self.site = None
    
    async def start(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, 'localhost', 8080)
        await self.site.start()
        print("Signaling server running at http://localhost:8080")
    
    async def stop(self):
        await self.site.stop()
        await self.runner.cleanup()
        print("Server stopped")

    async def websocket_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        peer_id = None

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    print(f"Received message: {data}")

                    if data['type'] == 'join':
                        peer_id = data['peer_id']
                        self.clients[peer_id] = ws
                        await self.handle_join(peer_id, data)

                    elif data['type'] in ['offer', 'answer', 'candidate']:
                        await self.forward_message(peer_id, data)

                elif msg.type == web.WSMsgType.ERROR:
                    print(f"WebSocket error: {ws.exception()}")
                    
        finally:
            if peer_id:
                self.cleanup_peer(peer_id)
                await ws.close()
            return ws

    async def handle_join(self, peer_id, data):
        room_id = data.get('room', 'default')
        if room_id not in self.room:
            self.room[room_id] = {'host': peer_id, 'viewers': []}
            print(f"Host {peer_id} created room {room_id}")
        else:
            self.room[room_id]['viewers'].append(peer_id)
            print(f"Viewer {peer_id} joined room {room_id}")
            await self.notify_host(room_id, peer_id)

    async def forward_message(self, sender_id, message):
        room_id = next(
            (rid for rid, info in self.room.items() if sender_id in [info['host']] + info['viewers']),
            None
        )

        if sender_id == self.room[room_id]['host']:
            recipients = self.room[room_id]['viewers']
        else:
            recipients = [self.room[room_id]['host']]

        for peer_id in recipients:
            if peer_id in self.clients:
                await self.clients[peer_id].send_json(message)
                print(f"Forwarded {message['type']} to {peer_id}")

    async def notify_host(self, room_id, viewer_id):
        host_id = self.room[room_id]['host']
        if host_id in self.clients:
            await self.clients[host_id].send_json({
                'type': 'new_viewer',
                'viewer_id': viewer_id
            })

    def cleanup_peer(self, peer_id):
        for room_id, info in self.room.items():
            if peer_id == info['host']:
                print(f"Room {room_id} closed")
                del self.room[room_id]
                break
            elif peer_id in info['viewers']:
                info['viewers'].remove(peer_id)
                break

        if peer_id in self.clients:
            del self.clients[peer_id]

async def main():
    server = SignalingServer()
    await server.start()
    await asyncio.Event().wait()  # Бесконечное ожидание
    await server.stop()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped gracefully")
