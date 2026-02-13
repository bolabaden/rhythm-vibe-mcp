"""HTTP client timeouts and options for external requests."""

# Timeout in seconds for MuseScore API requests
MUSESCORE_REQUEST_TIMEOUT = 45.0

# Timeout in seconds for music asset downloads (e.g. fetch from URL)
DOWNLOAD_REQUEST_TIMEOUT = 90.0

# Follow redirects for HTTP clients (standard for GET/fetch)
FOLLOW_REDIRECTS = True

# HTTP header names (lowercase for request/response header lookup)
HEADER_AUTHORIZATION = "authorization"
HEADER_CONTENT_TYPE = "content-type"

# HTTP method names (for MuseScore API and similar)
HTTP_GET = "GET"
HTTP_POST = "POST"
HTTP_PUT = "PUT"
HTTP_DELETE = "DELETE"
