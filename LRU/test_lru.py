import time
import redis
from redis_lru import RedisLRU

client = redis.StrictRedis(host="redis", port=6379)
cache = RedisLRU(client)


@cache()
def fib(n):
    if n < 2:
        print('Result from function!')
        return n
    return fib(n-1) + fib(n-2)

if __name__ == "__main__":
    print(fib(10))
    print('------')
    print(fib(10))
    print('------')
    print(fib(10))

