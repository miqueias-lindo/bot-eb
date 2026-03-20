<script>
const SUPABASE_URL = 'https://fcrzzuyfmdkkelylphdm.supabase.co';
const SUPABASE_KEY = 'sb_publishable_n_EVOo3TszHpm25nWNIj0w_Z9U36-3P';
const STAFF_ROLE_ID = '1470615090951880806';

const { createClient } = supabase;
const db = createClient(SUPABASE_URL, SUPABASE_KEY);

// INTRO (corrigido pra não quebrar)
setTimeout(() => {
  const intro = document.getElementById('intro');
  if (intro) {
    intro.style.transition = 'opacity 0.5s ease';
    intro.style.opacity = '0';
    setTimeout(() => intro.style.display = 'none', 500);
  }
}, 3000);

// 🔥 CARREGAR USUÁRIO (FIX PRINCIPAL)
async function carregarUsuario() {
  try {
    const { data: { session }, error } = await db.auth.getSession();

    if (error) {
      console.error('Erro sessão:', error);
      return;
    }

    // SE NÃO ESTIVER LOGADO
    if (!session) {
      window.location.href = 'index.html';
      return;
    }

    const user = session.user;
    const meta = user.user_metadata || {};

    const nome = meta.full_name || meta.name || meta.global_name || 'Soldado';
    const tag = meta.discriminator ? '#' + meta.discriminator : '';

    // 🔥 SAFE DOM (evita tela branca)
    const setText = (id, value) => {
      const el = document.getElementById(id);
      if (el) el.textContent = value;
    };

    setText('perfilNome', nome);
    setText('perfilTag', tag ? 'Discord ' + tag : 'Discord');
    setText('navNome', nome);
    setText('fichaNome', nome);

    // AVATAR (seguro)
    if (meta.avatar_url || meta.picture) {
      const avatarUrl = meta.avatar_url || meta.picture;

      const perfil = document.getElementById('perfilAvatar');
      if (perfil) {
        perfil.outerHTML = `<img src="${avatarUrl}" class="perfil-avatar">`;
      }

      const nav = document.getElementById('navAvatar');
      if (nav) {
        nav.outerHTML = `<img src="${avatarUrl}" class="nav-avatar">`;
      }
    }

    // ROLES (não quebra se não existir)
    const roles = meta.roles || [];
    const cargosEl = document.getElementById('perfilCargos');

    if (cargosEl) {
      if (roles.length > 0) {
        cargosEl.innerHTML = roles.map(r =>
          `<span class="cargo-badge ${r === STAFF_ROLE_ID ? 'staff' : ''}">
            ${r === STAFF_ROLE_ID ? '🛡️ Staff' : 'Cargo'}
          </span>`
        ).join('');
      } else {
        cargosEl.innerHTML = '<span class="cargo-badge">Membro</span>';
      }
    }

    // STAFF MENU
    if (roles.includes(STAFF_ROLE_ID)) {
      const staffItem = document.getElementById('staffMenuItem');
      if (staffItem) staffItem.style.display = 'flex';
      carregarStaff();
    }

  } catch (err) {
    console.error('ERRO GERAL:', err);
    alert('Erro no sistema (abre F12)');
  }
}

// 🔥 STAFF (corrigido)
async function carregarStaff() {
  try {
    const { data, error } = await db.from('usuarios')
      .select('*')
      .order('criado_em', { ascending: false });

    const tabela = document.getElementById('staffTabela');

    if (!tabela) return;

    if (error || !data || data.length === 0) {
      tabela.innerHTML = '<tr><td colspan="4">Nenhum membro.</td></tr>';
      return;
    }

    tabela.innerHTML = data.map(u => `
      <tr>
        <td>${u.nick || '—'}</td>
        <td>${u.email || '—'}</td>
        <td>${u.criado_em ? new Date(u.criado_em).toLocaleDateString('pt-BR') : '—'}</td>
        <td>
          <button class="btn-action btn-promover" onclick="mostrarToast('Promoção!')">Promover</button>
          <button class="btn-action btn-ban" onclick="mostrarToast('Banido!')">Banir</button>
        </td>
      </tr>
    `).join('');

  } catch (err) {
    console.error('Erro staff:', err);
  }
}

// MENU (inalterado)
function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
  document.getElementById('overlay').classList.toggle('active');
}

function fecharSidebar() {
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('overlay').classList.remove('active');
}

function trocarTab(tab, el) {
  document.querySelectorAll('.content-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.sidebar-item').forEach(s => s.classList.remove('active'));
  document.getElementById('tab-' + tab).classList.add('active');
  if (el) el.classList.add('active');
  fecharSidebar();
}

// LOGOUT
async function fazerLogout() {
  await db.auth.signOut();
  window.location.href = 'index.html';
}

// TOAST (seguro)
function mostrarToast(msg) {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.classList.add('active');
  setTimeout(() => t.classList.remove('active'), 3000);
}

// START
carregarUsuario();
</script>
