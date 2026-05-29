function openEditProfileModal() {

    const modal = document.getElementById('editProfileModal');

    modal.classList.remove('hidden');
    modal.classList.add('flex');

}

function closeEditProfileModal() {

    const modal = document.getElementById('editProfileModal');

    modal.classList.add('hidden');
    modal.classList.remove('flex');

}

function openChangePasswordModal() {

    const modal = document.getElementById('changePasswordModal');

    modal.classList.remove('hidden');
    modal.classList.add('flex');

}

function closeChangePasswordModal() {

    const modal = document.getElementById('changePasswordModal');

    modal.classList.add('hidden');
    modal.classList.remove('flex');

}