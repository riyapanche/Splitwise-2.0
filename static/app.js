const upload = document.getElementById('upload');
const preview = document.getElementById('preview');
const previewThumb = document.getElementById('preview-thumb');
const scanBtn = document.getElementById('scan-btn');
const status = document.getElementById('status');
const itemsList = document.getElementById('items-list');
const peopleList = document.getElementById('people-list');
const assignItemsList = document.getElementById('assign-items-list');
const summaryList = document.getElementById('summary-list');
const summaryHint = document.getElementById('summary-hint');
const assignInstructions = document.getElementById('assign-instructions');

const state = {
    items: [],
    people: [],
    previewUrl: ''
};

function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.add('hidden');
    });
    document.getElementById(screenId).classList.remove('hidden');
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function resetFlow() {
    state.items = [];
    state.people = [];
    state.previewUrl = '';
    itemsList.innerHTML = '';
    peopleList.innerHTML = '';
    assignItemsList.innerHTML = '';
    summaryList.innerHTML = '';
    summaryHint.textContent = '';
    assignInstructions.textContent = 'Tap the people who shared each item.';
    document.getElementById('manual-item-name').value = '';
    document.getElementById('manual-item-price').value = '';
}

function renderItemsScreen() {
    itemsList.innerHTML = '';

    if (state.items.length === 0) {
        const emptyState = document.createElement('li');
        emptyState.textContent = 'No items yet. Add one manually below.';
        itemsList.appendChild(emptyState);
        return;
    }

    state.items.forEach((item) => {
        const li = document.createElement('li');
        li.innerHTML = `<strong>${escapeHtml(item.name)}</strong><span>$${item.price.toFixed(2)}</span>`;
        itemsList.appendChild(li);
    });
}

// One item can now be shared by several people. Each item stores
// assignedTo as an array of person names, e.g. ["Alice", "Bob"].
// Tapping a person chip on an item toggles them in/out of that array.
function renderAssignScreen() {
    assignItemsList.innerHTML = '';

    if (!state.people.length) {
        const emptyState = document.createElement('li');
        emptyState.textContent = 'Add people above before assigning items.';
        peopleList.innerHTML = '';
        peopleList.appendChild(emptyState);
    }

    if (!state.items.length) {
        const emptyState = document.createElement('li');
        emptyState.textContent = 'Add items before assigning them.';
        assignItemsList.appendChild(emptyState);
        assignInstructions.textContent = 'Add items first, then assign them to people.';
        return;
    }

    assignInstructions.textContent = 'Tap the people who shared each item.';

    state.items.forEach((item) => {
        const li = document.createElement('li');
        li.className = 'assign-item-row';

        const header = document.createElement('div');
        header.className = 'assign-item-header';
        header.innerHTML = `<strong>${escapeHtml(item.name)}</strong><span>$${item.price.toFixed(2)}</span>`;
        li.appendChild(header);

        const chipRow = document.createElement('div');
        chipRow.className = 'chip-row';

        if (!state.people.length) {
            const hint = document.createElement('span');
            hint.className = 'chip-hint';
            hint.textContent = 'No people added yet';
            chipRow.appendChild(hint);
        } else {
            state.people.forEach((person) => {
                const chip = document.createElement('button');
                chip.type = 'button';
                const isSelected = item.assignedTo.includes(person.name);
                chip.className = `person-chip${isSelected ? ' selected' : ''}`;
                chip.textContent = person.name;
                chip.addEventListener('click', () => {
                    toggleAssignment(item, person.name);
                });
                chipRow.appendChild(chip);
            });
        }

        li.appendChild(chipRow);
        assignItemsList.appendChild(li);
    });
}

function toggleAssignment(item, personName) {
    const index = item.assignedTo.indexOf(personName);
    if (index === -1) {
        item.assignedTo.push(personName);
    } else {
        item.assignedTo.splice(index, 1);
    }
    renderAssignScreen();
}

function renderPeopleChips() {
    peopleList.innerHTML = '';

    if (state.people.length === 0) {
        const emptyState = document.createElement('li');
        emptyState.textContent = 'No people yet. Add one to start assigning.';
        peopleList.appendChild(emptyState);
        return;
    }

    state.people.forEach((person) => {
        const li = document.createElement('li');
        li.textContent = person.name;
        peopleList.appendChild(li);
    });
}

