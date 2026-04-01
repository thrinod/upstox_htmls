import time
import hmac
import hashlib
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app) # Enable CORS for all routes

# --- Configuration ---
DELTA_API_BASE_URL = 'https://api.india.delta.exchange'
API_VERSION = '/v2'

# --- Python HMAC Signature Generation ---
def generate_signature(method, timestamp, request_path, query_params, request_body, secret):
    """Generates the HMAC SHA256 signature for Delta Exchange API."""
    if not secret:
        raise ValueError('API Secret missing for signature generation.')

    # Ensure method is uppercase
    method = method.upper()

    # The requestBody for signature must be identical to the actual request body string
    # and its internal quotes must be escaped.
    # From previous debugging, the server expects `{\"key\":\"value\"}` for the body.
    if request_body:
        # Step 1: Stringify the Python dict to a JSON string (e.g., '{"product_id":91472}')
        json_body_string = json.dumps(request_body, separators=(',', ':')) # separators removes whitespace
        # Step 2: Escape all double quotes within this JSON string
        # This converts '{"product_id":91472}' into '{\"product_id\":91472}'
        request_body_for_signature = json_body_string.replace('"', '\\"')
    else:
        request_body_for_signature = ''

    # Build the string to sign
    string_to_sign = f"{method}{timestamp}{request_path}{query_params}{request_body_for_signature}"

    print(f"[DEBUG] Backend string_to_sign (pre-hash): \"{string_to_sign}\"")

    # Generate HMAC SHA256 signature
    signature = hmac.new(
        secret.encode('utf-8'),
        string_to_sign.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    print(f"[DEBUG] Backend Generated HMAC Signature (Hex): {signature}")
    return signature

# --- API Helper Function (Backend's wrapper for Delta Exchange) ---
def make_delta_api_call(endpoint, method='GET', body=None, requires_auth=False, api_key=None, api_secret=None):
    """
    Makes a call to the Delta Exchange API.
    Handles signature generation if requires_auth is True.
    """
    url = f"{DELTA_API_BASE_URL}{endpoint}"
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'python-flask-api'
    }

    if requires_auth:
        if not api_key or not api_secret:
            raise ValueError('API Key or Secret missing for authenticated call.')

        current_timestamp = str(int(time.time())) # Unix epoch seconds as string

        # Extract path and query for signature
        full_request_path = f"{API_VERSION}{endpoint}"
        path_parts = full_request_path.split('?')
        path_for_signature = path_parts[0]
        query_params_for_signature = f"?{path_parts[1]}" if len(path_parts) > 1 else ''

        signature = generate_signature(
            method,
            current_timestamp,
            path_for_signature,
            query_params_for_signature,
            body, # Pass the Python dict body, generate_signature will handle stringifying and escaping
            api_secret
        )

        headers['api-key'] = api_key
        headers['timestamp'] = current_timestamp
        headers['signature'] = signature

    if (method == 'POST' or method == 'PUT') and body:
        headers['Content-Type'] = 'application/json'

    # Convert Python dict body to JSON string for the actual request
    json_data = json.dumps(body, separators=(',', ':')) if body else None # separators removes whitespace

    print(f"[REQUEST] Backend calling Delta: {method} {url}, Headers: {headers}, Body: {json_data}")

    try:
        response = requests.request(method, url, headers=headers, data=json_data)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        data = response.json()
        print(f"[RESPONSE] From Delta: {response.status_code}, Data: {json.dumps(data, indent=2)}")

        if not response.ok or (data.get('success') is not None and not data['success']):
            error_context = data.get('error', {}).get('context', '')
            error_msg = data.get('error', {}).get('message', 'Unknown error')
            raise requests.exceptions.RequestException(
                f"Delta API Error ({response.status_code}): {error_msg} {error_context}"
            )
        return data
    except requests.exceptions.HTTPError as http_err:
        print(f"[ERROR] HTTP Error calling Delta: {http_err} - {response.text}")
        raise ValueError(f"HTTP Error: {http_err.response.status_code} - {http_err.response.text}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"[ERROR] Connection Error calling Delta: {conn_err}")
        raise ValueError(f"Connection Error: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"[ERROR] Timeout Error calling Delta: {timeout_err}")
        raise ValueError(f"Timeout Error: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"[ERROR] Request Error calling Delta: {req_err}")
        raise ValueError(f"Request Error: {req_err}")
    except json.JSONDecodeError:
        print(f"[ERROR] JSON Decode Error from Delta response: {response.text}")
        raise ValueError(f"Invalid JSON response from Delta: {response.text}")
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}")
        raise ValueError(f"An unexpected error occurred: {e}")


# --- Flask API Endpoints ---

@app.route('/api/option_chain', methods=['GET'])
def get_option_chain():
    try:
        api_key = request.headers.get('x-api-key')
        api_secret = request.headers.get('x-api-secret')
        asset = request.args.get('asset')
        expiry_date_raw = request.args.get('expiry_date') # YYYY-MM-DD
        
        if not all([api_key, api_secret, asset, expiry_date_raw]):
            return jsonify({'success': False, 'error': 'Missing required parameters (API Key/Secret, asset, expiry_date)'}), 400

        # Format expiry_date from YYYY-MM-DD to DD-MM-YYYY
        year, month, day = expiry_date_raw.split('-')
        expiry_date_formatted = f"{day}-{month}-{year}"

        endpoint = f"/tickers?contract_types=call_options,put_options&underlying_asset_symbols={asset}&expiry_date={expiry_date_formatted}"
        
        response_data = make_delta_api_call(endpoint, method='GET', requires_auth=True, api_key=api_key, api_secret=api_secret)
        
        return jsonify(response_data), 200
    except ValueError as ve:
        return jsonify({'success': False, 'error': str(ve)}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': f'An unexpected error occurred: {e}'}), 500

@app.route('/api/place_order', methods=['POST'])
def place_order():
    try:
        api_key = request.headers.get('x-api-key')
        api_secret = request.headers.get('x-api-secret')
        order_payload_raw = request.get_json()

        if not all([api_key, api_secret, order_payload_raw]):
            return jsonify({'success': False, 'error': 'Missing required parameters (API Key/Secret, order payload)'}), 400

        # Validate minimal payload fields
        required_fields = ['product_id', 'size', 'side', 'order_type']
        if not all(field in order_payload_raw for field in required_fields):
            return jsonify({'success': False, 'error': f'Missing one or more required fields in order payload: {required_fields}'}), 400
        
        if order_payload_raw['order_type'] == 'limit_order' and 'limit_price' not in order_payload_raw:
             return jsonify({'success': False, 'error': 'limit_price is required for limit_order'}), 400

        endpoint = "/orders"
        response_data = make_delta_api_call(
            endpoint,
            method='POST',
            body=order_payload_raw, # Pass the dict directly
            requires_auth=True,
            api_key=api_key,
            api_secret=api_secret
        )
        
        return jsonify(response_data), 200
    except ValueError as ve:
        return jsonify({'success': False, 'error': str(ve)}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': f'An unexpected error occurred: {e}'}), 500

if __name__ == '__main__':
    # Run the Flask app
    # Host '0.0.0.0' makes it accessible from other devices on your network
    # For local development, '127.0.0.1' or 'localhost' is fine.
    app.run(debug=True, host='127.0.0.1', port=5000)