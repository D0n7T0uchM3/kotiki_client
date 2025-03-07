import asyncio
from webrtc.signaling import WebSocketSignaling
from webrtc.peer import WebRTCPeer

async def main():
    try:
        # Инициализация сигналинга
        ws_signal= WebSocketSignaling('ws://localhost:8080/ws')
        await ws_signal.connect()

        # Создаем пир
        print("Создание WebRTC пира...")
        peer = WebRTCPeer(ws_signal, is_initiator=True)  # Укажите явно is_initiator
        
        # Запускаем логику установки соединения
        await peer.start()
        
        # Основной цикл обработки
        print("Ожидание событий...")
        while True:
            await asyncio.sleep(1)  # Удерживаем соединение
            
    except Exception as e:
        print(f"Fatal error: {str(e)}")
    finally:
        await peer.close()
        await ws_signal.disconnect()

if __name__ == "__main__":  # Исправленный синтаксис
    asyncio.run(main())