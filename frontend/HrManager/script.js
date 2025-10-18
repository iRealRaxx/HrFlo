// script.js

document.addEventListener('DOMContentLoaded', () => {
    // ====================================
    // 1. SIDEBAR TOGGLE LOGIC
    // ====================================
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    
    // Function to handle the sidebar toggle
    const toggleSidebar = () => {
        const isExpanded = sidebar.classList.toggle('expanded');
        // Update ARIA attributes for accessibility
        sidebarToggle.setAttribute('aria-expanded', isExpanded);
    };

    // Attach event listener to the toggle button
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', toggleSidebar);
    }
    
    // ====================================
    // 2. SEGMENTED CONTROL LOGIC
    // ====================================
    const toggleGroup = document.querySelector('.toggle-group');

    if (toggleGroup) {
        toggleGroup.addEventListener('click', (event) => {
            const clickedButton = event.target.closest('.seg');
            
            // Ensure a button was clicked and it's not already active
            if (clickedButton && !clickedButton.classList.contains('active')) {
                // Remove 'active' from all siblings
                toggleGroup.querySelectorAll('.seg').forEach(btn => {
                    btn.classList.remove('active');
                });
                
                // Add 'active' to the clicked button
                clickedButton.classList.add('active');
                
                // Use the data attribute to log the new state
                const period = clickedButton.getAttribute('data-period');
                console.log(`Analytics period set to: ${period}. Data update placeholder.`);
                
                // --- Real-world action would go here (e.g., fetch new chart data) ---
            }
        });
    }

    // ====================================
    // 3. TOP-ACTIONS (e.g., Notifications)
    // ====================================
    const notificationBtn = document.querySelector('[aria-label="Notifications"]');
    if (notificationBtn) {
        notificationBtn.addEventListener('click', () => {
            console.log('Notification button clicked.');
            // In a real application, this would toggle a notification dropdown/modal.
            alert('Notifications functionality is coming soon!');
        });
    }
});