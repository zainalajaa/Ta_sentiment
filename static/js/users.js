function openModal(id)
{
    const modal = document.getElementById(id);
    const overlay = document.getElementById('modalOverlay');
    const content = document.getElementById(id + 'Content');

    overlay.classList.remove(
        'opacity-0',
        'invisible'
    );

    overlay.classList.add(
        'opacity-100'
    );

    modal.classList.remove(
        'opacity-0',
        'invisible'
    );

    modal.classList.add(
        'opacity-100'
    );

    setTimeout(() =>
    {
        content.classList.remove(
            'scale-95',
            'opacity-0'
        );

        content.classList.add(
            'scale-100',
            'opacity-100'
        );

    }, 10);
}

function closeModal(id)
{
    const modal = document.getElementById(id);
    const overlay = document.getElementById('modalOverlay');
    const content = document.getElementById(id + 'Content');

    content.classList.remove(
        'scale-100',
        'opacity-100'
    );

    content.classList.add(
        'scale-95',
        'opacity-0'
    );

    setTimeout(() =>
    {
        modal.classList.remove(
            'opacity-100'
        );

        modal.classList.add(
            'opacity-0',
            'invisible'
        );

        overlay.classList.remove(
            'opacity-100'
        );

        overlay.classList.add(
            'opacity-0',
            'invisible'
        );

    }, 200);
}

function showToast(title, message)
{
    const toast = document.getElementById('toast');

    document.getElementById('toastTitle').innerText = title;

    document.getElementById('toastMessage').innerText = message;

    // muncul
    toast.classList.remove(
        'translate-x-[150%]'
    );

    toast.classList.add(
        'translate-x-0'
    );

    // hilang
    setTimeout(() =>
    {
        toast.classList.remove(
            'translate-x-0'
        );

        toast.classList.add(
            'translate-x-[150%]'
        );

    }, 3000);
}

function openDeleteModal(id)
{
    const deleteButton =
        document.getElementById('deleteButton');

    deleteButton.onclick = function ()
    {
        window.location.href =
            `/users/delete/${id}`;
    };

    openModal('deleteModal');
}