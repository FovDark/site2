// FovDark - JavaScript Principal
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar componentes
    initMobileMenu();
    initUserMenu();
    initFormValidation();
    initLoadingStates();
    initNotifications();
    
    console.log('FovDark carregado com sucesso!');
});

// Menu Mobile
function initMobileMenu() {
    const mobileToggle = document.getElementById('mobileToggle');
    const navLinks = document.querySelector('.nav-links');
    
    if (mobileToggle && navLinks) {
        mobileToggle.addEventListener('click', function() {
            navLinks.classList.toggle('show');
            const icon = this.querySelector('i');
            icon.classList.toggle('fa-bars');
            icon.classList.toggle('fa-times');
        });
    }
}

// Menu do Usuário
function initUserMenu() {
    const userMenuToggle = document.querySelector('.user-menu-toggle');
    const userMenuDropdown = document.querySelector('.user-menu-dropdown');
    
    if (userMenuToggle && userMenuDropdown) {
        userMenuToggle.addEventListener('click', function(e) {
            e.preventDefault();
            userMenuDropdown.style.display = 
                userMenuDropdown.style.display === 'block' ? 'none' : 'block';
        });
        
        // Fechar menu ao clicar fora
        document.addEventListener('click', function(e) {
            if (!userMenuToggle.contains(e.target)) {
                userMenuDropdown.style.display = 'none';
            }
        });
    }
}

// Validação de Formulários
function initFormValidation() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn && !submitBtn.disabled) {
                // Adicionar loading
                addLoadingState(submitBtn);
                
                // Validações específicas por formulário
                if (form.id === 'loginForm') {
                    return validateLoginForm(form, e);
                } else if (form.id === 'registerForm') {
                    return validateRegisterForm(form, e);
                }
            }
        });
    });
}

// Validação Login
function validateLoginForm(form, e) {
    const username = form.querySelector('#username')?.value;
    const password = form.querySelector('#password')?.value;
    
    if (!username || !password) {
        e.preventDefault();
        showNotification('Por favor, preencha todos os campos', 'danger');
        removeLoadingState(form.querySelector('button[type="submit"]'));
        return false;
    }
    
    return true;
}

// Validação Registro
function validateRegisterForm(form, e) {
    const username = form.querySelector('#username')?.value;
    const email = form.querySelector('#email')?.value;
    const password = form.querySelector('#password')?.value;
    const confirmPassword = form.querySelector('#confirm_password')?.value;
    const acceptTerms = form.querySelector('input[name="accept_terms"]')?.checked;
    
    // Validar campos obrigatórios
    if (!username || !email || !password || !confirmPassword) {
        e.preventDefault();
        showNotification('Por favor, preencha todos os campos obrigatórios', 'danger');
        removeLoadingState(form.querySelector('button[type="submit"]'));
        return false;
    }
    
    // Validar senhas
    if (password !== confirmPassword) {
        e.preventDefault();
        showNotification('As senhas não coincidem', 'danger');
        removeLoadingState(form.querySelector('button[type="submit"]'));
        return false;
    }
    
    // Validar força da senha
    if (password.length < 6) {
        e.preventDefault();
        showNotification('A senha deve ter pelo menos 6 caracteres', 'danger');
        removeLoadingState(form.querySelector('button[type="submit"]'));
        return false;
    }
    
    // Validar termos
    if (!acceptTerms) {
        e.preventDefault();
        showNotification('Você deve aceitar os termos de uso', 'danger');
        removeLoadingState(form.querySelector('button[type="submit"]'));
        return false;
    }
    
    return true;
}

// Estados de Loading
function initLoadingStates() {
    // Adicionar loading aos links de navegação
    const navLinks = document.querySelectorAll('a[href^="/"]');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            if (this.target !== '_blank') {
                addLoadingState(this);
            }
        });
    });
}

function addLoadingState(element) {
    if (!element) return;
    
    element.disabled = true;
    element.style.opacity = '0.7';
    
    // Salvar conteúdo original
    if (!element.dataset.originalContent) {
        element.dataset.originalContent = element.innerHTML;
    }
    
    // Adicionar spinner
    const spinner = '<span class="loading"></span>';
    if (element.tagName === 'BUTTON') {
        element.innerHTML = spinner + ' Carregando...';
    } else {
        element.style.position = 'relative';
        element.innerHTML += ' ' + spinner;
    }
}

