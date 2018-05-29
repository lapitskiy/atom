import redis

class Baking:
# создаем печеньки, количество печенек будет конечно, и базу нельзя будет изменить
    def __init__(self):
        self.id = []
        self.owner = []

    def size(self,dbkey):
        # присваиваем переменной test1 значение 5
        r = redis.StrictRedis(host='localhost', db=dbkey)
        return r.dbsize()

    @staticmethod
    def clear(dbkey):
        # получаем из переменной test1 значение
        r = redis.StrictRedis(host='localhost', db=dbkey)
        r.flushdb()

    def baking(self, dbkey):
        r = redis.StrictRedis(host='localhost', db=dbkey)
        data = {}
        strvalue1 = '4SzkNXVjE9tFhBJWYKLPFfKcqxSY'
        strvalue2 = 'U12cyWUQMYBtFnuMCjrr2FmCfnS'
        for i in range(0, 10):
            r.rpush(i, strvalue1)
            r.rpush(i, 0.5)
            r.rpush(i, strvalue2)
            r.rpush(i, 0.5)
            r_str_get = r.lindex(i, 0).decode() + ' - ' + r.lindex(i, 1).decode() + ';' + r.lindex(i,                                                                                                   2).decode() + ' - ' + r.lindex(
                i, 3).decode()
            data[i] = r_str_get
        r.bgsave()
        return data