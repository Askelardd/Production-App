// Função para alternar visibilidade da password
function togglePassword() {
    const passwordInput = document.getElementById('password');
    const eyeIcon = document.getElementById('eye-icon');
    
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        eyeIcon.innerHTML = '<path d="M12 7c2.76 0 5 2.24 5 5 0 .65-.13 1.26-.36 1.83l2.92 2.92c1.51-1.26 2.7-2.89 3.43-4.75-1.73-4.39-6-7.5-11-7.5-1.4 0-2.74.25-3.98.7l2.16 2.16C10.74 7.13 11.35 7 12 7zM2 4.27l2.28 2.28.46.46C3.08 8.3 1.78 10.02 1 12c1.73 4.39 6 7.5 11 7.5 1.55 0 3.03-.3 4.38-.84l.42.42L19.73 22 21 20.73 3.27 3 2 4.27zM7.53 9.8l1.55 1.55c-.05.21-.08.43-.08.65 0 1.66 1.34 3 3 3 .22 0 .44-.03.65-.08l1.55 1.55c-.67.33-1.41.53-2.2.53-2.76 0-5-2.24-5-5 0-.79.2-1.53.53-2.2zm4.31-.78l3.15 3.15.02-.16c0-1.66-1.34-3-3-3l-.17.01z"/>';
    } else {
        passwordInput.type = 'password';
        eyeIcon.innerHTML = '<path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/>';
    }
}

// Validação do campo first_name
function validateFirstName() {
    const firstNameInput = document.getElementById('first_name');
    const errorDiv = document.getElementById('first_name_error');
    const value = firstNameInput.value.trim();

    if (value.length === 0) {
        showError(errorDiv, 'O nome é obrigatório');
        return false;
    } else if (value.length > 30) {
        showError(errorDiv, 'O nome não pode ter mais de 30 caracteres');
        return false;
    } else {
        hideError(errorDiv);
        return true;
    }
}

// Validação do campo password
function validatePassword() {
    const passwordInput = document.getElementById('password');
    const errorDiv = document.getElementById('password_error');
    const value = passwordInput.value;

    if (value.length === 0) {
        showError(errorDiv, 'A palavra-passe é obrigatória');
        return false;
    } else if (value.length < 6) {
        showError(errorDiv, 'A palavra-passe deve ter pelo menos 6 caracteres');
        return false;
    } else if (value.length > 100) {
        showError(errorDiv, 'A palavra-passe não pode ter mais de 100 caracteres');
        return false;
    } else {
        hideError(errorDiv);
        return true;
    }
}

// Função para mostrar erro
function showError(errorDiv, message) {
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
}

// Função para esconder erro
function hideError(errorDiv) {
    errorDiv.classList.add('hidden');
}

// Validação completa do formulário
function validateForm() {
    const isFirstNameValid = validateFirstName();
    const isPasswordValid = validatePassword();
    
    return isFirstNameValid && isPasswordValid;
}

// Adicionar event listeners para validação em tempo real
document.getElementById('first_name').addEventListener('input', function() {
    if (this.value.length > 0) {
        validateFirstName();
    }
});

document.getElementById('password').addEventListener('input', function() {
    if (this.value.length > 0) {
        validatePassword();
    }
});
