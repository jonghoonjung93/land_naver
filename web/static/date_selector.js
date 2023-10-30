// 일자변경 기능을 위한 JavaScript

// dateSelector 가 변경될때 해당값을 url argument 로 추가해줌
const dateSelector = document.getElementById("dateSelector");
// Add an event listener to listen for changes in the selected option
dateSelector.addEventListener("change", function () {
  const selectedDate = dateSelector.value; // Get the selected date value
  const currentUrl = new URL(window.location.href); // Get the current URL
  currentUrl.searchParams.set("date", selectedDate); // Set the 'date' query parameter to the selected date
  window.location.href = currentUrl.toString(); // Redirect to the updated URL
});

// 페이지 로드될때 date 변수값을 읽고 없으면 첫번째, 있으면 해당일자를 dateSeletor를 선택한 상태로 표시
function setSelectedDateOption(date) {
  const dateSelector = document.getElementById("dateSelector");
  for (let option of dateSelector.options) {
    if (option.value === date) {
      option.selected = true;
      break;
    }
  }
}
// Function to get the value of a URL query parameter
function getQueryParamValue(name) {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get(name);
}
// Get the 'date' query parameter value from the URL
const dateFromUrl = getQueryParamValue("date");
// Check if a date is available in the URL
if (dateFromUrl) {
  // Set the selected date option based on the 'date' query parameter
  setSelectedDateOption(dateFromUrl);
}
