from hashlib import sha256

# Find a nonce such that the hash of "Dima"+nonce starts with six zeros
def find_nonce():
    nonce = 0
    while True:
        input_str = "Alex" + str(nonce)
        hash_result = sha256(input_str.encode()).hexdigest()
        if hash_result.startswith('000000'):
            return nonce, hash_result
        nonce += 1

nonce, hash_result = find_nonce()
print(nonce, hash_result)
