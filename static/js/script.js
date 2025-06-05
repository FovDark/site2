// FovDark - JavaScript Principal
document.addEventListener('DOMContentLoaded', function() {
    // Inicialização
    initializeApp();
    
    // Event Listeners
    setupEventListeners();
    
    // Animações
    setupAnimations();
});

function initializeApp() {
    // Verificar se há mensagens de alerta na URL
    const urlParams = new URLSearchParams(window.location.search);
    const message = urlParams.get('message');
    
    if (message) {
        showAlert(message, 'success');
        // Limpar a URL
        window.history.replaceState({}, document.title, window.location.pathname);
    }
    
    // Inicializar tooltips
    initializeTooltips();
    
    // Configurar tema
    setupTheme();
}

function setupEventListeners() {
    // Formulários
    setupFormHandlers();
    
    // Botões de ação
    setupActionButtons();
    
    // Navegação mobile
    setupMobileNavigation();
    
    // Busca
    setupSearchHandlers();
}

function setupFormHandlers() {
    // Formulário de login
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    // Formulário de registro
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
    }
    
    // Validação em tempo real
    setupRealTimeValidation();
}

function handleLogin(e) {
    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    
    // Adicionar loading
    if (submitBtn) {
        submitBtn.innerHTML = '<span class="loading"></span> Entrando...';
        submitBtn.disabled = true;
    }
    
    // O formulário será enviado normalmente
    // Em caso de erro, restaurar o botão
    setTimeout(() => {
        if (submitBtn) {
            submitBtn.innerHTML = 'Entrar';
            submitBtn.disabled = false;
        }
    }, 5000);
}

function handleRegister(e) {
    const form = e.target;
    const password = form.password.value;
    const confirmPassword = form.confirm_password.value;
    
    // Validar senhas
    if (password !== confirmPassword) {
        e.preventDefault();
        showAlert('As senhas não coincidem', 'danger');
        return;
    }
    
    if (password.length < 6) {
        e.preventDefault();
        showAlert('A senha deve ter pelo menos 6 caracteres', 'danger');
        return;
    }
    
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.innerHTML = '<span class="loading"></span> Criando conta...';
        submitBtn.disabled = true;
    }
}

function setupRealTimeValidation() {
    // Validação de email
    const emailInputs = document.querySelectorAll('input[type="email"]');
    emailInputs.forEach(input => {
        input.addEventListener('blur', validateEmail);
    });
    
    // Validação de senha
    const passwordInputs = document.querySelectorAll('input[type="password"]');
    passwordInputs.forEach(input => {
        input.addEventListener('input', validatePassword);
    });
}

function validateEmail(e) {
    const input = e.target;
    const email = input.value;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    
    if (email && !emailRegex.test(email)) {
        showFieldError(input, 'Email inválido');
    } else {
        clearFieldError(input);
    }
}

function validatePassword(e) {
    const input = e.target;
    const password = input.value;
    
    if (password && password.length < 6) {
        showFieldError(input, 'Senha deve ter pelo menos 6 caracteres');
    } else {
        clearFieldError(input);
    }
}

function showFieldError(input, message) {
    clearFieldError(input);
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'field-error';
    errorDiv.textContent = message;
    errorDiv.style.color = 'var(--danger-color)';
    errorDiv.style.fontSize = '0.875rem';
    errorDiv.style.marginTop = '0.25rem';
    
    input.parentNode.appendChild(errorDiv);
    input.style.borderColor = 'var(--danger-color)';
}

function clearFieldError(input) {
    const existingError = input.parentNode.querySelector('.field-error');
    if (existingError) {
        existingError.remove();
    }
    input.style.borderColor = '';
}

function setupActionButtons() {
    // Botões de compra
    const purchaseButtons = document.querySelectorAll('.purchase-btn');
    purchaseButtons.forEach(btn => {
        btn.addEventListener('click', handlePurchase);
    });
    
    // Botões de download
    const downloadButtons = document.querySelectorAll('.download-btn');
    downloadButtons.forEach(btn => {
        btn.addEventListener('click', handleDownload);
    });
    
    // Botões de cópia
    const copyButtons = document.querySelectorAll('.copy-btn');
    copyButtons.forEach(btn => {
        btn.addEventListener('click', handleCopy);
    });
}

function handlePurchase(e) {
    const button = e.target.closest('.purchase-btn');
    const productId = button.dataset.productId;
    const productName = button.dataset.productName;
    
    if (confirm(`Deseja comprar ${productName}?`)) {
        // Redirecionar para página de pagamento ou processar compra
        window.location.href = `/purchase/${productId}`;
    }
}

function handleDownload(e) {
    const button = e.target.closest('.download-btn');
    const productId = button.dataset.productId;
    const productName = button.dataset.productName;
    
    // Adicionar loading
    const originalText = button.innerHTML;
    button.innerHTML = '<span class="loading"></span> Baixando...';
    button.disabled = true;
    
    // Simular download
    fetch(`/api/download/${productId}`, {
        method: 'POST',
        credentials: 'include'
    })
    .then(response => {
        if (response.ok) {
            showAlert(`Download de ${productName} iniciado!`, 'success');
        } else {
            throw new Error('Erro no download');
        }
    })
    .catch(error => {
        showAlert('Erro ao iniciar download', 'danger');
    })
    .finally(() => {
        button.innerHTML = originalText;
        button.disabled = false;
    });
}

