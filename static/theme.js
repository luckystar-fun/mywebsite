(function () {
    var root = document.documentElement;
    var btn = document.getElementById('theme-toggle');

    // 双写：localStorage + cookie（任一可用即可持久化）
    function save(v) {
        try { localStorage.setItem('theme', v); } catch (e) {}
        document.cookie = 'theme=' + v + '; path=/; max-age=31536000; SameSite=Lax';
    }

    function updateIcon() {
        if (!btn) return;
        var dark = root.getAttribute('data-theme') === 'dark';
        btn.textContent = dark ? '☀️' : '🌙';
        btn.title = dark ? '切换到浅色' : '切换到深色';
    }

    function toggleTheme() {
        var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        root.setAttribute('data-theme', next);
        save(next);
        updateIcon();
    }

    if (btn) {
        btn.addEventListener('click', toggleTheme);
    }

    updateIcon();

    // 同一浏览器其他标签页切换时同步
    window.addEventListener('storage', function (e) {
        if (e.key === 'theme' && (e.newValue === 'dark' || e.newValue === 'light')) {
            root.setAttribute('data-theme', e.newValue);
            updateIcon();
        }
    });
})();