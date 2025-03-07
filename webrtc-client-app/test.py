import cv2
import numpy as np
import mss
import time

def stream_screen():
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # Основной экран
        
        while True:
            try:
                frame = np.array(sct.grab(monitor))  # Захватываем экран
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)  # Убираем альфа-канал
                
                cv2.imshow("Screen Stream", frame)  # Отображаем окно
                
                key = cv2.waitKey(1)

                if key in [ord('q'), 27]:  # Выход по 'q' или 'Esc'
                    print("Выход из программы.")
                    break

            except Exception as e:
                print(f"Ошибка: {e}")
        
        cv2.destroyAllWindows()
        print("Окно закрыто.")

if __name__ == "__main__":
    stream_screen()