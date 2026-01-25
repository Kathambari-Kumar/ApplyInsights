function updateChartLink() {
    const month = document.querySelector('select[name="month"]').value;
    document.getElementById("chartLink").href = "/city_chart?month=" + month;
}
