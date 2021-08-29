import base64
import gzip

def encode(data):
    gzipped = gzip.compress(bytes(data, 'utf-8'))
    base64_bytes = base64.b64encode(gzipped)
    base64_message = base64_bytes.decode('ascii')
    return base64_message

