/**
 * FovDark Admin Panel JavaScript
 * Gerenciamento de produtos, usuários e transações
 */

document.addEventListener('DOMContentLoaded', function() {
    // Elementos do DOM
    const productModal = document.getElementById('productModal');
    const productForm = document.getElementById('productForm');
    const productModalTitle = document.getElementById('productModalTitle');
    const addProductBtn = document.getElementById('addProductBtn');
    
    // Estado atual da edição
    let currentEditingProductId = null;
    let isEditMode = false;

    // Inicializar componentes
    initTabNavigation();
    initProductManagement();
    initUserManagement();
    initCategoryManagement();
    initTransactionManagement();
    
    /**
     * Navegação entre abas
     */
    function initTabNavigation() {
        const tabButtons = document.querySelectorAll('.tab-btn');
        const tabContents = document.querySelectorAll('.tab-content');
        
        tabButtons.forEach(btn => {
            btn.addEventListener('click', function() {
                const targetTab = this.getAttribute('data-tab');
                
                // Remover classes ativas
                tabButtons.forEach(b => b.classList.remove('active'));
                tabContents.forEach(c => c.classList.remove('active'));
                
                // Adicionar classe ativa
                this.classList.add('active');
                document.getElementById(targetTab + '-tab').classList.add('active');
            });
        });
    }
    
    /**
     * Gerenciamento de produtos
     */
    function initProductManagement() {
        // Botão adicionar produto
        if (addProductBtn) {
            addProductBtn.addEventListener('click', function() {
                openProductModal();
            });
        }
        
        // Botões de editar produto
        document.querySelectorAll('.edit-product-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const productId = this.getAttribute('data-product-id');
                editProduct(productId);
            });
        });
        
        // Botões de deletar produto
        document.querySelectorAll('.delete-product-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const productId = this.getAttribute('data-product-id');
                const productName = this.getAttribute('data-product-name');
                deleteProduct(productId, productName);
            });
        });
        
        // Form de produto
        if (productForm) {
            productForm.addEventListener('submit', function(e) {
                e.preventDefault();
                saveProduct();
            });
        }
        
        // Fechar modal
        document.querySelectorAll('.modal-close, [data-dismiss="modal"]').forEach(btn => {
            btn.addEventListener('click', function() {
                closeModal();
            });
        });
        
        // Fechar modal clicando fora
        window.addEventListener('click', function(e) {
            if (e.target.classList.contains('modal')) {
                closeModal();
            }
        });
    }
    
    /**
     * Abrir modal de produto
     */
    function openProductModal(productData = null) {
        isEditMode = productData !== null;
        currentEditingProductId = isEditMode ? productData.id : null;
        
        // Atualizar título do modal
        productModalTitle.textContent = isEditMode ? 'Editar Produto' : 'Novo Produto';
        
        // Limpar formulário
        productForm.reset();
        
        // Se estiver editando, preencher dados
        if (isEditMode && productData) {
            document.getElementById('productName').value = productData.name || '';
            document.getElementById('productCategory').value = productData.category_id || '';
            document.getElementById('productPrice').value = productData.price || '';
            document.getElementById('productDuration').value = productData.duration_days || 30;
            document.getElementById('productDescription').value = productData.description || '';
            document.getElementById('productDownloadUrl').value = productData.download_url || '';
            document.getElementById('productRequirements').value = productData.requirements || '';
            document.getElementById('productTags').value = productData.tags || '';
            document.getElementById('productFeatured').checked = productData.is_featured || false;
        }
        
        // Mostrar modal
        productModal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
    
    /**
     * Fechar modal
     */
    function closeModal() {
        productModal.style.display = 'none';
        document.body.style.overflow = 'auto';
        isEditMode = false;
        currentEditingProductId = null;
        productForm.reset();
    }
    
    /**
     * Editar produto
     */
    async function editProduct(productId) {
        try {
            showLoading('Carregando dados do produto...');
            
            const response = await fetch(`/admin/api/products/${productId}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            hideLoading();
            
            if (response.ok) {
                const productData = await response.json();
                openProductModal(productData);
            } else {
                const error = await response.json();
                showAlert('Erro ao carregar produto: ' + (error.detail || 'Erro desconhecido'), 'error');
            }
        } catch (error) {
            hideLoading();
            console.error('Erro ao carregar produto:', error);
            showAlert('Erro ao carregar produto. Tente novamente.', 'error');
        }
    }
    
    /**
     * Salvar produto (criar ou atualizar)
     */
    async function saveProduct() {
        try {
            showLoading(isEditMode ? 'Atualizando produto...' : 'Criando produto...');
            
            const formData = new FormData(productForm);
            
            let url = '/admin/api/products';
            let method = 'POST';
            
            if (isEditMode) {
                url = `/admin/api/products/${currentEditingProductId}`;
                method = 'PUT';
            }
            
            const response = await fetch(url, {
                method: method,
                body: formData
            });
            
            hideLoading();
            
            if (response.ok) {
                const result = await response.json();
                showAlert(isEditMode ? 'Produto atualizado com sucesso!' : 'Produto criado com sucesso!', 'success');
                closeModal();
                
                // Recarregar página para mostrar mudanças
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                const error = await response.json();
                showAlert('Erro ao salvar produto: ' + (error.detail || 'Erro desconhecido'), 'error');
            }
        } catch (error) {
            hideLoading();
            console.error('Erro ao salvar produto:', error);
            showAlert('Erro ao salvar produto. Tente novamente.', 'error');
        }
    }
    
    /**
     * Deletar produto
     */
    async function deleteProduct(productId, productName) {
        if (!confirm(`Tem certeza que deseja deletar o produto "${productName}"?\n\nEsta ação não pode ser desfeita.`)) {
            return;
        }
        
        try {
            showLoading('Deletando produto...');
            
            const response = await fetch(`/admin/api/products/${productId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            hideLoading();
            
            if (response.ok) {
                showAlert('Produto deletado com sucesso!', 'success');
                
                // Remover linha da tabela
                const row = document.querySelector(`tr[data-product-id="${productId}"]`);
                if (row) {
                    row.remove();
                }
            } else {
                const error = await response.json();
                showAlert('Erro ao deletar produto: ' + (error.detail || 'Erro desconhecido'), 'error');
            }
        } catch (error) {
            hideLoading();
            console.error('Erro ao deletar produto:', error);
            showAlert('Erro ao deletar produto. Tente novamente.', 'error');
        }
    }
    
    /**
     * Gerenciamento de usuários
     */
    function initUserManagement() {
        // Botões de visualizar usuário
        document.querySelectorAll('.view-user-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const userId = this.getAttribute('data-user-id');
                viewUser(userId);
            });
        });
        
        // Botões de ativar/desativar usuário
        document.querySelectorAll('.toggle-user-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const userId = this.getAttribute('data-user-id');
                const currentStatus = this.getAttribute('data-current-status') === 'true';
                toggleUserStatus(userId, !currentStatus);
            });
        });
    }
    
    /**
     * Visualizar detalhes do usuário
     */
    async function viewUser(userId) {
        try {
            showLoading('Carregando dados do usuário...');
            
            const response = await fetch(`/admin/api/users/${userId}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            hideLoading();
            
            if (response.ok) {
                const userData = await response.json();
                showUserDetails(userData);
            } else {
                const error = await response.json();
                showAlert('Erro ao carregar usuário: ' + (error.detail || 'Erro desconhecido'), 'error');
            }
        } catch (error) {
            hideLoading();
            console.error('Erro ao carregar usuário:', error);
            showAlert('Erro ao carregar usuário. Tente novamente.', 'error');
        }
    }
    
    /**
     * Mostrar detalhes do usuário em modal
     */
    function showUserDetails(userData) {
        const userModal = document.getElementById('userModal');
        const userDetails = document.getElementById('userDetails');
        
        userDetails.innerHTML = `
            <div class="user-details-grid">
                <div class="detail-section">
                    <h4>Informações Básicas</h4>
                    <div class="detail-item">
                        <label>Nome de usuário:</label>
                        <span>${userData.username}</span>
                    </div>
                    <div class="detail-item">
                        <label>Email:</label>
                        <span>${userData.email}</span>
                    </div>
                    <div class="detail-item">
                        <label>Status:</label>
                        <span class="status-badge ${userData.is_active ? 'active' : 'inactive'}">
                            ${userData.is_active ? 'Ativo' : 'Inativo'}
                        </span>
                    </div>
                    <div class="detail-item">
                        <label>Tipo:</label>
                        <span>${userData.is_admin ? 'Administrador' : 'Usuário'}</span>
                    </div>
                </div>
                
                <div class="detail-section">
                    <h4>Estatísticas</h4>
                    <div class="detail-item">
                        <label>Licenças ativas:</label>
                        <span>${userData.active_licenses_count || 0}</span>
                    </div>
                    <div class="detail-item">
                        <label>Total de compras:</label>
                        <span>${userData.total_purchases || 0}</span>
                    </div>
                    <div class="detail-item">
                        <label>Último login:</label>
                        <span>${userData.last_login || 'Nunca'}</span>
                    </div>
                    <div class="detail-item">
                        <label>Data de cadastro:</label>
                        <span>${userData.created_at || 'N/A'}</span>
                    </div>
                </div>
            </div>
        `;
        
        userModal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
    
    /**
     * Alternar status do usuário
     */
    async function toggleUserStatus(userId, newStatus) {
        try {
            showLoading('Atualizando status do usuário...');
            
            const response = await fetch(`/admin/api/users/${userId}/status`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    is_active: newStatus
                })
            });
            
            hideLoading();
            
            if (response.ok) {
                showAlert('Status do usuário atualizado com sucesso!', 'success');
                
                // Atualizar interface
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                const error = await response.json();
                showAlert('Erro ao atualizar status: ' + (error.detail || 'Erro desconhecido'), 'error');
            }
        } catch (error) {
            hideLoading();
            console.error('Erro ao atualizar status:', error);
            showAlert('Erro ao atualizar status. Tente novamente.', 'error');
        }
    }
    
    /**
     * Gerenciamento de categorias
     */
    function initCategoryManagement() {
        // Implementar quando necessário
    }
    
    /**
     * Gerenciamento de transações
     */
    function initTransactionManagement() {
        // Botões de visualizar transação
        document.querySelectorAll('.view-transaction-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const transactionId = this.getAttribute('data-transaction-id');
                viewTransaction(transactionId);
            });
        });
    }
    
    /**
     * Visualizar detalhes da transação
     */
    async function viewTransaction(transactionId) {
        // Implementar visualização de transação
        showAlert('Funcionalidade em desenvolvimento', 'info');
    }
    
    /**
     * Utilitários
     */
    function showLoading(message = 'Carregando...') {
        // Criar ou atualizar elemento de loading
        let loader = document.getElementById('globalLoader');
        if (!loader) {
            loader = document.createElement('div');
            loader.id = 'globalLoader';
            loader.className = 'global-loader';
            loader.innerHTML = `
                <div class="loader-content">
                    <div class="loader-spinner"></div>
                    <div class="loader-text">${message}</div>
                </div>
            `;
            document.body.appendChild(loader);
        } else {
            loader.querySelector('.loader-text').textContent = message;
        }
        
        loader.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
    
    function hideLoading() {
        const loader = document.getElementById('globalLoader');
        if (loader) {
            loader.style.display = 'none';
            document.body.style.overflow = 'auto';
        }
    }
    
    function showAlert(message, type = 'info') {
        // Criar elemento de alerta
        const alert = document.createElement('div');
        alert.className = `admin-alert alert-${type}`;
        alert.innerHTML = `
            <div class="alert-content">
                <div class="alert-icon">
                    <i class="fas ${getAlertIcon(type)}"></i>
                </div>
                <div class="alert-message">${message}</div>
                <button class="alert-close">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        // Adicionar ao body
        document.body.appendChild(alert);
        
        // Auto-remover após 5 segundos
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 5000);
        
        // Botão de fechar
        alert.querySelector('.alert-close').addEventListener('click', () => {
            alert.remove();
        });
        
        // Animar entrada
        setTimeout(() => {
            alert.classList.add('show');
        }, 100);
    }
    
    function getAlertIcon(type) {
        switch (type) {
            case 'success': return 'fa-check-circle';
            case 'error': return 'fa-exclamation-circle';
            case 'warning': return 'fa-exclamation-triangle';
            default: return 'fa-info-circle';
        }
    }
});

