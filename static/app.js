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
    previewUrl: '',
    groups: [],
    activeGroupId: null,
    transactions: [],
    activeTransactionId: null,
    selectedManualAssignees: [],
    editingTransactionId: null
};

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach((screen) => {
        screen.classList.add('hidden');
    });
    document.getElementById(screenId).classList.remove('hidden');
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

async function loadGroups() {
    const response = await fetch('/groups');
    const groups = await response.json();
    state.groups = groups;
    renderDashboard();
}

function renderDashboard() {
    const target = document.getElementById('dashboard-groups-list');
    target.innerHTML = '';

    state.groups.forEach((group) => {
        const card = document.createElement('button');
        card.type = 'button';
        card.className = 'list-card';
        card.innerHTML = `<strong>${escapeHtml(group.name)}</strong><div class="helper-text">${escapeHtml(group.members.join(', '))}</div>`;
        card.addEventListener('click', () => openGroup(group.id));
        target.appendChild(card);
    });
}

async function openGroup(groupId) {
    const response = await fetch(`/groups/${groupId}`);
    const group = await response.json();
    state.activeGroupId = group.id;
    document.getElementById('group-title').textContent = group.name;
    const groupMembers = document.getElementById('group-members');
    groupMembers.innerHTML = '';
    group.members.forEach((member) => {
        const chip = document.createElement('span');
        chip.className = 'chip';
        chip.textContent = member;
        groupMembers.appendChild(chip);
    });
    await loadGroupTransactions(groupId);
    showScreen('screen-group');
}

async function loadGroupTransactions(groupId) {
    const response = await fetch(`/groups/${groupId}/transactions`);
    const transactions = await response.json();
    state.transactions = transactions;
    renderTransactionsList();
}

function renderTransactionsList() {
    const target = document.getElementById('transactions-list');
    target.innerHTML = '';

    if (!state.transactions.length) {
        target.innerHTML = '<div class="helper-text">No transactions yet.</div>';
        return;
    }

    const fragment = document.createDocumentFragment();
    state.transactions.forEach((transaction) => {
        const card = document.createElement('button');
        card.type = 'button';
        card.className = 'list-card';
        card.innerHTML = `
            <div class="button-row">
                <strong>${escapeHtml(transaction.title)}</strong>
                <span>$${Number(transaction.amount).toFixed(2)}</span>
            </div>
            <div class="helper-text">${escapeHtml(transaction.paidBy)} • ${escapeHtml(transaction.date)}</div>
            <div class="helper-text">Assigned to: ${escapeHtml(transaction.assignees.map((entry) => entry.person).join(', '))}</div>
        `;
        card.addEventListener('click', () => openTransactionDetail(transaction.id));
        fragment.appendChild(card);
    });
    target.appendChild(fragment);
}

async function openTransactionDetail(transactionId) {
    const response = await fetch(`/transactions/${transactionId}`);
    const transaction = await response.json();
    state.activeTransactionId = transaction.id;
    const card = document.getElementById('transaction-detail-card');
    card.innerHTML = `
        <h2>${escapeHtml(transaction.title)}</h2>
        <p class="helper-text">${escapeHtml(transaction.description || 'No description')}</p>
        <div class="button-row"><strong>Amount</strong><span>$${Number(transaction.amount).toFixed(2)}</span></div>
        <div class="helper-text">Paid by: ${escapeHtml(transaction.paidBy)}</div>
        <div class="helper-text">Date: ${escapeHtml(transaction.date)}</div>
        <div class="helper-text">Source: ${escapeHtml(transaction.source)}</div>
        ${transaction.assignees.length ? `<div class="helper-text">Assignees: ${transaction.assignees.map((entry) => `${entry.person} ($${Number(entry.amount).toFixed(2)})`).join(', ')}</div>` : ''}
        ${transaction.items.length ? `<div class="stack-list" style="margin-top: 12px;">${transaction.items.map((item) => `<div class="card"><strong>${escapeHtml(item.name)}</strong><div class="helper-text">$${Number(item.price).toFixed(2)}</div><div class="helper-text">${item.splits.map((split) => `${escapeHtml(split.person)}: $${Number(split.amount).toFixed(2)}`).join(' • ')}</div></div>`).join('')}</div>` : ''}
        ${transaction.source === 'manual' ? '<button id="transaction-edit-btn" class="btn-primary">Edit</button>' : ''}
    `;
    const editButton = document.getElementById('transaction-edit-btn');
    if (editButton) {
        editButton.addEventListener('click', () => startEditingTransaction(transaction));
    }
    showScreen('screen-transaction-detail');
}

