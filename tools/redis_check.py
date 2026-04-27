import redis

def check():
    for db in range(5):
        r = redis.Redis(host='localhost', port=6379, db=db, decode_responses=True)
        try:
            keys = r.keys("*")
            if keys:
                print(f"--- DB {db} ---")
                for k in keys:
                    print(f"Chave: {k} (Tipo: {r.type(k)})")
        except:
            pass

if __name__ == '__main__':
    check()
