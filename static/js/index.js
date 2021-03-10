document.addEventListener('DOMContentLoaded', function (event) {
    let list = document.getElementById('list');
    let groups = document.getElementById('groups');
    refresh_list();
    setInterval(refresh_list, 60000);

    function refresh_list() {
        fetch('api/get_list', {
            method: 'GET',
        })
            .then(response => response.json())
            .then(data => {
                list.innerText = data['subs'];
                groups.innerHTML = '';
                data['groups'].forEach(function (item) {
                    groups.innerHTML += ' - ' + item + '<br>';
                });
            })
            .catch(error => {
                console.log(error);
            });
    }
});