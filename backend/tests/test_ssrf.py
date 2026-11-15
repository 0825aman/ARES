"""test_ssrf.py — Tests for SSRF protection and safe URL validation."""
from unittest.mock import patch
from app.providers.web_fetcher import is_safe_url


def test_ssrf_blocks_private_ips():
    assert not is_safe_url("http://127.0.0.1/secret")
    assert not is_safe_url("http://10.0.0.1/data")
    assert not is_safe_url("http://192.168.1.1/admin")
    assert not is_safe_url("http://172.16.0.1/internal")
    assert not is_safe_url("http://169.254.169.254/latest/meta-data")


def test_ssrf_blocks_unsafe_schemes():
    assert not is_safe_url("file:///etc/passwd")
    assert not is_safe_url("ftp://example.com/data.txt")
    assert not is_safe_url("javascript:alert(1)")
    assert not is_safe_url("data:text/html,hello")
    assert not is_safe_url("gopher://example.com:70/_")


def test_ssrf_allows_public_urls():
    with patch("socket.gethostbyname", return_value="93.184.216.34"):
        assert is_safe_url("https://example.com/research")
        assert is_safe_url("http://example.com/paper.pdf")


def test_ssrf_blocks_invalid_hostnames():
    assert not is_safe_url("not_a_url")
    assert not is_safe_url("http:///empty-host")
