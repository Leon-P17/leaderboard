const sqlite3 = require('sqlite3').verbose();

function refreshLeaderboard() {
  // Code to fetch the current sum of lap times from the database
  var currentSumOfLapTimes = fetchSumOfLapTimesFromDatabase();

  // Check if there has been a change in the sum of lap times
  if (currentSumOfLapTimes !== previousSumOfLapTimes) {
    // Update the previous sum of lap times
    previousSumOfLapTimes = currentSumOfLapTimes;

    // Code to refresh the leaderboard page
    refreshPage();
  }
}

// Function to fetch the sum of lap times from the database
function fetchSumOfLapTimesFromDatabase() {
  // Connect to database
  const db = new sqlite3.Database('drivers.db');
  
  return new Promise((resolve, reject) => {
    // Query the database to calculate the sum of lap times
    db.get('SELECT SUM(lap_time) AS total_lap_time FROM drivers', (err, row) => {
      if (err) {
        console.error('Error fetching sum of lap times:', err);
        reject(err);
      } else {
        // Resolve the promise with the sum of lap times
        resolve(row.total_lap_time || 0);
      }
    });

    // Close the database connection
    db.close();
  });
}

// Function to refresh the leaderboard page
function refreshPage() {
  // Code to refresh the leaderboard page
  // Replace this with your actual implementation to refresh the leaderboard page
  location.reload(); // This will reload the current page
}

// Variable to store the previous sum of lap times
var previousSumOfLapTimes = fetchSumOfLapTimesFromDatabase();

// Set the interval to check for updates every 5 seconds (5000 milliseconds)
setInterval(refreshLeaderboard, 5000);
