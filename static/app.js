const upload = document.getElementById('upload');
const preview = document.getElementById('preview');
const scanBtn = document.getElementById('scan-btn');
const status = document.getElementById('status');
const output = document.getElementById('output');
const itemsList = document.getElementById('items-list');

upload.addEventListener('change', function() {
    const file = upload.files[0];
    const url = URL.createObjectURL(file);
    preview.src = url;
    preview.style.display = 'block';
});

scanBtn.addEventListener('click', function() {
    if (preview.style.display === 'block') {
        status.textContent = 'Scanning...';

        const formData = new FormData();
        formData.append('image', upload.files[0]);

        fetch('/scan', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            status.textContent = 'Scan complete!';
            output.textContent = data.text;
            itemsList.innerHTML = '';
            
            for (const item of data.items) {
                const li = document.createElement('li');
                li.textContent = item;
                itemsList.appendChild(li);
            }
        })
        .catch(err => {
            status.textContent = 'Error scanning receipt.';
            console.error(err);
        });
    } else {
        alert('Please upload a receipt image first.');
    }
});