function openEditProfileModal() {
    document
        .getElementById('editProfileModal')
        .classList.remove('hidden');

    document
        .getElementById('editProfileModal')
        .classList.add('flex');
}

function closeEditProfileModal() {
    document
        .getElementById('editProfileModal')
        .classList.add('hidden');

    document
        .getElementById('editProfileModal')
        .classList.remove('flex');
}

function openChangePasswordModal() {
    document
        .getElementById('changePasswordModal')
        .classList.remove('hidden');

    document
        .getElementById('changePasswordModal')
        .classList.add('flex');
}

function closeChangePasswordModal() {
    document
        .getElementById('changePasswordModal')
        .classList.add('hidden');

    document
        .getElementById('changePasswordModal')
        .classList.remove('flex');
}