function startEditingTransaction(transaction) {
    state.editingTransactionId = transaction.id;
    state.selectedManualAssignees = transaction.assignees.map((entry) => entry.person);
    document.getElementById('manual-title').value = transaction.title;
    document.getElementById('manual-description').value = transaction.description || '';
    document.getElementById('manual-amount').value = transaction.amount;
    document.getElementById('manual-status').textContent = '';
    document.getElementById('manual-submit-btn').textContent = 'Save changes';
    document.querySelector('#screen-manual-entry .nav-back').dataset.screen = 'screen-transaction-detail';
    renderManualAssignees();
    showScreen('screen-manual-entry');
}

function renderManualAssignees() {
    const target = document.getElementById('manual-assignees-list');
    target.innerHTML = '';
    if (!state.activeGroupId) {
        return;
    }

    const group = state.groups.find((entry) => entry.id === state.activeGroupId);
    if (!group) {
        return;
    }

    group.members.forEach((member) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = `chip${state.selectedManualAssignees.includes(member) ? ' selected' : ''}`;
        button.textContent = member;
        button.addEventListener('click', () => toggleManualAssignee(member));
        target.appendChild(button);
    });
}

function toggleManualAssignee(member) {
    if (state.selectedManualAssignees.includes(member)) {
        state.selectedManualAssignees = state.selectedManualAssignees.filter((entry) => entry !== member);
    } else {
        state.selectedManualAssignees.push(member);
    }
    renderManualAssignees();
}

async function submitManualTransaction() {
    const title = document.getElementById('manual-title').value.trim();
    const description = document.getElementById('manual-description').value.trim();
    const amount = parseFloat(document.getElementById('manual-amount').value);
    const status = document.getElementById('manual-status');

    if (!title || Number.isNaN(amount) || !state.selectedManualAssignees.length) {
        status.textContent = 'Please enter a title, amount, and at least one assignee.';
        return;
    }

    const editing = state.editingTransactionId !== null;
    const endpoint = editing
        ? `/transactions/${state.editingTransactionId}`
        : `/groups/${state.activeGroupId}/transactions`;
    const response = await fetch(endpoint, {
        method: editing ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            title,
            description,
            amount,
            paidBy: 'You',
            assignedTo: state.selectedManualAssignees,
            source: 'manual'
        })
    });
    const data = await response.json();
    if (!response.ok) {
        status.textContent = data.error || 'Unable to create transaction.';
        return;
    }

    status.textContent = 'Transaction created.';
    if (editing) {
        status.textContent = 'Transaction updated.';
    }
    state.selectedManualAssignees = [];
    state.editingTransactionId = null;
    document.getElementById('manual-title').value = '';
    document.getElementById('manual-description').value = '';
    document.getElementById('manual-amount').value = '';
    document.getElementById('manual-submit-btn').textContent = 'Create transaction';
    document.querySelector('#screen-manual-entry .nav-back').dataset.screen = 'screen-add-transaction-choice';
    await loadGroupTransactions(state.activeGroupId);
    showScreen('screen-group');
}

upload.addEventListener('change', handleFileSelection);

const uploadBtn = document.getElementById('upload-btn');
uploadBtn.addEventListener('click', function () {
    upload.click();
});

document.getElementById('group-add-transaction-btn').addEventListener('click', function () {
    showScreen('screen-add-transaction-choice');
});

