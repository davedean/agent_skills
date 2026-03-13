---
name: jellyseerr
description: Search for and request movies/TV shows via the Jellyseerr API. Use when the user wants to find, request, or check the status of media requests.
---

# Jellyseerr Skill

Interact with Jellyseerr to search for and request media (movies and TV shows).

## Authentication

Set environment variables before use. Either method works:

- **API Key** (full admin access): Set `JELLYSEERR_API_KEY`
- **Cookie Auth** (respects user permissions): Set `JELLYSEERR_USERNAME` + `JELLYSEERR_PASSWORD`

Optional: `JELLYSEERR_URL` (default: `http://localhost:5055`)

## Commands

All commands support `--debug` to show raw API responses.

### `search <query> [--page N] [--language CODE]`

Search for movies or TV shows. Returns type, title, year, rating, and TMDB ID.

```bash
jellyseerr-cli.py search "Inception"
# [MOVIE] Inception (2010) - Rating: 8.4 - ID: 27205
```

### `request <movie|tv> <tmdb_id> [--seasons SEASONS] [--4k]`

Request media by TMDB ID (from search results). TV shows require `--seasons` (comma-separated or `all`).

```bash
jellyseerr-cli.py request movie 27205
jellyseerr-cli.py request tv 1396 --seasons all
jellyseerr-cli.py request tv 1396 --seasons 1,2,3 --4k
```

### `list [--filter STATUS] [--media-type TYPE] [--take N]`

List requests. Filter options: `all`, `approved`, `available`, `pending`, `processing`, `deleted`, `completed`. Media type: `movie`, `tv`, `all`. Default take: 20.

```bash
jellyseerr-cli.py list --filter pending --media-type tv
```

### `details <request_id>`

Get detailed info about a specific request.

### `counts`

Get request counts by status (pending, approved, available, completed).

### `login`

Manually verify cookie auth credentials. Runs automatically when needed.

## Typical Flow

1. **Search** for media to get its TMDB ID
2. **Request** it using the ID
3. **List** or **details** to check status

## Error Recovery

- **401 Unauthorized**: Credentials are wrong or expired. Verify env vars are set correctly. For cookie auth, try `login` to test credentials.
- **404 Not Found**: The TMDB ID or request ID doesn't exist. Re-search to confirm the ID.
- **Connection Error**: Check that `JELLYSEERR_URL` is correct and the server is reachable.
- **Search returns nothing**: Try a shorter or alternative query (e.g. original title vs translated title).
- **Request fails with 409**: Media has already been requested.

## Notes

- Requests are auto-approved if the user has `ADMIN` or `AUTO_APPROVE` permissions
- API key auth has full admin access; cookie auth respects the user's permission level
- The `JELLYSEERR_USERNAME` field accepts your Jellyseerr username (the API field is named "email" but works with usernames)
