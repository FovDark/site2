/**
 * FovDark Admin Panel - Edição de Produtos
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Admin JS carregado');
    
    // Elementos do DOM
    const productModal = document.getElementById('productModal');
    const productForm = document.getElementById('productForm');
    const productModalTitle = document.getElementById('productModalTitle');
    
    // Estado
    let currentEditingProductId = null;
    let isEditMode = false;
    
    // Função para obter cookie
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }
    
    // Função para mostrar alerta
    function showAlert(message, type = 'info') {
        alert(message); // Versão simples por enquanto
    }
    
    // Função para mostrar loading
    function showLoading(message) {
        console.log('Loading:', message);
    }
    
    // Função para esconder loading
    function hideLoading() {
        console.log('Loading hidden');
    }
    
    // Delegação de eventos para botões de editar
    document.addEventListener('click', function(e) {
        if (e.target.closest('.edit-product-btn')) {
            e.preventDefault();
            const btn = e.target.closest('.edit-product-btn');
            const productId = btn.getAttribute('data-product-id');
            console.log('Clicou para editar produto:', productId);
            editProduct(productId);
        }
        
        if (e.target.closest('.delete-product-btn')) {
            e.preventDefault();
            const btn = e.target.closest('.delete-product-btn');
            const productId = btn.getAttribute('data-product-id');
            const productName = btn.getAttribute('data-product-name');
            console.log('Clicou para deletar produto:', productId);
            deleteProduct(productId, productName);
        }
        
        // Fechar modal
        if (e.target.classList.contains('modal-close') || e.target.getAttribute('data-dismiss') === 'modal') {
            closeModal();
        }
    });
    
    // Fechar modal clicando fora
    window.addEventListener('click', function(e) {
        if (e.target === productModal) {
            closeModal();
        }
    });
    
    // Submit do formulário
    if (productForm) {
        productForm.addEventListener('submit', function(e) {
            e.preventDefault();
            saveProduct();
        });
    }
    
    // Função para editar produto
    async function editProduct(productId) {
        try {
            console.log('Iniciando edição do produto:', productId);
            showLoading('Carregando dados do produto...');
            
            const token = getCookie('access_token');
            console.log('Token encontrado:', !!token);
            
            const response = await fetch(`/admin/api/products/${productId}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include'
            });
            
            console.log('Response status:', response.status);
            hideLoading();
            
            if (response.ok) {
                const productData = await response.json();
                console.log('Dados do produto:', productData);
                openProductModal(productData);
            } else {
                const errorText = await response.text();
                console.error('Erro na API:', errorText);
                showAlert('Erro ao carregar produto: ' + errorText, 'error');
            }
        } catch (error) {
            hideLoading();
            console.error('Erro ao carregar produto:', error);
            showAlert('Erro ao carregar produto: ' + error.message, 'error');
        }
    }
    
    // Função para abrir modal
    function openProductModal(productData = null) {
        console.log('Abrindo modal com dados:', productData);
        
        isEditMode = productData !== null;
        currentEditingProductId = isEditMode ? productData.id : null;
        
        // Atualizar título
        if (productModalTitle) {
            productModalTitle.textContent = isEditMode ? 'Editar Produto' : 'Novo Produto';
        }
        
        // Limpar formulário
        if (productForm) {
            productForm.reset();
        }
        
        // Preencher dados se estiver editando
        if (isEditMode && productData) {
            const fields = {
                'productName': productData.name,
                'productCategory': productData.category_id,
                'productPrice': productData.price,
                'productDuration': productData.duration_days,
                'productDescription': productData.description,
                'productDownloadUrl': productData.download_url,
                'productRequirements': productData.requirements,
                'productTags': productData.tags,
                'productFeatured': productData.is_featured
            };
            
            Object.keys(fields).forEach(fieldId => {
                const element = document.getElementById(fieldId);
                if (element) {
                    if (element.type === 'checkbox') {
                        element.checked = fields[fieldId] || false;
                    } else {
                        element.value = fields[fieldId] || '';
                    }
                }
            });
        }
        
        // Mostrar modal
        if (productModal) {
            productModal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        }
    }
    
    // Função para fechar modal
    function closeModal() {
        if (productModal) {
            productModal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }
        isEditMode = false;
        currentEditingProductId = null;
        if (productForm) {
            productForm.reset();
        }
    }
    
    // Função para salvar produto
    async function saveProduct() {
        try {
            console.log('Salvando produto...');
            showLoading(isEditMode ? 'Atualizando produto...' : 'Criando produto...');
            
            const formData = new FormData(productForm);
            
            let url = '/api/admin/products';
            let method = 'POST';
            
            if (isEditMode) {
                url = `/admin/api/products/${currentEditingProductId}`;
                method = 'PUT';
            }
            
            console.log('URL:', url, 'Method:', method);
            
            const response = await fetch(url, {
                method: method,
                body: formData,
                credentials: 'include'
            });
            
            console.log('Save response status:', response.status);
            hideLoading();
            
            if (response.ok) {
                const result = await response.json();
                console.log('Produto salvo:', result);
                showAlert(isEditMode ? 'Produto atualizado com sucesso!' : 'Produto criado com sucesso!', 'success');
                closeModal();
                
                // Recarregar página
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                const errorText = await response.text();
                console.error('Erro ao salvar:', errorText);
                showAlert('Erro ao salvar produto: ' + errorText, 'error');
            }
        } catch (error) {
            hideLoading();
            console.error('Erro ao salvar produto:', error);
            showAlert('Erro ao salvar produto: ' + error.message, 'error');
        }
    }
    
    // Função para deletar produto
    async function deleteProduct(productId, productName) {
        if (!confirm(`Tem certeza que deseja deletar o produto "${productName}"?\n\nEsta ação não pode ser desfeita.`)) {
            return;
        }
        
        try {
            console.log('Deletando produto:', productId);
            showLoading('Deletando produto...');
            
            const response = await fetch(`/admin/api/products/${productId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include'
            });
            
            console.log('Delete response status:', response.status);
            hideLoading();
            
            if (response.ok) {
                showAlert('Produto deletado com sucesso!', 'success');
                
                // Remover linha da tabela
                const row = document.querySelector(`tr[data-product-id="${productId}"]`);
                if (row) {
                    row.remove();
                }
            } else {
                const errorText = await response.text();
                console.error('Erro ao deletar:', errorText);
                showAlert('Erro ao deletar produto: ' + errorText, 'error');
            }
        } catch (error) {
            hideLoading();
            console.error('Erro ao deletar produto:', error);
            showAlert('Erro ao deletar produto: ' + error.message, 'error');
        }
    }
    
    // Navegação entre abas
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
            const targetContent = document.getElementById(targetTab + '-tab');
            if (targetContent) {
                targetContent.classList.add('active');
            }
        });
    });
    
    console.log('Admin JS inicializado completamente');
});