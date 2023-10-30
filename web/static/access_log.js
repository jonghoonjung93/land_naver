// 현재 URL을 가져오는 함수
function getCurrentURL() {
  return window.location.href;
}

// 공인ip server로 전달 */
function getPublicIP(callback) {
  // fetch('http://ip-api.com/json/')
  fetch("http://ip-api.com/json/?fields=61439")
    .then((response) => response.json())
    .then((data) => {
      // console.log("Your public IP address: " + data.query);
      // console.log("Your url: " + getCurrentURL());
      callback(data.query, getCurrentURL()); // Pass both IP and URL to the callback);
    })
    .catch((error) => {
      console.error("Error fetching IP address:", error);
      callback("", getCurrentURL()); // Handle errors by passing an empty IP and URL
    });
}
// Get the public IP and send it to the Flask server
getPublicIP(function (publicIP, currentURL) {
  // Send a POST request to your Flask route to save the IP address
  fetch("/save_ip", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ ip: publicIP, url: currentURL }), // Include URL in the data
    mode: "cors", // Add this line to specify CORS mode
  })
    .then((response) => response.json())
    .then((data) => {
      console.log("Public IP and URL sent to the server.");
    })
    .catch((error) => {
      console.error("Error sending IP and URL to the server:", error);
    });
});
