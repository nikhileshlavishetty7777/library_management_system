/* ═══════════════════════════════════════
   LIBRARY MANAGEMENT SYSTEM — main.js
═══════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {

  /* ── Dark / Light mode toggle ── */
  const themeBtn  = document.getElementById('themeToggle');
  const body      = document.body;
  const saved     = localStorage.getItem('lms-theme') || 'dark';
  if (saved === 'light') body.classList.add('light-mode');
  if (themeBtn) {
    updateThemeIcon();
    themeBtn.addEventListener('click', () => {
      body.classList.toggle('light-mode');
      localStorage.setItem('lms-theme', body.classList.contains('light-mode') ? 'light' : 'dark');
      updateThemeIcon();
    });
  }
  function updateThemeIcon() {
    if (!themeBtn) return;
    const icon = themeBtn.querySelector('i');
    if (!icon) return;
    icon.className = body.classList.contains('light-mode')
      ? 'fas fa-moon' : 'fas fa-sun';
  }

  /* ── Mobile sidebar toggle ── */
  const mobileBtn = document.getElementById('mobileSidebarBtn');
  const sidebar   = document.querySelector('.sidebar');
  if (mobileBtn && sidebar) {
    mobileBtn.addEventListener('click', () => {
      sidebar.classList.toggle('mobile-open');
    });
    document.addEventListener('click', e => {
      if (!sidebar.contains(e.target) && !mobileBtn.contains(e.target)) {
        sidebar.classList.remove('mobile-open');
      }
    });
  }

  /* ── Sidebar expand (desktop) ── */
  if (sidebar) {
    sidebar.addEventListener('mouseenter', () => {
      if (window.innerWidth > 768) sidebar.classList.add('expanded');
    });
    sidebar.addEventListener('mouseleave', () => {
      if (window.innerWidth > 768) sidebar.classList.remove('expanded');
    });
  }

  /* ── Auto-dismiss flash alerts ── */
  document.querySelectorAll('.alert-dismissible').forEach(alert => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 4500);
  });

  /* ── Animated number counters ── */
  const counters = document.querySelectorAll('[data-count]');
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const el    = entry.target;
      const target= parseInt(el.dataset.count, 10);
      const dur   = 900;
      const step  = Math.ceil(target / (dur / 16));
      let current = 0;
      const tick  = () => {
        current = Math.min(current + step, target);
        el.textContent = current.toLocaleString();
        if (current < target) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
      observer.unobserve(el);
    });
  }, { threshold: .3 });
  counters.forEach(c => observer.observe(c));

  /* ── Confirm delete dialogs ── */
  document.querySelectorAll('[data-confirm]').forEach(btn => {
    btn.addEventListener('click', e => {
      const msg = btn.dataset.confirm || 'Are you sure?';
      if (!confirm(msg)) e.preventDefault();
    });
  });

  /* ── AJAX Book search for Issue form ── */
  const bookSearch = document.getElementById('bookSearchInput');
  const bookSel    = document.getElementById('book_id');
  const bookList   = document.getElementById('bookDropdown');
  if (bookSearch && bookSel && bookList) {
    let debounce;
    bookSearch.addEventListener('input', () => {
      clearTimeout(debounce);
      debounce = setTimeout(async () => {
        const q = bookSearch.value.trim();
        if (q.length < 1) { bookList.innerHTML = ''; bookList.style.display='none'; return; }
        const res  = await fetch(`/api/books/search?q=${encodeURIComponent(q)}`);
        const data = await res.json();
        if (!data.length) { bookList.innerHTML = '<div class="dd-item text-muted">No books found</div>'; }
        else {
          bookList.innerHTML = data.map(b =>
            `<div class="dd-item" data-id="${b.id}" data-title="${b.title}">
               <strong>${b.title}</strong><small class="text-muted2"> — ${b.author}</small>
             </div>`
          ).join('');
        }
        bookList.style.display = 'block';
        bookList.querySelectorAll('.dd-item[data-id]').forEach(item => {
          item.addEventListener('click', () => {
            bookSearch.value  = item.dataset.title;
            bookSel.value     = item.dataset.id;
            bookList.style.display = 'none';
          });
        });
      }, 250);
    });
  }

  /* ── AJAX Student search for Issue form ── */
  const stuSearch = document.getElementById('studentSearchInput');
  const stuSel    = document.getElementById('user_id');
  const stuList   = document.getElementById('studentDropdown');
  if (stuSearch && stuSel && stuList) {
    let debounce2;
    stuSearch.addEventListener('input', () => {
      clearTimeout(debounce2);
      debounce2 = setTimeout(async () => {
        const q = stuSearch.value.trim();
        if (q.length < 1) { stuList.innerHTML = ''; stuList.style.display='none'; return; }
        const res  = await fetch(`/api/students/search?q=${encodeURIComponent(q)}`);
        const data = await res.json();
        if (!data.length) { stuList.innerHTML = '<div class="dd-item text-muted">No students found</div>'; }
        else {
          stuList.innerHTML = data.map(s =>
            `<div class="dd-item" data-id="${s.id}" data-name="${s.name}">
               <strong>${s.name}</strong><small class="text-muted2"> — ${s.email}</small>
             </div>`
          ).join('');
        }
        stuList.style.display = 'block';
        stuList.querySelectorAll('.dd-item[data-id]').forEach(item => {
          item.addEventListener('click', () => {
            stuSearch.value = item.dataset.name;
            stuSel.value    = item.dataset.id;
            stuList.style.display = 'none';
          });
        });
      }, 250);
    });
  }

  /* Close dropdowns on outside click */
  document.addEventListener('click', e => {
    [bookList, stuList].forEach(dd => {
      if (dd && !dd.contains(e.target)) dd.style.display = 'none';
    });
  });

  /* ── Table row search filter (client-side) ── */
  const tableFilter = document.getElementById('tableFilter');
  if (tableFilter) {
    tableFilter.addEventListener('input', () => {
      const q   = tableFilter.value.toLowerCase();
      const rows = document.querySelectorAll('.filterable-table tbody tr');
      rows.forEach(row => {
        row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
      });
    });
  }

  /* ── Tooltip init ── */
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
    new bootstrap.Tooltip(el, { trigger: 'hover' });
  });

  /* ── Password strength indicator ── */
  const pwInput  = document.getElementById('password');
  const pwStrBar = document.getElementById('pwStrengthBar');
  if (pwInput && pwStrBar) {
    pwInput.addEventListener('input', () => {
      const v  = pwInput.value;
      let score = 0;
      if (v.length >= 6)  score++;
      if (v.length >= 10) score++;
      if (/[A-Z]/.test(v)) score++;
      if (/[0-9]/.test(v)) score++;
      if (/[^A-Za-z0-9]/.test(v)) score++;
      const colors = ['#ef4444','#f59e0b','#f59e0b','#22c55e','#00d4aa'];
      pwStrBar.style.width  = `${score * 20}%`;
      pwStrBar.style.background = colors[score - 1] || '#ef4444';
    });
  }

  /* ── Due date colour-coding on page load ── */
  document.querySelectorAll('[data-due]').forEach(el => {
    const due = new Date(el.dataset.due);
    const now = new Date();
    const diff = Math.ceil((due - now) / 864e5);
    if (diff < 0)     el.classList.add('text-danger');
    else if (diff <=3) el.classList.add('text-warning');
    else               el.classList.add('text-success');
  });

});

/* ── AJAX Dropdown styles (inline, no extra CSS file) ── */
const ddStyle = document.createElement('style');
ddStyle.textContent = `
  .dd-wrap { position: relative; }
  .dd-results {
    position: absolute; top: 100%; left: 0; right: 0; z-index: 9999;
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: var(--radius-sm); box-shadow: var(--shadow-md);
    max-height: 220px; overflow-y: auto; display: none;
  }
  .dd-item {
    padding: .55rem 1rem; cursor: pointer;
    font-size: .82rem; transition: background .15s;
    border-bottom: 1px solid var(--border-light);
  }
  .dd-item:last-child { border-bottom: none; }
  .dd-item:hover { background: rgba(0,212,170,.1); }
`;
document.head.appendChild(ddStyle);
