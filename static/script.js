function uploadVideo() {
    let fileInput = document.getElementById("videoInput");

    if (fileInput.files.length === 0) {
        alert("Please select a video first!");
        return;
    }

    let formData = new FormData();
    formData.append("video", fileInput.files[0]);

    fetch("/upload", {
        method: "POST",
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        alert("Video uploaded successfully!");

        // Start video stream AFTER upload
        document.getElementById("videoFeed").src = "/video_feed";
    })
    .catch(err => {
        console.error(err);
        alert("Upload failed!");
    });
}


// Live stats update every second
setInterval(() => {
    fetch('/stats')
    .then(res => res.json())
    .then(data => {
        document.getElementById("total").innerText = data.total;
        document.getElementById("cars").innerText = data.cars;
        document.getElementById("buses").innerText = data.buses;
        document.getElementById("trucks").innerText = data.trucks;
        document.getElementById("bikes").innerText = data.bikes;
    })
    .catch(err => console.log(err));
}, 1000);

// CSV Download
function downloadCSV() {
    window.location.href = "/download_csv";
}