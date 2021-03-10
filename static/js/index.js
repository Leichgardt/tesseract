document.addEventListener('DOMContentLoaded', function (event) {
    let list = document.getElementById('list');
    let history = document.getElementById('history');
    let groups = document.getElementById('groups');
    setInterval(refresh_data_request, 60000);

    function refresh_data_request() {
        fetch('api/get_data', {
            method: 'GET',
        })
            .then(response => response.json())
            .then(data => {
                list.innerText = data.subs;
                history.innerText = data.history;
                groups.innerHTML = '';
                data.groups.forEach(function (item) {
                    groups.innerHTML += ' - ' + item + '<br>';
                });
            })
            .catch(error => {
                console.log(error);
            });
    }
});