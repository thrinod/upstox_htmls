document.addEventListener('DOMContentLoaded', () => {
    const fetchChainBtn = document.getElementById('fetchChainBtn');
    const placeMultiOrderBtn = document.getElementById('placeMultiOrderBtn');
    const instrumentKeyInput = document.getElementById('instrumentKey');
    const expiryDateInput = document.getElementById('expiryDate');
    const optionChainContainer = document.getElementById('optionChainContainer');
    const orderControlsDiv = document.getElementById('orderControls');
    const logsPre = document.getElementById('logs');
    const quantityInput = document.getElementById('quantity');

    const API_BASE_URL = 'https://api.upstox.com/v2';
    let accessToken = null;

    // --- Utility Functions ---
    function logMessage(message, type = 'info') {
        const timestamp = new Date().toLocaleTimeString();
        const logEntry = document.createElement('div');
        logEntry.textContent = `[${timestamp}] ${message}`;
        if (type === 'error') {
            logEntry.classList.add('log-error');
        } else if (type === 'success') {
             logEntry.classList.add('log-success');
        }
        logsPre.appendChild(logEntry);
        logsPre.scrollTop = logsPre.scrollHeight; // Auto-scroll to bottom
    }

    function getToken() {
        accessToken = localStorage.getItem('upstoxAccessToken');
        if (!accessToken) {
            logMessage('Error: Upstox Access Token not found in Local Storage.', 'error');
            logMessage('Please obtain a token via Upstox OAuth flow and store it as "upstoxAccessToken" in Local Storage.', 'info');
            fetchChainBtn.disabled = true;
            placeMultiOrderBtn.disabled = true;
            return false;
        }
        logMessage('Access Token found in Local Storage.', 'success');
        // Optional: Add token validation logic here if needed (e.g., check expiry)
        return true;
    }

    // --- API Call Functions ---

    async function fetchOptionChain(instrumentKey, expiryDate) {
        if (!accessToken) {
            logMessage('Cannot fetch: Access Token missing.', 'error');
            return;
        }
        if (!instrumentKey || !expiryDate) {
            logMessage('Please provide both Instrument Key and Expiry Date.', 'error');
            return;
        }

        logMessage(`Fetching option chain for ${instrumentKey} expiring on ${expiryDate}...`);
        optionChainContainer.innerHTML = '<p>Loading option chain...</p>';
        fetchChainBtn.disabled = true;
        orderControlsDiv.style.display = 'none'; // Hide order controls while fetching


        const url = `${API_BASE_URL}/market/option/chain?instrument_key=${encodeURIComponent(instrumentKey)}&expiry_date=${expiryDate}`;

        try {
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Authorization': `Bearer ${accessToken}`
                }
            });

            const data = await response.json();

            if (response.ok && data.status === 'success') {
                logMessage('Option chain data fetched successfully.', 'success');
                displayOptionChain(data.data); // Pass the actual chain data array
                orderControlsDiv.style.display = 'block'; // Show order controls
            } else {
                const errorMsg = data.errors?.[0]?.message || JSON.stringify(data);
                logMessage(`Error fetching option chain: ${response.status} - ${errorMsg}`, 'error');
                optionChainContainer.innerHTML = `<p class="log-error">Error fetching option chain: ${errorMsg}</p>`;
                 orderControlsDiv.style.display = 'none';
            }
        } catch (error) {
            logMessage(`Network or other error fetching option chain: ${error.message}`, 'error');
            optionChainContainer.innerHTML = `<p class="log-error">Failed to fetch. Check console/network tab for details.</p>`;
             orderControlsDiv.style.display = 'none';
        } finally {
             fetchChainBtn.disabled = false;
        }
    }

    async function placeOrder(orderPayload) {
         if (!accessToken) {
            logMessage('Cannot place order: Access Token missing.', 'error');
            return { success: false, message: 'Access Token missing.' };
        }

        const url = `${API_BASE_URL}/order/place`;
        logMessage(`Placing order: ${orderPayload.transaction_type} ${orderPayload.quantity} ${orderPayload.instrument_token} @ ${orderPayload.order_type}`);

        try {
             const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'Authorization': `Bearer ${accessToken}`
                },
                body: JSON.stringify(orderPayload)
             });

             const data = await response.json();

            if (response.ok && data.status === 'success') {
                 const orderId = data.data?.order_id || 'N/A';
                 logMessage(`Order placed successfully for ${orderPayload.instrument_token}. Order ID: ${orderId}`, 'success');
                 return { success: true, orderId: orderId, instrument: orderPayload.instrument_token };
             } else {
                 const errorMsg = data.errors?.[0]?.message || JSON.stringify(data);
                 logMessage(`Order placement failed for ${orderPayload.instrument_token}: ${response.status} - ${errorMsg}`, 'error');
                 return { success: false, message: errorMsg, instrument: orderPayload.instrument_token };
             }

        } catch (error) {
            logMessage(`Network or other error placing order for ${orderPayload.instrument_token}: ${error.message}`, 'error');
             return { success: false, message: error.message, instrument: orderPayload.instrument_token };
        }
    }

    // --- Display Functions ---

    function displayOptionChain(chainData) {
        if (!chainData || chainData.length === 0) {
            optionChainContainer.innerHTML = '<p>No option chain data received or chain is empty.</p>';
            return;
        }

        // Sort data by strike price (API might already do this, but good practice)
        chainData.sort((a, b) => a.strike_price - b.strike_price);

        let tableHTML = `
            <table class="option-chain-table">
                <thead>
                    <tr>
                        <th class="call-header" colspan="6">CALLS</th>
                        <th class="strike-header">STRIKE</th>
                        <th class="put-header" colspan="6">PUTS</th>
                    </tr>
                    <tr>
                        <!-- Calls -->
                        <th class="call-header">OI</th>
                        <th class="call-header">Chng OI</th>
                        <th class="call-header">LTP</th>
                        <th class="call-header">IV</th>
                        <th class="call-header">Volume</th>
                        <th class="call-header">Select</th>
                        <!-- Strike -->
                        <th class="strike-header">Price</th>
                        <!-- Puts -->
                        <th class="put-header">Select</th>
                        <th class="put-header">Volume</th>
                         <th class="put-header">IV</th>
                        <th class="put-header">LTP</th>
                        <th class="put-header">Chng OI</th>
                        <th class="put-header">OI</th>
                    </tr>
                </thead>
                <tbody>
        `;

        chainData.forEach(item => {
            const strike = item.strike_price || '-';
            const call = item.call_options?.market_data || {};
            const put = item.put_options?.market_data || {};
            const callInstrumentKey = item.call_options?.instrument_key || '';
            const putInstrumentKey = item.put_options?.instrument_key || '';

            tableHTML += `
                <tr>
                    <!-- Call Data -->
                    <td>${call.open_interest ?? '-'}</td>
                    <td>${call.oi_change ?? '-'}</td>
                    <td>${call.last_price ?? '-'}</td>
                    <td>${call.implied_volatility ?? '-'}</td>
                    <td>${call.volume ?? '-'}</td>
                    <td>
                        ${callInstrumentKey ? `<input type="checkbox" class="option-checkbox" value="${callInstrumentKey}" data-type="CE" data-strike="${strike}">` : ''}
                    </td>

                    <!-- Strike Price -->
                    <td>${strike}</td>

                    <!-- Put Data -->
                     <td>
                         ${putInstrumentKey ? `<input type="checkbox" class="option-checkbox" value="${putInstrumentKey}" data-type="PE" data-strike="${strike}">` : ''}
                    </td>
                    <td>${put.volume ?? '-'}</td>
                     <td>${put.implied_volatility ?? '-'}</td>
                    <td>${put.last_price ?? '-'}</td>
                    <td>${put.oi_change ?? '-'}</td>
                    <td>${put.open_interest ?? '-'}</td>
                </tr>
            `;
        });

        tableHTML += `</tbody></table>`;
        optionChainContainer.innerHTML = tableHTML;
    }

    // --- Event Handlers ---

    fetchChainBtn.addEventListener('click', () => {
        const instrumentKey = instrumentKeyInput.value.trim();
        const expiryDate = expiryDateInput.value;
        fetchOptionChain(instrumentKey, expiryDate);
    });

    placeMultiOrderBtn.addEventListener('click', async () => {
        const selectedCheckboxes = document.querySelectorAll('.option-checkbox:checked');
        if (selectedCheckboxes.length === 0) {
            logMessage('No options selected for ordering.', 'error');
            alert('Please select at least one option checkbox to place orders.');
            return;
        }

        const quantity = parseInt(quantityInput.value, 10);
        if (isNaN(quantity) || quantity <= 0) {
            logMessage('Invalid quantity specified.', 'error');
            alert('Please enter a valid quantity greater than 0.');
            return;
        }

        const transactionType = document.querySelector('input[name="orderAction"]:checked').value; // BUY or SELL
        const productType = document.querySelector('input[name="productType"]:checked').value; // I or D
        const orderType = document.querySelector('input[name="orderType"]:checked').value; // MARKET (add LIMIT later if needed)

        logMessage(`--- Initiating Multi-Order Placement (${transactionType}) ---`);
        placeMultiOrderBtn.disabled = true;

        const orderPromises = [];

        selectedCheckboxes.forEach(checkbox => {
            const instrumentKey = checkbox.value;
            // Basic payload - Adjust price, trigger_price etc for other order types
            const payload = {
                quantity: quantity,
                product: productType,
                validity: "DAY",
                price: 0, // 0 for Market Order
                tag: "multi_order_tool", // Optional tag
                instrument_token: instrumentKey,
                order_type: orderType,
                transaction_type: transactionType,
                disclosed_quantity: 0,
                trigger_price: 0, // Required for SL/SL-M
                is_amo: false // Set true for After Market Orders
            };
            // IMPORTANT: For safety, place orders sequentially using await in a loop,
            // rather than Promise.all, to avoid hitting rate limits too easily.
            // orderPromises.push(placeOrder(payload)); // Don't use Promise.all for now
        });

        // Place orders sequentially
        let successCount = 0;
        let failCount = 0;
        for (const checkbox of selectedCheckboxes) {
             const instrumentKey = checkbox.value;
             const payload = { /* construct payload as above */
                quantity: quantity, product: productType, validity: "DAY", price: 0,
                instrument_token: instrumentKey, order_type: orderType, transaction_type: transactionType,
                disclosed_quantity: 0, trigger_price: 0, is_amo: false, tag: "multi_order_tool"
            };
            const result = await placeOrder(payload); // Await ensures sequential execution
            if (result.success) {
                successCount++;
            } else {
                failCount++;
            }
            // Optional: Add a small delay between orders if needed
            // await new Promise(resolve => setTimeout(resolve, 200)); // e.g., 200ms delay
        }


        // If using Promise.all (can hit rate limits):
        // const results = await Promise.all(orderPromises);
        // const successCount = results.filter(r => r.success).length;
        // const failCount = results.length - successCount;

        logMessage(`--- Multi-Order Placement Complete ---`);
        logMessage(`Successfully placed: ${successCount}, Failed: ${failCount}`, successCount > 0 && failCount === 0 ? 'success' : (failCount > 0 ? 'error' : 'info'));

        placeMultiOrderBtn.disabled = false;
        // Optional: Uncheck boxes after ordering
        // selectedCheckboxes.forEach(cb => cb.checked = false);
    });


    // --- Initialization ---
    if (!getToken()) {
        // Disable inputs if token is not found initially
        instrumentKeyInput.disabled = true;
        expiryDateInput.disabled = true;
    } else {
         fetchChainBtn.disabled = false; // Enable fetch button if token exists
         placeMultiOrderBtn.disabled = false; // Should initially be linked to chain display
    }
     orderControlsDiv.style.display = 'none'; // Hide order controls initially

});

