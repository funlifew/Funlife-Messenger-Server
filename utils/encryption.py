from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from base64 import b64encode, b64decode
import os, json

class E2EEncryption:
    """ End-to-End Encryption utilities for secure messaging
    
    This class provides methods for:
    1. Generating RSA key pairs
    2. Encrypting messages using recipient's public key
    3. Decrypting messages using sender's private key
    
    The implementation uses a hybrid approach:
    - AES for message encryption (symmetric)
    - RSA for key exchange (asymmetric)
    """
    
    @staticmethod
    def generate_key_pair():
        """
        Generate a new RSA key pair for a user
        
        Returns:
            tuple: (private_key_pem, public_key_pem) as strings
        """
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Get public key
        public_key = private_key.public_key()
        
        # Serialize the keys to PEM format
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
        return private_pem, public_pem
    
    @staticmethod
    def encrypt_message(plaintext, recipient_public_key_pem):
        """
        Encrypt a message for a recipient using their public key
        
        Args:
            plaintext (str): The message to encrypt
            recipient_public_key_pem (str): Recipient's public key in PEM format
            
        Returns:
            str: JSON string containing the encrypted message and session key
        """
        
        # Load recipient's public_key
        public_key = serialization.load_pem_public_key(
            recipient_public_key_pem.encode('utf-8'),
            backend=default_backend()
        )
        
        # Generate a random AES session key
        session_key = os.urandom(32)  # 256-bit key
        
        # Generate a random IV
        iv = os.urandom(16)  # 128-bit IV for AES
        
        # Encrypt the message with AES
        cipher = Cipher(
            algorithms.AES(session_key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        # Pad the plaintext to be a multiple of 16 bytes (AES block size)
        plaintext_bytes = plaintext.encode('utf-8')
        padded_plaintext = E2EEncryption._pad(plaintext_bytes)
        
        # Encrypt the padded plaintext
        ciphertext = encryptor.update(padded_plaintext) + encryptor.finalize()
        
        # Encrypt the session key with RSA
        encrypted_session_key = public_key.encrypt(
            session_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        # Encode binary data as base64 for JSON compatibility
        payload = {
            'encrypted_session_key': b64encode(encrypted_session_key).decode('utf-8'),
            'iv': b64encode(iv).decode('utf-8'),
            'ciphertext': b64encode(ciphertext).decode('utf-8')
        }
        
        # Return the JSON payload
        return json.dumps(payload)
    
    @staticmethod
    def decrypt_message(encrypted_payload, private_key_pem):
        """
        Decrypt a message using the recipient's private key
        
        Args:
            encrypted_payload (str): JSON string from encrypt_message
            private_key_pem (str): Recipient's private key in PEM format
            
        Returns:
            str: Decrypted message text
        """
        # Load the private key
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode('utf-8'),
            password=None,
            backend=default_backend()
        )
        
        # Parse the JSON payload
        payload = json.loads(encrypted_payload)
        
        # Decode base64 components
        encrypted_session_key = b64decode(payload['encrypted_session_key'])
        iv = b64decode(payload['iv'])
        ciphertext = b64decode(payload['ciphertext'])
        
        # Decrypt the session key with the private key
        session_key = private_key.decrypt(
            encrypted_session_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        # Decrypt the message with AES
        cipher = Cipher(
            algorithms.AES(session_key),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        # Decrypt and unpad
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        plaintext_bytes = E2EEncryption._unpad(padded_plaintext)
        
        # Return the plaintext message
        return plaintext_bytes.decode('utf-8')
    
    
    @staticmethod
    def _pad(data):
        """
        PKCS#7 padding for AES
        """
        block_size = 16
        padding_length = block_size - (len(data) % block_size)
        padding = bytes([padding_length] * padding_length)
        return data + padding
    
    @staticmethod
    def _unpad(padded_data):
        """
        Remove PKCS#7 padding
        """
        padding_length = padded_data[-1]
        return padded_data[:-padding_length]