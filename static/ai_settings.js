document.addEventListener('DOMContentLoaded', () => {
    const apiKeyInput = document.getElementById('openaiApiKey');
    const testButton = document.getElementById('testApiKeyBtn');
    const resultDiv = document.getElementById('apiKeyTestResult');

    if (testButton) {
        testButton.addEventListener('click', async () => {
            const apiKey = apiKeyInput.value.trim();
            resultDiv.innerHTML = ''; // Clear previous results

            if (!apiKey) {
                resultDiv.textContent = 'Please enter an API key.';
                resultDiv.style.color = 'red';
                return;
            }

            try {
                const response = await fetch('/test_openai_key', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ api_key: apiKey }),
                });

                const data = await response.json();

                if (response.ok) {
                    resultDiv.textContent = data.message;
                    resultDiv.style.color = data.success ? 'green' : 'red';
                } else {
                    resultDiv.textContent = `Error: ${data.message || response.statusText}`;
                    resultDiv.style.color = 'red';
                }
            } catch (error) {
                console.error('Error testing API key:', error);
                resultDiv.textContent = 'An unexpected error occurred. Check the console.';
                resultDiv.style.color = 'red';
            }
        });
    }
});
