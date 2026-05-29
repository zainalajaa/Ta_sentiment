document.addEventListener('DOMContentLoaded', () => {

    const profileBtn = document.getElementById('profileBtn');
    const profileMenu = document.getElementById('profileMenu');

    if (!profileBtn || !profileMenu) return;

    profileBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        profileMenu.classList.toggle('hidden');
    });

    document.addEventListener('click', () => {
        profileMenu.classList.add('hidden');
    });

    profileMenu.addEventListener('click', (e) => {
        e.stopPropagation();
    });

});