document.addEventListener('DOMContentLoaded', () => {
    const indexSelect = document.getElementById('indexSelect');
    const expiryDateInput = document.getElementById('expiryDate');
    const fetchChainBtn = document.getElementById('fetchChainBtn');
    const optionsArea = document.getElementById('optionsArea');
    const callOptionsSelect = document.getElementById('callOptions');
    const putOptionsSelect = document.getElementById('putOptions');
    const buyCallBtn = document.getElementById('buyCallBtn');
    const buyPutBtn = document.getElementById('buyPutBtn');
    const callQuantityInput = document.getElementById('callQuantity');
    const putQuantityInput = document.getElementById('putQuantity');
    const logDiv = document.getElementById('log');
    const tokenStatusSpan = document.getElementById('tokenStatus');
    const underlyingLtpSpan = document.getElementById('underlyingLtp');
    const atmStrikeSpan = document.getElementById('atmStrike');

    const UPSTOX_API_BASE = 'https://api.upstox.com/v2';
    let accessToken = null;

    // --- Utility Functions ---

    function logMessage(message, isError = false) {
        const timestamp = new Date().toLocaleTimeString();
        const logEntry = document.createElement('div');
        logEntry.textContent = `[${timestamp}] ${message}`;
        if (isError) {
            logEntry.classList.add('log-error');
        }
        logDiv.appendChild(logEntry);
        logDiv.scrollTop = logDiv.scrollHeight; // Auto-scroll
    }

    function getAccessToken() {
        accessToken = localStorage.getItem('upstoxAccessToken');
        if (!accessToken) {
            logMessage('ERROR: Access Token not found in localStorage key "upstoxAccessToken". Please login first.', true);
            tokenStatusSpan.textContent = 'Status: Not Found!';
            tokenStatusSpan.style.color = 'red';
            return false;
        }
        logMessage('Access Token retrieved from localStorage.');
        tokenStatusSpan.textContent = 'Status: Found (masked)'; // Don't display the token itself
        tokenStatusSpan.style.color = 'green';
        return true;
    }

    function disableButtons(disabled) {
        fetchChainBtn.disabled = disabled;
        buyCallBtn.disabled = disabled;
        buyPutBtn.disabled = disabled;
    }

    // --- API Call Functions ---

    async function makeApiCall(endpoint, method = 'GET', body = null) {
        if (!accessToken) {
            logMessage('Cannot make API call: Access Token is missing.', true);
            return null;
        }

        const url = `${UPSTOX_API_BASE}${endpoint}`;
        const headers = {
            'Authorization': `Bearer ${accessToken}`,
            'Accept': 'application/json'
        };

        const options = {
            method: method,
            headers: headers
        };

        if (body && (method === 'POST' || method === 'PUT')) {
            headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(body);
        }

        logMessage(`Calling API: ${method} ${url}`);
        disableButtons(true);

        try {
            const response = await fetch(url, options);

            // Attempt to parse JSON regardless of status for potential error details
            let responseData = null;
            try {
                responseData = await response.json();
            } catch (parseError) {
                logMessage(`Could not parse JSON response from ${method} ${url}`, true)
                // Don't throw here, let the status check handle it
            }

            if (!response.ok) {
                const errorMsg = responseData?.errors?.[0]?.message || responseData?.message || `HTTP error! Status: ${response.status}`;
                logMessage(`API Error (${response.status}): ${errorMsg}`, true);
                console.error("API Error Details:", responseData);
                return null; // Indicate failure
            }

            logMessage(`API Success: ${method} ${url} (${response.status})`);
            return responseData; // Return parsed JSON data

        } catch (error) {
            logMessage(`Network or other error calling API: ${error}`, true);
            console.error("Fetch Error:", error);
            return null; // Indicate failure
        } finally {
            disableButtons(false);
        }
    }

    // --- Core Logic ---

    async function fetchUnderlyingLtp(index) {
        // Map index name to Upstox instrument key format
        let instrumentKey;
        if (index === 'NIFTY') {
            instrumentKey = 'NSE_INDEX|Nifty 50';
        } else if (index === 'BANKNIFTY') {
            instrumentKey = 'NSE_INDEX|Nifty Bank';
        } else {
            logMessage(`Unsupported index: ${index}`, true);
            return null;
        }

        // URL encode the instrument key
        const instrumentKeyResp = instrumentKey.replace("|", ":");
        const encodedKey = encodeURIComponent(instrumentKey);
        const endpoint = `/market-quote/quotes?instrument_key=${encodedKey}`;
        const response = await makeApiCall(endpoint);

        if (response && response.data && response.data[instrumentKeyResp]) {
             const ltp = response.data[instrumentKeyResp].last_price;
             logMessage(`Fetched LTP for ${index}: ${ltp}`);
             return ltp;
        } else {
            logMessage(`Could not fetch LTP for ${index}. Response missing data.`, true);
            console.error("LTP Fetch Response:", response);
            return null;
        }
    }

    function getStrikeInterval(index) {
        if (index === 'NIFTY') return 50;
        if (index === 'BANKNIFTY') return 100;
        return 50; // Default
    }

    function calculateAtmStrikes(ltp, index) {
        if (ltp === null || ltp === undefined) return { atmStrike: null, strikes: [] };

        const interval = getStrikeInterval(index);
        const atmStrike = Math.round(ltp / interval) * interval;

        const strikes = [];
        for (let i = -2; i <= 2; i++) {
            strikes.push(atmStrike + i * interval);
        }
        return { atmStrike, strikes };
    }

    // **IMPORTANT:** Adjust this function based on Upstox's EXACT instrument key format
    function formatInstrumentKey(index, expiryDateStr, strike, optionType) {
        // Input expiryDateStr is 'YYYY-MM-DD'
        // Needs conversion to Upstox format (e.g., YYMMMDD or YYDDM? Check Docs!)
        // Example assuming YYMonDD (e.g., 24JUL04):
        try {
            const date = new Date(expiryDateStr + 'T00:00:00'); // Ensure parsing as local date
            if (isNaN(date.getTime())) throw new Error("Invalid date");

            const year = date.getFullYear().toString().slice(-2); // YY
            const month = date.toLocaleString('en-US', { month: 'short' }).toUpperCase(); // MON (e.g., JUL)
            const day = ('0' + date.getDate()).slice(-2); // DD

            // **CRUCIAL:** Verify this format with Upstox Docs for options!
            // Might be YYMMDD or YY<Month Initial>DD e.g. 24704 for 4th July 2024
            // Let's try YY + Month Initial (numeric) + DD format - **THIS IS A GUESS**
            const monthNum = ('0' + (date.getMonth() + 1)).slice(-2);
            const upstoxExpiry = `${year}${monthNum}${day}`; // e.g., 240718 for 18 Jul 2024

             // Format for Index Options (Needs confirmation from Upstox Docs)
             // NSE_FO | INDEXNAME + YY + MON (Letter?) + DD + STRIKE + TYPE
             // Example: NSE_FO|NIFTY24JUL1822500CE - Let's try constructing this
             const upstoxExpiryYYMMMDD = `${year}${month}${day}`; // e.g., 24JUL18
             const key = `NSE_FO|${index}${upstoxExpiryYYMMMDD}${strike}${optionType}`;
             logMessage(`Constructed key: ${key}`); // Log the constructed key for debugging
             return key;

            // --- Alternative GUESS (YYMMDD format) ---
            // const upstoxExpiryYYMMDD = `${year}${monthNum}${day}`; // e.g., 240718
            // const key = `NSE_FO|${index}${upstoxExpiryYYMMDD}${strike}${optionType}`;
            // logMessage(`Constructed key (YYMMDD): ${key}`);
            // return key;


        } catch (e) {
            logMessage(`Error formatting date ${expiryDateStr}: ${e.message}`, true);
            return null;
        }
    }


    async function fetchAndDisplayAtmOptions() {
        const selectedIndex = indexSelect.value;
        const expiryDate = expiryDateInput.value; // Format: YYYY-MM-DD

        if (!expiryDate) {
            logMessage('Please select an expiry date.', true);
            return;
        }

        logMessage(`Fetching ATM options for ${selectedIndex}, Expiry: ${expiryDate}`);
        optionsArea.style.display = 'none'; // Hide until data is ready
        callOptionsSelect.innerHTML = ''; // Clear previous options
        putOptionsSelect.innerHTML = '';

        const ltp = await fetchUnderlyingLtp(selectedIndex);
        underlyingLtpSpan.textContent = ltp !== null ? ltp : 'Error';

        if (ltp === null) {
             logMessage('Failed to get Underlying LTP. Cannot proceed.', true);
             return;
        }

        const { atmStrike, strikes } = calculateAtmStrikes(ltp, selectedIndex);
        atmStrikeSpan.textContent = atmStrike !== null ? atmStrike : 'Error';


        if (!strikes || strikes.length === 0) {
            logMessage('Could not calculate ATM strikes.', true);
            return;
        }

        logMessage(`Calculated ATM Strike: ${atmStrike}. Nearby strikes: ${strikes.join(', ')}`);

        let atmCallOption = null;
        let atmPutOption = null;

        strikes.forEach(strike => {
            // Create Call Option Entry
            const callKey = formatInstrumentKey(selectedIndex, expiryDate, strike, 'CE');
            if (callKey) {
                const callOption = document.createElement('option');
                callOption.value = callKey; // Value is the API instrument key
                callOption.textContent = `${selectedIndex} ${strike} CE (${expiryDate})`; // Display text
                callOptionsSelect.appendChild(callOption);
                if (strike === atmStrike) atmCallOption = callOption;
            } else {
                 logMessage(`Skipping Call for strike ${strike} due to key formatting error.`, true);
            }


            // Create Put Option Entry
            const putKey = formatInstrumentKey(selectedIndex, expiryDate, strike, 'PE');
             if (putKey) {
                const putOption = document.createElement('option');
                putOption.value = putKey; // Value is the API instrument key
                putOption.textContent = `${selectedIndex} ${strike} PE (${expiryDate})`; // Display text
                putOptionsSelect.appendChild(putOption);
                if (strike === atmStrike) atmPutOption = putOption;
             } else {
                 logMessage(`Skipping Put for strike ${strike} due to key formatting error.`, true);
             }
        });

        // Select the ATM options by default
        if (atmCallOption) atmCallOption.selected = true;
        if (atmPutOption) atmPutOption.selected = true;

        optionsArea.style.display = 'block'; // Show the options section
        logMessage('ATM (+/- 2 strikes) options populated.');
    }


    async function placeOrder(instrumentKey, quantity) {
        if (!instrumentKey) {
            logMessage('No instrument selected for placing order.', true);
            return;
        }
         if (!quantity || quantity <= 0) {
            logMessage('Invalid quantity specified.', true);
            return;
        }


        logMessage(`Placing BUY MARKET order for ${instrumentKey}, Quantity: ${quantity}`);

        const orderPayload = {
            quantity: parseInt(quantity, 10), // Ensure it's a number
            product: "I", // I for Intraday, D for Delivery (NRML), CO, BO etc. Check Upstox docs.
            validity: "DAY",
            order_type: "MARKET", // Or LIMIT, SL, SL-M
            transaction_type: "BUY",
            instrument_token: instrumentKey, // This is the 'value' from the select box
            // For LIMIT orders, add 'price': desired_price
            // For SL/SL-M orders, add 'trigger_price': trigger_price
             price: 0, // Required for MARKET order
             trigger_price: 0, // Required if not a trigger order
             disclosed_quantity: 0 // Required
        };

        const endpoint = '/order/place';
        const response = await makeApiCall(endpoint, 'POST', orderPayload);

        if (response && response.status === 'success' && response.data?.order_id) {
            logMessage(`Order placed successfully! Order ID: ${response.data.order_id}`);
            // Optionally, fetch order status using the order_id
        } else {
            const errorDetail = response?.errors?.[0]?.message || response?.message || 'Failed to place order. Check console for details.';
            logMessage(`Order placement failed: ${errorDetail}`, true);
             console.error("Order Placement Failed Response:", response);
        }
    }


    // --- Event Listeners ---

    fetchChainBtn.addEventListener('click', fetchAndDisplayAtmOptions);

    buyCallBtn.addEventListener('click', () => {
        const selectedCallKey = callOptionsSelect.value;
        const quantity = callQuantityInput.value;
        placeOrder(selectedCallKey, quantity);
    });

    buyPutBtn.addEventListener('click', () => {
        const selectedPutKey = putOptionsSelect.value;
        const quantity = putQuantityInput.value;
        placeOrder(selectedPutKey, quantity);
    });


    // --- Initial Setup ---
    getAccessToken(); // Check for token on load
    // Set default expiry date (e.g., next Thursday if applicable, or just leave blank)
     const today = new Date().toISOString().split('T')[0];
     expiryDateInput.min = today; // Prevent selecting past dates
     // expiryDateInput.value = today; // Optional: default to today
});