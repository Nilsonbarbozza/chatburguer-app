import redis

def nuke():
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    keys_to_kill = [
        "batalhao:global_dedup",
        "stream:ingestion",
        "stream:level_0",
        "stream:level_12",
        "stream:level_34",
        "stream:dataclear",
        "stream:dead_letters"
    ]
    
    print("--- Operacao TERRA ARRASADA (Redis Nuke) ---")
    for k in keys_to_kill:
        if r.exists(k):
            r.delete(k)
            print(f"Aniquilado: {k}")
        else:
            print(f"Ja estava limpo: {k}")
    
    print("\nQuartel General Resetado. Pronto para Invasao V2.")

if __name__ == '__main__':
    nuke()
