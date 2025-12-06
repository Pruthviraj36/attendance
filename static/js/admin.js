document.addEventListener('DOMContentLoaded', function() {
    // Handle CSV upload form submit
    const uploadForm = document.querySelector('form[action*="upload"]');
    if (uploadForm) {
        uploadForm.addEventListener('submit', function() {
            const uploadBtn = document.getElementById('uploadBtn');
            if (uploadBtn) {
                uploadBtn.innerHTML = 'Uploading...';
                uploadBtn.disabled = true;
            }
        });
    }

    // Handle delete faculty forms
    const deleteForms = document.querySelectorAll('form[action*="delete"]');
    deleteForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!confirm('Are you sure?')) {
                e.preventDefault();
            }
        });
    });
});