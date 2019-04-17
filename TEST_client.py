from __future__ import print_function

import time
import zmq
import sys
import threading
from random import randint, random
from cl_thread import *
from cl_node import *

node = Node()

def main():
    #
    # включаем поток для сообщения соседям, что ты жив (сосед слева)
    # alive отправляет данные 1 - alive (номер ноды + проверка ip + код alive), 2 - последнее значение блокчейна, 3 - закачивает данные вектора нода + его блокчейн
    #
    alive = AliveClientTask(node)
    alive.run()

    server = ServerTask(node)
    server.start()

    client = ClientTask(node)
    client.start()

    #
    # включаем поток для дрочки соседей
    # pingpong отправляет данные 1 - tyktyk (номер ноды + проверка ip), 2 - хеш вектора своего и того кому отправляет данные, 3 - последние значение блокчейна хеша.
    #
    #pingpong = ClientTask('pingpong', '')
    #pingpong.start()


if __name__ == "__main__":
    main()

