/* Expense Tracker - small UI helpers (no dependencies) */
(function () {
    'use strict';

    var root = document.documentElement;
    var body = document.body;

    /* ---- Dark / light theme ---- */
    document.querySelectorAll('[data-theme-toggle]').forEach(function (button) {
        button.addEventListener('click', function () {
            var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
            root.setAttribute('data-theme', next);
            try { localStorage.setItem('theme', next); } catch (e) { /* storage blocked */ }
            document.dispatchEvent(new CustomEvent('themechange'));
        });
    });

    /* ---- Mobile sidebar ---- */
    function closeSidebar() { body.classList.remove('sidebar-open'); }
    document.querySelectorAll('[data-sidebar-open]').forEach(function (button) {
        button.addEventListener('click', function () { body.classList.add('sidebar-open'); });
    });
    var backdrop = document.querySelector('.backdrop');
    if (backdrop) { backdrop.addEventListener('click', closeSidebar); }
    document.querySelectorAll('.sidebar a').forEach(function (link) {
        link.addEventListener('click', closeSidebar);
    });
    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') { closeSidebar(); }
    });

    /* ---- Dismissible messages (success ones fade out by themselves) ---- */
    document.querySelectorAll('.alert').forEach(function (alert) {
        function dismiss() {
            alert.classList.add('hide');
            setTimeout(function () { alert.remove(); }, 300);
        }
        var close = alert.querySelector('.alert-close');
        if (close) { close.addEventListener('click', dismiss); }
        if (alert.classList.contains('alert-success')) { setTimeout(dismiss, 6000); }
    });

    /* ---- Category colours: same category always gets the same hue ---- */
    function hueFor(text) {
        var hash = 0;
        for (var i = 0; i < text.length; i++) { hash = (hash * 31 + text.charCodeAt(i)) % 360; }
        return hash;
    }
    document.querySelectorAll('[data-cat]').forEach(function (el) {
        el.style.setProperty('--h', hueFor(el.getAttribute('data-cat').toLowerCase()));
    });

    /* ---- Styled confirm dialog for forms with data-confirm="..." ---- */
    var dialog = document.getElementById('confirm-dialog');
    var supportsDialog = dialog && typeof dialog.showModal === 'function';
    var pendingForm = null;

    document.addEventListener('submit', function (event) {
        var form = event.target;
        var message = form.getAttribute ? form.getAttribute('data-confirm') : null;
        if (!message) { return; }

        if (!supportsDialog) {  // very old browsers: plain confirm box
            if (!window.confirm(message)) { event.preventDefault(); }
            return;
        }
        event.preventDefault();
        pendingForm = form;
        document.getElementById('confirm-title').textContent = form.getAttribute('data-confirm-title') || 'Are you sure?';
        document.getElementById('confirm-text').textContent = message;
        document.getElementById('confirm-ok').textContent = form.getAttribute('data-confirm-ok') || 'Delete';
        dialog.showModal();
    });

    if (supportsDialog) {
        document.getElementById('confirm-ok').addEventListener('click', function () {
            var form = pendingForm;
            pendingForm = null;
            dialog.close();
            if (form) { form.submit(); }
        });
        document.getElementById('confirm-cancel').addEventListener('click', function () {
            pendingForm = null;
            dialog.close();
        });
        dialog.addEventListener('click', function (event) {  // click on the dark backdrop
            if (event.target === dialog) { pendingForm = null; dialog.close(); }
        });
    }
})();