function handleCopy(e) {
    const button = e.target.closest('.copy-btn');
    const textToCopy = button.dataset.copy;
    
    navigator.clipboard.writeText(textToCopy).then(() => {
        showAlert('Copiado para a área de transferência!', 'success');
        
        // Feedback visual
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check"></i>';
        button.style.color = 'var(--success-color)';
        
        setTimeout(() => {
            button.innerHTML = originalText;
            button.style.color = '';
        }, 2000);
    }).catch(() => {
        showAlert('Erro ao copiar', 'danger');
    });
}

function setupMobileNavigation() {
    // Toggle mobile menu
    const mobileToggle = document.getElementById('mobileToggle');
    const navLinks = document.querySelector('.nav-links');
    
    if (mobileToggle && navLinks) {
        mobileToggle.addEventListener('click', () => {
            navLinks.classList.toggle('show');
        });
    }
}

function setupSearchHandlers() {
    // Busca de produtos
    const productSearch = document.getElementById('productSearch');
    if (productSearch) {
        productSearch.addEventListener('input', debounce(handleProductSearch, 300));
    }
    
    // Busca de usuários
    const userSearch = document.getElementById('userSearch');
    if (userSearch) {
        userSearch.addEventListener('input', debounce(handleUserSearch, 300));
    }
}

function handleProductSearch(e) {
    const query = e.target.value.toLowerCase();
    const productCards = document.querySelectorAll('.product-card');
    
    productCards.forEach(card => {
        const title = card.querySelector('.product-title').textContent.toLowerCase();
        const description = card.querySelector('.product-description').textContent.toLowerCase();
        
        if (title.includes(query) || description.includes(query)) {
            card.style.display = 'block';
            card.classList.add('fade-in');
        } else {
            card.style.display = 'none';
        }
    });
}

function handleUserSearch(e) {
    const query = e.target.value.toLowerCase();
    const userRows = document.querySelectorAll('tr[data-user-id]');
    
    userRows.forEach(row => {
        const username = row.querySelector('h4').textContent.toLowerCase();
        const email = row.cells[1].textContent.toLowerCase();
        
        if (username.includes(query) || email.includes(query)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

function setupAnimations() {
    // Intersection Observer para animações
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
            }
        });
    }, observerOptions);
    
    // Observar elementos que devem animar
    const animatedElements = document.querySelectorAll('.card, .product-card, .hero-content');
    animatedElements.forEach(el => observer.observe(el));
}

function setupTheme() {
    // Detectar preferência do sistema
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const savedTheme = localStorage.getItem('theme');
    
    const theme = savedTheme || (prefersDark ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', theme);
}

function initializeTooltips() {
    // Adicionar tooltips simples
    const elementsWithTooltip = document.querySelectorAll('[title]');
    elementsWithTooltip.forEach(element => {
        element.addEventListener('mouseenter', showTooltip);
        element.addEventListener('mouseleave', hideTooltip);
    });
}

function showTooltip(e) {
    const element = e.target;
    const title = element.getAttribute('title');
    
    if (!title) return;
    
    // Criar tooltip
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = title;
    tooltip.style.cssText = `
        position: absolute;
        background: var(--gray-900);
        color: white;
        padding: 0.5rem;
        border-radius: 4px;
        font-size: 0.875rem;
        z-index: 1000;
        pointer-events: none;
        opacity: 0;
        transition: opacity 0.2s ease;
    `;
    
    document.body.appendChild(tooltip);
    
    // Posicionar tooltip
    const rect = element.getBoundingClientRect();
    tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
    tooltip.style.top = rect.top - tooltip.offsetHeight - 8 + 'px';
    
    // Mostrar tooltip
    requestAnimationFrame(() => {
        tooltip.style.opacity = '1';
    });
    
    // Remover title para evitar tooltip nativo
    element.setAttribute('data-title', title);
    element.removeAttribute('title');
}

function hideTooltip(e) {
    const element = e.target;
    const tooltip = document.querySelector('.tooltip');
    
    if (tooltip) {
        tooltip.remove();
    }
    
    // Restaurar title
    const title = element.getAttribute('data-title');
    if (title) {
        element.setAttribute('title', title);
        element.removeAttribute('data-title');
    }
}

function showAlert(message, type = 'info') {
    // Remover alertas existentes
    const existingAlerts = document.querySelectorAll('.alert-toast');
    existingAlerts.forEach(alert => alert.remove());
    
    // Criar novo alerta
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-toast`;
    alert.textContent = message;
    alert.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(alert);
    
    // Remover após 5 segundos
    setTimeout(() => {
        alert.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => alert.remove(), 300);
    }, 5000);
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// CSS adicional para animações
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    .nav-links.show {
        display: flex !important;
        flex-direction: column;
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        background: white;
        box-shadow: var(--shadow-lg);
        padding: 1rem;
    }
    
    @media (max-width: 768px) {
        .nav-links {
            display: none;
        }
    }
`;
document.head.appendChild(style);