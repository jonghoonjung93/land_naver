//중복 제거 체크박스 기능을 위한 스크립트
// Function to set a cookie with the checkbox state
function setCheckboxState(value) {
  document.cookie = `rm_dup=${value}`;
}

// Function to get the checkbox state from the cookie
function getCheckboxState() {
  const name = "rm_dup=";
  const cookies = document.cookie.split(";");
  for (let cookie of cookies) {
    cookie = cookie.trim();
    if (cookie.indexOf(name) === 0) {
      return cookie.substring(name.length, cookie.length) === "true";
    }
  }
  return false; // Default value if not found
}

// Function to update the checkbox state in localStorage and cookie
function updateCheckboxState() {
  var groupByCheckbox = document.getElementById("groupByCheckbox");
  setCheckboxState(groupByCheckbox.checked);
  updatePage();
}

// Function to update the page by modifying the URL and triggering refresh
function updatePage() {
  var groupByCheckboxState = getCheckboxState();
  var currentUrl = new URL(window.location.href);

  // Update the query parameter
  currentUrl.searchParams.set("rm_dup", groupByCheckboxState);

  window.location.href = currentUrl.toString(); // Redirect to the updated URL
}

// Function to initialize the checkbox state based on the query parameter
function initializeCheckboxState() {
  var groupByCheckbox = document.getElementById("groupByCheckbox");
  groupByCheckbox.checked = getCheckboxState();
}

// Call the initialization function when the page loads
document.addEventListener("DOMContentLoaded", function () {
  initializeCheckboxState();
});

// 전체,신규 버튼 클릭시에 체크박스 해제를 위한 부분
// Function to update the page by modifying the URL and triggering refresh
function updatePage() {
  var groupByCheckboxState = getCheckboxState();
  var currentUrl = new URL(window.location.href);

  // Update the query parameter
  currentUrl.searchParams.set("rm_dup", groupByCheckboxState);

  window.location.href = currentUrl.toString(); // Redirect to the updated URL
}

// Function to uncheck the checkbox when the "All" or "New" button is clicked
function uncheckCheckbox() {
  var groupByCheckbox = document.getElementById("groupByCheckbox");
  groupByCheckbox.checked = false;
  updateCheckboxState();
}
// rm_dup 없이 접속시에 체크박스 해제된 상태로 보이기
function initializeCheckboxState() {
  var groupByCheckbox = document.getElementById("groupByCheckbox");
  var urlParams = new URLSearchParams(window.location.search);
  groupByCheckbox.checked = urlParams.has("rm_dup") ? urlParams.get("rm_dup") === "true" : false;
}

// Call the initialization function when the page loads
document.addEventListener("DOMContentLoaded", function () {
  initializeCheckboxState();

  // Add event listeners for the "All" and "New" buttons
  var allButton = document.querySelector('a[href="/all"]');
  var newButton = document.querySelector('a[href="/new"]');

  allButton.addEventListener("click", uncheckCheckbox);
  newButton.addEventListener("click", uncheckCheckbox);
});
