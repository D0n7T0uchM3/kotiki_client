import asyncio
import cv2
import numpy as np
from av import VideoFrame
from aiortc import (
    RTCPeerConnection, 
    RTCSessionDescription, 
    MediaStreamTrack
)
import mss

class ScreenCaptureTrack(MediaStreamTrack):
    kind = "video"

    def __init__(self, fps=30):
        super().__init__()  # Исправлено: правильный вызов super
        self.fps = fps
        self.frame_interval = 1 / fps
        self.running = True
        self.sct = mss.mss()
        self.monitor = self.sct.monitors[1]

    async def recv(self):
        if not self.running:
            raise Exception("Track is stopped")  # Генерируем ошибку вместо return
            
        start_time = asyncio.get_event_loop().time()
        
        # Захват экрана с обработкой ошибок MMSS
        try:
            frame = np.array(self.sct.grab(self.monitor))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        except mss.exception.ScreenShotError as e:
            self.stop()
            raise
            
        video_frame = VideoFrame.from_ndarray(frame, format='bgr24')
        video_frame.pts = int(start_time // self.frame_interval)
        
        # Неблокирующий показ окна
        cv2.imshow("Screen Stream", frame)
        if cv2.pollKey() in [ord('q'), 27]:
            self.stop()
            
        elapsed = asyncio.get_event_loop().time() - start_time
        await asyncio.sleep(max(0, self.frame_interval - elapsed))
        
        return video_frame

    def stop(self):
        self.running = False
        cv2.destroyAllWindows()
        self.sct.close()
        super().stop()


class VideoDisplayTrack:
    def __init__(self, track):  # Важно: исправлено на __init__
        if track is None or not hasattr(track, 'recv'):
            raise ValueError("Получен некорректный видео-трек")
        self.track = track
        self.running = False
        self.task = None

    async def start(self):
        if not self.running and self.track:
            self.running = True
            self.task = asyncio.create_task(self.display_loop())

    async def display_loop(self):
        while self.running and self.track:
            try:
                frame = await self.track.recv()
                if frame is None:  # Проверка на закрытие трека
                    raise ValueError("Трек завершил передачу")
                    
                img = frame.to_ndarray(format="bgr24")
                
                # Безопасный вывод через асинхронный цикл
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: (cv2.imshow("Remote Video", img), cv2.waitKey(1))
                )
                
                if cv2.pollKey() in [ord('q'), 27]:
                    await self.stop()

            except Exception as e:
                print(f"Ошибка отображения: {e}")
                await self.stop()

    async def stop(self):
        self.running = False
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        cv2.destroyAllWindows()

class WebRTCPeer:
    def __init__(self, signaling, is_initiator=True):  # Исправлено имя конструктора
        self.is_initiator = is_initiator
        self.pc = RTCPeerConnection()
        self.signaling = signaling
        self.screen_track = None
        self.video_displays = []

        if self.is_initiator:
            self.screen_track = ScreenCaptureTrack()  # Убедитесь, что этот класс реализован
            if self.screen_track:
                self.pc.addTrack(self.screen_track)

        self.pc.on("track")(self.on_track)
        self.pc.on("icecandidate")(self.on_icecandidate)  # Теперь метод определен правильно
    

    async def on_icecandidate(self, event):  # Исправлены отступы (должен быть внутри класса)
        try:
            if event.candidate:
                await self.signaling.send({
                    'type': 'candidate',
                    'candidate': {
                        'candidate': event.candidate.candidate,
                        'sdpMid': event.candidate.sdpMid,
                        'sdpMLineIndex': event.candidate.sdpMLineIndex
                    }
                })
        except Exception as e:
            print(f"Ошибка ICE кандидата: {str(e)}")


    async def on_track(self, track):
        # Проверка состояния соединения
        if self.pc.connectionState not in ['connected', 'connecting']:
            print(f"Игнopupyeм тpек (статус: {self.pc.connectionState})")
            return

        # Тройная проверка валидности трека
        if not track:
            print("Получен None-трек!")
            return
            
        if not hasattr(track, 'kind'):
            print(f"Некорректный объект трека: {type(track)}")
            return

        # try:
        #     if track.kind == "video":
        display = VideoDisplayTrack(track)
        self.video_displays.append(display)
        await display.start()
        # except Exception as e:
        #     print(f"Critical error: {str(e)}")
        #     await self.close()

    async def start(self):
        if self.is_initiator:
            try:
                offer = await self.pc.createOffer()
                await self.pc.setLocalDescription(offer)
                await self.signaling.send({
                    'type': 'offer',
                    'sdp': self.pc.localDescription.sdp
                })
            except Exception as e:
                print(f"Ошибка создания оффера: {e}")
                await self.close()