function renderSummaryScreen() {
    summaryList.innerHTML = '';
    summaryHint.textContent = 'Calculating totals...';

    const unassignedCount = state.items.filter((item) => item.assignedTo.length === 0).length;
    if (unassignedCount > 0) {
        summaryHint.textContent = `${unassignedCount} item(s) still need at least one person.`;
        return;
    }

    // Send items + assignments to Flask so the actual dollar totals are
    // computed by the Split/SplitFactory classes on the backend, not in JS.
    fetch('/compute-summary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            items: state.items.map((item) => ({
                name: item.name,
                price: item.price,
                assignedTo: item.assignedTo,
                splitType: 'EQUAL'
            }))
        })
    })
        .then((response) => response.json())
        .then((data) => {
            if (data.error) {
                throw new Error(data.error);
            }

            Object.entries(data.totals).forEach(([person, total]) => {
                const li = document.createElement('li');
                li.innerHTML = `<strong>${escapeHtml(person)}</strong><span>$${total.toFixed(2)}</span>`;
                summaryList.appendChild(li);
            });

            summaryHint.textContent = 'Totals calculated. Ready to confirm.';
        })
        .catch((err) => {
            summaryHint.textContent = 'Error calculating totals: ' + err.message;
            console.error(err);
        });
}

function handleFileSelection() {
    const file = upload.files[0];
    if (!file) {
        return;
    }

    resetFlow();
    const url = URL.createObjectURL(file);
    state.previewUrl = url;
    preview.src = url;
    preview.style.display = 'block';
    previewThumb.src = url;
    previewThumb.style.display = 'block';
    document.getElementById('rescan-btn').style.display = 'block';
    showScreen('screen-scan');
}

upload.addEventListener('change', handleFileSelection);

const uploadBtn = document.getElementById('upload-btn');
uploadBtn.addEventListener('click', function() {
    upload.click();
});

document.getElementById('assign-btn').addEventListener('click', function() {
    renderPeopleChips();
    renderAssignScreen();
    showScreen('screen-assign');
});

document.getElementById('done-btn').addEventListener('click', function() {
    renderSummaryScreen();
    showScreen('screen-summary');
});

document.getElementById('edit-btn').addEventListener('click', function() {
    renderItemsScreen();
    showScreen('screen-items');
});

document.getElementById('rescan-btn').addEventListener('click', function() {
    showScreen('screen-scan');
});

document.getElementById('add-item-btn').addEventListener('click', function() {
    renderItemsScreen();
    previewThumb.style.display = 'none';
    document.getElementById('rescan-btn').style.display = 'none';
    showScreen('screen-items');
});

document.getElementById('manual-add-btn').addEventListener('click', function() {
    const nameInput = document.getElementById('manual-item-name');
    const priceInput = document.getElementById('manual-item-price');
    const name = nameInput.value.trim();
    const price = parseFloat(priceInput.value);

    if (!name || isNaN(price)) {
        alert('Please enter an item name and a valid price.');
        return;
    }

    state.items.push({
        id: Date.now(),
        name,
        price,
        assignedTo: []
    });

    renderItemsScreen();

    nameInput.value = '';
    priceInput.value = '';
    nameInput.focus();
});

document.getElementById('add-person-btn').addEventListener('click', function() {
    const input = document.getElementById('search-people');
    const name = input.value.trim();

    if (!name) {
        alert('Please enter a person name.');
        return;
    }

    state.people.push({ id: Date.now(), name });
    input.value = '';
    renderPeopleChips();
    renderAssignScreen();
});

document.getElementById('search-people').addEventListener('keydown', function(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        document.getElementById('add-person-btn').click();
    }
});

document.getElementById('confirm-btn').addEventListener('click', function() {
    summaryHint.textContent = 'Receipt split confirmed.';
    alert('Receipt split confirmed.');
});

scanBtn.addEventListener('click', function() {
    const file = upload.files[0];
    if (!file) {
        alert('Please upload a receipt image first.');
        return;
    }

    status.textContent = 'Scanning...';

    const formData = new FormData();
    formData.append('image', file, file.name);

    fetch('/scan', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(errData => {
                throw new Error(errData.error || 'Scan request failed');
            }).catch(() => {
                throw new Error('Scan request failed with status ' + response.status);
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.error) {
            throw new Error(data.error);
        }

        state.items = data.items.map((item, index) => ({
            id: index + 1,
            name: item.name,
            price: item.price,
            assignedTo: []
        }));
        state.people = [];
        status.textContent = 'Scan complete!';
        renderItemsScreen();
        showScreen('screen-items');
    })
    .catch(err => {
        status.textContent = 'Error scanning receipt: ' + err.message;
        console.error(err);
    });
});

showScreen('screen-upload');