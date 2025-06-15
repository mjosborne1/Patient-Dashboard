document.addEventListener('DOMContentLoaded', () => {
    const connectMetamaskBtn = document.getElementById('connectMetamaskBtn');
    const signInMetamaskBtn = document.getElementById('signInMetamaskBtn');

    if (connectMetamaskBtn) {
        connectMetamaskBtn.addEventListener('click', async () => {
            if (typeof window.ethereum !== 'undefined') {
                try {
                    const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
                    console.log('Connected accounts:', accounts);
                    // For now, just log the first account
                    if (accounts.length > 0) {
                        console.log('Using account:', accounts[0]);
                        // Optionally, display this account address in the UI
                    }

                    if (signInMetamaskBtn) {
                        signInMetamaskBtn.style.display = 'block';
                    }
                    // Hide the connect button after successful connection
                    connectMetamaskBtn.style.display = 'none';

                } catch (error) {
                    console.error('Error connecting to Metamask:', error);
                    alert('Error connecting to Metamask. Check the console for details.');
                }
            } else {
                alert('Metamask is not installed. Please install it to use this feature.');
            }
        });
    }

    if (signInMetamaskBtn) {
        signInMetamaskBtn.addEventListener('click', () => {
            console.log('Sign In with Metamask button clicked.');
            alert('Signed in with Metamask (basic client-side)!');
            // Optional: Update user status display element here if it exists
        });
    }
});
