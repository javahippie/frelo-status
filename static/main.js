var map = L.map('map').setView([48.01164, 7.82282], 13);
var markers = L.layerGroup().addTo(map);

L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);

function load(ts) {
    fetch(`/xhr/${ts}`)
        .then((response) => {
            return response.json()
        })
        .then((json) => {
            markers.clearLayers()
            json.forEach(refreshMap)
        })
}

let delayTimer;
function fetchStatus(ts) {
    document.getElementById("time-headline").textContent = ts.readable;
    clearTimeout(delayTimer);
    delayTimer = setTimeout(function() {
        load(ts.last_reported)
    }, 300);
}

function refreshMap(v) {
    const bike_no = v.BIKES_AVAILABLE;
    L.marker([v.LAT, v.LON], {
        icon: new L.DivIcon({
            className: 'my-div-icon',
            html: `<div class="frelo-station" style="height: ${bike_no * 3}px; width: 5px; background: rgb(9,121,25);"></div>`,
            iconSize: [5, bike_no],
            iconAnchor: [2.5, bike_no * 3]
        })
    }).addTo(markers);

}