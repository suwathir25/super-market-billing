// Auth and validation script

document.addEventListener("DOMContentLoaded", function() {
    // 1. Alert Auto-fade helper
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            // Smoothly fade out using bootstrap or CSS transition
            alert.style.transition = 'opacity 0.5s ease';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });

    // 2. Client-side Form Validations
    const validatedForms = document.querySelectorAll('.needs-validation');
    validatedForms.forEach(form => {
        form.addEventListener('submit', function(event) {
            let isValid = true;
            
            // Password verification match checks
            const password = form.querySelector('input[name="password"], input[name="new_password"]');
            const confirm = form.querySelector('input[name="confirm_password"]');
            
            if (password && confirm) {
                if (password.value !== confirm.value) {
                    confirm.setCustomValidity("Passwords do not match.");
                    isValid = false;
                } else {
                    confirm.setCustomValidity("");
                }
            }

            if (!form.checkValidity() || !isValid) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // 3. User toggle status (AJAX helper for Admins)
    const userToggleButtons = document.querySelectorAll('.toggle-user-status-btn');
    userToggleButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const userId = btn.getAttribute('data-user-id');
            const currentStatus = btn.getAttribute('data-status');
            
            if (confirm(`Are you sure you want to change this user status?`)) {
                fetch(`/users/${userId}/toggle`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showToast(data.message, 'success');
                        // Update UI status label and button styling dynamically
                        const label = document.getElementById(`status-badge-${userId}`);
                        if (data.new_status === 'active') {
                            label.className = 'badge bg-success';
                            label.innerText = 'Active';
                            btn.className = 'btn btn-sm btn-outline-warning toggle-user-status-btn';
                            btn.innerText = 'Deactivate';
                        } else {
                            label.className = 'badge bg-danger';
                            label.innerText = 'Inactive';
                            btn.className = 'btn btn-sm btn-outline-success toggle-user-status-btn';
                            btn.innerText = 'Activate';
                        }
                        btn.setAttribute('data-status', data.new_status);
                    } else {
                        showToast(data.message, 'danger');
                    }
                })
                .catch(err => {
                    showToast('Connection error. Please try again.', 'danger');
                });
            }
        });
    });
});

// Toast notification popups creator
function showToast(message, type = 'success') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `custom-toast ${type}`;
    
    // Choose icons based on toast type
    let icon = '✔';
    if (type === 'danger') icon = '❌';
    if (type === 'warning') icon = '⚠';
    if (type === 'info') icon = 'ℹ';

    toast.innerHTML = `
        <span class="toast-icon">${icon}</span>
        <span class="toast-message">${message}</span>
    `;

    container.appendChild(toast);

    // Trigger transition Reflow
    setTimeout(() => {
        toast.classList.add('show');
    }, 50);

    // Auto-remove toast after 4 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}