document.getElementById('group-settle-up-btn').addEventListener('click', function () {
    showScreen('screen-placeholder');
    document.getElementById('placeholder-title').textContent = 'Settle up';
    document.getElementById('placeholder-message').textContent = 'Settlement flow is stubbed for this pass.';
});

document.getElementById('group-edit-btn').addEventListener('click', function () {
    showScreen('screen-placeholder');
    document.getElementById('placeholder-title').textContent = 'Edit group';
    document.getElementById('placeholder-message').textContent = 'Group editing is a placeholder for now.';
});

document.getElementById('group-settings-btn').addEventListener('click', function () {
    showScreen('screen-placeholder');
    document.getElementById('placeholder-title').textContent = 'Settings';
    document.getElementById('placeholder-message').textContent = 'Settings are not implemented yet.';
});

document.getElementById('add-manual-btn').addEventListener('click', function () {
    renderManualAssignees();
    showScreen('screen-manual-entry');
});

document.getElementById('add-scan-btn').addEventListener('click', function () {
    resetFlow();
    showScreen('screen-upload');
});

document.getElementById('manual-submit-btn').addEventListener('click', submitManualTransaction);

document.getElementById('assign-btn').addEventListener('click', function () {
    renderPeopleChips();
    renderAssignScreen();
    showScreen('screen-assign');
});

document.getElementById('done-btn').addEventListener('click', function () {
    renderSummaryScreen();
    showScreen('screen-summary');
});

document.getElementById('edit-btn').addEventListener('click', function () {
    renderItemsScreen();
    showScreen('screen-items');
});

document.getElementById('rescan-btn').addEventListener('click', function () {
    showScreen('screen-scan');
});

document.getElementById('add-item-btn').addEventListener('click', function () {
    renderItemsScreen();
    previewThumb.style.display = 'none';
    document.getElementById('rescan-btn').style.display = 'none';
    showScreen('screen-items');
});

document.getElementById('manual-add-btn').addEventListener('click', function () {
    const nameInput = document.getElementById('manual-item-name');
    const priceInput = document.getElementById('manual-item-price');
    const name = nameInput.value.trim();
    const price = parseFloat(priceInput.value);

    if (!name || Number.isNaN(price)) {
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

document.getElementById('add-person-btn').addEventListener('click', function () {
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

document.getElementById('search-people').addEventListener('keydown', function (event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        document.getElementById('add-person-btn').click();
    }
});

document.getElementById('confirm-btn').addEventListener('click', async function () {
    const response = await fetch(`/groups/${state.activeGroupId}/transactions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            title: 'Scanned receipt',
            description: 'Created from receipt scan',
            amount: state.items.reduce((sum, item) => sum + item.price, 0),
            paidBy: 'You',
            source: 'scan',
            items: state.items.map((item) => ({
                name: item.name,
                price: item.price,
                assignedTo: item.assignedTo,
                splitType: 'EQUAL'
            }))
        })
    });
    const data = await response.json();
    if (!response.ok) {
        summaryHint.textContent = data.error || 'Unable to save scanned transaction.';
        return;
    }
    summaryHint.textContent = 'Receipt saved to your group.';
    await loadGroupTransactions(state.activeGroupId);
    showScreen('screen-group');
});

scanBtn.addEventListener('click', function () {
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
        .then((response) => {
            if (!response.ok) {
                return response.json().then((errData) => {
                    throw new Error(errData.error || 'Scan request failed');
                }).catch(() => {
                    throw new Error('Scan request failed with status ' + response.status);
                });
            }
            return response.json();
        })
        .then((data) => {
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
        .catch((err) => {
            status.textContent = 'Error scanning receipt: ' + err.message;
            console.error(err);
        });
});

document.querySelectorAll('.nav-back').forEach((button) => {
    button.addEventListener('click', () => {
        const targetScreen = button.getAttribute('data-screen');
        if (targetScreen) {
            showScreen(targetScreen);
        }
    });
});

loadGroups().then(() => {
    showScreen('screen-dashboard');
});