// Function to handle tab switching on the Student Dashboard
function openTab(evt, tabName) {
    var i, tabcontent, tablinks;

    // Hide all tab content
    tabcontent = document.getElementsByClassName("tab-content");
    for (i = 0; i < tabcontent.length; i++) {
        tabcontent[i].style.display = "none";
        tabcontent[i].classList.remove("active-tab");
    }

    // Remove 'active' class from all buttons
    tablinks = document.getElementsByClassName("tab-button");
    for (i = 0; i < tablinks.length; i++) {
        tablinks[i].classList.remove("active");
    }

    // Show the current tab and set the button to active
    document.getElementById(tabName).style.display = "block";
    document.getElementById(tabName).classList.add("active-tab");
    evt.currentTarget.classList.add("active");
}

// Set the default tab on page load
document.addEventListener('DOMContentLoaded', () => {
    const defaultTab = document.getElementById('Clubs');
    const defaultButton = document.querySelector('.tab-button');
    if (defaultTab && defaultButton) {
        defaultTab.style.display = "block";
        defaultButton.classList.add("active");
    }
});