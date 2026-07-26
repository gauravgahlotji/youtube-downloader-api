import time
import unittest
from fastapi.testclient import TestClient
from main import app
from app.core.config import settings
from app.core.security import calculate_signature

client = TestClient(app)


class TestSecurity(unittest.TestCase):
    def test_hmac_signature_calculation(self):
        api_key = "test_key"
        secret_key = "test_secret"
        timestamp = "1700000000"
        nonce = "nonce123"
        payload = '{"url":"https://example.com"}'

        sig1 = calculate_signature(api_key, secret_key, timestamp, nonce, payload)
        sig2 = calculate_signature(api_key, secret_key, timestamp, nonce, payload)

        self.assertEqual(sig1, sig2)
        self.assertEqual(len(sig1), 64)

    def test_request_without_signature_when_disabled(self):
        settings.SECURITY_ENFORCE_SIGNATURE = False
        response = client.get("/version")
        self.assertEqual(response.status_code, 200)
        self.assertIn("version", response.json())


if __name__ == "__main__":
    unittest.main()
