"""Tests for ETA QR URL parsing logic — the regex-based parser in qr_decode.py."""

from app.services.qr_decode import _parse_eta_url, ETAQRData


class TestParseETAUrl:
    def test_valid_eta_url(self):
        url = (
            "https://invoicing.eta.gov.eg/receipts/search/"
            "AB12CD34-EF56-7890-GH12-IJ34KL56MN78/share/"
            "2026-05-15T14:30:00#Total:1500.50,IssuerRIN:123456789"
        )
        result = _parse_eta_url(url)
        assert result is not None
        assert result.uuid == "AB12CD34-EF56-7890-GH12-IJ34KL56MN78"
        assert result.total == 1500.50
        assert result.issuer_rin == "123456789"
        assert result.datetime == "2026-05-15T14:30:00"
        assert result.raw_url == url

    def test_integer_total(self):
        url = "receipts/search/UUID-123/share/2026-01-01#Total:500,IssuerRIN:999"
        result = _parse_eta_url(url)
        assert result is not None
        assert result.total == 500.0

    def test_large_total(self):
        url = "receipts/search/UUID-X/share/DT#Total:999999.99,IssuerRIN:111222333"
        result = _parse_eta_url(url)
        assert result is not None
        assert result.total == 999999.99

    def test_non_eta_url_returns_none(self):
        result = _parse_eta_url("https://example.com/not-eta")
        assert result is None

    def test_empty_string_returns_none(self):
        result = _parse_eta_url("")
        assert result is None

    def test_partial_match_missing_issuer(self):
        url = "receipts/search/UUID/share/DT#Total:100"
        result = _parse_eta_url(url)
        assert result is None

    def test_partial_match_missing_total(self):
        url = "receipts/search/UUID/share/DT#IssuerRIN:123"
        result = _parse_eta_url(url)
        assert result is None

    def test_invalid_total_becomes_none(self):
        url = "receipts/search/UUID/share/DT#Total:abc,IssuerRIN:123"
        result = _parse_eta_url(url)
        assert result is not None
        assert result.total is None
        assert result.issuer_rin == "123"

    def test_zero_total(self):
        url = "receipts/search/UUID/share/DT#Total:0,IssuerRIN:123"
        result = _parse_eta_url(url)
        assert result is not None
        assert result.total == 0.0
