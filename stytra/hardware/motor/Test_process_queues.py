from multiprocessing import Process, Queue, Event
from queue import Empty
from time import sleep
import datetime
import random
from stytra.hardware.motor.stageAPI import Motor

class SendPositionsProcess(Process):
    def __init__(self):
        super().__init__()
        self.position_queue = Queue()

    def run(self):
        while True:
            num = random.random()
            print (num)
            self.position_queue.put(num)
            print("put in queue")



class ReceiverProcess(Process):
    def __init__(self, dot_position_queue):
        super().__init__()
        self.position_queue = dot_position_queue
        self.motor = Motor(1, scale=1)
        self.motor.open()

    def run(self):
        while True:
            try:
                num = self.position_queue.get(timeout=0.01)
                print ("number from queue", num)
                pos = self.motor.get_position()
                print (pos)

            except Empty:
                break


################################


if __name__ == "__main__":
    event = Event()
    source = SendPositionsProcess()
    receiver = ReceiverProcess(source.position_queue)
    source.start()
    receiver.start()

    finishUp = True
    sleep(20)
    event.set()
    source.join()
    receiver.join()