function removeLoadingState(element) {
    if (!element) return;
    
    element.disabled = false;
    element.style.opacity = '';
    
    if (element.dataset.originalContent) {
        element.innerHTML = element.dataset.originalContent;
    }
}

// Sistema de Notificações
function initNotifications() {
    // Verificar se há mensagens flash no servidor
    const flashMessages = document.querySelector('.flash-messages');
    if (flashMessages) {
        const messages = flashMessages.querySelectorAll('.alert');
        messages.forEach(message => {
            const type = message.classList.contains('alert-success') ? 'success' :
                        message.classList.contains('alert-danger') ? 'danger' :
                        message.classList.contains('alert-warning') ? 'warning' : 'info';
            
            showNotification(message.textContent.trim(), type);
        });
        
        // Remover mensagens originais
        flashMessages.remove();
    }
}

function showNotification(message, type = 'info', duration = 5000) {
    // Remover notificações existentes
    const existing = document.querySelectorAll('.notification-toast');
    existing.forEach(toast => toast.remove());
    
    // Criar nova notificação
    const toast = document.createElement('div');
    toast.className = `notification-toast alert alert-${type}`;
    toast.innerHTML = `
        <div class="notification-content">
            <i class="fas ${getNotificationIcon(type)}"></i>
            <span>${message}</span>
            <button class="notification-close" onclick="this.parentElement.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    
    // Estilos da notificação
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        max-width: 500px;
        animation: slideInRight 0.3s ease;
        border-left: 4px solid var(--${type === 'danger' ? 'danger' : type === 'success' ? 'success' : type === 'warning' ? 'warning' : 'info'}-color);
    `;
    
    document.body.appendChild(toast);
    
    // Auto remover
    if (duration > 0) {
        setTimeout(() => {
            toast.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
}

function getNotificationIcon(type) {
    switch(type) {
        case 'success': return 'fa-check-circle';
        case 'danger': return 'fa-exclamation-circle';
        case 'warning': return 'fa-exclamation-triangle';
        case 'info': return 'fa-info-circle';
        default: return 'fa-info-circle';
    }
}

// Utilitários
function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    const toggle = input.nextElementSibling;
    const icon = toggle.querySelector('i');
    
    if (input.type === 'password') {
        input.type = 'text';
        icon.className = 'fas fa-eye-slash';
    } else {
        input.type = 'password';
        icon.className = 'fas fa-eye';
    }
}

function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}

function formatDate(date) {
    return new Intl.DateTimeFormat('pt-BR').format(new Date(date));
}

// AJAX Helper
async function makeRequest(url, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        }
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(url, options);
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.message || 'Erro na requisição');
        }
        
        return result;
    } catch (error) {
        console.error('Erro na requisição:', error);
        showNotification(error.message || 'Erro na requisição', 'danger');
        throw error;
    }
}

// Funcionalidades específicas
function purchaseProduct(productId) {
    if (!confirm('Confirma a compra deste produto?')) {
        return;
    }
    
    const btn = event.target.closest('.btn');
    addLoadingState(btn);
    
    makeRequest(`/api/purchase/${productId}`, 'POST')
        .then(response => {
            showNotification('Produto adicionado ao carrinho!', 'success');
            // Redirecionar para checkout ou atualizar página
            setTimeout(() => {
                window.location.href = '/checkout';
            }, 1500);
        })
        .catch(error => {
            removeLoadingState(btn);
        });
}

function downloadProduct(productId) {
    const btn = event.target.closest('.btn');
    addLoadingState(btn);
    
    window.location.href = `/api/download/${productId}`;
    
    setTimeout(() => {
        removeLoadingState(btn);
    }, 2000);
}

// Animações CSS
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    .notification-toast {
        box-shadow: var(--shadow-xl);
        border-radius: var(--border-radius);
    }
    
    .notification-content {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }
    
    .notification-close {
        background: none;
        border: none;
        color: inherit;
        cursor: pointer;
        opacity: 0.7;
        margin-left: auto;
    }
    
    .notification-close:hover {
        opacity: 1;
    }
    
    .nav-links.show {
        display: flex;
        flex-direction: column;
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        background: white;
        padding: 1rem;
        box-shadow: var(--shadow-lg);
        border-radius: 0 0 var(--border-radius) var(--border-radius);
    }
    
    @media (max-width: 768px) {
        .nav-links {
            display: none;
        }
    }
`;

document.head.appendChild(style);