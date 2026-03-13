#!/usr/bin/env python3
import argparse
import json
import os
import sys
from datetime import datetime
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, build_opener, install_opener, HTTPCookieProcessor

JELLYSEERR_URL = os.environ.get('JELLYSEERR_URL', 'http://localhost:5055')
JELLYSEERR_API_KEY = os.environ.get('JELLYSEERR_API_KEY', '')
JELLYSEERR_USERNAME = os.environ.get('JELLYSEERR_USERNAME', '')
JELLYSEERR_PASSWORD = os.environ.get('JELLYSEERR_PASSWORD', '')
API_BASE = f"{JELLYSEERR_URL.rstrip('/')}/api/v1/"

cookie_jar = CookieJar()
cookie_processor = HTTPCookieProcessor(cookie_jar)
opener = build_opener(cookie_processor)
install_opener(opener)


def api_request(endpoint, method='GET', data=None, debug=False):
    headers = {'Content-Type': 'application/json'}
    
    if JELLYSEERR_API_KEY:
        headers['X-Api-Key'] = JELLYSEERR_API_KEY
    
    url = f"{API_BASE}{endpoint.lstrip('/')}"
    
    req = Request(url, headers=headers, method=method)
    if data:
        req.data = json.dumps(data).encode('utf-8')
    
    try:
        response = opener.open(req)
        result = json.loads(response.read().decode('utf-8'))
        if debug:
            print(f"DEBUG: API Response for {method} {endpoint}:", file=sys.stderr)
            print(json.dumps(result, indent=2), file=sys.stderr)
        return result
    except HTTPError as e:
        error_body = ''
        if hasattr(e, 'read') and e.fp:
            try:
                error_body = e.read().decode('utf-8')
            except:
                pass
        print(f"HTTP {e.code} Error: {error_body or e.reason}", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"Connection Error: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def login():
    if not JELLYSEERR_USERNAME or not JELLYSEERR_PASSWORD:
        print("Error: JELLYSEERR_USERNAME and JELLYSEERR_PASSWORD environment variables not set", file=sys.stderr)
        print("Note: The API accepts your Jellyseer username (not email)", file=sys.stderr)
        sys.exit(1)
    
    data = {
        'email': JELLYSEERR_USERNAME,
        'password': JELLYSEERR_PASSWORD
    }
    
    result = api_request('/auth/local', method='POST', data=data)
    
    if result.get('id'):
        print(f"Logged in as: {result.get('displayName') or result.get('username') or result.get('email') or 'Unknown'}")
        return result
    
    print("Login failed", file=sys.stderr)
    sys.exit(1)


def search(query, page=1, language='en', debug=False):
    encoded_query = quote(query)
    result = api_request(f"/search?query={encoded_query}&page={page}&language={language}", debug=debug)
    
    if not result.get('results'):
        print(f"No results found for: {query}")
        return
    
    for item in result['results']:
        media_type = item.get('mediaType', 'unknown').upper()
        title = item.get('title') or item.get('name') or 'Unknown'
        if not title or title == 'None' or title == 'null':
            title = 'Unknown'
        date_str = item.get('releaseDate') or item.get('firstAirDate') or ''
        year = date_str[:4] if date_str else 'N/A'
        rating = item.get('voteAverage', 'N/A')
        media_id = item.get('id', 'N/A')
        
        print(f"[{media_type}] {title} ({year}) - Rating: {rating} - ID: {media_id}")


def request_media(media_type, media_id, seasons=None, is4k=False, debug=False):
    if seasons and media_type != 'tv':
        print("Error: Seasons can only be specified for TV shows", file=sys.stderr)
        sys.exit(1)
    
    data = {
        'mediaType': media_type,
        'mediaId': media_id
    }
    
    if seasons:
        data['seasons'] = seasons
    
    if is4k:
        data['is4k'] = True
    
    result = api_request('/request', method='POST', data=data, debug=debug)
    
    status = result.get('status')
    status_map = {1: 'PENDING APPROVAL', 2: 'APPROVED', 3: 'DECLINED'}
    
    print(f"Request created! Status: {status_map.get(status, 'UNKNOWN')}")
    print(f"Request ID: {result.get('id')}")


def list_requests(filter_type='all', media_type='all', take=20, debug=False):
    params = f"?filter={quote(filter_type)}&mediaType={quote(media_type)}&take={take}"
    result = api_request(f"/request{params}", debug=debug)
    
    if not result.get('results'):
        print(f"No requests found")
        return
    
    for req in result['results']:
        media = req.get('media', {})
        req_media_type = media.get('mediaType', 'unknown').upper()
        req_id = req.get('id', 'N/A')
        status = req.get('status')
        status_map = {1: 'PENDING', 2: 'APPROVED', 3: 'DECLINED', 4: 'PROCESSING', 5: 'AVAILABLE', 6: 'DELETED'}
        
        title = media.get('title') or media.get('name')
        if not title or title == 'None' or title == 'null':
            tmdb_id = media.get('tmdbId')
            if tmdb_id:
                try:
                    media_type_lower = media.get('mediaType', '').lower()
                    if media_type_lower == 'movie':
                        media_details = api_request(f"/movie/{tmdb_id}", debug=debug)
                        title = media_details.get('title')
                    elif media_type_lower == 'tv':
                        media_details = api_request(f"/tv/{tmdb_id}", debug=debug)
                        title = media_details.get('name')
                    
                    if not title or title == 'None' or title == 'null':
                        title = f"<TMDB ID: {tmdb_id}>"
                except:
                    title = f"<TMDB ID: {tmdb_id}>"
            else:
                title = f"<No title info available>"
        
        seasons_info = ''
        seasons = req.get('seasons')
        if req_media_type == 'TV' and seasons:
            seasons_info = f" (Seasons: {', '.join(str(s) for s in seasons)})"
        
        print(f"[{req_id}] {req_media_type}: {title}{seasons_info} - Status: {status_map.get(status, 'UNKNOWN')}")


def get_request_details(request_id, debug=False):
    result = api_request(f"/request/{request_id}", debug=debug)
    
    media = result.get('media', {})
    media_type = media.get('mediaType', 'unknown').upper()
    title = media.get('title') or media.get('name')
    if not title or title == 'None' or title == 'null':
        tmdb_id = media.get('tmdbId')
        if tmdb_id:
            try:
                media_type_lower = media.get('mediaType', '').lower()
                if media_type_lower == 'movie':
                    media_details = api_request(f"/movie/{tmdb_id}", debug=debug)
                    title = media_details.get('title')
                elif media_type_lower == 'tv':
                    media_details = api_request(f"/tv/{tmdb_id}", debug=debug)
                    title = media_details.get('name')
                
                if not title or title == 'None' or title == 'null':
                    title = f"<TMDB ID: {tmdb_id}>"
            except:
                title = f"<TMDB ID: {tmdb_id}>"
        else:
            title = '<No title info available>'
    
    created_at = result.get('createdAt', '')
    formatted_date = 'N/A'
    if created_at:
        try:
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            formatted_date = dt.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            formatted_date = created_at if created_at else 'N/A'
    
    print(f"Request ID: {result.get('id', 'N/A')}")
    print(f"Media: {title}")
    print(f"Type: {media_type}")
    print(f"4K: {'Yes' if result.get('is4k') else 'No'}")
    print(f"Created: {formatted_date}")


def get_request_counts(debug=False):
    result = api_request('/request/count', debug=debug)
    print(f"Pending: {result.get('pending', 0)}")
    print(f"Approved: {result.get('approved', 0)}")
    print(f"Available: {result.get('available', 0)}")
    print(f"Completed: {result.get('completed', 0)}")


def main():
    parser = argparse.ArgumentParser(description='Jellyseerr CLI')
    parser.add_argument('--debug', action='store_true', help='Show raw API responses')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    search_parser = subparsers.add_parser('search', help='Search for movies, TV shows, or people')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--page', type=int, default=1, help='Page number (default: 1)')
    search_parser.add_argument('--language', default='en', help='Language code (default: en)')
    
    request_parser = subparsers.add_parser('request', help='Request media')
    request_parser.add_argument('media_type', choices=['movie', 'tv'], help='Media type')
    request_parser.add_argument('media_id', type=int, help='Media TMDB ID')
    request_parser.add_argument('--seasons', help='Season numbers (comma-separated or "all")')
    request_parser.add_argument('--4k', action='store_true', dest='four_k', help='Request 4K version')
    
    list_parser = subparsers.add_parser('list', help='List requests')
    list_parser.add_argument('--filter', choices=['all', 'approved', 'available', 'pending', 'processing', 'deleted', 'completed'], default='all', help='Filter requests')
    list_parser.add_argument('--media-type', choices=['movie', 'tv', 'all'], default='all', help='Media type filter')
    list_parser.add_argument('--take', type=int, default=20, help='Number of results (default: 20)')
    
    subparsers.add_parser('counts', help='Get request counts')
    
    details_parser = subparsers.add_parser('details', help='Get request details')
    details_parser.add_argument('request_id', type=int, help='Request ID')
    
    login_parser = subparsers.add_parser('login', help='Login to Jellyseerr (for cookie auth)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == 'login':
        login()
        sys.exit(0)
    
    if not JELLYSEERR_API_KEY and not (JELLYSEERR_USERNAME and JELLYSEERR_PASSWORD):
        print("Error: Either JELLYSEERR_API_KEY or JELLYSEERR_USERNAME + JELLYSEERR_PASSWORD must be set", file=sys.stderr)
        print("Note: Use your Jellyseerr username (not email) for cookie auth", file=sys.stderr)
        sys.exit(1)
    
    if JELLYSEERR_USERNAME and JELLYSEERR_PASSWORD and not JELLYSEERR_API_KEY:
        login()
    
    if args.command == 'search':
        search(args.query, args.page, args.language, args.debug)
    elif args.command == 'request':
        seasons = None
        if args.seasons:
            if args.seasons.lower() == 'all':
                seasons = 'all'
            else:
                try:
                    seasons = [int(s.strip()) for s in args.seasons.split(',')]
                except ValueError:
                    print("Error: Seasons must be numbers separated by commas (e.g., '1,2,3') or 'all'", file=sys.stderr)
                    sys.exit(1)
        request_media(args.media_type, args.media_id, seasons, args.four_k, args.debug)
    elif args.command == 'list':
        list_requests(args.filter, args.media_type, args.take, args.debug)
    elif args.command == 'counts':
        get_request_counts(args.debug)
    elif args.command == 'details':
        get_request_details(args.request_id, args.debug)


if __name__ == '__main__':
    main()
