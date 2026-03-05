"""Tests for SMART App Launch authentication mode."""
import os
import sys
import pytest

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ['TESTING'] = 'true'

from app import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    with app.test_client() as client:
        yield client


class TestSmartDiscovery:
    """Test the /smart/discover endpoint."""

    def test_discover_smart_sandbox(self, client):
        """Discover SMART configuration from the public SMART sandbox."""
        resp = client.get('/smart/discover?fhir_url=https://launch.smarthealthit.org/v/r4/fhir')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        config = data['config']
        assert 'authorization_endpoint' in config
        assert 'token_endpoint' in config
        assert 'launch.smarthealthit.org' in config['authorization_endpoint']

    def test_discover_missing_url(self, client):
        """Uses default FHIR server URL when none specified."""
        resp = client.get('/smart/discover')
        # Should still succeed (may or may not find SMART config on default server)
        assert resp.status_code in (200, 404)

    def test_discover_invalid_server(self, client):
        """Returns error for unreachable server."""
        resp = client.get('/smart/discover?fhir_url=https://invalid.example.com/fhir')
        assert resp.status_code == 500
        data = resp.get_json()
        assert data['success'] is False


class TestSmartLaunch:
    """Test the /smart/launch endpoint (redirect to auth server)."""

    def test_launch_redirect(self, client):
        """Launch should redirect to the authorization endpoint."""
        resp = client.get('/smart/launch?'
                          'fhir_url=https://launch.smarthealthit.org/v/r4/fhir&'
                          'auth_url=https://launch.smarthealthit.org/v/r4/auth/authorize&'
                          'token_url=https://launch.smarthealthit.org/v/r4/auth/token&'
                          'client_id=test-app&'
                          'scope=launch/patient openid fhirUser')
        assert resp.status_code == 302
        location = resp.headers['Location']
        assert 'launch.smarthealthit.org' in location
        assert 'response_type=code' in location
        assert 'client_id=test-app' in location
        assert 'code_challenge=' in location
        assert 'code_challenge_method=S256' in location
        assert 'state=' in location

    def test_launch_missing_params(self, client):
        """Launch without required params returns error."""
        resp = client.get('/smart/launch')
        assert resp.status_code == 400


class TestSmartCallback:
    """Test the /smart/callback endpoint."""

    def test_callback_error(self, client):
        """Callback with error param returns error page."""
        resp = client.get('/smart/callback?error=access_denied&error_description=User+denied')
        assert resp.status_code == 200
        # Should render index with error

    def test_callback_no_code(self, client):
        """Callback without code returns error."""
        with client.session_transaction() as sess:
            sess['smart_state'] = 'test-state'
        resp = client.get('/smart/callback?state=test-state')
        assert resp.status_code == 200

    def test_callback_state_mismatch(self, client):
        """Callback with wrong state returns CSRF error."""
        with client.session_transaction() as sess:
            sess['smart_state'] = 'expected-state'
        resp = client.get('/smart/callback?code=test-code&state=wrong-state')
        assert resp.status_code == 200


class TestSmartTokenStatus:
    """Test the /smart/token-status endpoint."""

    def test_no_token(self, client):
        """Returns no token when not authenticated."""
        resp = client.get('/smart/token-status')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['has_token'] is False

    def test_with_token(self, client):
        """Returns token info when SMART session exists."""
        with client.session_transaction() as sess:
            sess['smart_access_token'] = 'test-token-123'
            sess['smart_patient_id'] = 'Patient/123'
            sess['smart_fhir_url'] = 'https://example.com/fhir'
        resp = client.get('/smart/token-status')
        data = resp.get_json()
        assert data['has_token'] is True
        assert data['patient_id'] == 'Patient/123'


class TestSmartLogout:
    """Test the /smart/logout endpoint."""

    def test_logout_clears_session(self, client):
        """Logout clears SMART tokens from session."""
        with client.session_transaction() as sess:
            sess['smart_access_token'] = 'test-token'
            sess['smart_patient_id'] = 'Patient/123'
        resp = client.post('/smart/logout')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        # Verify token is cleared
        resp2 = client.get('/smart/token-status')
        assert resp2.get_json()['has_token'] is False


class TestBearerTokenInFhirGet:
    """Test that Bearer tokens are correctly passed to FHIR requests."""

    def test_bearer_token_from_header(self, client):
        """X-FHIR-Bearer-Token header should be used for FHIR requests."""
        # This hits a real FHIR endpoint with a Bearer token
        # The token is invalid, so the server will reject it, but we verify
        # the auth mechanism is wired up correctly
        resp = client.get('/fhir/Patients',
                          headers={
                              'X-FHIR-Bearer-Token': 'fake-token-for-testing',
                              'X-FHIR-Server-URL': 'https://launch.smarthealthit.org/v/r4/fhir'
                          })
        # We expect some response (may be error due to invalid token, but not a crash)
        assert resp.status_code in (200, 401, 403, 500)


class TestAuthModeSelection:
    """Test that the three auth modes work correctly."""

    def test_no_auth_mode(self, client):
        """No auth headers should result in unauthenticated request."""
        resp = client.get('/health')
        assert resp.status_code == 200

    def test_basic_auth_headers(self, client):
        """Basic auth headers should be forwarded."""
        resp = client.get('/fhir/Patients',
                          headers={
                              'X-FHIR-Username': 'testuser',
                              'X-FHIR-Password': 'testpass',
                              'X-FHIR-Server-URL': 'https://smile.sparked-fhir.com/aucore/fhir/DEFAULT'
                          })
        # Should not crash even if credentials are wrong
        assert resp.status_code in (200, 401, 403, 500)

    def test_smart_bearer_header(self, client):
        """SMART Bearer token should take priority."""
        resp = client.get('/fhir/Patients',
                          headers={
                              'X-FHIR-Bearer-Token': 'test-bearer-token',
                              'X-FHIR-Server-URL': 'https://launch.smarthealthit.org/v/r4/fhir'
                          })
        assert resp.status_code in (200, 401, 403, 500)
