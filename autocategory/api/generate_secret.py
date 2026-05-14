"""
Generate JWT secret key for environment configuration
"""
import secrets

def generate_secret_key():
    """Generate a secure random secret key"""
    return secrets.token_hex(32)

if __name__ == "__main__":
    secret_key = generate_secret_key()
    print("=" * 70)
    print("JWT Secret Key Generated")
    print("=" * 70)
    print(f"\nSECRET_KEY={secret_key}")
    print("\n⚠️  Add this to your .env file!")
    print("⚠️  Keep this secret and never commit it to version control!")
    print("=" * 70)