// Estilos CSS adicionais para componentes JavaScript
const adminStyles = `
    .global-loader {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.8);
        display: none;
        justify-content: center;
        align-items: center;
        z-index: 10000;
    }
    
    .loader-content {
        text-align: center;
        color: white;
    }
    
    .loader-spinner {
        width: 40px;
        height: 40px;
        border: 4px solid rgba(255, 255, 255, 0.3);
        border-top: 4px solid #007bff;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin: 0 auto 15px;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    .admin-alert {
        position: fixed;
        top: 20px;
        right: 20px;
        max-width: 400px;
        background: white;
        border-radius: 8px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
        z-index: 9999;
        transform: translateX(100%);
        transition: transform 0.3s ease;
    }
    
    .admin-alert.show {
        transform: translateX(0);
    }
    
    .alert-content {
        display: flex;
        align-items: center;
        padding: 15px;
        gap: 12px;
    }
    
    .alert-icon {
        font-size: 20px;
    }
    
    .alert-success .alert-icon { color: #28a745; }
    .alert-error .alert-icon { color: #dc3545; }
    .alert-warning .alert-icon { color: #ffc107; }
    .alert-info .alert-icon { color: #007bff; }
    
    .alert-message {
        flex: 1;
        font-weight: 500;
    }
    
    .alert-close {
        background: none;
        border: none;
        font-size: 16px;
        color: #666;
        cursor: pointer;
        padding: 5px;
    }
    
    .alert-close:hover {
        color: #333;
    }
    
    .user-details-grid {
        display: grid;
        gap: 20px;
    }
    
    .detail-section h4 {
        margin-bottom: 15px;
        color: #333;
        border-bottom: 2px solid #007bff;
        padding-bottom: 5px;
    }
    
    .detail-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px solid #eee;
    }
    
    .detail-item:last-child {
        border-bottom: none;
    }
    
    .detail-item label {
        font-weight: 600;
        color: #555;
    }
    
    .detail-item span {
        color: #333;
    }
`;

// Adicionar estilos ao documento
const styleSheet = document.createElement('style');
styleSheet.textContent = adminStyles;
document.head.appendChild(styleSheet);