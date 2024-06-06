const buttons = [
    {href:'#', text: 'Inicio'},
    {href:'#', text: 'Recompensas'},
    {href:'#', text: 'Estadisticas'},
    {href:'#', text: 'Evaluar'},
    {href:'#', text: 'Pedidos'},
    {href:'#', text: 'Usuarios'}
]

function createButton(buttonDetails,container) {
    const a = document.createElement('a');
    a.href = buttonDetails.href;
    a.className = 'botones perfil';
    a.textContent = buttonDetails.text;
    container.appendChild(a);
}

async function fetchUser(buttons){
    const baseurl = 'http://127.0.0.1:8080/users?username=';
    const url = baseurl.concat(sessionStorage.getItem('username'))
    const response = await fetch(url);

    if (response.ok){
        const data = await response.json();
        document.getElementById('nombre').textContent = data['firstName'];
        document.getElementById('puntos').textContent = data['points'].toString().concat(' pts');

        switch (data['role']) {
            case 'admin':{
                let container = document.getElementById('containerLeft');
                while (container.firstChild) {
                    container.removeChild(container.firstChild);
                }

                createButton(buttons[0],container);
                createButton(buttons[1],container);
                createButton(buttons[2],container);
                createButton(buttons[3],container);


                container = document.getElementById('containerRight');
                while (container.firstChild) {
                    container.removeChild(container.firstChild);
                }

                createButton(buttons[4],container);
                createButton(buttons[5],container);

                break;
            }
            case 'vse':{
                let container = document.getElementById('containerLeft');
                while (container.firstChild) {
                    container.removeChild(container.firstChild);
                }

                createButton(buttons[0],container);
                createButton(buttons[1],container);
                createButton(buttons[2],container);
                createButton(buttons[3],container);


                container = document.getElementById('containerRight');
                while (container.firstChild) {
                    container.removeChild(container.firstChild);
                }

                createButton(buttons[4],container);


                break;
            }
            case 'champion':{
                let container = document.getElementById('containerLeft');
                while (container.firstChild) {
                    container.removeChild(container.firstChild);
                }

                createButton(buttons[0],container);
                createButton(buttons[1],container);
                createButton(buttons[3],container);

                container = document.getElementById('containerRight');
                while (container.firstChild) {
                    container.removeChild(container.firstChild);
                }
                break;
            }
            default:{
                let container = document.getElementById('containerLeft');
                while (container.firstChild) {
                    container.removeChild(container.firstChild);
                }

                createButton(buttons[0],container);
                createButton(buttons[1],container);
                container = document.getElementById('containerRight');
                while (container.firstChild) {
                    container.removeChild(container.firstChild);
                }
                break;
            }
        }
    } else {

    }
}
fetchUser(buttons);