document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    console.log('Attempting login with username:', username);
    
    try {
        const response = await fetch('/admin/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        console.log('Server response:', data);
        
        if (response.ok) {
            console.log('Login successful, redirecting...');
            window.location.href = '/admin/dashboard';
        } else {
            console.error('Login failed:', data.message);
            alert(`Login failed: ${data.message || 'Invalid credentials'}`);
        }
    } catch (error) {
        console.error('Login error:', error);
        alert('Login failed. Please check the browser console for details.');
    }
});
