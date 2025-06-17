document.addEventListener('DOMContentLoaded', () => {
    const connectMetamaskBtn = document.getElementById('connectMetamaskBtn');
    const signInMetamaskBtn = document.getElementById('signInMetamaskBtn');
    // Assuming a <button id="logoutBtn">Logout</button> exists or will be added in header.html
    // const logoutBtn = document.getElementById('logoutBtn');

    let currentAccount = null;

    // Function to update UI based on login status (called on page load and after actions)
    // This is a placeholder for now. The page reload handles most of this by letting Flask serve new state.
    function updateLoginStatusUI() {
        if (currentAccount) { // Connected to Metamask
            if (connectMetamaskBtn) connectMetamaskBtn.style.display = 'none';
            // signInMetamaskBtn visibility will be handled by page reload after login
            // logoutBtn visibility will also be handled by page reload
        } else { // Not connected
            if (connectMetamaskBtn) connectMetamaskBtn.style.display = 'block';
            if (signInMetamaskBtn) signInMetamaskBtn.style.display = 'none';
            // if (logoutBtn) logoutBtn.style.display = 'none';
        }
    }

    if (connectMetamaskBtn) {
        connectMetamaskBtn.addEventListener('click', async () => {
            if (typeof window.ethereum !== 'undefined') {
                try {
                    const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
                    if (accounts.length > 0) {
                        currentAccount = accounts[0];
                        console.log('Connected account:', currentAccount);

                        if (signInMetamaskBtn) {
                            signInMetamaskBtn.style.display = 'block'; // Show sign-in button
                        }
                        connectMetamaskBtn.style.display = 'none'; // Hide connect button

                        // Optionally, display currentAccount somewhere
                        // const accountDisplay = document.getElementById('accountDisplay');
                        // if (accountDisplay) accountDisplay.textContent = `Connected: ${currentAccount}`;

                    } else {
                        currentAccount = null;
                        alert('No accounts found. Please ensure Metamask is set up correctly.');
                    }
                } catch (error) {
                    currentAccount = null;
                    console.error('Error connecting to Metamask:', error);
                    alert('Error connecting to Metamask. Check console for details.');
                }
            } else {
                alert('Metamask is not installed. Please install it to use this feature.');
            }
            // updateLoginStatusUI(); // Reflect connection status
        });
    }

    if (signInMetamaskBtn) {
        signInMetamaskBtn.addEventListener('click', async () => {
            if (!currentAccount) {
                alert('Please connect to Metamask first.');
                return;
            }

            try {
                // 1. Fetch Nonce
                const nonceResponse = await fetch(`/get_nonce_to_sign/${currentAccount}`);
                if (!nonceResponse.ok) {
                    const errorData = await nonceResponse.json();
                    alert(`Error fetching nonce: ${errorData.error || nonceResponse.statusText}`);
                    return;
                }
                const nonceData = await nonceResponse.json();
                const nonce = nonceData.nonce;
                if (!nonce) {
                    alert('Nonce not received from server.');
                    return;
                }
                console.log('Nonce received:', nonce);

                // 2. Request Signature
                const signature = await window.ethereum.request({
                    method: 'personal_sign',
                    params: [nonce, currentAccount], // Metamask will handle hex-encoding if needed for the message
                });
                console.log('Signature received:', signature);

                // 3. Verify Signature
                const verifyResponse = await fetch('/verify_signature', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        signed_message: signature,
                        original_nonce: nonce,
                        wallet_address: currentAccount,
                    }),
                });

                const verifyData = await verifyResponse.json();
                if (verifyResponse.ok && verifyData.success) {
                    alert('Successfully signed in!');
                    window.location.reload(); // Reload to reflect login state from server
                } else {
                    alert(`Sign-in failed: ${verifyData.error || verifyData.message || 'Unknown error'}`);
                }
            } catch (error) {
                console.error('Error during sign-in process:', error);
                alert(`An error occurred: ${error.message || 'Check console for details.'}`);
            }
        });
    }

    // Initial UI state check (basic)
    // updateLoginStatusUI(); // More complex logic would be needed if page doesn't reload post-login
    // For now, the default HTML state (connect visible, sign-in hidden) is the starting point.
});
